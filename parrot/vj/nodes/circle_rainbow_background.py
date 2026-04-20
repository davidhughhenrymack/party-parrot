#!/usr/bin/env python3
"""Fullscreen CircleRainbow feedback shader (after Shadertoy MsS3Wc) for prom backdrops."""

import time
from typing import Optional

import moderngl as mgl
import numpy as np
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_HEIGHT, DEFAULT_WIDTH


@beartype
class CircleRainbowBackground(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """Ping-pong feedback shader: rainbow dots on an oscillating ring with temporal blur."""

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        super().__init__([])
        self.width = width
        self.height = height
        self._t0 = time.perf_counter()
        self._read_idx = 0

        self._textures: list[Optional[mgl.Texture]] = [None, None]
        self._framebuffers: list[Optional[mgl.Framebuffer]] = [None, None]
        self.shader_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

    def enter(self, context: mgl.Context) -> None:
        self._setup_gl_resources(context)
        for i in (0, 1):
            assert self._framebuffers[i] is not None
            self._framebuffers[i].use()
            context.clear(0.0, 0.0, 0.0, 1.0)

    def exit(self) -> None:
        for i in (0, 1):
            if self._framebuffers[i]:
                self._framebuffers[i].release()
                self._framebuffers[i] = None
            if self._textures[i]:
                self._textures[i].release()
                self._textures[i] = None
        if self.shader_program:
            self.shader_program.release()
            self.shader_program = None
        if self.quad_vao:
            self.quad_vao.release()
            self.quad_vao = None

    def generate(self, vibe: Vibe) -> None:
        pass

    def _setup_gl_resources(self, context: mgl.Context) -> None:
        for i in (0, 1):
            if self._textures[i] is None:
                tex = context.texture((self.width, self.height), 4)
                tex.filter = (mgl.LINEAR, mgl.LINEAR)
                tex.repeat_x = False
                tex.repeat_y = False
                self._textures[i] = tex
                self._framebuffers[i] = context.framebuffer(color_attachments=[tex])

        if self.shader_program is None:
            vertex_shader = """
            #version 330 core
            in vec2 in_position;
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
            }
            """
            fragment_shader = """
            #version 330 core
            #define PI 3.14159265359
            #define MAX_POINTS 512

            uniform sampler2D iChannel0;
            uniform vec2 iResolution;
            uniform float iTime;

            out vec4 fragColor;

            vec3 hsv2rgb(in vec3 c) {
                vec3 rgb = clamp(abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0);
                rgb = rgb * rgb * (3.0 - 2.0 * rgb);
                return c.z * mix(vec3(1.0), rgb, c.y);
            }

            void main() {
                vec2 fragCoord = gl_FragCoord.xy;
                vec2 circle_center = iResolution * 0.5;
                float circle_radius = min(circle_center.x, circle_center.y);
                float point_radius = circle_radius / 16.0;
                int num_points = min(int(pow(2.0, floor(iTime / PI))), MAX_POINTS);

                // Previous frame: RGB decay + sample slightly toward UV center so old paint
                // very slowly creeps inward (tunnel / drain toward middle).
                const float FEEDBACK_DECAY = 0.993;
                const vec2 UV_CENTER = vec2(0.5, 0.5);
                const float FEEDBACK_PULL = 0.99965;
                vec2 uv = fragCoord.xy / iResolution.xy;
                vec2 uv_past = UV_CENTER + (uv - UV_CENTER) * FEEDBACK_PULL;
                vec3 past = texture(iChannel0, uv_past).rgb;
                fragColor = vec4(past * FEEDBACK_DECAY, 1.0);

                const float RADIUS_SCALE = 2.0;

                for (int point_index = 0; point_index < MAX_POINTS; point_index++) {
                    if (point_index >= num_points) {
                        break;
                    }
                    float point_angle = PI * float(point_index) / float(num_points);
                    vec2 dir = vec2(cos(point_angle), sin(point_angle));
                    float orbit = cos(iTime * 2.0 - point_angle);
                    // Slow sine mix on radius: global breathe + per-point phase (wide swing shrink/grow).
                    float radius_wobble = 1.0
                        + 0.28 * sin(iTime * 0.27)
                        + 0.22 * sin(iTime * 0.31 + point_angle * 2.7)
                        + 0.14 * sin(iTime * 0.18 - point_angle * 1.15);
                    vec2 point_center = circle_center
                        + dir * circle_radius * RADIUS_SCALE * orbit * radius_wobble;

                    float point_dist = length(fragCoord - point_center);
                    if (point_dist < point_radius) {
                        vec3 hsv = vec3(abs(sin(point_angle + iTime / 2.0)), 1.0, 1.0);
                        fragColor = mix(fragColor, vec4(hsv2rgb(hsv), 1.0), 0.5);
                    }
                }
            }
            """
            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if self.quad_vao is None:
            vertices = np.array(
                [
                    -1.0,
                    -1.0,
                    1.0,
                    -1.0,
                    -1.0,
                    1.0,
                    1.0,
                    1.0,
                ],
                dtype=np.float32,
            )
            vbo = context.buffer(vertices.tobytes())
            assert self.shader_program is not None
            self.quad_vao = context.vertex_array(
                self.shader_program, [(vbo, "2f", "in_position")]
            )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        if self._textures[0] is None or self.shader_program is None or self.quad_vao is None:
            self._setup_gl_resources(context)

        write_idx = 1 - self._read_idx
        read_tex = self._textures[self._read_idx]
        write_fb = self._framebuffers[write_idx]
        assert read_tex is not None and write_fb is not None

        i_time = time.perf_counter() - self._t0

        write_fb.use()
        rw = int(write_fb.width)
        rh = int(write_fb.height)
        context.viewport = (0, 0, rw, rh)
        read_tex.use(location=0)
        self.shader_program["iChannel0"] = 0
        self.shader_program["iResolution"] = (float(rw), float(rh))
        self.shader_program["iTime"] = float(i_time)
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        self._read_idx = write_idx
        return write_fb
