from __future__ import annotations

import json
import threading
import time
from urllib.parse import urlparse

import requests
import websocket
from beartype import beartype

from parrot.runtime_fixture_state import build_fixture_runtime_payload
from parrot.state import State
from parrot_cloud.domain import ControlState, RuntimeBootstrap, VenueSnapshot, VenueSummary


def _to_websocket_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}/ws/venue-updates"


@beartype
class RuntimeVenueClient:
    def __init__(self, state: State, base_url: str):
        self.state = state
        self.base_url = base_url.rstrip("/")
        self.ws_url = _to_websocket_url(self.base_url)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._fixture_push_lock = threading.Lock()
        self._last_fixture_push_mono = 0.0
        self._last_fixture_payload_json: str | None = None
        self.state.set_remote_control_state_updater(self.update_control_state)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def maybe_push_fixture_runtime_state(self) -> None:
        if self._stop_event.is_set():
            return
        patch = self.state.runtime_patch
        if patch is None:
            return
        now = time.monotonic()
        if now - self._last_fixture_push_mono < 0.1:
            return
        payload = build_fixture_runtime_payload(patch, self.state.runtime_manual_group)
        encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        with self._fixture_push_lock:
            if encoded == self._last_fixture_payload_json:
                return
            self._last_fixture_payload_json = encoded
        self._last_fixture_push_mono = now
        try:
            requests.post(
                f"{self.base_url}/api/runtime/fixture-state",
                json=payload,
                timeout=2.0,
            ).raise_for_status()
        except Exception:
            with self._fixture_push_lock:
                self._last_fixture_payload_json = None

    def push_vj_preview_jpeg(self, jpeg_bytes: bytes) -> bool:
        """Upload a JPEG snapshot of the VJ framebuffer (caller controls cadence, e.g. every 30s)."""
        if self._stop_event.is_set():
            return False
        try:
            requests.post(
                f"{self.base_url}/api/runtime/vj-preview",
                data=jpeg_bytes,
                headers={"Content-Type": "image/jpeg"},
                timeout=15.0,
            ).raise_for_status()
            return True
        except Exception:
            return False

    def bootstrap(self) -> None:
        response = requests.get(f"{self.base_url}/api/runtime/bootstrap", timeout=5)
        response.raise_for_status()
        bootstrap = RuntimeBootstrap.from_dict(response.json())
        self.state.queue_runtime_bootstrap(bootstrap)

    def update_control_state(self, patch: dict[str, object]) -> None:
        try:
            requests.patch(
                f"{self.base_url}/api/control-state",
                json=patch,
                timeout=5,
            ).raise_for_status()
        except Exception as exc:
            print(f"Failed to update remote control state: {exc}")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.bootstrap()
                self._run_websocket_loop()
            except Exception as exc:
                print(f"Venue service sync unavailable: {exc}")
                time.sleep(2.0)

    def _run_websocket_loop(self) -> None:
        def on_message(_, message: str):
            payload = json.loads(message)
            message_type = payload.get("type")
            if message_type == "bootstrap":
                bootstrap = RuntimeBootstrap.from_dict(payload["data"])
                self.state.queue_runtime_venues(list(bootstrap.venues))
                if bootstrap.active_venue is not None:
                    self.state.queue_runtime_snapshot(bootstrap.active_venue)
            elif message_type == "venues":
                venues = [
                    VenueSummary.from_dict(dict(venue_data))
                    for venue_data in payload.get("data", {}).get("venues", [])
                ]
                self.state.queue_runtime_venues(venues)
            elif message_type == "venue_snapshot":
                snapshot_data = payload.get("data")
                if snapshot_data:
                    snapshot = VenueSnapshot.from_dict(dict(snapshot_data))
                    if snapshot.summary.active:
                        self.state.queue_runtime_snapshot(snapshot)
            elif message_type == "control_state":
                control_state = ControlState.from_dict(dict(payload.get("data", {})))
                self.state.queue_runtime_control_state(control_state)
            elif message_type == "effect":
                effect = str(payload.get("data", {}).get("effect", ""))
                if effect:
                    self.state.queue_runtime_effect(effect)
            elif message_type == "shift_lighting_only":
                self.state.queue_runtime_shift("lighting_only")
            elif message_type == "shift_color_scheme":
                self.state.queue_runtime_shift("color_scheme")
            elif message_type == "shift_vj_only":
                self.state.queue_runtime_shift("vj_only")

        def on_error(_, error):
            print(f"Venue websocket error: {error}")

        def on_close(_, __, ___):
            pass

        ws_app = websocket.WebSocketApp(
            self.ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        while not self._stop_event.is_set():
            ws_app.run_forever(ping_interval=20, ping_timeout=10)
            if not self._stop_event.is_set():
                time.sleep(1.0)
