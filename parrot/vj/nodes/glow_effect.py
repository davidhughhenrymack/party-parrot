#!/usr/bin/env python3

import random
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase
from parrot.vj.utils.signal_utils import get_random_frame_signal


@beartype
class GlowEffect(PostProcessEffectBase):
    """
    A glow effect that adds a soft, luminous halo around bright areas of the input.
    The glow intensity and radius respond to frame signals for dynamic atmospheric lighting.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        base_intensity: float = 0.3,
        max_intensity: float = 0.8,
        glow_radius: float = 8.0,
        threshold: float = 0.6,
        signal: FrameSignal = FrameSignal.sustained_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            base_intensity: Minimum glow intensity (0.0 = no glow, 1.0 = full glow)
            max_intensity: Maximum glow intensity when signal is high
            glow_radius: Radius of the glow effect in pixels
            threshold: Brightness threshold for glow (0.0 = all pixels glow, 1.0 = only white pixels)
            signal: Which frame signal modulates the glow intensity
        """
        super().__init__(input_node)
        self.base_intensity = base_intensity
        self.max_intensity = max_intensity
        self.glow_radius = glow_radius
        self.threshold = threshold
        self.signal = signal

    def generate(self, vibe: Vibe):
        """Configure glow parameters based on the vibe"""
        # Randomly pick a signal from available Frame signals
        self.signal = get_random_frame_signal()

        # Vary glow parameters for organic feel
        self.base_intensity = random.uniform(0.2, 0.5)
        self.max_intensity = random.uniform(0.6, 0.9)
        self.glow_radius = random.uniform(6.0, 12.0)
        self.threshold = random.uniform(0.4, 0.7)

    def print_self(self) -> str:
        """Return class name with current signal and glow parameters"""
        return f"✨ {Fore.MAGENTA}{self.__class__.__name__}{Style.RESET_ALL} [{Fore.YELLOW}{self.signal.name}{Style.RESET_ALL}, intensity:{Fore.WHITE}{self.max_intensity:.2f}{Style.RESET_ALL}, radius:{Fore.WHITE}{self.glow_radius:.1f}{Style.RESET_ALL}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for glow effect using gaussian blur approximation"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float glow_intensity;
        uniform float glow_radius;
        uniform float glow_threshold;
        uniform vec2 texture_size;
        
        // Gaussian blur weights for 9-tap blur
        const float weights[9] = float[](
            0.0947416, 0.118318, 0.0947416,
            0.118318,  0.147761, 0.118318,
            0.0947416, 0.118318, 0.0947416
        );
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Calculate luminance to determine bright areas
            float luminance = dot(input_color, vec3(0.299, 0.587, 0.114));
            
            // Only apply glow to pixels above threshold
            if (luminance < glow_threshold) {
                color = input_color;
                return;
            }
            
            // Calculate texel size for blur sampling
            vec2 texel_size = 1.0 / texture_size;
            vec2 blur_offset = texel_size * glow_radius;
            
            // Sample surrounding pixels for blur effect
            vec3 blur_sum = vec3(0.0);
            int sample_index = 0;
            
            for (int x = -1; x <= 1; x++) {
                for (int y = -1; y <= 1; y++) {
                    vec2 sample_uv = uv + vec2(float(x), float(y)) * blur_offset;
                    vec3 sample_color = texture(input_texture, sample_uv).rgb;
                    
                    // Only include bright pixels in the glow
                    float sample_luminance = dot(sample_color, vec3(0.299, 0.587, 0.114));
                    if (sample_luminance > glow_threshold) {
                        blur_sum += sample_color * weights[sample_index];
                    }
                    sample_index++;
                }
            }
            
            // Create glow by adding blurred bright areas
            vec3 glow_color = blur_sum * glow_intensity;
            
            // Combine original with glow using additive blending
            color = input_color + glow_color;
            
            // Slight color temperature shift for warmer glow
            color.r *= 1.1;
            color.g *= 1.05;
            
            // Clamp to prevent overexposure
            color = clamp(color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set glow effect uniforms"""
        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]

        # Calculate dynamic glow intensity based on signal
        dynamic_intensity = (
            self.base_intensity
            + (self.max_intensity - self.base_intensity) * signal_value
        )

        # Set uniforms
        self.shader_program["glow_intensity"] = dynamic_intensity
        self.shader_program["glow_radius"] = self.glow_radius
        self.shader_program["glow_threshold"] = self.threshold

        # Set texture size for proper blur sampling
        if self.framebuffer:
            self.shader_program["texture_size"] = (
                float(self.framebuffer.width),
                float(self.framebuffer.height),
            )
        else:
            self.shader_program["texture_size"] = (1920.0, 1080.0)
