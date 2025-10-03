#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

import moderngl as mgl
import numpy as np
from beartype import beartype

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.fixtures.moving_head import MovingHead
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
from parrot.vj.constants import DEFAULT_HEIGHT, DEFAULT_WIDTH
from parrot.vj.utils.math_3d import (
    align_to_direction,
    create_scale_matrix,
    create_translation_matrix,
    look_at_matrix,
    perspective_matrix,
)


def _as_vec3(value: Iterable[float]) -> np.ndarray:
    vec = np.asarray(list(value), dtype=np.float32)
    if vec.shape != (3,):
        raise ValueError("Expected a 3D vector")
    return vec


@dataclass
class MovingHeadPlacement:
    position: np.ndarray
    forward: np.ndarray

    def __post_init__(self) -> None:
        self.position = _as_vec3(self.position)
        fwd = _as_vec3(self.forward)
        norm = np.linalg.norm(fwd)
        if norm < 1e-6:
            raise ValueError("Forward vector must be non-zero")
        self.forward = fwd / norm


def _cube_geometry() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.array(
        [
            # fmt: off
            -0.5, -0.5, -0.5,
             0.5, -0.5, -0.5,
             0.5,  0.5, -0.5,
            -0.5,  0.5, -0.5,
            -0.5, -0.5,  0.5,
             0.5, -0.5,  0.5,
             0.5,  0.5,  0.5,
            -0.5,  0.5,  0.5,
            # fmt: on
        ],
        dtype=np.float32,
    )

    indices = np.array(
        [
            0,
            1,
            2,
            2,
            3,
            0,
            4,
            5,
            6,
            6,
            7,
            4,
            0,
            4,
            5,
            5,
            1,
            0,
            3,
            2,
            6,
            6,
            7,
            3,
            0,
            3,
            7,
            7,
            4,
            0,
            1,
            5,
            6,
            6,
            2,
            1,
        ],
        dtype=np.uint32,
    )

    return vertices, indices


def _beam_geometry() -> np.ndarray:
    return np.array(
        [
            -0.5,
            -0.5,
            0.0,
            0.5,
            -0.5,
            0.0,
            -0.5,
            0.5,
            1.0,
            0.5,
            0.5,
            1.0,
        ],
        dtype=np.float32,
    )


@beartype
class MovingHeadArrayRenderer(
    BaseInterpretationNode[mgl.Context, List[MovingHead], mgl.Framebuffer]
):
    """Render a collection of moving heads with simple geometry."""

    def __init__(
        self,
        interpreter_node: BaseInterpretationNode[mgl.Context, None, List[MovingHead]],
        *,
        placements: List[MovingHeadPlacement],
        camera_eye: np.ndarray,
        camera_target: np.ndarray,
        camera_up: np.ndarray,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        body_size: float = 0.45,
        beam_length: float = 20.0,
        beam_width: float = 0.25,
    ):
        if len(placements) == 0:
            raise ValueError("placements must not be empty")
        super().__init__([interpreter_node])
        self._placements = placements
        self._camera_eye = _as_vec3(camera_eye)
        self._camera_target = _as_vec3(camera_target)
        self._camera_up = _as_vec3(camera_up)
        self.width = width
        self.height = height
        self.body_size = body_size
        self.beam_length = beam_length
        self.beam_width = beam_width

        self._context: mgl.Context | None = None
        self._framebuffer: mgl.Framebuffer | None = None
        self._color_texture: mgl.Texture | None = None
        self._depth_texture: mgl.Texture | None = None
        self._body_program: mgl.Program | None = None
        self._beam_program: mgl.Program | None = None
        self._cube_vao: mgl.VertexArray | None = None
        self._beam_vao: mgl.VertexArray | None = None

    def enter(self, context: mgl.Context) -> None:
        self._context = context
        self._allocate_framebuffer(context)
        self._create_programs(context)
        self._create_geometry(context)

    def exit(self) -> None:
        for resource in [
            self._framebuffer,
            self._color_texture,
            self._depth_texture,
            self._body_program,
            self._beam_program,
            self._cube_vao,
            self._beam_vao,
        ]:
            if resource is not None:
                resource.release()
        self._context = None
        self._framebuffer = None
        self._color_texture = None
        self._depth_texture = None
        self._body_program = None
        self._beam_program = None
        self._cube_vao = None
        self._beam_vao = None

    def _allocate_framebuffer(self, context: mgl.Context) -> None:
        self._color_texture = context.texture((self.width, self.height), 4)
        self._depth_texture = context.depth_texture((self.width, self.height))
        self._framebuffer = context.framebuffer(
            color_attachments=[self._color_texture],
            depth_attachment=self._depth_texture,
        )

    def _create_programs(self, context: mgl.Context) -> None:
        self._body_program = context.program(
            vertex_shader="""
            #version 330 core
            in vec3 in_position;
            uniform mat4 mvp;
            void main() {
                gl_Position = mvp * vec4(in_position, 1.0);
            }
            """,
            fragment_shader="""
            #version 330 core
            out vec4 frag_color;
            void main() {
                frag_color = vec4(0.06, 0.06, 0.06, 1.0);
            }
            """,
        )

        self._beam_program = context.program(
            vertex_shader="""
            #version 330 core
            in vec3 in_position;
            uniform mat4 mvp;
            void main() {
                gl_Position = mvp * vec4(in_position, 1.0);
            }
            """,
            fragment_shader="""
            #version 330 core
            uniform vec3 beam_color;
            uniform float beam_alpha;
            out vec4 frag_color;
            void main() {
                frag_color = vec4(beam_color, beam_alpha);
            }
            """,
        )

    def _create_geometry(self, context: mgl.Context) -> None:
        cube_vertices, cube_indices = _cube_geometry()
        cube_vbo = context.buffer(cube_vertices.tobytes())
        cube_ibo = context.buffer(cube_indices.tobytes())
        self._cube_vao = context.vertex_array(
            self._body_program,
            [(cube_vbo, "3f", "in_position")],
            cube_ibo,
        )

        beam_vertices = _beam_geometry()
        beam_vbo = context.buffer(beam_vertices.tobytes())
        self._beam_vao = context.simple_vertex_array(
            self._beam_program,
            beam_vbo,
            "in_position",
        )

    def _view_projection(self) -> tuple[np.ndarray, np.ndarray]:
        view = look_at_matrix(self._camera_eye, self._camera_target, self._camera_up)
        aspect = self.width / self.height
        projection = perspective_matrix(45.0, aspect, 0.1, 200.0)
        return view, projection

    def _fixtures(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> List[MovingHead]:
        child = self.children[0]
        fixtures = child.render(frame, scheme, context)
        if len(fixtures) != len(self._placements):
            raise ValueError("Fixture count does not match placement count")
        return fixtures

    def render(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: mgl.Context,
    ) -> mgl.Framebuffer | None:
        if self._framebuffer is None or self._body_program is None:
            self.enter(context)

        assert self._framebuffer is not None
        assert self._body_program is not None
        assert self._beam_program is not None
        assert self._cube_vao is not None
        assert self._beam_vao is not None

        fixtures = self._fixtures(frame, scheme, context)
        view, projection = self._view_projection()

        self._framebuffer.use()
        context.enable(mgl.DEPTH_TEST)
        context.enable(mgl.BLEND)
        context.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        context.clear(0.0, 0.0, 0.0, 0.0)

        for fixture, placement in zip(fixtures, self._placements):
            model_body = create_translation_matrix(
                placement.position
            ) @ create_scale_matrix(self.body_size)
            mvp_body = projection @ view @ model_body
            self._body_program["mvp"].write(mvp_body.astype(np.float32).tobytes())
            self._cube_vao.render()

            direction = self._beam_direction(placement.forward, fixture)
            model_beam = (
                create_translation_matrix(placement.position)
                @ align_to_direction(direction)
                @ create_scale_matrix(
                    np.array(
                        [self.beam_width, self.beam_width, self.beam_length],
                        dtype=np.float32,
                    )
                )
            )
            mvp_beam = projection @ view @ model_beam
            self._beam_program["mvp"].write(mvp_beam.astype(np.float32).tobytes())

            rgb = fixture.get_color().get_rgb()
            color_vec = np.array(rgb, dtype=np.float32) / 255.0
            dimmer = fixture.get_dimmer() / 255.0
            strobe = fixture.get_strobe()
            alpha = 0.0 if strobe > 0 and int(frame.time * strobe) % 2 == 0 else dimmer

            self._beam_program["beam_color"] = tuple(color_vec)
            self._beam_program["beam_alpha"] = alpha

            context.blend_func = (mgl.SRC_ALPHA, mgl.ONE)
            self._beam_vao.render(mgl.TRIANGLE_STRIP)
            context.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)

        context.disable(mgl.DEPTH_TEST)
        context.disable(mgl.BLEND)
        return self._framebuffer

    def _beam_direction(
        self, base_forward: np.ndarray, fixture: MovingHead
    ) -> np.ndarray:
        pan_rad = np.deg2rad(fixture.get_pan_angle())
        tilt_rad = np.deg2rad(fixture.get_tilt_angle())

        rot_y = np.array(
            [
                [np.cos(pan_rad), 0.0, np.sin(pan_rad)],
                [0.0, 1.0, 0.0],
                [-np.sin(pan_rad), 0.0, np.cos(pan_rad)],
            ],
            dtype=np.float32,
        )
        rot_x = np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, np.cos(tilt_rad), -np.sin(tilt_rad)],
                [0.0, np.sin(tilt_rad), np.cos(tilt_rad)],
            ],
            dtype=np.float32,
        )
        direction = rot_y @ rot_x @ base_forward
        norm = np.linalg.norm(direction)
        if norm < 1e-6:
            raise ValueError("Computed beam direction is degenerate")
        return direction / norm
