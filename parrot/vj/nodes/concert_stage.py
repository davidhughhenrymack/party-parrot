#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from typing import Optional
from beartype import beartype

from dataclasses import dataclass

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.mode_switch import ModeSwitch
from parrot.vj.nodes.color_strobe import ColorStrobe
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.hot_sparks_effect import HotSparksEffect
from parrot.vj.nodes.sparkle_field_effect import SparkleFieldEffect
from parrot.vj.nodes.stage_blinders import StageBlinders
from parrot.vj.nodes.laser_scan_heads import LaserScanHeads
from parrot.vj.nodes.text_renderer import TextRenderer, muro_font_path
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.crt_mask import CRTMask
from parrot.vj.nodes.bright_glow import BrightGlow
from parrot.director.frame import FrameSignal
from parrot.vj.profiler import vj_profiler
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.nodes.fixture_interpreter import (
    FixtureInterpreterNode,
    create_fixture_interpreter,
)
from parrot.vj.nodes.moving_head_array_renderer import (
    MovingHeadArrayRenderer,
    MovingHeadPlacement,
)
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.vj.vj_mode import VJMode
# NOTE: Zombie Rave (zr_*) scenes are disabled for now. Re-enable by uncommenting
# the zr_* entries in `VJMode` and wiring `build_zombie_rave_bundle` back into
# the ModeSwitch below. The helper is still available:
#   from parrot.vj.nodes.zombie_rave_stage import build_zombie_rave_bundle


@beartype
@dataclass(frozen=True)
class _PromSceneSpec:
    """Per-DJ prom scene recipe.

    `tint` drives `SparkleFieldEffect`'s palette. `video_fn_group`, when set,
    places a looping `VideoPlayer` (from `media/videos/<fn_group>/*/`) behind
    the sparkles with a music-video-style CRT effect stack; when `None` the
    scene is sparkles-only on a black background.
    """

    dj_name: str
    tint: tuple[float, float, float]
    video_fn_group: str | None = None


# Per-DJ prom scene recipes. DMACK gets the prom video backdrop; the other
# DJs stay on the original sparkles-only layout for now.
_PROM_SCENES: dict[VJMode, _PromSceneSpec] = {
    VJMode.prom_dmack: _PromSceneSpec(
        dj_name="dmack",
        tint=(1.0, 0.72, 0.18),  # warm gold
        video_fn_group="prom",
    ),
    VJMode.prom_wufky: _PromSceneSpec(
        dj_name="wufky", tint=(1.0, 0.25, 0.75)  # hot magenta
    ),
    VJMode.prom_mayhem: _PromSceneSpec(
        dj_name="mayhem", tint=(0.30, 0.55, 1.0)  # electric blue
    ),
    VJMode.prom_thunderbunny: _PromSceneSpec(
        dj_name="thunderbunny", tint=(0.50, 1.0, 0.35)  # neon green
    ),
}


@beartype
def _blackout_aware_overlay(
    effect: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
) -> ModeSwitch:
    """One physical effect for all lit modes; full black only on `VJMode.blackout`."""
    nodes: dict[str, BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]] = {
        m.name: effect for m in VJMode if m != VJMode.blackout
    }
    nodes[VJMode.blackout.name] = Black()
    return ModeSwitch(**nodes)


@beartype
def _build_prom_video_backdrop(
    fn_group: str,
) -> BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]:
    """Looping prom-footage backdrop with a gentle CRT / music-video effect stack.

    Modeled on the halloween ``zr_music_vids`` pipeline (see
    ``parrot/vj/nodes/zombie_rave_stage.py::create_crt_video_pipeline``) but
    tuned softer, since the sparkle field and Muro title sit on top of it —
    the video has to read as a *backdrop*, not the focal point.
    """
    video = VideoPlayer(fn_group=fn_group)
    with_rgb_shift = RGBShiftEffect(
        video, shift_strength=0.004, signal=FrameSignal.freq_high
    )
    with_scanlines = ScanlinesEffect(
        with_rgb_shift,
        scanline_intensity=0.18,
        scanline_count=420.0,
        signal=FrameSignal.sustained_low,
    )
    with_saturation = SaturationPulse(
        with_scanlines,
        base_saturation=1.15,
        intensity=0.4,
        signal=FrameSignal.sustained_low,
    )
    # Keep base brightness low so sparkles + title stay legible on top.
    with_brightness = BrightnessPulse(
        with_saturation,
        intensity=0.4,
        base_brightness=0.45,
        signal=FrameSignal.sustained_low,
    )
    with_zoom = CameraZoom(
        with_brightness,
        max_zoom=1.2,
        zoom_speed=1.8,
        return_speed=1.2,
        blur_intensity=0.15,
        signal=FrameSignal.sustained_low,
    )
    with_crt = CRTMask(with_zoom)
    return BrightGlow(
        with_crt,
        brightness_threshold=0.7,
        blur_radius=8,
        glow_intensity=0.12,
    )


@beartype
def _build_prom_scene(
    spec: _PromSceneSpec,
) -> BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]:
    """Optional video backdrop → sparkle field → DJ title in Muro.

    Sparkles render as black + colored specks, so stacking them with
    `BlendMode.ADDITIVE` lets the prom video read through where sparkles
    are dark. Title uses `SCREEN` the same way (white-on-black).
    """
    # Longer names (like "thunderbunny") need a smaller font to fit on screen.
    # Sized so the 12-char "thunderbunny" stays inside the frame with margin.
    font_size = 360 if len(spec.dj_name) <= 6 else 180
    sparkles = SparkleFieldEffect(tint=spec.tint)
    title = TextRenderer(
        text=spec.dj_name,
        font_name="Muro",
        font_path=muro_font_path(),
        font_size=font_size,
        text_color=(255, 245, 200),
        bg_color=(0, 0, 0),
    )

    if spec.video_fn_group is None:
        return LayerCompose(
            LayerSpec(sparkles, BlendMode.NORMAL),
            LayerSpec(title, BlendMode.SCREEN),
        )

    video_backdrop = _build_prom_video_backdrop(spec.video_fn_group)
    return LayerCompose(
        LayerSpec(video_backdrop, BlendMode.NORMAL),
        LayerSpec(sparkles, BlendMode.ADDITIVE),
        LayerSpec(title, BlendMode.SCREEN),
    )


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
        moving_head_renderer = self._create_virtual_moving_heads()
        self.moving_head_renderer = moving_head_renderer

        prom_scene_nodes: dict[
            str, BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
        ] = {
            vj_mode.name: _build_prom_scene(spec)
            for vj_mode, spec in _PROM_SCENES.items()
        }

        mode_switch = ModeSwitch(
            blackout=Black(),
            **prom_scene_nodes,
        )

        laser_scan_heads = _blackout_aware_overlay(
            LaserScanHeads(
                num_heads=5,
                beams_per_head=12,
                base_rotation_speed=0.35,
                base_tilt_speed=0.25,
                base_beam_spread=0.25,
                attack_time=0.08,
                decay_time=0.4,
                opacity_multiplier=0.65,
                head_placement_scheme="corners",
                allow_random_heads=True,
                allow_random_placement=True,
            )
        )
        self.laser_scan_heads = laser_scan_heads

        color_strobe = _blackout_aware_overlay(
            ColorStrobe(strobe_frequency=8.0, opacity_multiplier=0.6)
        )
        self.color_strobe = color_strobe

        hot_sparks = _blackout_aware_overlay(
            HotSparksEffect(num_sparks=350, opacity_multiplier=0.65)
        )
        self.hot_sparks = hot_sparks

        stage_blinders = _blackout_aware_overlay(
            StageBlinders(
                num_blinders=8,
                attack_time=0.05,
                decay_time=0.35,
                opacity_multiplier=0.4,
            )
        )
        self.stage_blinders = stage_blinders

        final_composition = LayerCompose(
            LayerSpec(mode_switch, BlendMode.NORMAL),
            LayerSpec(hot_sparks, BlendMode.ADDITIVE, opacity=0.9),
            LayerSpec(laser_scan_heads, BlendMode.ADDITIVE, opacity=1.0),
            LayerSpec(stage_blinders, BlendMode.ADDITIVE, opacity=1.0),
            LayerSpec(color_strobe, BlendMode.ADDITIVE),
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
            head = ChauvetSpot160_12Ch(
                patch=200 + idx * 16,
                pan_lower=270,
                pan_upper=450,
                tilt_lower=0,
                tilt_upper=90,
            )
            head.cloud_group_name = "Sheer lights"
            fixtures.append(head)

        def interpreter_factory(mode: Mode, group: list[MovingHead]):
            hype = 75 if mode == Mode.rave else 40
            args = InterpreterArgs(hype, True, 0, 100)
            return create_fixture_interpreter(mode, group, args)

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
