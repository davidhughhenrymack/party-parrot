#!/usr/bin/env python3
"""Full-screen procedural twinkling sparkles on a dark background (no video)."""

import time
from beartype import beartype

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


@beartype
class SparkleFieldEffect(GenerativeEffectBase):
    """Random soft sparkles with slow drift and twinkle, GPU-only."""

    def __init__(self, width: int = 1920, height: int = 1080):
        super().__init__(width, height)
        self._t0 = time.perf_counter()

    def generate(self, vibe: Vibe) -> None:
        """No-op; sparkles are driven in the fragment shader."""


    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme) -> None:
        t = time.perf_counter() - self._t0
        self._safe_set_uniform("time", float(t))
        self._safe_set_uniform("resolution", (float(self.width), float(self.height)))

    def _get_fragment_shader(self) -> str:
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;

        uniform float time;
        uniform vec2 resolution;

        float hash(vec2 p) {
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
        }

        float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            vec2 u = f * f * (3.0 - 2.0 * f);
            return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
        }

        void main() {
            vec2 p = uv * resolution;
            vec3 bg = mix(vec3(0.02, 0.02, 0.07), vec3(0.04, 0.03, 0.12), uv.y);
            vec3 acc = bg;

            float scale = 0.35;
            for (int layer = 0; layer < 4; layer++) {
                vec2 q = p * scale + vec2(float(layer) * 19.7, time * (0.03 + float(layer) * 0.02));
                vec2 cell = floor(q);
                vec2 f = fract(q) - 0.5;
                float h = hash(cell + float(layer) * 3.1);
                if (h > 0.72) {
                    float tw = 0.5 + 0.5 * sin(time * (2.0 + h * 4.0) + h * 40.0);
                    float d = length(f);
                    float s = smoothstep(0.35, 0.0, d) * tw * (0.15 + 0.85 * h);
                    vec3 tint = mix(vec3(0.85, 0.92, 1.0), vec3(1.0, 0.75, 0.95), h);
                    acc += tint * s * 0.55;
                }
                scale *= 1.65;
            }

            float n = noise(p * 0.004 + time * 0.01);
            acc += vec3(0.05, 0.06, 0.1) * n * 0.15;

            color = acc;
        }
        """
