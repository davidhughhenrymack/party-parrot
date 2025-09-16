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


@beartype
class ConcertStage(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A complete concert stage setup that combines 2D canvas with 3D lighting effects.
    Contains volumetric beams, laser arrays, and 2D video content in one cohesive unit.
    """

    def __init__(self):
        # Create all stage components
        canvas_2d, volumetric_beams, laser_array = self._create_stage_components()

        # Initialize with children - they will be managed recursively
        super().__init__([canvas_2d, volumetric_beams, laser_array])

        # Store references for convenience
        self.canvas_2d = canvas_2d
        self.volumetric_beams = volumetric_beams
        self.laser_array = laser_array

        # Compositing framebuffer
        self.final_framebuffer: Optional[mgl.Framebuffer] = None
        self.final_texture: Optional[mgl.Texture] = None
        self._context: Optional[mgl.Context] = None

    def _create_stage_components(self):
        """Create all stage components: 2D canvas, volumetric beams, and laser array"""
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

        # Create 3D volumetric beams for atmospheric lighting
        volumetric_beams = VolumetricBeam(
            beam_count=6,
            beam_length=12.0,
            beam_width=0.4,
            beam_intensity=1.2,
            haze_density=0.8,
            movement_speed=1.8,
            color=(1.0, 0.8, 0.6),  # Warm concert lighting
            signal=FrameSignal.freq_low,  # React to bass
        )

        # Create 3D laser array for sharp laser effects
        laser_array = LaserArray(
            laser_count=8,
            array_radius=2.5,
            laser_length=20.0,
            laser_width=0.02,
            fan_angle=3.14159 / 3,  # 60 degrees
            scan_speed=2.5,
            strobe_frequency=0.0,  # No strobe by default
            laser_intensity=2.0,
            color=(0.0, 1.0, 0.0),  # Classic green lasers
            signal=FrameSignal.freq_high,  # React to treble
        )

        return canvas_2d, volumetric_beams, laser_array

    def enter(self, context: mgl.Context):
        """Initialize this node with GL context"""
        self._context = context

        # Create final compositing framebuffer
        self.final_texture = context.texture((1280, 720), 4)  # RGBA
        self.final_framebuffer = context.framebuffer(
            color_attachments=[self.final_texture]
        )

    def exit(self):
        """Clean up this node's resources"""
        # Clean up compositing resources
        if self.final_framebuffer:
            self.final_framebuffer.release()
        if self.final_texture:
            self.final_texture.release()

        self._context = None

    def generate(self, vibe: Vibe):
        """Generate new configurations for this node based on vibe"""
        # Mode-specific adjustments are now handled by each fixture's generate method
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the complete concert stage with 2D and 3D elements"""
        if not self.final_framebuffer:
            return None

        # Render to final compositing framebuffer
        self.final_framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 1.0)  # Clear to black

        # First render the 2D canvas content
        canvas_result = self.canvas_2d.render(frame, scheme, context)

        # Blit 2D canvas to final framebuffer as base layer
        if canvas_result and canvas_result.color_attachments:
            context.copy_framebuffer(self.final_framebuffer, canvas_result)

        # Render 3D volumetric beams (atmospheric lighting)
        beams_result = self.volumetric_beams.render(frame, scheme, context)

        # Composite volumetric beams over 2D canvas with alpha blending
        if beams_result and beams_result.color_attachments:
            context.enable(mgl.BLEND)
            context.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

            # Use texture to render a fullscreen quad with blending
            beams_texture = beams_result.color_attachments[0]
            beams_texture.use(location=0)

            # TODO: Implement proper fullscreen quad rendering with blending
            # For now, copy the framebuffer content
            context.copy_framebuffer(self.final_framebuffer, beams_result)

            context.disable(mgl.BLEND)

        # Render laser array (sharp laser effects)
        laser_result = self.laser_array.render(frame, scheme, context)

        # Composite laser array over everything with additive blending for bright laser effects
        if laser_result and laser_result.color_attachments:
            context.enable(mgl.BLEND)
            context.blend_func = mgl.SRC_ALPHA, mgl.ONE  # Additive blending for lasers

            # Use texture to render a fullscreen quad with additive blending
            laser_texture = laser_result.color_attachments[0]
            laser_texture.use(location=0)

            # TODO: Implement proper fullscreen quad rendering with additive blending
            # For now, copy the framebuffer content
            context.copy_framebuffer(self.final_framebuffer, laser_result)

            context.disable(mgl.BLEND)

        return self.final_framebuffer
