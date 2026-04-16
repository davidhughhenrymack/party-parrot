#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from typing import Optional
from beartype import beartype

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
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.profiler import vj_profiler
from parrot.fixtures.moving_head import MovingHead
from parrot.director.mode_interpretations import get_interpreter
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.nodes.fixture_interpreter import FixtureInterpreterNode
from parrot.vj.nodes.moving_head_array_renderer import (
    MovingHeadArrayRenderer,
    MovingHeadPlacement,
)
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.vj.nodes.zombie_rave_stage import (
    build_zombie_rave_bundle,
    blackout_aware_overlay,
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
        bundle = build_zombie_rave_bundle()
        self.canvas_2d = bundle.canvas_2d
        self.oscilloscope = bundle.oscilloscope

        moving_head_renderer = self._create_virtual_moving_heads()
        self.moving_head_renderer = moving_head_renderer

        black_node = Black()

        prom_sparkles = SparkleFieldEffect()
        prom_title = TextRenderer(
            text="dmack",
            font_name="Chalkboard SE",
            font_size=200,
            text_color=(255, 248, 252),
            bg_color=(8, 10, 28),
        )
        prom_dmack_scene = LayerCompose(
            LayerSpec(prom_sparkles, BlendMode.NORMAL),
            LayerSpec(prom_title, BlendMode.NORMAL),
        )

        mode_switch = ModeSwitch(
            prom_dmack=prom_dmack_scene,
            zr_full_rave=bundle.rave_composition,
            zr_early_rave=bundle.zr_early_rave,
            blackout=black_node,
            zr_golden_age=bundle.zr_golden_age,
            zr_music_vids=bundle.zr_music_vids,
            zr_hiphop=bundle.zr_hiphop,
        )

        laser_scan_heads = blackout_aware_overlay(
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

        color_strobe = blackout_aware_overlay(
            ColorStrobe(strobe_frequency=8.0, opacity_multiplier=0.6)
        )
        self.color_strobe = color_strobe

        hot_sparks = blackout_aware_overlay(
            HotSparksEffect(num_sparks=350, opacity_multiplier=0.65)
        )
        self.hot_sparks = hot_sparks

        stage_blinders = blackout_aware_overlay(
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

