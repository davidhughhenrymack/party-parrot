#!/usr/bin/env python3
"""Full-screen procedural sparkles on a dark background (no video)."""

import time
from beartype import beartype

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


@beartype
class SparkleFieldEffect(GenerativeEffectBase):
    """Sparse golden sparkles: audio-driven spawn rate, sudden onset, exponential decay."""

    def __init__(self, width: int = 1920, height: int = 1080):
        super().__init__(width, height)
        self._t0 = time.perf_counter()

    def generate(self, vibe: Vibe) -> None:
        """No-op; sparkles are driven in the fragment shader."""

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme) -> None:
        t = time.perf_counter() - self._t0
        self._safe_set_uniform("time", float(t))
        self._safe_set_uniform("resolution", (float(self.width), float(self.height)))
        self._safe_set_uniform(
            "u_audio",
            (
                float(frame[FrameSignal.freq_low]),
                float(frame[FrameSignal.freq_high]),
                float(frame[FrameSignal.pulse]),
                float(frame[FrameSignal.strobe]),
            ),
        )

    def _get_fragment_shader(self) -> str:
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;

        uniform float time;
        uniform vec2 resolution;
        uniform vec4 u_audio;

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

            // Drive 0..1 from audio — controls how many sparkles fire and how fast they repeat.
            float drive = clamp(
                u_audio.x * 0.18 + u_audio.y * 0.36 + u_audio.z * 0.38 + u_audio.w * 0.22,
                0.0, 1.0);

            // Fewer sparkles at rest; more when the mix is hot (lower hash cutoff).
            float spawn_thresh = 0.972 - drive * 0.038;

            // Larger grid cells => fewer, bigger sparkles on screen.
            float scale = 0.0148;

            for (int layer = 0; layer < 3; layer++) {
                float lz = float(layer);
                vec2 scroll = vec2(
                    sin(time * 0.009 + lz) * 0.55,
                    time * (0.0025 + u_audio.y * 0.012));
                vec2 q = p * scale + scroll + vec2(lz * 29.0, lz * 19.0);
                vec2 cell = floor(q);
                vec2 f = fract(q) - 0.5;

                float id = hash3(cell, lz + 2.0);
                if (id >= spawn_thresh) {
                    vec2 j = vec2(hash3(cell, 1.0), hash3(cell, 3.0)) - 0.5;
                    j *= 0.34;
                    vec2 pf = f - j;

                    float ph = hash3(cell, 7.0);
                    // Burst rate rises with audio, but kept slower against wall-clock time.
                    float spd = (0.26 + ph * 0.44) * (0.24 + drive * 0.95);
                    float cycle = fract(time * spd + ph * 19.0 + lz * 4.1);
                    // Sudden peak at cycle=0, then exponential decay (no sinusoidal fade-in).
                    float decay_k = 3.2 + drive * 5.6;
                    float tw = exp(-cycle * decay_k);

                    float r = length(pf);
                    float core = smoothstep(0.56, 0.0, r);
                    float halo = smoothstep(0.84, 0.12, r) * 0.4;

                    float ax = exp(-abs(pf.x) * (88.0 + 50.0 * ph)) * exp(-abs(pf.y) * (11.0 + 9.0 * ph));
                    float ay = exp(-abs(pf.y) * (88.0 + 50.0 * ph)) * exp(-abs(pf.x) * (11.0 + 9.0 * ph));
                    float star = (ax + ay) * 0.6;

                    float s = (core * 1.28 + halo + star) * tw * (0.42 + 0.58 * id);

                    vec3 tint = mix(goldDeep, goldMid, ph);
                    tint = mix(tint, goldBright, core);
                    tint = mix(tint, glint, pow(core, 3.0));

                    acc += tint * s * (0.45 + 0.55 * lz / 3.0);
                }
                scale *= 1.36;
            }

            color = min(acc, vec3(1.15));
        }
        """
