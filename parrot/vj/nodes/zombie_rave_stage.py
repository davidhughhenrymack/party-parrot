#!/usr/bin/env python3
"""Zombie Rave event VJ compositions (zr_* modes). Built for use inside `ConcertStage`."""

from __future__ import annotations

from dataclasses import dataclass

import moderngl as mgl
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, RandomChild, RandomOperation
from parrot.director.frame import FrameSignal
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
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.vintage_film_mask import VintageFilmMask
from parrot.vj.nodes.crt_mask import CRTMask
from parrot.vj.nodes.bright_glow import BrightGlow
from parrot.vj.nodes.sepia_effect import SepiaEffect
from parrot.vj.nodes.glow_effect import GlowEffect
from parrot.vj.nodes.bloom_filter import BloomFilter
from parrot.vj.vj_mode import VJMode
from parrot.vj.nodes.camera_zoom import CameraZoom


@dataclass(frozen=True)
class ZombieRaveBundle:
    """Scene roots and exposed nodes for tests / introspection."""

    canvas_2d: CameraZoom
    oscilloscope: OscilloscopeEffect
    rave_composition: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
    zr_golden_age: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
    zr_early_rave: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
    zr_music_vids: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
    zr_hiphop: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]


@beartype
def blackout_aware_overlay(
    effect: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
) -> ModeSwitch:
    """One physical effect for all lit modes; full black only on `VJMode.blackout`."""
    black = Black()
    nodes: dict[str, BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]] = {
        m.name: effect for m in VJMode if m != VJMode.blackout
    }
    nodes[VJMode.blackout.name] = black
    return ModeSwitch(**nodes)


@beartype
def build_zombie_rave_bundle() -> ZombieRaveBundle:
    black_background = Black()

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
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )
    text_masked_video_no_fx = MultiplyCompose(video_player, text_renderer)

    black_text_renderer = TextRenderer(
        text=zombie_texts,
        font_name="The Sonnyfive",
        font_size=180,
        text_color=(0, 0, 0),
        bg_color=(255, 255, 255),
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
    black_text_renderer = CameraZoom(black_text_renderer, signal=FrameSignal.freq_high)

    video_with_black_text = LayerCompose(
        LayerSpec(video_with_fx, BlendMode.NORMAL),
        LayerSpec(black_text_renderer, BlendMode.MULTIPLY),
    )

    optional_masked_video = RandomChild([video_with_fx, video_with_black_text])

    canvas_2d = CameraZoom(optional_masked_video)

    oscilloscope = OscilloscopeEffect()
    optional_oscilloscope = RandomChild([oscilloscope, Black()], weights=[0.05, 0.95])

    base_layers = LayerCompose(
        LayerSpec(black_background, BlendMode.NORMAL),
        LayerSpec(optional_oscilloscope, BlendMode.ADDITIVE, opacity=0.3),
        LayerSpec(canvas_2d, BlendMode.NORMAL),
    )

    rave_composition = BrightnessPulse(
        base_layers,
        intensity=1.0,
        base_brightness=0.1,
        signal=FrameSignal.freq_high,
    )

    chill_video_player = VideoPlayer(fn_group="bg_chill")
    gentle_noise_effect = NoiseEffect(
        chill_video_player,
        noise_intensity=0.15,
        noise_scale=100.0,
        static_lines=True,
        color_noise=True,
        signal=FrameSignal.sustained_low,
    )

    chill_video_with_gentle_zoom = CameraZoom(
        gentle_noise_effect,
        max_zoom=1.3,
        zoom_speed=2.0,
        return_speed=1.5,
        blur_intensity=0.2,
        signal=FrameSignal.sustained_low,
    )

    chill_video_masked = VintageFilmMask(chill_video_with_gentle_zoom)

    chill_video_with_sepia = SepiaEffect(
        chill_video_masked,
        base_intensity=0.4,
        max_intensity=0.8,
        signal=FrameSignal.sustained_low,
    )

    chill_video_with_pulse = BrightnessPulse(
        chill_video_with_sepia,
        intensity=0.3,
        base_brightness=0.55,
        signal=FrameSignal.sustained_low,
    )

    zr_golden_age = BloomFilter(
        chill_video_with_pulse,
        base_intensity=0.3,
        max_intensity=0.6,
        bloom_radius=3.0,
        threshold=0.25,
        signal=FrameSignal.sustained_low,
        blur_passes=2,
    )

    gentle_brightness_pulse = BrightnessPulse(
        text_masked_video_no_fx,
        intensity=0.5,
        base_brightness=0.6,
        signal=FrameSignal.sustained_low,
    )

    gentle_glow_effect = GlowEffect(
        text_masked_video_no_fx,
        base_intensity=0.3,
        max_intensity=0.7,
        glow_radius=6.0,
        threshold=0.5,
        signal=FrameSignal.sustained_low,
    )

    gentle_bloom_effect = BloomFilter(
        text_masked_video_no_fx,
        base_intensity=0.4,
        max_intensity=0.7,
        bloom_radius=4.0,
        threshold=0.3,
        signal=FrameSignal.sustained_low,
        blur_passes=2,
    )

    gentle_with_effect = RandomChild(
        [gentle_brightness_pulse, gentle_glow_effect, gentle_bloom_effect]
    )

    zr_early_rave = CameraZoom(
        gentle_with_effect,
        max_zoom=1.2,
        zoom_speed=1.5,
        return_speed=1.0,
        blur_intensity=0.1,
        signal=FrameSignal.sustained_low,
    )

    def create_crt_video_pipeline(fn_group: str):
        vplayer = VideoPlayer(fn_group=fn_group)
        with_rgb = RGBShiftEffect(
            vplayer,
            shift_strength=0.006,
            signal=FrameSignal.freq_high,
        )
        with_scanlines = ScanlinesEffect(
            with_rgb,
            scanline_intensity=0.25,
            scanline_count=400.0,
            signal=FrameSignal.sustained_low,
        )
        with_saturation = SaturationPulse(
            with_scanlines,
            base_saturation=1.2,
            intensity=0.6,
            signal=FrameSignal.sustained_low,
        )
        with_brightness = BrightnessPulse(
            with_saturation,
            intensity=0.7,
            base_brightness=0.5,
            signal=FrameSignal.sustained_low,
        )
        with_zoom = CameraZoom(
            with_brightness,
            max_zoom=1.4,
            zoom_speed=3.0,
            return_speed=2.0,
            blur_intensity=0.3,
            signal=FrameSignal.sustained_low,
        )
        with_crt = CRTMask(with_zoom)
        return BrightGlow(
            with_crt,
            brightness_threshold=0.75,
            blur_radius=8,
            glow_intensity=0.1,
        )

    zr_music_vids = create_crt_video_pipeline("bg_music_vid")
    zr_hiphop = create_crt_video_pipeline("bg_hiphop")

    return ZombieRaveBundle(
        canvas_2d=canvas_2d,
        oscilloscope=oscilloscope,
        rave_composition=rave_composition,
        zr_golden_age=zr_golden_age,
        zr_early_rave=zr_early_rave,
        zr_music_vids=zr_music_vids,
        zr_hiphop=zr_hiphop,
    )
