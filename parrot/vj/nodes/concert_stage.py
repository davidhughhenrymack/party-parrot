#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import (
    BaseInterpretationNode,
    RandomChild,
    RandomOperation,
    Vibe,
)
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.vj.nodes.laser_array import LaserArray
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.oscilloscope_effect import OscilloscopeEffect
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode


@beartype
class ConcertStage(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A complete concert stage setup that combines 2D canvas with 3D lighting effects.
    Contains volumetric beams, laser arrays, and 2D video content in one cohesive unit.
    Defines the camera system for the 3D space.
    """

    def __init__(self):
        # Define camera system - audience perspective looking at stage
        self.camera_eye = np.array(
            [0.0, 6.0, -8.0]
        )  # Audience position (mid-height, in front)
        self.camera_target = np.array(
            [0.0, 6.0, 0.0]
        )  # Looking straight ahead at stage
        self.camera_up = np.array([0.0, 1.0, 0.0])  # World up vector

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
        video_with_fx = RandomOperation(
            video_player,
            [
                BrightnessPulse,
                SaturationPulse,
                BeatHueShift,
                DatamoshEffect,
                RGBShiftEffect,
                ScanlinesEffect,
                NoiseEffect,
            ],
        )

        # Create text renderer with white text on black background (perfect for masking)
        text_renderer = TextRenderer(
            text="DEAD\nSEXY",
            font_name="The Sonnyfive",
            font_size=140,
            text_color=(255, 255, 255),  # White text
            bg_color=(0, 0, 0),  # Black background
        )
        text_renderer = RandomOperation(
            text_renderer,
            [BrightnessPulse, NoiseEffect, PixelateEffect, ScanlinesEffect],
        )
        text_renderer_with_zoom = CameraZoom(
            text_renderer, signal=FrameSignal.freq_high
        )
        text_renderer = RandomChild([text_renderer, text_renderer_with_zoom])

        # Multiply video with text mask - white text shows video, black background hides it
        text_masked_video = MultiplyCompose(video_with_fx, text_renderer)

        # Create black text overlay on video
        black_text_renderer = TextRenderer(
            text="DEAD\nSEXY",
            font_name="The Sonnyfive",
            font_size=140,
            text_color=(0, 0, 0),  # Black text
            bg_color=(255, 255, 255),  # White background (will be multiplied away)
        )
        black_text_renderer = RandomOperation(
            black_text_renderer,
            [BrightnessPulse, NoiseEffect, PixelateEffect, ScanlinesEffect],
        )
        black_text_renderer = CameraZoom(
            black_text_renderer, signal=FrameSignal.freq_high
        )

        # Create video with black text overlay using LayerCompose
        # MULTIPLY blend: white areas (1.0) don't affect video, black areas (0.0) darken video to black
        video_with_black_text = LayerCompose(
            LayerSpec(video_with_fx, BlendMode.NORMAL),  # Base video layer
            LayerSpec(
                black_text_renderer, BlendMode.MULTIPLY
            ),  # Black text overlay with multiply blend
        )

        optional_masked_video = RandomChild(
            [video_with_fx, text_masked_video, video_with_black_text]
        )

        canvas_2d = CameraZoom(optional_masked_video)
        self.canvas_2d = canvas_2d

        # Create 3D volumetric beams for atmospheric lighting
        volumetric_beams = VolumetricBeam()

        self.volumetric_beams = volumetric_beams
        # Create 3D laser array for sharp laser effects
        # Position at top left of stage pointing back at audience
        laser_position = np.array([-4.0, 8.0, 2.0])  # Top left of stage
        laser_point_vector = self.camera_eye - laser_position  # Point toward audience
        laser_point_vector = laser_point_vector / np.linalg.norm(
            laser_point_vector
        )  # Normalize

        laser_array = LaserArray(
            camera_eye=self.camera_eye,
            camera_target=self.camera_target,
            camera_up=self.camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
        )
        self.laser_array = laser_array

        # Create oscilloscope effect for retro waveform visualization
        oscilloscope = OscilloscopeEffect()
        self.oscilloscope = oscilloscope

        # Make oscilloscope optional - sometimes show it, sometimes show black (nothing)
        # Use weights: oscilloscope appears 30% of the time, black 70% of the time
        optional_oscilloscope = RandomChild(
            [oscilloscope, Black()], weights=[0.05, 0.95]
        )

        # Create layer composition with proper blend modes
        return LayerCompose(
            LayerSpec(black_background, BlendMode.NORMAL),  # Base layer: solid black
            LayerSpec(canvas_2d, BlendMode.NORMAL),  # Canvas: video + text
            LayerSpec(
                optional_oscilloscope, BlendMode.ADDITIVE, opacity=0.3
            ),  # Oscilloscope: additive blending for glow with 30% opacity
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
