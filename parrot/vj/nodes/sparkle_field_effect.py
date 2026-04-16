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
    """Full-screen 2D field: sparse golden sparkles twinkle on black (GPU-only, not particles)."""

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

        float hash3(vec2 p, float z) {
            return hash(p + vec2(z * 17.0, z * 41.0));
        }

        void main() {
            vec2 p = uv * resolution;
            vec3 acc = vec3(0.0);

            vec3 goldDeep = vec3(0.92, 0.42, 0.02);
            vec3 goldMid = vec3(1.0, 0.72, 0.18);
            vec3 goldBright = vec3(1.0, 0.94, 0.55);
            vec3 glint = vec3(1.0, 0.98, 0.88);

            // Lower scale = fewer, larger grid cells (sparkles read bigger on screen).
            float scale = 0.038;
            for (int layer = 0; layer < 4; layer++) {
                float lz = float(layer);
                vec2 scroll = vec2(sin(time * 0.022 + lz) * 2.0, time * (0.012 + lz * 0.006));
                vec2 q = p * scale + scroll + vec2(lz * 23.7, lz * 11.3);
                vec2 cell = floor(q);
                vec2 f = fract(q) - 0.5;

                float id = hash3(cell, lz + 2.0);
                if (id >= 0.935) {
                    vec2 j = vec2(hash3(cell, 1.0), hash3(cell, 3.0)) - 0.5;
                    j *= 0.38;
                    vec2 pf = f - j;

                    float ph = hash3(cell, 7.0);
                    // Slow twinkle (longer-lived brightness cycles)
                    float tw = 0.42 + 0.58 * sin(time * (0.35 + ph * 0.9) + ph * 47.0);
                    float slow = 0.82 + 0.18 * sin(time * 0.11 + float(layer) + ph * 3.1);
                    tw *= slow;

                    float r = length(pf);
                    // Wider core + halo so each sparkle is visibly larger
                    float core = smoothstep(0.42, 0.0, r);
                    float halo = smoothstep(0.62, 0.12, r) * 0.42;

                    float ax = exp(-abs(pf.x) * (95.0 + 55.0 * ph)) * exp(-abs(pf.y) * (12.0 + 10.0 * ph));
                    float ay = exp(-abs(pf.y) * (95.0 + 55.0 * ph)) * exp(-abs(pf.x) * (12.0 + 10.0 * ph));
                    float star = (ax + ay) * 0.62;

                    float s = (core * 1.2 + halo + star) * tw * (0.35 + 0.65 * id);

                    vec3 tint = mix(goldDeep, goldMid, ph);
                    tint = mix(tint, goldBright, core);
                    tint = mix(tint, glint, pow(core, 3.0));

                    acc += tint * s * (0.4 + 0.6 * float(layer) / 4.0);
                }
                scale *= 1.42;
            }

            color = min(acc, vec3(1.15));
        }
        """
