#!/usr/bin/env python3

import moderngl as mgl
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.vj.nodes.laser_array import LaserArray
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode


@beartype
class ConcertStage(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A complete concert stage setup that combines 2D canvas with 3D lighting effects.
    Contains volumetric beams, laser arrays, and 2D video content in one cohesive unit.
    """

    def __init__(self):
        # Create stage components and layer composition
        self.layer_compose = self._create_layer_composition()

        # Initialize with layer compose as single child
        super().__init__([self.layer_compose])

    def _create_layer_composition(self):
        """Create a LayerCompose with all stage components and proper blend modes"""
        # Create black background as base layer
        black_background = Black()

        # Create 2D canvas with video, text, and effects
        video_player = VideoPlayer(fn_group="bg")
        pulsing_video = BrightnessPulse(video_player, signal=FrameSignal.freq_low)

        # Create text renderer with white text on black background (perfect for masking)
        text_renderer = TextRenderer(
            text="DEAD\nSEXY",
            font_name="The Sonnyfive",
            font_size=140,
            text_color=(255, 255, 255),  # White text
            bg_color=(0, 0, 0),  # Black background
        )
        text_renderer = BrightnessPulse(text_renderer, signal=FrameSignal.freq_low)
        text_renderer = CameraZoom(text_renderer, signal=FrameSignal.freq_high)

        # Multiply video with text mask - white text shows video, black background hides it
        text_masked_video = MultiplyCompose(pulsing_video, text_renderer)
        canvas_2d = CameraZoom(text_masked_video)
        self.canvas_2d = canvas_2d

        # Create 3D volumetric beams for atmospheric lighting
        volumetric_beams = VolumetricBeam()
        self.volumetric_beams = volumetric_beams
        # Create 3D laser array fo
        # r sharp laser effects
        laser_array = LaserArray()
        self.laser_array = laser_array

        # Create layer composition with proper blend modes
        return LayerCompose(
            LayerSpec(black_background, BlendMode.NORMAL),  # Base layer: solid black
            LayerSpec(canvas_2d, BlendMode.NORMAL),  # Canvas: video + text
            LayerSpec(
                volumetric_beams, BlendMode.ADDITIVE
            ),  # Beams: additive blending (FIXED!)
            LayerSpec(laser_array, BlendMode.ADDITIVE),  # Lasers: additive blending
        )

    def enter(self, context: mgl.Context):
        """Initialize this node with GL context - children handled by base class"""
        pass

    def exit(self):
        """Clean up this node's resources - children handled by base class"""
        pass

    def generate(self, vibe: Vibe):
        """Generate new configurations - children handled by base class"""
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the complete concert stage using LayerCompose"""
        return self.layer_compose.render(frame, scheme, context)
