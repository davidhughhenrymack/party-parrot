#!/usr/bin/env python3

import time
import random
import math
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class BeatHueShift(PostProcessEffectBase):
    """
    Beat-synchronized hue shifting effect that changes color filter on each beat.
    Cycles through different hues creating dynamic color transformations.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        hue_shift_amount: float = 60.0,
        saturation_boost: float = 1.2,
        transition_speed: float = 8.0,
        random_hues: bool = True,
        signal: FrameSignal = FrameSignal.pulse,
    ):
        """
        Args:
            input_node: The node that provides the video input
            hue_shift_amount: Degrees to shift hue on each beat (0-360)
            saturation_boost: Multiply saturation (1.0 = no change, >1.0 = more vibrant)
            transition_speed: Speed of hue transitions (higher = faster)
            random_hues: If True, pick random hues; if False, cycle through spectrum
            signal: Beat signal that triggers hue changes
        """
        super().__init__(input_node)
        self.hue_shift_amount = hue_shift_amount
        self.saturation_boost = saturation_boost
        self.transition_speed = transition_speed
        self.random_hues = random_hues
        self.signal = signal

        # State for beat detection and hue cycling
        self.current_target_hue = 0.0
        self.current_hue = 0.0
        self.last_beat_time = time.time()
        self.last_signal_value = 0.0
        self.beat_detected = False

        # Predefined hue sequence for non-random mode
        self.hue_sequence = [
            0,
            60,
            120,
            180,
            240,
            300,
        ]  # Red, Yellow, Green, Cyan, Blue, Magenta
        self.hue_index = 0

    def generate(self, vibe: Vibe):
        """Configure hue shift parameters based on the vibe"""
        # Randomly pick a signal from available Frame signals
        available_signals = [
            FrameSignal.freq_all,
            FrameSignal.freq_high,
            FrameSignal.freq_low,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
            FrameSignal.strobe,
            FrameSignal.big_blinder,
            FrameSignal.small_blinder,
            FrameSignal.pulse,
            FrameSignal.dampen,
        ]
        self.signal = random.choice(available_signals)

    def print_self(self) -> str:
        """Return class name with current signal in brackets"""
        return format_node_status(
            self.__class__.__name__,
            emoji="🌈",
            signal=self.signal,
        )

    def _detect_beat(self, signal_value: float) -> bool:
        """Simple beat detection based on signal threshold crossing"""
        current_time = time.time()

        # Detect rising edge (beat)
        beat_threshold = 0.7
        min_beat_interval = 0.1  # Minimum 100ms between beats

        if (
            signal_value > beat_threshold
            and self.last_signal_value <= beat_threshold
            and current_time - self.last_beat_time > min_beat_interval
        ):

            self.last_beat_time = current_time
            self.last_signal_value = signal_value
            return True

        self.last_signal_value = signal_value
        return False

    def _get_next_hue(self) -> float:
        """Get the next hue value in the sequence"""
        if self.random_hues:
            # Random hue
            return random.uniform(0.0, 360.0)
        else:
            # Cycle through predefined sequence
            hue = self.hue_sequence[self.hue_index]
            self.hue_index = (self.hue_index + 1) % len(self.hue_sequence)
            return float(hue)

    def _get_fragment_shader(self) -> str:
        """Fragment shader for beat-synchronized hue shifting"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float target_hue;
        uniform float current_hue;
        uniform float saturation_boost;
        uniform float transition_progress;
        
        // Convert RGB to HSV
        vec3 rgb2hsv(vec3 c) {
            vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
            vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
            vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
            
            float d = q.x - min(q.w, q.y);
            float e = 1.0e-10;
            return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
        }
        
        // Convert HSV to RGB
        vec3 hsv2rgb(vec3 c) {
            vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
            vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
            return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
        }
        
        // Smooth hue interpolation (handles 360-degree wraparound)
        float interpolate_hue(float from_hue, float to_hue, float t) {
            float diff = to_hue - from_hue;
            
            // Handle wraparound
            if (diff > 180.0) {
                diff -= 360.0;
            } else if (diff < -180.0) {
                diff += 360.0;
            }
            
            float result = from_hue + diff * t;
            
            // Normalize to 0-360 range
            if (result < 0.0) {
                result += 360.0;
            } else if (result >= 360.0) {
                result -= 360.0;
            }
            
            return result;
        }
        
        void main() {
            // Sample the input texture
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Convert to HSV
            vec3 hsv = rgb2hsv(input_color);
            
            // Interpolate between current and target hue
            float interpolated_hue = interpolate_hue(current_hue, target_hue, transition_progress);
            
            // Apply hue shift
            hsv.x = interpolated_hue / 360.0; // Normalize to 0-1 range for HSV
            
            // Boost saturation for more vibrant colors
            hsv.y *= saturation_boost;
            hsv.y = clamp(hsv.y, 0.0, 1.0);
            
            // Convert back to RGB
            color = hsv2rgb(hsv);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set beat hue shift effect uniforms"""
        # Get signal value for beat detection
        signal_value = frame[self.signal]

        # Special responses to specific Frame signals
        strobe_value = frame[FrameSignal.strobe]
        big_blinder_value = frame[FrameSignal.big_blinder]
        pulse_value = frame[FrameSignal.pulse]

        # STROBE: Rapid hue cycling
        if strobe_value > 0.5:
            # Force rapid hue changes during strobe
            current_time = time.time()
            strobe_hue = (
                current_time * 360.0 * 4.0
            ) % 360.0  # 4 full cycles per second
            self.current_target_hue = strobe_hue
            self.current_hue = strobe_hue

        # BIG BLINDER: Desaturate to white/bright
        elif big_blinder_value > 0.5:
            # Force to white/bright colors during big blinder
            self.current_target_hue = 0.0  # Red base
            self.current_hue = 0.0

        # PULSE: Instant hue snap
        elif pulse_value > 0.5:
            # Instant hue change on strong pulse
            self.current_target_hue = self._get_next_hue()
            self.current_hue = self.current_target_hue

        else:
            # Normal beat detection behavior
            if self._detect_beat(signal_value):
                self.beat_detected = True
                # Get next hue in sequence
                self.current_target_hue = self._get_next_hue()

        # Smooth transition between hues (except during special signals)
        if strobe_value <= 0.5 and big_blinder_value <= 0.5 and pulse_value <= 0.5:
            current_time = time.time()
            dt = min(
                current_time - getattr(self, "_last_update_time", current_time),
                1.0 / 30.0,
            )
            self._last_update_time = current_time

            # Calculate transition progress
            hue_diff = abs(self.current_target_hue - self.current_hue)
            if hue_diff > 180.0:  # Handle wraparound
                hue_diff = 360.0 - hue_diff

            # Smooth interpolation towards target hue
            transition_rate = self.transition_speed * dt

            if hue_diff > 1.0:  # Still transitioning
                # Calculate shortest path between hues
                diff = self.current_target_hue - self.current_hue
                if diff > 180.0:
                    diff -= 360.0
                elif diff < -180.0:
                    diff += 360.0

                # Move towards target
                self.current_hue += diff * transition_rate

                # Normalize
                if self.current_hue < 0.0:
                    self.current_hue += 360.0
                elif self.current_hue >= 360.0:
                    self.current_hue -= 360.0
            else:
                self.current_hue = self.current_target_hue

        # Calculate transition progress for smooth interpolation in shader
        hue_diff = abs(self.current_target_hue - self.current_hue)
        if hue_diff > 180.0:  # Handle wraparound
            hue_diff = 360.0 - hue_diff
        transition_progress = 1.0 - (hue_diff / 180.0)  # 0 = far apart, 1 = same hue
        transition_progress = max(0.0, min(1.0, transition_progress))

        # Modify saturation based on special signals
        saturation_boost = self.saturation_boost
        if big_blinder_value > 0.5:
            # Reduce saturation during big blinder for white-out effect
            saturation_boost = 0.1
        elif strobe_value > 0.5:
            # Boost saturation during strobe for intense colors
            saturation_boost = min(2.0, self.saturation_boost * 1.5)

        # Set uniforms
        self.shader_program["target_hue"] = self.current_target_hue
        self.shader_program["current_hue"] = self.current_hue
        self.shader_program["saturation_boost"] = saturation_boost
        self.shader_program["transition_progress"] = transition_progress
