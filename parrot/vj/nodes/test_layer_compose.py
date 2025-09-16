#!/usr/bin/env python3

import pytest
import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.vj.nodes.laser_array import LaserArray
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestLayerCompose:
    """Test LayerCompose functionality"""

    def test_initialization(self):
        """Test LayerCompose initialization"""
        black = Black()
        video = VideoPlayer(fn_group="bg")

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(video, BlendMode.NORMAL),
        )

        assert len(layer_compose.layer_specs) == 2
        assert layer_compose.layer_specs[0].blend_mode == BlendMode.NORMAL
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.NORMAL
        assert layer_compose.width == 1280  # DEFAULT_WIDTH
        assert layer_compose.height == 720  # DEFAULT_HEIGHT

    def test_blend_modes(self):
        """Test different blend modes"""
        black = Black()
        video = VideoPlayer(fn_group="bg")

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(video, BlendMode.ADDITIVE, opacity=0.8),
        )

        assert layer_compose.layer_specs[1].blend_mode == BlendMode.ADDITIVE
        assert layer_compose.layer_specs[1].opacity == 0.8

    def test_blend_func_mapping(self):
        """Test OpenGL blend function mapping"""
        layer_compose = LayerCompose()

        # Test normal blending
        src, dst = layer_compose._get_blend_func(BlendMode.NORMAL)
        assert src == mgl.SRC_ALPHA
        assert dst == mgl.ONE_MINUS_SRC_ALPHA

        # Test additive blending
        src, dst = layer_compose._get_blend_func(BlendMode.ADDITIVE)
        assert src == mgl.SRC_ALPHA
        assert dst == mgl.ONE

        # Test multiply blending
        src, dst = layer_compose._get_blend_func(BlendMode.MULTIPLY)
        assert src == mgl.DST_COLOR
        assert dst == mgl.ZERO

    def test_blend_mode_int_mapping(self):
        """Test blend mode integer mapping for shaders"""
        layer_compose = LayerCompose()

        assert layer_compose._get_blend_mode_int(BlendMode.NORMAL) == 0
        assert layer_compose._get_blend_mode_int(BlendMode.ADDITIVE) == 1
        assert layer_compose._get_blend_mode_int(BlendMode.MULTIPLY) == 2
        assert layer_compose._get_blend_mode_int(BlendMode.SCREEN) == 3

    def test_render_without_gl_context(self):
        """Test render without GL context returns None"""
        black = Black()
        layer_compose = LayerCompose(LayerSpec(black, BlendMode.NORMAL))

        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        result = layer_compose.render(frame, scheme, context)
        assert result is None  # No GL setup

    @pytest.mark.skipif(True, reason="Requires OpenGL context")
    def test_layer_composition_with_gl(self):
        """Test actual layer composition with OpenGL context"""
        # This test would require a real OpenGL context
        # Skip for now as it's complex to set up in CI
        pass


class TestSceneElementComposition:
    """Test each major scene element compositing on Black base layer"""

    def test_black_base_layer(self):
        """Test Black node as base layer"""
        black = Black(width=100, height=100)

        # Test initialization
        assert black.width == 100
        assert black.height == 100
        assert black.framebuffer is None
        assert black.texture is None

    def test_video_on_black_composition(self):
        """Test video compositing on black background"""
        black = Black()
        video = VideoPlayer(fn_group="bg")

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(video, BlendMode.NORMAL),  # Video on top
        )

        # Verify layer setup
        assert len(layer_compose.layer_specs) == 2
        assert isinstance(layer_compose.layer_specs[0].node, Black)
        assert isinstance(layer_compose.layer_specs[1].node, VideoPlayer)
        assert layer_compose.layer_specs[0].blend_mode == BlendMode.NORMAL
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.NORMAL

    def test_text_on_black_composition(self):
        """Test text compositing on black background"""
        black = Black()
        text = TextRenderer(
            text="TEST",
            font_name="Arial",
            font_size=48,
            text_color=(255, 255, 255),
            bg_color=(0, 0, 0),
        )

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(text, BlendMode.NORMAL),  # Text on top
        )

        # Verify layer setup
        assert len(layer_compose.layer_specs) == 2
        assert isinstance(layer_compose.layer_specs[0].node, Black)
        assert isinstance(layer_compose.layer_specs[1].node, TextRenderer)

    def test_volumetric_beams_on_black_composition(self):
        """Test volumetric beams compositing on black background"""
        black = Black()
        beams = VolumetricBeam(
            beam_count=3,
            beam_length=10.0,
            beam_width=0.3,
            beam_intensity=2.0,
            haze_density=0.8,
            movement_speed=1.5,
            color=(1.0, 0.8, 0.6),
            signal=FrameSignal.freq_low,
        )

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(beams, BlendMode.NORMAL),  # Beams with alpha blending
        )

        # Verify layer setup
        assert len(layer_compose.layer_specs) == 2
        assert isinstance(layer_compose.layer_specs[0].node, Black)
        assert isinstance(layer_compose.layer_specs[1].node, VolumetricBeam)
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.NORMAL

    def test_laser_array_on_black_composition(self):
        """Test laser array compositing on black background with additive blending"""
        black = Black()
        lasers = LaserArray(
            laser_count=4,
            array_radius=2.0,
            laser_length=15.0,
            laser_width=0.02,
            fan_angle=1.57,  # 90 degrees
            scan_speed=2.0,
            strobe_frequency=0.0,
            laser_intensity=1.5,
            color=(0.0, 1.0, 0.0),
            signal=FrameSignal.freq_high,
        )

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(lasers, BlendMode.ADDITIVE),  # Lasers with additive blending
        )

        # Verify layer setup
        assert len(layer_compose.layer_specs) == 2
        assert isinstance(layer_compose.layer_specs[0].node, Black)
        assert isinstance(layer_compose.layer_specs[1].node, LaserArray)
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.ADDITIVE

    def test_full_concert_stage_composition(self):
        """Test full concert stage composition with all elements"""
        black = Black()
        video = VideoPlayer(fn_group="bg")
        text = TextRenderer(text="CONCERT", font_size=64)
        beams = VolumetricBeam(beam_count=4, signal=FrameSignal.freq_low)
        lasers = LaserArray(laser_count=6, signal=FrameSignal.freq_high)

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(video, BlendMode.NORMAL),  # Video background
            LayerSpec(text, BlendMode.MULTIPLY),  # Text mask
            LayerSpec(beams, BlendMode.NORMAL),  # Atmospheric beams
            LayerSpec(lasers, BlendMode.ADDITIVE),  # Sharp laser effects
        )

        # Verify complete composition
        assert len(layer_compose.layer_specs) == 5
        assert layer_compose.layer_specs[0].blend_mode == BlendMode.NORMAL  # Black
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.NORMAL  # Video
        assert layer_compose.layer_specs[2].blend_mode == BlendMode.MULTIPLY  # Text
        assert layer_compose.layer_specs[3].blend_mode == BlendMode.NORMAL  # Beams
        assert layer_compose.layer_specs[4].blend_mode == BlendMode.ADDITIVE  # Lasers

    def test_layer_opacity_control(self):
        """Test layer opacity control"""
        black = Black()
        video = VideoPlayer(fn_group="bg")

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL, opacity=1.0),
            LayerSpec(video, BlendMode.NORMAL, opacity=0.7),  # 70% opacity
        )

        assert layer_compose.layer_specs[0].opacity == 1.0
        assert layer_compose.layer_specs[1].opacity == 0.7

    def test_children_management(self):
        """Test that LayerCompose properly manages children nodes"""
        black = Black()
        video = VideoPlayer(fn_group="bg")

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(video, BlendMode.NORMAL),
        )

        # Children should be extracted from layer specs
        assert len(layer_compose.children) == 2
        assert layer_compose.children[0] is black
        assert layer_compose.children[1] is video
