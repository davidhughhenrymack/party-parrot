#!/usr/bin/env python3

import time
from beartype import beartype

from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.static_color import StaticColor
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.layer_compose import LayerCompose
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.camera_zoom import CameraZoom


@beartype
class VJDirector:
    """
    Director for the VJ system that manages video nodes and coordinates with the main director.
    Handles the visual composition and effects that respond to audio and lighting.
    """

    def __init__(self):
        # Create a pulsing video canvas by default
        video_player = VideoPlayer(fn_group="bg")
        pulsing_video = BrightnessPulse(video_player)
        red = StaticColor(color=(1.0, 0.0, 0.0))
        red_pulse = BrightnessPulse(red, signal=FrameSignal.freq_high)
        red_pulse = SaturationPulse(red_pulse, signal=FrameSignal.freq_low)

        text_renderer = TextRenderer(
            text="DEAD\nSEXY", font_name="The Sonnyfive", font_size=120
        )
        text_renderer = BrightnessPulse(text_renderer, signal=FrameSignal.freq_high)
        text_renderer = CameraZoom(text_renderer, signal=FrameSignal.freq_low)

        self.canvas: BaseInterpretationNode = CameraZoom(pulsing_video)

        self.last_shift_time = time.time()
        self.shift_count = 0
        self.window = None  # Will be set by the window manager

        # Thread-safe frame data storage
        self._latest_frame = None
        self._latest_scheme = None

    def setup(self, context):
        """Setup the canvas with GL context and generate initial state"""
        self.canvas.enter_recursive(context)
        vibe = Vibe(Mode.gentle)
        self.canvas.generate_recursive(vibe)

    def render(self, context, frame: Frame, scheme: ColorScheme):
        """Render the VJ content and return the result"""
        return self.canvas.render(frame, scheme, context)

    def update_frame_data(self, frame: Frame, scheme: ColorScheme):
        """Update frame data (thread-safe, called from director thread)"""
        self._latest_frame = frame
        self._latest_scheme = scheme

    def get_latest_frame_data(self):
        """Get latest frame data (called from main thread)"""
        return self._latest_frame, self._latest_scheme

    def shift(self, mode: Mode, threshold: float = 1.0):

        vibe = Vibe(mode)
        self.canvas.generate_recursive(vibe, threshold)
        self.last_shift_time = time.time()
        self.shift_count += 1

    def get_canvas(self) -> BaseInterpretationNode:
        """Get the current canvas for external access"""
        return self.canvas

    def set_canvas(self, canvas: BaseInterpretationNode, context):
        """Set a new canvas composition and set it up"""
        self.canvas.exit_recursive()
        self.canvas = canvas
        self.canvas.enter_recursive(context)

    def set_window(self, window):
        """Set the window for rendering"""
        self.window = window

    def create_pulsing_canvas(
        self, intensity: float = 0.7, base_brightness: float = 0.6
    ):
        """Create a new pulsing video canvas with specified parameters"""
        video_player = VideoPlayer(fn_group="bg")
        pulsing_video = BrightnessPulse(
            video_player, intensity=intensity, base_brightness=base_brightness
        )
        # TODO: Fix LayerCompose size mismatch, for now return just pulsing video
        return pulsing_video

    def set_pulse_intensity(
        self, intensity: float, base_brightness: float = None, context=None
    ):
        """Update the pulse effect parameters by creating a new canvas"""
        if base_brightness is None:
            base_brightness = 0.6

        new_canvas = self.create_pulsing_canvas(intensity, base_brightness)

        if context:
            self.set_canvas(new_canvas, context)
        else:
            # Just update the canvas without GL setup (will need setup later)
            self.canvas.exit_recursive()
            self.canvas = new_canvas

    def set_subtle_pulse(self, context=None):
        """Switch to subtle pulsing effect"""
        self.set_pulse_intensity(intensity=0.4, base_brightness=0.6, context=context)

    def set_dramatic_pulse(self, context=None):
        """Switch to dramatic pulsing effect"""
        self.set_pulse_intensity(intensity=1.2, base_brightness=0.2, context=context)

    def set_aggressive_pulse(self, context=None):
        """Switch to very aggressive pulsing (may be dark during silence)"""
        self.set_pulse_intensity(intensity=0.8, base_brightness=0.3, context=context)

    def set_static_video(self, context=None):
        """Switch to static video without pulsing"""
        static_canvas = VideoPlayer(
            fn_group="bg"
        )  # TODO: Add Black background when LayerCompose is fixed
        if context:
            self.set_canvas(static_canvas, context)
        else:
            self.canvas.exit_recursive()
            self.canvas = static_canvas

    def cleanup(self):
        """Clean up resources"""
        self.canvas.exit_recursive()
