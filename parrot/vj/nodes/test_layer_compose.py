#!/usr/bin/env python3

import os
import pytest
import moderngl as mgl
import numpy as np
from unittest.mock import Mock
from PIL import Image

from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.vj.nodes.laser_scan_heads import LaserScanHeads
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
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
        assert src == mgl.ONE
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

    def test_laser_scan_heads_on_black_composition(self):
        """Test laser scan heads compositing on black background with additive blending"""
        black = Black()

        # Create laser scan heads
        lasers = LaserScanHeads(
            num_heads=4,
            beams_per_head=12,
        )

        layer_compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(lasers, BlendMode.ADDITIVE),  # Lasers with additive blending
        )

        # Verify layer setup
        assert len(layer_compose.layer_specs) == 2
        assert isinstance(layer_compose.layer_specs[0].node, Black)
        assert isinstance(layer_compose.layer_specs[1].node, LaserScanHeads)
        assert layer_compose.layer_specs[1].blend_mode == BlendMode.ADDITIVE

    def test_full_concert_stage_composition(self):
        """Test full concert stage composition with all elements"""
        black = Black()
        video = VideoPlayer(fn_group="bg")
        text = TextRenderer(text="CONCERT", font_size=64)
        beams = VolumetricBeam(beam_count=4, signal=FrameSignal.freq_low)

        # Create laser scan heads
        lasers = LaserScanHeads(num_heads=4, beams_per_head=16)

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


class TestLayerComposeRendering:
    """Test LayerCompose with actual rendering to PNG"""

    @pytest.fixture
    def gl_context(self):
        """Create standalone GL context"""
        try:
            ctx = mgl.create_context(standalone=True, backend="egl")
            yield ctx
        except Exception:
            ctx = mgl.create_context(standalone=True)
            yield ctx
        finally:
            ctx.release()

    @pytest.fixture
    def test_frame(self):
        """Create test frame with signals"""
        return Frame(
            {
                FrameSignal.strobe: 0.8,
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.7,
                FrameSignal.sustained_low: 0.5,
            }
        )

    @pytest.fixture
    def test_scheme(self):
        """Create test color scheme"""
        return ColorScheme(
            fg=Color("#FF0066"),  # Pink
            bg=Color("#000000"),  # Black
            bg_contrast=Color("#00FFFF"),  # Cyan
        )

    def _save_framebuffer_to_png(self, fb: mgl.Framebuffer, filename: str):
        """Helper to save framebuffer to PNG"""
        # Read pixels as RGB
        data = fb.read(components=3)
        width, height = fb.width, fb.height

        # Convert to numpy array
        arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

        # Flip vertically (OpenGL convention)
        arr = np.flipud(arr)

        # Save PNG
        project_out_dir = os.path.join(os.getcwd(), "test_output")
        os.makedirs(project_out_dir, exist_ok=True)
        out_path = os.path.join(project_out_dir, filename)

        img = Image.fromarray(arr, mode="RGB")
        img.save(out_path)

        print(f"✅ Saved render to: {out_path}")
        return out_path

    def test_normal_blend_two_colors(self, gl_context, test_frame, test_scheme):
        """Test normal blending with two colored layers"""
        # Create two colored layers
        red_layer = StaticColor(color=(1.0, 0.0, 0.0), width=800, height=600)
        blue_layer = StaticColor(color=(0.0, 0.0, 1.0), width=800, height=600)

        # Compose with normal blending (opacity in LayerSpec)
        compose = LayerCompose(
            LayerSpec(red_layer, BlendMode.NORMAL),
            LayerSpec(blue_layer, BlendMode.NORMAL, opacity=0.5),
            width=800,
            height=600,
        )

        # Initialize all nodes
        red_layer.enter(gl_context)
        blue_layer.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_normal_blend.png")

        # Cleanup
        compose.exit()
        red_layer.exit()
        blue_layer.exit()

    def test_additive_blend_layers(self, gl_context, test_frame, test_scheme):
        """Test additive blending (like lasers on black)"""
        # Black base
        black = Black(width=800, height=600)

        # Red and blue layers
        red_layer = StaticColor(color=(0.5, 0.0, 0.0), width=800, height=600)
        blue_layer = StaticColor(color=(0.0, 0.0, 0.5), width=800, height=600)

        # Compose with additive blending
        compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(red_layer, BlendMode.ADDITIVE),
            LayerSpec(blue_layer, BlendMode.ADDITIVE),
            width=800,
            height=600,
        )

        # Initialize all nodes
        black.enter(gl_context)
        red_layer.enter(gl_context)
        blue_layer.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_additive_blend.png")

        # Cleanup
        compose.exit()
        black.exit()
        red_layer.exit()
        blue_layer.exit()

    def test_multiply_blend_mask(self, gl_context, test_frame, test_scheme):
        """Test multiply blending (like text mask)"""
        # White base
        white = StaticColor(color=(1.0, 1.0, 1.0), width=800, height=600)

        # Gray layer for mask effect
        mask = StaticColor(color=(0.5, 0.5, 0.5), width=800, height=600)

        # Compose with multiply blending
        compose = LayerCompose(
            LayerSpec(white, BlendMode.NORMAL),
            LayerSpec(mask, BlendMode.MULTIPLY),
            width=800,
            height=600,
        )

        # Initialize all nodes
        white.enter(gl_context)
        mask.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_multiply_blend.png")

        # Cleanup
        compose.exit()
        white.exit()
        mask.exit()

    def test_laser_heads_on_black(self, gl_context, test_frame, test_scheme):
        """Test laser scan heads with additive blending on black"""
        # Black base
        black = Black(width=1280, height=720)

        # Laser scan heads
        lasers = LaserScanHeads(width=1280, height=720, beams_per_head=16)

        # Compose
        compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(lasers, BlendMode.ADDITIVE),
            width=1280,
            height=720,
        )

        # Initialize all nodes
        black.enter(gl_context)
        lasers.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_lasers_on_black.png")

        # Cleanup
        compose.exit()
        black.exit()
        lasers.exit()

    def test_volumetric_beams_composition(self, gl_context, test_frame, test_scheme):
        """Test volumetric beams with normal blending"""
        # Black base
        black = Black(width=1280, height=720)

        # Volumetric beams
        beams = VolumetricBeam(
            beam_count=4,
            beam_length=10.0,
            beam_width=0.3,
            signal=FrameSignal.freq_low,
            width=1280,
            height=720,
        )

        # Compose
        compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),
            LayerSpec(beams, BlendMode.NORMAL),
            width=1280,
            height=720,
        )

        # Initialize all nodes
        black.enter(gl_context)
        beams.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_beams.png")

        # Cleanup
        compose.exit()
        black.exit()
        beams.exit()

    def test_multi_layer_composition(self, gl_context, test_frame, test_scheme):
        """Test complex multi-layer composition with different blend modes"""
        # Base layer
        black = Black(width=1280, height=720)

        # Colored background
        bg_color = StaticColor(color=(0.1, 0.05, 0.2), width=1280, height=720)

        # Volumetric beams
        beams = VolumetricBeam(
            beam_count=3, signal=FrameSignal.freq_low, width=1280, height=720
        )

        # Laser scan heads
        lasers = LaserScanHeads(width=1280, height=720, beams_per_head=12)

        # Compose all layers
        compose = LayerCompose(
            LayerSpec(black, BlendMode.NORMAL),  # Black base
            LayerSpec(bg_color, BlendMode.NORMAL),  # Colored background
            LayerSpec(beams, BlendMode.NORMAL),  # Atmospheric beams
            LayerSpec(lasers, BlendMode.ADDITIVE),  # Sharp laser effects
            width=1280,
            height=720,
        )

        # Initialize all nodes
        black.enter(gl_context)
        bg_color.enter(gl_context)
        beams.enter(gl_context)
        lasers.enter(gl_context)
        compose.enter(gl_context)
        compose.generate(Vibe(mode=Mode.rave))

        # Render
        result = compose.render(test_frame, test_scheme, gl_context)
        assert result is not None

        # Save to PNG
        self._save_framebuffer_to_png(result, "layer_compose_multi_layer.png")

        # Cleanup
        compose.exit()
        black.exit()
        bg_color.exit()
        beams.exit()
        lasers.exit()
