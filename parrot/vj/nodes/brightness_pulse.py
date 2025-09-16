#!/usr/bin/env python3

from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


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
        base_brightness: float = 0.2,
        signal: FrameSignal = FrameSignal.freq_all,
    ):
        """
        Args:
            input_node: The node that provides the video input (e.g., VideoPlayer)
            intensity: How strong the pulse effect is (0.0 = no effect, 1.0 = full range)
            base_brightness: Minimum brightness level (0.0 = black, 1.0 = full brightness)
            signal: Which frame signal to use for modulation
        """
        super().__init__(input_node)
        self.intensity = intensity
        self.base_brightness = base_brightness
        self.signal = signal

    def generate(self, vibe: Vibe):
        """Configure brightness pulse parameters based on the vibe"""
        # Could randomize intensity and base_brightness based on vibe.mode
        # For now, keep the initialized values
        pass

    def _get_fragment_shader(self) -> str:
        """Fragment shader for brightness modulation"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float brightness_multiplier;
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            color = input_color * brightness_multiplier;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set brightness effect uniforms"""
        # Calculate brightness multiplier based on signal
        signal_value = frame[self.signal]  # This should be 0.0 to 1.0

        # Map signal to brightness: base_brightness + (intensity * signal_value)
        brightness_multiplier = self.base_brightness + (self.intensity * signal_value)

        # Clamp to reasonable range
        brightness_multiplier = max(0.0, min(2.0, brightness_multiplier))

        self.shader_program["brightness_multiplier"] = brightness_multiplier
