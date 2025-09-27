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
class BloomFilter(PostProcessEffectBase):
    """
    A gentle bloom filter effect that creates a soft, dreamy glow around bright areas.
    Designed specifically for gentle and chill modes with low frequency signal sensitivity.
    Uses a multi-pass gaussian blur approach for high-quality bloom.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        base_intensity: float = 0.4,
        max_intensity: float = 0.8,
        bloom_radius: float = 4.0,
        threshold: float = 0.3,
        signal: FrameSignal = FrameSignal.sustained_low,
        blur_passes: int = 2,
    ):
        """
        Args:
            input_node: The node that provides the video input
            base_intensity: Minimum bloom intensity (0.0 = no bloom, 1.0 = full bloom)
            max_intensity: Maximum bloom intensity when signal is high
            bloom_radius: Radius of the bloom effect in pixels (gentle: 2-6)
            threshold: Brightness threshold for bloom (0.0 = all pixels bloom, 1.0 = only white pixels)
            signal: Which frame signal modulates the bloom intensity
            blur_passes: Number of blur passes for smoother bloom (1-3 for gentle effect)
        """
        super().__init__(input_node)
        self.base_intensity = base_intensity
        self.max_intensity = max_intensity
        self.bloom_radius = bloom_radius
        self.threshold = threshold
        self.signal = signal
        self.blur_passes = blur_passes

    def generate(self, vibe: Vibe):
        """Configure bloom parameters based on the vibe"""
        # For gentle/chill modes, keep parameters subtle and stable
        # Randomly pick a low frequency signal for gentle response
        low_freq_signals = [
            FrameSignal.sustained_low,
            FrameSignal.freq_low,
            FrameSignal.dampen,
        ]
        self.signal = random.choice(low_freq_signals)

        # Vary bloom parameters gently for organic feel
        self.base_intensity = random.uniform(0.3, 0.5)
        self.max_intensity = random.uniform(0.6, 0.9)
        self.bloom_radius = random.uniform(3.0, 6.0)
        self.threshold = random.uniform(0.2, 0.4)

    def print_self(self) -> str:
        """Return class name with current signal and bloom parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="🌸",
            signal=self.signal,
            intensity=self.max_intensity,
            radius=(self.bloom_radius, 1),
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for gentle bloom effect using multi-pass gaussian blur"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float bloom_intensity;
        uniform float bloom_radius;
        uniform float bloom_threshold;
        uniform vec2 texture_size;
        uniform int blur_passes;
        
        // High-quality gaussian blur weights for 13-tap blur
        const float weights[13] = float[](
            0.0044, 0.0175, 0.0540, 0.1295, 0.2420, 0.3521, 0.3989,
            0.3521, 0.2420, 0.1295, 0.0540, 0.0175, 0.0044
        );
        
        // Extract bright areas above threshold
        vec3 extractBrightAreas(vec3 input_color) {
            float luminance = dot(input_color, vec3(0.299, 0.587, 0.114));
            
            if (luminance > bloom_threshold) {
                // Smooth falloff near threshold for gentle transition
                float falloff = smoothstep(bloom_threshold - 0.1, bloom_threshold + 0.1, luminance);
                return input_color * falloff;
            }
            
            return vec3(0.0);
        }
        
        // Perform gaussian blur in one direction
        vec3 gaussianBlur(vec2 direction) {
            vec2 texel_size = 1.0 / texture_size;
            vec2 blur_offset = texel_size * bloom_radius * direction;
            
            vec3 blur_sum = vec3(0.0);
            float weight_sum = 0.0;
            
            // 13-tap gaussian blur
            for (int i = -6; i <= 6; i++) {
                vec2 sample_uv = uv + float(i) * blur_offset;
                
                // Clamp to texture bounds
                if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 && 
                    sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
                    
                    vec3 sample_color = texture(input_texture, sample_uv).rgb;
                    vec3 bright_areas = extractBrightAreas(sample_color);
                    
                    float weight = weights[i + 6];
                    blur_sum += bright_areas * weight;
                    weight_sum += weight;
                }
            }
            
            return weight_sum > 0.0 ? blur_sum / weight_sum : vec3(0.0);
        }
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Create bloom by blurring bright areas
            vec3 bloom_color = vec3(0.0);
            
            // Multi-pass blur for smoother bloom
            if (blur_passes >= 1) {
                // Horizontal blur pass
                bloom_color += gaussianBlur(vec2(1.0, 0.0));
            }
            
            if (blur_passes >= 2) {
                // Vertical blur pass
                bloom_color += gaussianBlur(vec2(0.0, 1.0));
                bloom_color *= 0.5; // Average the two passes
            }
            
            if (blur_passes >= 3) {
                // Diagonal blur passes for extra smoothness
                bloom_color += gaussianBlur(normalize(vec2(1.0, 1.0)));
                bloom_color += gaussianBlur(normalize(vec2(1.0, -1.0)));
                bloom_color *= 0.25; // Average all four passes
            }
            
            // Apply bloom intensity
            bloom_color *= bloom_intensity;
            
            // Combine original with bloom using gentle additive blending
            vec3 final_color = input_color + bloom_color;
            
            // Gentle color temperature shift for warmer bloom (subtle)
            final_color.r *= 1.02;
            final_color.g *= 1.01;
            
            // Soft tone mapping to prevent harsh overexposure
            final_color = final_color / (1.0 + final_color * 0.3);
            
            color = final_color;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set bloom effect uniforms"""
        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]

        # Calculate dynamic bloom intensity based on signal
        # Use gentle curve for smooth transitions
        signal_curve = signal_value * signal_value  # Quadratic for gentle response
        dynamic_intensity = (
            self.base_intensity
            + (self.max_intensity - self.base_intensity) * signal_curve
        )

        # Set uniforms
        self.shader_program["bloom_intensity"] = dynamic_intensity
        self.shader_program["bloom_radius"] = self.bloom_radius
        self.shader_program["bloom_threshold"] = self.threshold
        self.shader_program["blur_passes"] = self.blur_passes

        # Set texture size for proper blur sampling
        if self.framebuffer:
            self.shader_program["texture_size"] = (
                float(self.framebuffer.width),
                float(self.framebuffer.height),
            )
        else:
            self.shader_program["texture_size"] = (1920.0, 1080.0)
