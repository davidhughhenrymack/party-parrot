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
from parrot.vj.vj_mode import VJMode
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.camera_shake import CameraShake
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.text_color_pulse import TextColorPulse
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.mode_switch import ModeSwitch
from parrot.vj.nodes.oscilloscope_effect import OscilloscopeEffect
from parrot.vj.nodes.color_strobe import ColorStrobe
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.vintage_film_mask import VintageFilmMask
from parrot.vj.nodes.crt_mask import CRTMask
from parrot.vj.nodes.bright_glow import BrightGlow
from parrot.vj.nodes.sepia_effect import SepiaEffect
from parrot.vj.nodes.glow_effect import GlowEffect
from parrot.vj.nodes.bloom_filter import BloomFilter
from parrot.vj.nodes.hot_sparks_effect import HotSparksEffect
from parrot.vj.nodes.stage_blinders import StageBlinders
from parrot.vj.nodes.laser_scan_heads import LaserScanHeads
from parrot.vj.profiler import vj_profiler
from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.moving_head import MovingHead
from parrot.director.mode_interpretations import get_interpreter
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.nodes.fixture_interpreter import FixtureInterpreterNode
from parrot.vj.nodes.moving_head_array_renderer import (
    MovingHeadArrayRenderer,
    MovingHeadPlacement,
)
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch


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

        # Create stage components and layer composition (now includes blackout switch)
        self.mode_switch = self._create_mode_switch()

        # Initialize with mode switch as single child
        super().__init__([self.mode_switch])

    def _create_mode_switch(self):
        """Create a ModeSwitch with different nodes for each mode"""
        # Create black background as base layer
        black_background = Black()

        # Create 2D canvas with video, text, and effects
        video_player = VideoPlayer(fn_group="bg")
        video_with_fx = RandomOperation(
            video_player,
            [
                BrightnessPulse,
                SaturationPulse,
                CameraShake,
                BeatHueShift,
                DatamoshEffect,
                RGBShiftEffect,
                ScanlinesEffect,
                NoiseEffect,
            ],
        )

        # Create text renderer with white text on black background (perfect for masking)
        zombie_texts = [
            "DEAD\nSEXY",
            "RAVE",
            "BRAINS",
            "U R SEXY",
            "BITE ME",
            "GET DOWN",
            "SUCK MY\nBLOOD",
            "DOM ZOM",
        ]
        text_renderer = TextRenderer(
            text=zombie_texts,
            font_name="The Sonnyfive",
            font_size=140,
            text_color=(255, 255, 255),  # White text
            bg_color=(0, 0, 0),  # Black background
        )
        text_masked_video_no_fx = MultiplyCompose(video_player, text_renderer)

        # Create black text overlay on video
        black_text_renderer = TextRenderer(
            text=zombie_texts,
            font_name="The Sonnyfive",
            font_size=180,
            text_color=(0, 0, 0),  # Black text
            bg_color=(255, 255, 255),  # White background (will be multiplied away)
        )
        black_text_renderer = RandomOperation(
            black_text_renderer,
            [
                BrightnessPulse,
                TextColorPulse,
                CameraShake,
                NoiseEffect,
                PixelateEffect,
                ScanlinesEffect,
            ],
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

        optional_masked_video = RandomChild([video_with_fx, video_with_black_text])

        canvas_2d = CameraZoom(optional_masked_video)
        self.canvas_2d = canvas_2d

        moving_head_renderer = self._create_virtual_moving_heads()
        self.moving_head_renderer = moving_head_renderer

        # Create oscilloscope effect for retro waveform visualization
        oscilloscope = OscilloscopeEffect()
        self.oscilloscope = oscilloscope

        # Make oscilloscope optional - sometimes show it, sometimes show black (nothing)
        # Use weights: oscilloscope appears 30% of the time, black 70% of the time
        optional_oscilloscope = RandomChild(
            [oscilloscope, Black()], weights=[0.05, 0.95]
        )

        # Create base layer composition (everything below the strobe)
        base_layers = LayerCompose(
            LayerSpec(black_background, BlendMode.NORMAL),  # Base layer: solid black
            LayerSpec(
                optional_oscilloscope, BlendMode.ADDITIVE, opacity=0.3
            ),  # Oscilloscope: additive blending for glow with 30% opacity
            LayerSpec(canvas_2d, BlendMode.NORMAL),  # Canvas: video + text
            # LayerSpec(laser_array, BlendMode.ADDITIVE),  # Lasers: additive blending
            # LayerSpec(
            #     moving_head_renderer,
            #     BlendMode.ADDITIVE,
            #     opacity=0.85,
            # ),
        )

        # Wrap base layers in brightness pulse effect for rave mode
        brightness_pulsed_layers = BrightnessPulse(
            base_layers,
            intensity=1.0,
            base_brightness=0.1,
            signal=FrameSignal.freq_high,
        )

        # Store rave composition (without effects - they'll be added after mode switch)
        rave_composition = brightness_pulsed_layers

        # Create a black node for blackout mode
        black_node = Black()

        # Create chill mode configuration with only film grain/vintage effects and gentle camera zoom
        # Apply circular mask to video so it appears as a circle in the middle
        # Use separate video player for chill mode with bg_chill folder
        chill_video_player = VideoPlayer(fn_group="bg_chill")
        # Create noise effect with half intensity for subtle film grain
        gentle_noise_effect = NoiseEffect(
            chill_video_player,
            noise_intensity=0.15,  # Half of default 0.3 for subtle effect
            noise_scale=100.0,  # Keep default scale
            static_lines=True,  # Keep static lines for vintage feel
            color_noise=True,  # Keep color noise for authenticity
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        # Apply gentle camera zoom with mild parameters
        chill_video_with_gentle_zoom = CameraZoom(
            gentle_noise_effect,
            max_zoom=1.3,  # Mild zoom (instead of default 2.5)
            zoom_speed=2.0,  # Gentle zoom speed (instead of default 8.0)
            return_speed=1.5,  # Gentle return speed (instead of default 4.0)
            blur_intensity=0.2,  # Minimal blur (instead of default 0.8)
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        # Apply rounded rectangle mask with decayed film edges
        chill_video_masked = VintageFilmMask(chill_video_with_gentle_zoom)

        # Apply signal-responsive sepia effect for vintage warmth
        chill_video_with_sepia = SepiaEffect(
            chill_video_masked,
            base_intensity=0.4,  # Moderate base sepia for vintage feel
            max_intensity=0.8,  # Strong sepia when signal is high
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        # Wrap in gentle brightness pulse for subtle breathing effect
        chill_video_with_pulse = BrightnessPulse(
            chill_video_with_sepia,
            intensity=0.3,  # Very gentle intensity for minimal sound reactivity
            base_brightness=0.55,  # Higher base brightness to keep it bright overall
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        # Add gentle bloom filter for dreamy chill atmosphere
        chill_video_with_bloom = BloomFilter(
            chill_video_with_pulse,
            base_intensity=0.3,  # More visible bloom base intensity for chill
            max_intensity=0.6,  # Subtle bloom max intensity
            bloom_radius=3.0,  # Small bloom radius for chill mode
            threshold=0.25,  # Lower threshold for more dreamy bloom
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
            blur_passes=2,  # Smooth bloom with 2 passes
        )

        # Create gentle mode with random effect choice between brightness pulse and glow
        gentle_brightness_pulse = BrightnessPulse(
            text_masked_video_no_fx,
            intensity=0.5,  # Gentle intensity for subtle effect
            base_brightness=0.6,  # Higher base brightness for gentle mode
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        gentle_glow_effect = GlowEffect(
            text_masked_video_no_fx,
            base_intensity=0.3,  # Gentle glow base intensity
            max_intensity=0.7,  # Gentle glow max intensity
            glow_radius=6.0,  # Subtle glow radius
            threshold=0.5,  # Lower threshold for more glow
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        gentle_bloom_effect = BloomFilter(
            text_masked_video_no_fx,
            base_intensity=0.4,  # More visible bloom base intensity
            max_intensity=0.7,  # Gentle bloom max intensity
            bloom_radius=4.0,  # Subtle bloom radius
            threshold=0.3,  # Lower threshold for more bloom
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
            blur_passes=2,  # Smooth bloom with 2 passes
        )

        # Randomly choose between brightness pulse, glow effect, and bloom filter
        gentle_with_effect = RandomChild(
            [gentle_brightness_pulse, gentle_glow_effect, gentle_bloom_effect]
        )

        # Add gentle camera zoom to the whole composition
        gentle_with_zoom = CameraZoom(
            gentle_with_effect,
            max_zoom=1.2,  # Very subtle zoom (instead of default 2.5)
            zoom_speed=1.5,  # Gentle zoom speed (instead of default 8.0)
            return_speed=1.0,  # Gentle return speed (instead of default 4.0)
            blur_intensity=0.1,  # Minimal blur (instead of default 0.8)
            signal=FrameSignal.sustained_low,  # Use sustained low for gentle response
        )

        # Helper function to create CRT-style video aesthetic with vibrant colors
        def create_crt_video_pipeline(fn_group: str):
            """Create a CRT-style video pipeline for music video aesthetics"""
            video_player = VideoPlayer(fn_group=fn_group)

            # Apply RGB shift for chromatic aberration (80s VHS look)
            with_rgb = RGBShiftEffect(
                video_player,
                shift_strength=0.006,  # Moderate RGB shift for 80s VHS effect
                signal=FrameSignal.freq_high,  # Pulse with music
            )

            # Apply scanlines for CRT monitor look
            with_scanlines = ScanlinesEffect(
                with_rgb,
                scanline_intensity=0.25,  # Visible but not overwhelming scanlines
                scanline_count=400.0,  # Dense scanlines for CRT effect
                signal=FrameSignal.sustained_low,
            )

            # Apply saturation pulse for vibrant colors
            with_saturation = SaturationPulse(
                with_scanlines,
                base_saturation=1.2,  # Boosted base saturation for vibrant colors
                intensity=0.6,  # Moderate intensity for saturation variation
                signal=FrameSignal.sustained_low,
            )

            # Add brightness pulse for dynamic energy
            with_brightness = BrightnessPulse(
                with_saturation,
                intensity=0.7,  # Moderate intensity
                base_brightness=0.5,  # Medium base brightness
                signal=FrameSignal.sustained_low,
            )

            # Add camera zoom for movement (before CRT mask so zoom is inside the screen)
            with_zoom = CameraZoom(
                with_brightness,
                max_zoom=1.4,  # Moderate zoom
                zoom_speed=3.0,  # Medium zoom speed
                return_speed=2.0,  # Smooth return
                blur_intensity=0.3,  # Slight blur
                signal=FrameSignal.sustained_low,
            )

            # Apply CRT mask for old TV screen shape with fisheye (after zoom so mask stays fixed)
            with_crt = CRTMask(with_zoom)

            # Apply bright glow on top of CRT for luminous screen effect
            with_glow = BrightGlow(
                with_crt,
                brightness_threshold=0.75,  # Extract pixels 75%+ bright
                blur_radius=8,  # Strong blur for glow
                glow_intensity=0.1,  # 10% blend opacity
            )

            return with_glow

        # Create 80s music video aesthetic
        music_vid_with_glow = create_crt_video_pipeline("bg_music_vid")

        # Create hip-hop video aesthetic (same pipeline, different videos)
        hiphop_with_glow = create_crt_video_pipeline("bg_hiphop")

        # Create mode switch WITHOUT effects (effects will be added after)
        # Maps VJMode enum values to visual compositions
        mode_switch = ModeSwitch(
            full_rave=rave_composition,
            early_rave=gentle_with_zoom,
            blackout=black_node,
            golden_age=chill_video_with_bloom,
            music_vids=music_vid_with_glow,  # 80s music video with CRT mask and bright glow
            hiphop=hiphop_with_glow,  # Hip-hop video with CRT mask and bright glow
        )

        # Create mode-specific effects with two parameter sets: gentle and strong
        # Instantiate effects as variables, then pass into ModeSwitch

        # Color Strobe effects
        color_strobe_strong = ColorStrobe(strobe_frequency=12.0, opacity_multiplier=1.0)
        color_strobe_gentle = ColorStrobe(strobe_frequency=4.0, opacity_multiplier=0.2)
        color_strobe_black = Black()

        color_strobe = ModeSwitch(
            full_rave=color_strobe_strong,
            early_rave=color_strobe_gentle,
            golden_age=color_strobe_gentle,
            music_vids=color_strobe_gentle,
            hiphop=color_strobe_gentle,
            blackout=color_strobe_black,
        )
        self.color_strobe = color_strobe

        # Laser Scan Heads effects
        laser_scan_heads_strong = LaserScanHeads(
            num_heads=6,
            beams_per_head=16,
            base_rotation_speed=0.6,
            base_tilt_speed=0.4,
            base_beam_spread=0.35,
            attack_time=0.05,
            decay_time=0.3,
            opacity_multiplier=1.0,
            head_placement_scheme="corners",
            allow_random_heads=True,
            allow_random_placement=True,
        )
        laser_scan_heads_gentle = LaserScanHeads(
            num_heads=4,
            beams_per_head=8,
            base_rotation_speed=0.15,
            base_tilt_speed=0.1,
            base_beam_spread=0.15,
            attack_time=0.15,
            decay_time=0.6,
            opacity_multiplier=0.3,
            head_placement_scheme="corners",
        )
        laser_scan_heads_black = Black()

        laser_scan_heads = ModeSwitch(
            full_rave=laser_scan_heads_strong,
            early_rave=laser_scan_heads_gentle,
            golden_age=laser_scan_heads_gentle,
            music_vids=laser_scan_heads_gentle,
            hiphop=laser_scan_heads_gentle,
            blackout=laser_scan_heads_black,
        )
        self.laser_scan_heads = laser_scan_heads

        # Hot Sparks effects
        hot_sparks_strong = HotSparksEffect(num_sparks=500, opacity_multiplier=1.0)
        hot_sparks_gentle = HotSparksEffect(num_sparks=200, opacity_multiplier=0.3)
        hot_sparks_black = Black()

        hot_sparks = ModeSwitch(
            full_rave=hot_sparks_strong,
            early_rave=hot_sparks_gentle,
            golden_age=hot_sparks_gentle,
            music_vids=hot_sparks_gentle,
            hiphop=hot_sparks_gentle,
            blackout=hot_sparks_black,
        )
        self.hot_sparks = hot_sparks

        # Stage Blinders effects
        stage_blinders_strong = StageBlinders(
            num_blinders=10,
            attack_time=0.03,
            decay_time=0.25,
            opacity_multiplier=0.8,
        )
        stage_blinders_gentle = StageBlinders(
            num_blinders=6,
            attack_time=0.1,
            decay_time=0.5,
            opacity_multiplier=0.25,
        )
        stage_blinders_black = Black()

        stage_blinders = ModeSwitch(
            full_rave=stage_blinders_strong,
            early_rave=stage_blinders_gentle,
            golden_age=stage_blinders_gentle,
            music_vids=stage_blinders_gentle,
            hiphop=stage_blinders_gentle,
            blackout=stage_blinders_black,
        )
        self.stage_blinders = stage_blinders

        # Create final layer composition with mode-switched effects
        final_composition = LayerCompose(
            LayerSpec(mode_switch, BlendMode.NORMAL),  # Base: mode-specific content
            LayerSpec(
                hot_sparks, BlendMode.ADDITIVE, opacity=0.9
            ),  # Hot sparks: additive for glow effects
            LayerSpec(
                laser_scan_heads, BlendMode.ADDITIVE, opacity=1.0
            ),  # Laser scan heads: respond to small_blinder signal
            LayerSpec(
                stage_blinders, BlendMode.ADDITIVE, opacity=1.0
            ),  # Stage blinders: respond to big_blinder signal
            LayerSpec(
                color_strobe, BlendMode.ADDITIVE
            ),  # Color strobe: additive for flash effects
        )

        return final_composition

    def _create_virtual_moving_heads(self) -> MovingHeadArrayRenderer:
        placements: list[MovingHeadPlacement] = []
        fixtures: list[MovingHead] = []

        base_forward = self.camera_eye - self.camera_target
        base_forward = base_forward / np.linalg.norm(base_forward)

        offsets = [
            np.array([-5.0, 8.5, -1.0], dtype=np.float32),
            np.array([-1.5, 8.0, -1.5], dtype=np.float32),
            np.array([1.5, 8.0, -1.5], dtype=np.float32),
            np.array([5.0, 8.5, -1.0], dtype=np.float32),
        ]

        for idx, position in enumerate(offsets):
            forward = self.camera_target - position
            placements.append(MovingHeadPlacement(position=position, forward=forward))
            fixtures.append(
                ChauvetSpot160_12Ch(
                    patch=200 + idx * 16,
                    pan_lower=270,
                    pan_upper=450,
                    tilt_lower=0,
                    tilt_upper=90,
                )
            )

        def interpreter_factory(mode: Mode, group: list[MovingHead]):
            hype = 75 if mode == Mode.rave else 40
            args = InterpreterArgs(hype, True, 0, 100)
            return get_interpreter(mode, group, args)

        interpreter_node = FixtureInterpreterNode(
            fixtures=fixtures,
            interpreter_factory=interpreter_factory,
            initial_mode=Mode.rave,
        )

        return MovingHeadArrayRenderer(
            interpreter_node,
            placements=placements,
            camera_eye=self.camera_eye,
            camera_target=self.camera_target,
            camera_up=self.camera_up,
        )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the complete concert stage using ModeSwitch"""
        with vj_profiler.profile("concert_stage_render"):
            return self.mode_switch.render(frame, scheme, context)
