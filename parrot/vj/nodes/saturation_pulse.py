#!/usr/bin/env python3

from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class SaturationPulse(PostProcessEffectBase):
    """
    A saturation modulation effect that adjusts the saturation of its input based on audio signals.
    Takes a video input (framebuffer) and modulates its saturation using frame signals.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        intensity: float = 0.8,
        base_saturation: float = 0.2,
        signal: FrameSignal = FrameSignal.freq_high,
    ):
        """
        Args:
            input_node: The node that provides the video input
            intensity: How strong the saturation effect is (0.0 = no effect, 1.0 = full range)
            base_saturation: Minimum saturation level (0.0 = grayscale, 1.0 = full saturation)
            signal: Which frame signal to use for modulation
        """
        super().__init__(input_node)
        self.intensity = intensity
        self.base_saturation = base_saturation
        self.signal = signal

    def generate(self, vibe: Vibe):
        """Configure saturation pulse parameters based on the vibe"""
        # Could randomize intensity and base_saturation based on vibe.mode
        # For now, keep the initialized values
        pass

    def _get_fragment_shader(self) -> str:
        """Fragment shader for saturation modulation"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float saturation_multiplier;
        
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
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Convert to HSV
            vec3 hsv = rgb2hsv(input_color);
            
            // Modulate saturation
            hsv.y *= saturation_multiplier;
            hsv.y = clamp(hsv.y, 0.0, 1.0);
            
            // Convert back to RGB
            color = hsv2rgb(hsv);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set saturation effect uniforms"""
        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]
        
        # Map signal to saturation: base_saturation + (intensity * signal_value)
        saturation_multiplier = self.base_saturation + (self.intensity * signal_value)
        
        # Clamp to reasonable range
        saturation_multiplier = max(0.0, min(2.0, saturation_multiplier))
        
        self.shader_program["saturation_multiplier"] = saturation_multiplier
