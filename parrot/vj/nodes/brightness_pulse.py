#!/usr/bin/env python3

from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase
from parrot.vj.utils.signal_utils import get_random_frame_signal


@beartype
class BrightnessPulse(PostProcessEffectBase):
    """
    A brightness modulation node that pulses the brightness of its input based on low frequencies.
    Takes a video input (framebuffer) and modulates its brightness using frame.freq_low.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        intensity: float = 0.8,
        base_brightness: float = 0.4,
        signal: FrameSignal = FrameSignal.freq_all,
        noise_intensity: float = 0.0,
    ):
        """
        Args:
            input_node: The node that provides the video input (e.g., VideoPlayer)
            intensity: How strong the pulse effect is (0.0 = no effect, 1.0 = full range)
            base_brightness: Minimum brightness level (0.0 = black, 1.0 = full brightness)
            signal: Which frame signal to use for modulation
            noise_intensity: Random noise applied to brightness for vintage effect (0.0 = no noise, 1.0 = max noise)
        """
        super().__init__(input_node)
        self.intensity = intensity
        self.base_brightness = base_brightness
        self.signal = signal
        self.noise_intensity = noise_intensity

    def generate(self, vibe: Vibe):
        """Configure brightness pulse parameters based on the vibe"""
        # Randomly pick a signal from available Frame signals
        self.signal = get_random_frame_signal()

    def print_self(self) -> str:
        """Return class name with current signal and brightness parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="💡",
            signal=self.signal,
            intensity=self.intensity,
            base=self.base_brightness,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for brightness modulation with vintage noise"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float brightness_multiplier;
        uniform float noise_intensity;
        uniform float time_offset;
        
        // High-quality pseudo-random function for vintage noise
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Apply base brightness modulation
            vec3 modulated_color = input_color * brightness_multiplier;
            
            // Add vintage brightness noise if enabled
            if (noise_intensity > 0.0) {
                // Generate per-pixel noise that changes over time
                vec2 noise_coords = uv + vec2(time_offset * 0.1, time_offset * 0.07);
                float brightness_noise = random(noise_coords);
                
                // Convert noise from 0-1 to -1 to +1 range
                brightness_noise = (brightness_noise - 0.5) * 2.0;
                
                // Apply noise to brightness
                float noise_multiplier = 1.0 + (brightness_noise * noise_intensity);
                
                // Clamp to prevent extreme values
                noise_multiplier = clamp(noise_multiplier, 0.1, 3.0);
                
                modulated_color *= noise_multiplier;
            }
            
            color = modulated_color;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set brightness effect uniforms"""
        import time

        # Calculate brightness multiplier based on signal
        signal_value = frame[self.signal]  # This should be 0.0 to 1.0

        # Map signal to brightness: base_brightness + (intensity * signal_value)
        brightness_multiplier = self.base_brightness + (self.intensity * signal_value)

        # Clamp to reasonable range
        brightness_multiplier = max(0.0, min(2.0, brightness_multiplier))

        # Set uniforms
        self.shader_program["brightness_multiplier"] = brightness_multiplier
        self.shader_program["noise_intensity"] = self.noise_intensity
        self.shader_program["time_offset"] = time.time()
