from __future__ import annotations

import time
from urllib.parse import urlparse

import logging
from beartype import beartype

from parrot.audio.audio_analyzer import AudioAnalyzer
from parrot.director.director import Director
from parrot.runtime_venue_client import RuntimeVenueClient
from parrot.state import State
from parrot.utils.dmx_utils import get_controller


logger = logging.getLogger(__name__)


@beartype
class HeadlessDmxBridge:
    """Audio-reactive DMX runtime without a desktop GL window."""

    def __init__(self, args):
        self.args = args
        self.state = State()
        self.runtime_client: RuntimeVenueClient | None = None
        self.should_stop = False

        venue_service_url = getattr(args, "venue_service_url", None)
        if venue_service_url:
            self.runtime_client = RuntimeVenueClient(self.state, venue_service_url)
            try:
                self.runtime_client.bootstrap()
                self.state.process_gui_updates()
            except Exception as exc:
                logger.warning("Venue service bootstrap failed: %s", exc)
            self.runtime_client.start()

        self.audio_analyzer = AudioAnalyzer(self.state.signal_states)
        self.director = Director(
            self.state,
            interpretation_tree_publisher=(
                self.runtime_client.push_interpretation_tree
                if self.runtime_client is not None
                else None
            ),
        )
        self.dmx = get_controller(self.state.venue)
        self.state.events.on_venue_change += lambda _venue: self._refresh_dmx_controller()
        self.state.events.on_shift_lighting_only_request += self.director.shift_lighting_only
        self.state.events.on_shift_color_scheme_request += self.director.shift_color_scheme
        self.state.events.on_shift_vj_only_request += self.director.shift_vj_only

        if not getattr(self.args, "no_web", False):
            from parrot.api import start_web_server

            editor_port = urlparse(venue_service_url).port if venue_service_url else 4041
            start_web_server(
                self.state,
                director=self.director,
                port=getattr(self.args, "web_port", 4040),
                editor_port=editor_port or 4041,
            )

    def _refresh_dmx_controller(self) -> None:
        self.dmx = get_controller(self.state.venue)

    def stop(self) -> None:
        self.should_stop = True
        if self.runtime_client is not None:
            self.runtime_client.stop()

    def run(self) -> None:
        try:
            while not self.should_stop:
                self.state.process_gui_updates()
                frame = self.audio_analyzer.analyze_audio()
                if frame is None:
                    time.sleep(0.01)
                    continue
                self.director.step(frame)
                self.director.render(self.dmx)
                if self.runtime_client is not None:
                    self.runtime_client.maybe_push_fixture_runtime_state(
                        self.director.scheme.render(),
                        output_override_by_spec_id=self.director.output_fixture_overrides_by_spec_id(),
                    )
        except (KeyboardInterrupt, SystemExit):
            self.should_stop = True
        finally:
            self.stop()
            self.audio_analyzer.cleanup()


def run_headless_dmx_bridge(args) -> None:
    HeadlessDmxBridge(args).run()
