#!/usr/bin/env python3

import time
import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class TextColorPulse(PostProcessEffectBase):
    """
    A text color modulation effect that changes the color of non-alpha-0 pixels (text)
    based on pulse signals. The effect builds intensity during pulse signals and decays
    when the pulse signal is low. Colors are selected from the color scheme.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        intensity: float = 1.0,
        decay_rate: float = 0.95,
        signal: FrameSignal = FrameSignal.pulse,
    ):
        """
        Args:
            input_node: The node that provides the text input (e.g., TextRenderer)
            intensity: How strong the color effect is (0.0 = no effect, 1.0 = full color)
            decay_rate: How fast the effect decays when pulse is low (0.0 = instant, 1.0 = no decay)
            signal: Which frame signal to use for pulse detection
        """
        super().__init__(input_node)
        self.intensity = intensity
        self.decay_rate = decay_rate
        self.signal = signal

        # State tracking for pulse buildup and decay
        self.current_pulse_intensity = 0.0
        self.last_update_time = time.time()

        # Color selection from scheme
        self.current_color_index = 0
        self.color_change_threshold = 0.7  # Change color when pulse exceeds this

    def generate(self, vibe: Vibe):
        """Configure text color pulse parameters based on the vibe"""
        # Randomly pick a signal from pulse-related Frame signals
        pulse_signals = [
            FrameSignal.pulse,
            FrameSignal.freq_low,
            FrameSignal.freq_high,
            FrameSignal.freq_all,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
        ]
        self.signal = random.choice(pulse_signals)

        # Randomize intensity and decay parameters
        self.intensity = random.uniform(0.6, 1.0)
        self.decay_rate = random.uniform(0.85, 0.98)
        self.color_change_threshold = random.uniform(0.5, 0.8)

    def print_self(self) -> str:
        """Return class name with current signal in brackets"""
        return f"{self.__class__.__name__} [{self.signal.name}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for text color modulation"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform vec3 pulse_color;
        uniform float pulse_intensity;
        uniform float color_mix_factor;
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Calculate luminance to detect text vs background
            float luminance = dot(input_color, vec3(0.299, 0.587, 0.114));
            
            // If pixel is not black (i.e., it's text), apply color modulation
            if (luminance > 0.01) {
                // Mix original color with pulse color based on pulse intensity
                vec3 modulated_color = mix(input_color, pulse_color, color_mix_factor * pulse_intensity);
                color = modulated_color;
            } else {
                // Keep background pixels unchanged
                color = input_color;
            }
        }
        """

    def _update_pulse_state(self, frame: Frame):
        """Update the pulse intensity state with buildup and decay"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Get current signal value
        signal_value = frame[self.signal]

        # Build up intensity when signal is strong
        if signal_value > 0.3:
            # Quick buildup during pulse
            target_intensity = signal_value * self.intensity
            buildup_rate = 8.0  # Fast buildup
            self.current_pulse_intensity += (
                (target_intensity - self.current_pulse_intensity) * buildup_rate * dt
            )
            self.current_pulse_intensity = min(
                self.current_pulse_intensity, target_intensity
            )

            # Change color if pulse is strong enough
            if signal_value > self.color_change_threshold:
                self.current_color_index = (
                    self.current_color_index + 1
                ) % 3  # Cycle through fg, bg, bg_contrast
        else:
            # Decay when signal is low
            self.current_pulse_intensity *= self.decay_rate ** (
                dt * 60
            )  # Decay rate per second at 60fps
            self.current_pulse_intensity = max(0.0, self.current_pulse_intensity)

    def _get_pulse_color(self, scheme: ColorScheme) -> tuple[float, float, float]:
        """Get the current pulse color from the color scheme"""
        colors = [scheme.fg, scheme.bg, scheme.bg_contrast]
        selected_color = colors[self.current_color_index]
        return selected_color.rgb

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set text color pulse effect uniforms"""
        # Update pulse state
        self._update_pulse_state(frame)

        # Get pulse color from scheme
        pulse_color = self._get_pulse_color(scheme)

        # Calculate color mix factor based on pulse intensity
        # When pulse_intensity is 0, no color mixing (original text)
        # When pulse_intensity is 1, full color mixing (pure pulse color)
        color_mix_factor = self.current_pulse_intensity

        # Set uniforms
        self.shader_program["pulse_color"] = pulse_color
        self.shader_program["pulse_intensity"] = self.current_pulse_intensity
        self.shader_program["color_mix_factor"] = color_mix_factor
