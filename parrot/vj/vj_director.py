#!/usr/bin/env python3

import time
from beartype import beartype

from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.vj.nodes.concert_stage import ConcertStage


@beartype
class VJDirector:
    """
    Director for the VJ system that manages video nodes and coordinates with the main director.
    Handles the visual composition and effects that respond to audio and lighting.
    """

    def __init__(self, mode: Mode):
        # Create the complete concert stage with 2D canvas and 3D lighting
        self.concert_stage = ConcertStage()

        self.last_shift_time = time.time()
        self.shift_count = 0
        self.window = None  # Will be set by the window manager
        self.current_mode = mode

        # Latest frame data from director
        self._latest_frame = None
        self._latest_scheme = None

    def setup(self, context):
        """Setup the concert stage with GL context and generate initial state"""
        self.concert_stage.enter_recursive(context)

        vibe = Vibe(self.current_mode)
        self.concert_stage.generate_recursive(vibe)

        # Print the tree structure after initialization
        print("VJ Concert Stage Tree (after initialization):")
        print(self.concert_stage.print_tree())

    def step(self, frame: Frame, scheme: ColorScheme):
        """Step method called by director - stores latest frame data for rendering"""
        self._latest_frame = frame
        self._latest_scheme = scheme

    def get_latest_frame_data(self):
        """Get latest frame data for rendering"""
        return self._latest_frame, self._latest_scheme

    def render(self, context, frame: Frame, scheme: ColorScheme):
        """Render the complete concert stage"""
        return self.concert_stage.render(frame, scheme, context)

    def shift(self, mode: Mode, threshold: float = 1.0):
        """Shift the visual mode and update the concert stage"""
        self.current_mode = mode  # Track the current mode
        vibe = Vibe(mode)
        self.concert_stage.generate_recursive(vibe, threshold)

        self.last_shift_time = time.time()
        self.shift_count += 1

        # Print the tree structure after shift
        print(f"VJ Concert Stage Tree (after shift #{self.shift_count} to {mode}):")
        print(self.concert_stage.print_tree())

    def get_concert_stage(self) -> ConcertStage:
        """Get the complete concert stage"""
        return self.concert_stage

    def get_current_mode(self) -> Mode:
        """Get the current mode"""
        return self.current_mode

    def shift_current_mode(self, threshold: float = 1.0):
        """Shift using the current mode (regenerate with same mode)"""
        self.shift(self.current_mode, threshold)

    def set_window(self, window):
        """Set the window for rendering"""
        self.window = window

    def cleanup(self):
        """Clean up resources"""
        self.concert_stage.exit_recursive()
