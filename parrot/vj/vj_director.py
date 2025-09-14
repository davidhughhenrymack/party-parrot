#!/usr/bin/env python3

import time
from beartype import beartype

from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.layer_compose import LayerCompose


@beartype
class VJDirector:
    """
    Director for the VJ system that manages video nodes and coordinates with the main director.
    Handles the visual composition and effects that respond to audio and lighting.
    """

    def __init__(self):
        self.canvas: BaseInterpretationNode = VideoPlayer(fn_group="bg")
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

    def cleanup(self):
        """Clean up resources"""
        self.canvas.exit_recursive()
