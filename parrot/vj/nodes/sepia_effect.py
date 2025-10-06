#!/usr/bin/env python3

import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase
from parrot.vj.utils.signal_utils import get_random_frame_signal


@beartype
class SepiaEffect(PostProcessEffectBase):
    """
    A sepia tone effect that applies vintage sepia coloring to the input video.
    The intensity of the sepia effect responds to frame signals for dynamic vintage feel.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        base_intensity: float = 0.3,
        max_intensity: float = 0.8,
        signal: FrameSignal = FrameSignal.sustained_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            base_intensity: Minimum sepia intensity (0.0 = no sepia, 1.0 = full sepia)
            max_intensity: Maximum sepia intensity when signal is high
            signal: Which frame signal modulates the sepia intensity
        """
        super().__init__(input_node)
        self.base_intensity = base_intensity
        self.max_intensity = max_intensity
        self.signal = signal

    def generate(self, vibe: Vibe):
        """Configure sepia parameters based on the vibe"""
        self.signal = get_random_frame_signal()

        # Vary sepia intensity parameters for organic feel
        self.base_intensity = random.uniform(0.2, 0.5)
        self.max_intensity = random.uniform(0.6, 0.9)

    def print_self(self) -> str:
        """Return class name with current signal and intensity parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="📷",
            signal=self.signal,
            base=self.base_intensity,
            max=self.max_intensity,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for sepia effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float sepia_intensity;
        
        void main() {
            // Sample the input texture
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Calculate luminance for sepia conversion
            float luminance = dot(input_color, vec3(0.299, 0.587, 0.114));
            
            // Classic sepia tone colors
            vec3 sepia_color = vec3(
                luminance * 1.2,     // Red channel - warm highlights
                luminance * 1.0,     // Green channel - mid tones
                luminance * 0.8      // Blue channel - reduced for warmth
            );
            
            // Alternative sepia calculation using color matrix
            // This gives more authentic sepia tones
            vec3 sepia_alt = vec3(
                dot(input_color, vec3(0.393, 0.769, 0.189)),  // Red
                dot(input_color, vec3(0.349, 0.686, 0.168)),  // Green
                dot(input_color, vec3(0.272, 0.534, 0.131))   // Blue
            );
            
            // Blend between the two sepia methods for richer tones
            vec3 final_sepia = mix(sepia_color, sepia_alt, 0.6);
            
            // Clamp to prevent overexposure
            final_sepia = clamp(final_sepia, 0.0, 1.0);
            
            // Mix between original and sepia based on intensity
            color = mix(input_color, final_sepia, sepia_intensity);
            
            // Add slight contrast boost for vintage feel
            color = pow(color, vec3(1.1));
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set sepia effect uniforms"""
        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]

        # Calculate dynamic sepia intensity based on signal
        dynamic_intensity = (
            self.base_intensity
            + (self.max_intensity - self.base_intensity) * signal_value
        )

        # Set uniform
        self.shader_program["sepia_intensity"] = dynamic_intensity
