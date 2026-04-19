import queue
import threading
from typing import Callable, Optional, cast
from events import Events
from beartype import beartype
from parrot.director.frame import FrameSignal
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode, parse_vj_mode_string
from parrot.director.themes import themes, get_theme_by_name
from parrot.gl_display_mode import DISPLAY_MODE_CYCLE, EditorDisplayMode
from parrot.patch_bay import venues
from parrot_cloud.domain import ControlState, RuntimeBootstrap, VenueSnapshot, VenueSummary
from parrot_cloud.fixture_catalog import (
    build_runtime_fixture_groups,
    update_runtime_fixture_transforms,
)


@beartype
class State:
    def __init__(self):
        self.events = Events()

        # Default values
        self._mode = Mode.chill  # Default mode
        self._vj_mode = VJMode.prom_dmack  # Default VJ mode
        self._hype = 30
        self._theme = themes[0]
        self._venue = venues.dmack
        self._manual_fixture_dimmers: dict[str, float] = {}
        self._hype_limiter = False  # Start with hype limiter OFF
        self._show_waveform = True  # New property for waveform visibility
        self._editor_display_mode = EditorDisplayMode.DMX_HEATMAP
        self._available_venues = []
        self._runtime_venue_snapshot: Optional[VenueSnapshot] = None
        self._runtime_patch = None
        self._runtime_manual_group = None
        self._remote_control_state_updater: Optional[
            Callable[[dict[str, object]], None]
        ] = None
        self._suppress_remote_control_sync = False

        # Queue for GUI updates from other threads
        self._gui_update_queue = queue.Queue()

        # Initialize signal states
        from parrot.director.signal_states import SignalStates

        self.signal_states = SignalStates()
        # Auto-release timers for one-shot remote pulses (see ``set_effect_thread_safe``).
        self._effect_release_timers: dict[FrameSignal, threading.Timer] = {}


    @property
    def mode(self):
        return self._mode

    def set_mode(self, value: Mode):
        if self._mode == value:
            return

        self._mode = value
        self.events.on_mode_change(self._mode)
        self._push_remote_control_state({"mode": value.name})

    def set_mode_thread_safe(self, value: Mode):
        """Set the mode (web server runs on main thread; no extra threading needed)."""
        self.set_mode(value)

    def _dispatch_shift(self, target: str) -> None:
        """Fire the event matching a remote shift target.

        Subscribers (see ``gl_window_app``) register the director's
        ``shift_lighting_only`` / ``shift_color_scheme`` / ``shift_vj_only``
        methods against these events. ``Events()`` auto-creates event attributes
        on access, so firing with zero subscribers is a harmless no-op.
        """
        event = getattr(self.events, f"on_shift_{target}_request")
        event()

    def _cancel_effect_release_timer(self, signal: FrameSignal) -> None:
        timer = self._effect_release_timers.pop(signal, None)
        if timer is not None:
            timer.cancel()

    def _release_effect_signal_after_pulse(self, signal: FrameSignal) -> None:
        self._effect_release_timers.pop(signal, None)
        self.signal_states.set_signal(signal, 0.0)

    def set_effect_thread_safe(self, effect: str, value: Optional[float] = None):
        """Drive a FrameSignal from the remote / websocket.

        * ``value is None`` — one-shot pulse (1.0 for ~0.35s), same as a quick tap
          when the mobile UI sends the legacy pulse request.
        * ``value is 1.0`` or ``0.0`` — explicit hold / release (no timer). Used
          when the remote holds a button: high until ``value=0``.
        """
        signal = FrameSignal[effect]
        self._cancel_effect_release_timer(signal)

        if value is None:
            self.signal_states.set_signal(signal, 1.0)
            timer = threading.Timer(
                0.35,
                lambda s=signal: self._release_effect_signal_after_pulse(s),
            )
            self._effect_release_timers[signal] = timer
            timer.start()
        else:
            v = max(0.0, min(1.0, float(value)))
            self.signal_states.set_signal(signal, v)

    @property
    def vj_mode(self):
        return self._vj_mode

    def set_vj_mode(self, value: VJMode):
        if self._vj_mode == value:
            return

        self._vj_mode = value
        self.events.on_vj_mode_change(self._vj_mode)
        self._push_remote_control_state({"vj_mode": value.value})

    def set_vj_mode_thread_safe(self, value: VJMode):
        """Set the VJ mode (web server runs on main thread; no extra threading needed)."""
        self.set_vj_mode(value)

    @property
    def hype(self):
        return self._hype

    def set_hype(self, value: float):
        if self._hype == value:
            return

        self._hype = value
        self.events.on_hype_change(self._hype)

    @property
    def theme(self):
        return self._theme

    def set_theme(self, value):
        if self._theme == value:
            return

        self._theme = value
        self.events.on_theme_change(self._theme)
        theme_name = getattr(value, "name", None)
        if theme_name:
            self._push_remote_control_state({"theme_name": str(theme_name)})

    @property
    def venue(self):
        return self._venue

    def set_venue(self, value):
        if self._venue == value:
            return

        self._venue = value
        venue_id = getattr(value, "id", None)
        self.events.on_venue_change(self._venue)
        if venue_id:
            self._push_remote_control_state({"active_venue_id": str(venue_id)})

    @property
    def available_venues(self):
        return self._available_venues

    @property
    def runtime_venue_snapshot(self) -> Optional[VenueSnapshot]:
        return self._runtime_venue_snapshot

    @property
    def runtime_patch(self):
        return self._runtime_patch

    @property
    def runtime_manual_group(self):
        return self._runtime_manual_group

    def set_remote_control_state_updater(
        self, handler: Callable[[dict[str, object]], None]
    ):
        self._remote_control_state_updater = handler

    def _push_remote_control_state(self, patch: dict[str, object]) -> None:
        if self._suppress_remote_control_sync:
            return
        if self._remote_control_state_updater is None:
            return
        self._remote_control_state_updater(patch)

    def _display_mode_to_control_state(self, mode: EditorDisplayMode) -> str:
        if mode == EditorDisplayMode.FIXTURE_SCENE:
            return "venue"
        return mode.value

    def _display_mode_from_control_state(self, value: str) -> EditorDisplayMode:
        if value == "venue":
            return EditorDisplayMode.FIXTURE_SCENE
        try:
            return EditorDisplayMode(value)
        except ValueError:
            return EditorDisplayMode.DMX_HEATMAP

    def queue_runtime_bootstrap(self, bootstrap: RuntimeBootstrap):
        self._gui_update_queue.put(("runtime_bootstrap", bootstrap))

    def queue_runtime_venues(self, venues: list[VenueSummary]):
        self._gui_update_queue.put(("runtime_venues", venues))

    def queue_runtime_snapshot(self, snapshot: VenueSnapshot):
        self._gui_update_queue.put(("runtime_snapshot", snapshot))

    def queue_runtime_control_state(self, control_state: ControlState):
        self._gui_update_queue.put(("runtime_control_state", control_state))

    def queue_runtime_effect(self, effect: str, value: Optional[float] = None):
        self._gui_update_queue.put(("runtime_effect", (effect, value)))

    def queue_runtime_shift(self, target: str):
        """Queue a remote-triggered ``director.shift_<target>()`` request.

        Dispatched on the main thread via ``process_gui_updates`` so director
        calls happen in the same context as keyboard-driven shifts.
        """
        self._gui_update_queue.put(("runtime_shift", target))

    def _apply_runtime_venue_summaries(self, venues: list[VenueSummary]) -> None:
        self._available_venues = list(venues)
        self.events.on_available_venues_change(self._available_venues)

    def apply_runtime_bootstrap(self, bootstrap: RuntimeBootstrap):
        self._apply_control_state(bootstrap.control_state)
        self._apply_runtime_venue_summaries(list(bootstrap.venues))
        if bootstrap.active_venue is not None:
            self._apply_runtime_snapshot(bootstrap.active_venue)

    def _apply_control_state(self, control_state: ControlState):
        self._suppress_remote_control_sync = True
        try:
            next_mode = Mode[control_state.mode]
            if self._mode != next_mode:
                self._mode = next_mode
                self.events.on_mode_change(self._mode)

            next_vj_mode = parse_vj_mode_string(control_state.vj_mode)
            if self._vj_mode != next_vj_mode:
                self._vj_mode = next_vj_mode
                self.events.on_vj_mode_change(self._vj_mode)

            next_mfd = dict(control_state.manual_fixture_dimmers)
            if self._manual_fixture_dimmers != next_mfd:
                self._manual_fixture_dimmers = next_mfd

            next_hype_limiter = bool(control_state.hype_limiter)
            if self._hype_limiter != next_hype_limiter:
                self._hype_limiter = next_hype_limiter
                self.events.on_hype_limiter_change(self._hype_limiter)

            next_show_waveform = bool(control_state.show_waveform)
            if self._show_waveform != next_show_waveform:
                self._show_waveform = next_show_waveform
                self.events.on_show_waveform_change(self._show_waveform)

            display_mode = str(control_state.display_mode or "dmx_heatmap")
            next_display = self._display_mode_from_control_state(display_mode)
            if self._editor_display_mode != next_display:
                self._editor_display_mode = next_display
                self.events.on_show_fixture_mode_change(self.show_fixture_mode)

            try:
                next_theme = get_theme_by_name(control_state.theme_name)
            except ValueError:
                next_theme = self._theme
            if self._theme != next_theme:
                self._theme = next_theme
                self.events.on_theme_change(self._theme)
        finally:
            self._suppress_remote_control_sync = False

    def _apply_runtime_snapshot(self, snapshot: VenueSnapshot):
        previous_snapshot = self._runtime_venue_snapshot
        venue_changed = (
            previous_snapshot is None
            or previous_snapshot.summary.id != snapshot.summary.id
        )
        self._runtime_venue_snapshot = snapshot
        self._venue = snapshot.summary
        structure_changed = venue_changed
        if not venue_changed and self._runtime_patch is not None:
            updated_in_place = update_runtime_fixture_transforms(
                self._runtime_patch,
                self._runtime_manual_group,
                snapshot,
            )
            structure_changed = not updated_in_place
        if structure_changed:
            self._runtime_patch, self._runtime_manual_group = build_runtime_fixture_groups(
                snapshot
            )
        if venue_changed or structure_changed:
            self.events.on_venue_change(self._venue)
        else:
            self.events.on_runtime_scene_change(snapshot)

    @property
    def manual_fixture_dimmers(self) -> dict[str, float]:
        return self._manual_fixture_dimmers

    def merge_manual_fixture_dimmers(self, patch: dict[str, float]) -> None:
        """Merge dimmer levels (0–1) by fixture id and sync to Parrot Cloud."""
        next_map = dict(self._manual_fixture_dimmers)
        applied: dict[str, float] = {}
        for k, v in patch.items():
            key = str(k)
            vv = max(0.0, min(1.0, float(v)))
            if next_map.get(key) != vv:
                next_map[key] = vv
                applied[key] = vv
        if not applied:
            return
        self._manual_fixture_dimmers = next_map
        self._push_remote_control_state({"manual_fixture_dimmers": applied})

    @property
    def hype_limiter(self):
        return self._hype_limiter

    def set_hype_limiter(self, value):
        if self._hype_limiter == value:
            return

        self._hype_limiter = value
        self.events.on_hype_limiter_change(self._hype_limiter)
        self._push_remote_control_state({"hype_limiter": bool(value)})

    @property
    def show_waveform(self):
        return self._show_waveform

    def set_show_waveform(self, value):
        if self._show_waveform == value:
            return

        self._show_waveform = value
        self.events.on_show_waveform_change(self._show_waveform)
        self._push_remote_control_state({"show_waveform": bool(value)})

    @property
    def editor_display_mode(self) -> EditorDisplayMode:
        return self._editor_display_mode

    def set_editor_display_mode(self, value: EditorDisplayMode) -> None:
        if self._editor_display_mode == value:
            return

        self._editor_display_mode = value
        self.events.on_show_fixture_mode_change(self.show_fixture_mode)
        self._push_remote_control_state(
            {"display_mode": self._display_mode_to_control_state(self._editor_display_mode)}
        )

    def cycle_editor_display_mode(self) -> None:
        order = DISPLAY_MODE_CYCLE
        idx = order.index(self._editor_display_mode)
        self.set_editor_display_mode(order[(idx + 1) % len(order)])

    @property
    def show_fixture_mode(self) -> bool:
        return self._editor_display_mode == EditorDisplayMode.FIXTURE_SCENE

    def set_show_fixture_mode(self, value: bool) -> None:
        self.set_editor_display_mode(
            EditorDisplayMode.FIXTURE_SCENE if value else EditorDisplayMode.DMX_HEATMAP
        )

    def process_gui_updates(self):
        """Drain queued runtime updates on the main thread.

        Called every frame by the GL loop so WebSocket/bootstrap events land
        on the main thread (where OpenGL + pyglet are safe to touch).
        """
        try:
            while True:
                update_type, value = self._gui_update_queue.get_nowait()

                if update_type == "runtime_bootstrap":
                    self.apply_runtime_bootstrap(value)
                elif update_type == "runtime_venues":
                    self._apply_runtime_venue_summaries(list(value))
                elif update_type == "runtime_snapshot":
                    self._apply_runtime_snapshot(value)
                elif update_type == "runtime_control_state":
                    self._apply_control_state(value)
                elif update_type == "runtime_effect":
                    eff, val = cast(tuple[str, Optional[float]], value)
                    self.set_effect_thread_safe(eff, value=val)
                elif update_type == "runtime_shift":
                    self._dispatch_shift(value)

                self._gui_update_queue.task_done()

        except queue.Empty:
            pass
