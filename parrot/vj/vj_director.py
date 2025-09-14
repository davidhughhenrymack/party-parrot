#!/usr/bin/env python3

import random
import time
from typing import Optional
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
        self.canvas: Optional[BaseInterpretationNode] = None
        self.last_shift_time = time.time()
        self.shift_count = 0
        self._canvas_entered = False

        # Initialize with a simple video player canvas
        self.setup_canvas()

    def setup_canvas(self):
        """Setup the initial canvas composition"""
        # For now, start with a simple video player
        # Later this can be expanded to LayerCompose with multiple effects
        self.canvas = VideoPlayer(fn_group="bg")
        self._canvas_entered = False  # Reset enter flag when canvas changes

    def step(self, frame: Frame, scheme: ColorScheme):
        """
        Process a frame update from the main director.
        This is called in sync with the audio processing.
        """
        if not self.canvas:
            return

        # The canvas doesn't need to do anything special on step
        # The actual rendering happens when render() is called
        pass

    def render(self, context, frame: Frame, scheme: ColorScheme):
        """
        Render the VJ content and return the result.
        This is called by the VJ window during its render loop.
        """
        if not self.canvas:
            return None

        # Enter canvas on first render when we have context
        if not self._canvas_entered:
            try:
                self.canvas.enter_recursive(context)
                # Generate initial video selection
                from parrot.director.mode import Mode

                vibe = Vibe(Mode.gentle)
                self.canvas.generate_recursive(vibe)
                self._canvas_entered = True
            except Exception as e:
                print(f"Error entering VJ canvas: {e}")
                return None

        try:
            return self.canvas.render(frame, scheme, context)
        except Exception as e:
            print(f"Error rendering VJ canvas: {e}")
            return None

    def shift(self, mode: Mode, shift_percentage: float = 1.0):
        """
        Shift the VJ interpretation based on mode change.

        Args:
            mode: The new mode to adapt to
            shift_percentage: How much of the node tree to regenerate (0.0 to 1.0)
        """
        if not self.canvas:
            return

        # Reduced logging for cleaner output
        if shift_percentage >= 1.0:
            print(f"🎬 VJ mode: {mode.name}")

        try:
            # Create vibe for the new mode
            vibe = Vibe(mode)

            if shift_percentage >= 1.0:
                # Full regeneration
                self.canvas.generate_recursive(vibe)
            elif shift_percentage > 0.0:
                # Partial regeneration - for now just do full regeneration
                # TODO: Implement selective regeneration based on percentage
                self.canvas.generate_recursive(vibe)

            self.last_shift_time = time.time()
            self.shift_count += 1

        except Exception as e:
            print(f"Error during VJ shift: {e}")

    def recursive_generate(self, vibe: Vibe, percentage: float = 1.0):
        """
        Recursively regenerate nodes based on percentage.
        This allows for partial shifts where only some nodes are updated.

        Args:
            vibe: The vibe to generate for
            percentage: Percentage of nodes to regenerate (0.0 to 1.0)
        """
        if not self.canvas:
            return

        if percentage >= 1.0:
            # Full regeneration
            self.canvas.generate_recursive(vibe)
        elif percentage > 0.0:
            # For now, implement simple random regeneration
            # TODO: Implement more sophisticated partial regeneration
            if random.random() < percentage:
                self.canvas.generate_recursive(vibe)

    def get_canvas(self) -> Optional[BaseInterpretationNode]:
        """Get the current canvas for external access"""
        return self.canvas

    def set_canvas(self, canvas: BaseInterpretationNode):
        """Set a new canvas composition"""
        if self.canvas:
            self.canvas.exit_recursive()

        self.canvas = canvas
        self._canvas_entered = False  # Reset enter flag for new canvas

    def cleanup(self):
        """Clean up resources"""
        if self.canvas:
            self.canvas.exit_recursive()
            self.canvas = None
