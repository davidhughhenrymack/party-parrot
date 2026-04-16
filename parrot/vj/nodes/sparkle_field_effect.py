#!/usr/bin/env python3
"""Full-screen procedural sparkles on a dark background (no video)."""

import time

import numpy as np
from beartype import beartype

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


_EMIT_HISTORY_MAX = 128
# Sparkles fade by ~2s; drop slightly later so the shader does not lose the tail.
_EMIT_HISTORY_TTL = 2.5


@beartype
class SparkleFieldEffect(GenerativeEffectBase):
    """Sparse golden sparkles: audio-driven spawn rate, sudden onset, exponential decay."""

    def __init__(self, width: int = 1920, height: int = 1080):
        super().__init__(width, height)
        self._t0 = time.perf_counter()
        self._last_emit_trigger_time = -1000.0
        self._last_emit_trigger_strength = 0.0
        self._emit_burst_id = 0
        # (trigger_time, strength, burst_id) — each latched trigger adds a row; shader sums fades.
        self._emit_history: list[tuple[float, float, int]] = []

    def generate(self, vibe: Vibe) -> None:
        """No-op; sparkles are driven in the fragment shader."""

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme) -> None:
        t = time.perf_counter() - self._t0
        high_signal = max(
            0.0,
            min(
                1.0,
                float(frame[FrameSignal.freq_high]) * 0.62
                + float(frame[FrameSignal.pulse]) * 0.26
                + float(frame[FrameSignal.strobe]) * 0.20,
            ),
        )
        if high_signal >= 0.42 and (t - self._last_emit_trigger_time) >= 0.12:
            self._last_emit_trigger_time = t
            self._last_emit_trigger_strength = high_signal
            self._emit_burst_id += 1
            self._emit_history.append((t, high_signal, self._emit_burst_id))
            if len(self._emit_history) > _EMIT_HISTORY_MAX:
                self._emit_history.pop(0)
        self._emit_history = [
            row for row in self._emit_history if t - row[0] <= _EMIT_HISTORY_TTL
        ]
        self._set_emit_history_uniforms()
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
    def _set_emit_history_uniforms(self) -> None:
        if not self.shader_program:
            return
        n = len(self._emit_history)
        times = np.zeros(_EMIT_HISTORY_MAX, dtype=np.float32)
        strengths = np.zeros(_EMIT_HISTORY_MAX, dtype=np.float32)
        burst_ids = np.zeros(_EMIT_HISTORY_MAX, dtype=np.float32)
        for i, (tt, strength, burst_id) in enumerate(self._emit_history):
            times[i] = tt
            strengths[i] = strength
            burst_ids[i] = float(burst_id)
        try:
            self.shader_program["u_emit_n"] = n
            self.shader_program["u_emit_times"].write(times.tobytes())
            self.shader_program["u_emit_strengths"].write(strengths.tobytes())
            self.shader_program["u_emit_burst_ids"].write(burst_ids.tobytes())
        except KeyError:
            pass

    def _get_fragment_shader(self) -> str:
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;

        uniform float time;
        uniform vec2 resolution;
        uniform vec4 u_audio;
        const int EMIT_HISTORY_MAX = 128;
        uniform int u_emit_n;
        uniform float u_emit_times[EMIT_HISTORY_MAX];
        uniform float u_emit_strengths[EMIT_HISTORY_MAX];
        uniform float u_emit_burst_ids[EMIT_HISTORY_MAX];

        float hash(vec2 p) {
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
        }

        float hash3(vec2 p, float z) {
            return hash(p + vec2(z * 17.0, z * 41.0));
        }

        float hash31(vec3 p) {
            return fract(
                937.276 * cos(
                    836.826 * p.x + 263.736 * p.y + 374.723 * p.z + 637.839
                )
            );
        }

        vec3 render_cell(
            vec2 p,
            float scale,
            vec2 cell,
            float lz,
            float trigger_time,
            float trigger_strength,
            float burst_id,
            vec3 goldDeep,
            vec3 goldMid,
            vec3 goldBright,
            vec3 glint
        ) {
            // Per-burst salt so each audio trigger picks different cells and sub-positions.
            vec2 burst_jitter = vec2(
                sin(burst_id * 12.9898 + lz * 3.1),
                cos(burst_id * 78.233 + lz * 5.7)
            ) * 83.0;
            vec2 ch = cell + burst_jitter;

            float id = hash3(ch, lz + 2.0 + burst_id * 0.01);

            // Per-burst sparkle center within cell (not fixed across triggers).
            vec2 local_center = vec2(hash3(ch, 1.0 + burst_id * 0.07), hash3(ch, 3.0 + burst_id * 0.05)) - 0.5;
            local_center *= 0.42;
            vec2 sparkle_center = (cell + 0.5 + local_center) / scale;
            vec2 pf = (p - sparkle_center) * scale;

            float ph = hash3(ch, 7.0 + burst_id * 0.03);
            // Emit only from latched high-audio triggers, then fade for ~2s.
            if (trigger_time < -900.0) {
                return vec3(0.0);
            }
            float trigger_prob = smoothstep(0.42, 0.95, trigger_strength) * 0.22;
            float roll = hash3(ch, 23.0 + lz * 7.0 + burst_id * 0.13);
            if (roll >= trigger_prob) {
                return vec3(0.0);
            }
            // Per-cell spawn time offset from the trigger (random locations/time staggering).
            float spawn_offset = (hash3(ch, 31.0 + lz * 11.0 + burst_id * 0.09) - 0.5) * 0.22;
            float spawn_time = trigger_time + spawn_offset;
            float age = time - spawn_time;
            if (age < 0.0 || age > 2.0) {
                return vec3(0.0);
            }
            // Fade curve lasts ~2 seconds after trigger.
            float tw = exp(-age * 1.6);

            // Sparkle shape inspired by folded-angle star glints.
            vec2 pp = pf * 2.4;
            float pi = 3.14159265;
            float sector = pi / 3.0; // 6-fold
            float an = mod(atan(pp.y, pp.x) + sector, sector) - (sector * 0.5);
            vec2 folded = vec2(cos(an), sin(an)) * length(pp);

            float sec = floor(time * 2.0);
            float frac = fract(time * 2.0);
            float flicker_a = hash31(vec3(ch, sec + lz * 13.0 + burst_id));
            float flicker_b = hash31(vec3(ch, sec + 1.0 + lz * 13.0 + burst_id));
            float flicker = mix(flicker_a, flicker_b, frac);

            float rad = 24.0 + 20.0 * flicker;
            float shape = sqrt(abs(folded.x)) + sqrt(abs(folded.y));
            float br = 205.0 * pow(1.0 / max(9.0, rad * shape + 0.9), 2.45);
            br *= (0.65 + 0.35 * id);

            float r = length(pp);
            float core = smoothstep(0.44, 0.0, r);
            float halo = smoothstep(1.35, 0.16, r) * 0.62;
            // Strong cross glint + broad glow, closer to reference shader feel.
            float ax = exp(-abs(pp.x) * (64.0 + 34.0 * ph)) * exp(-abs(pp.y) * (5.8 + 4.8 * ph));
            float ay = exp(-abs(pp.y) * (64.0 + 34.0 * ph)) * exp(-abs(pp.x) * (5.8 + 4.8 * ph));
            float cross = (ax + ay) * 1.15;
            float glow = exp(-r * 1.75) * 0.46;
            float s = (br * 0.72 + cross + core * 0.62 + halo * 0.55 + glow) * tw;

            vec3 tint = mix(goldDeep, goldMid, ph);
            tint = mix(tint, goldBright, clamp(br * 0.45 + core, 0.0, 1.0));
            tint = mix(tint, glint, clamp(core * 0.7 + br * 0.7, 0.0, 1.0));
            tint *= 0.96 + 0.10 * flicker;
            return tint * s;
        }

        void main() {
            vec2 p = uv * resolution;
            vec3 acc = vec3(0.0);

            vec3 goldDeep = vec3(0.92, 0.42, 0.02);
            vec3 goldMid = vec3(1.0, 0.72, 0.18);
            vec3 goldBright = vec3(1.0, 0.94, 0.55);
            vec3 glint = vec3(1.0, 0.98, 0.88);

            // Larger grid cells => fewer, bigger sparkles on screen.
            float scale = 0.0148;

            for (int layer = 0; layer < 3; layer++) {
                float lz = float(layer);
                // Keep field stable in position (no scrolling) to avoid erratic jumps.
                vec2 q = p * scale + vec2(lz * 29.0, lz * 19.0);
                vec2 cell = floor(q);
                // Sample neighboring cells so large sparkles are not clipped at cell edges.
                for (int oy = -1; oy <= 1; oy++) {
                    for (int ox = -1; ox <= 1; ox++) {
                        vec2 c = cell + vec2(float(ox), float(oy));
                        float layer_w = (0.8 + 0.7 * lz / 3.0);
                        for (int bi = 0; bi < u_emit_n; bi++) {
                            acc += render_cell(
                                p,
                                scale,
                                c,
                                lz,
                                u_emit_times[bi],
                                u_emit_strengths[bi],
                                u_emit_burst_ids[bi],
                                goldDeep,
                                goldMid,
                                goldBright,
                                glint
                            ) * layer_w;
                        }
                    }
                }
                scale *= 1.36;
            }

            color = min(acc, vec3(1.15));
        }
        """
