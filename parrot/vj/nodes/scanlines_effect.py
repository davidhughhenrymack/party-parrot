#!/usr/bin/env python3

import time
import math
import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class ScanlinesEffect(PostProcessEffectBase):
    """
    Retro CRT scanlines effect with rolling distortion and phosphor glow.
    Creates authentic old-school monitor aesthetics with animated scanlines.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        scanline_intensity: float = 0.4,
        scanline_count: float = 300.0,
        roll_speed: float = 0.5,
        curvature: float = 0.1,
        signal: FrameSignal = FrameSignal.sustained_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            scanline_intensity: Darkness of scanlines (0.0 = none, 1.0 = black lines)
            scanline_count: Number of scanlines across the screen
            roll_speed: Speed of rolling/scrolling effect
            curvature: Amount of screen curvature (0.0 = flat, 1.0 = curved)
            signal: Which frame signal affects the distortion
        """
        super().__init__(input_node)
        self.scanline_intensity = scanline_intensity
        self.scanline_count = scanline_count
        self.roll_speed = roll_speed
        self.curvature = curvature
        self.signal = signal

        # Animation state
        self.start_time = time.time()

    def generate(self, vibe: Vibe):
        """Configure scanlines parameters based on the vibe"""
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

    def _get_fragment_shader(self) -> str:
        """Fragment shader for scanlines effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float scanline_intensity;
        uniform float scanline_count;
        uniform float time_offset;
        uniform float signal_strength;
        uniform float curvature;
        uniform float roll_speed;
        
        // Apply barrel distortion for CRT curvature
        vec2 barrel_distort(vec2 coord, float amount) {
            vec2 cc = coord - 0.5;
            float dist = dot(cc, cc) * amount;
            return coord + cc * (1.0 + dist) * dist;
        }
        
        void main() {
            vec2 distorted_uv = uv;
            
            // Apply CRT curvature
            if (curvature > 0.001) {
                distorted_uv = barrel_distort(uv, curvature);
                
                // Fade edges for CRT vignette effect
                vec2 edge_fade = smoothstep(0.0, 0.05, distorted_uv) * 
                               (1.0 - smoothstep(0.95, 1.0, distorted_uv));
                
                if (distorted_uv.x < 0.0 || distorted_uv.x > 1.0 || 
                    distorted_uv.y < 0.0 || distorted_uv.y > 1.0) {
                    color = vec3(0.0);
                    return;
                }
            }
            
            // Sample base color
            vec3 base_color = texture(input_texture, distorted_uv).rgb;
            
            // Create rolling scanlines
            float roll_offset = time_offset * roll_speed;
            float scanline_pos = (distorted_uv.y + roll_offset) * scanline_count;
            
            // Generate scanline pattern
            float scanline = sin(scanline_pos * 3.14159 * 2.0);
            scanline = (scanline + 1.0) * 0.5; // Normalize to 0-1
            
            // Apply scanline intensity
            float scanline_factor = 1.0 - (scanline_intensity * (1.0 - scanline));
            
            // Add signal-based interference
            float interference = sin(scanline_pos * 0.1 + time_offset * 10.0) * 
                               signal_strength * 0.1;
            scanline_factor += interference;
            
            // Apply phosphor glow effect
            vec3 phosphor_color = base_color;
            phosphor_color.g *= 1.1; // Slight green tint for old monitors
            
            // Combine effects
            color = phosphor_color * scanline_factor;
            
            // Add subtle bloom for phosphor effect
            float brightness = dot(color, vec3(0.299, 0.587, 0.114));
            if (brightness > 0.8) {
                color += vec3(0.1, 0.15, 0.1) * (brightness - 0.8);
            }
            
            color = clamp(color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set scanlines effect uniforms"""
        # Get signal value for interference
        signal_value = frame[self.signal]

        # Calculate time offset for rolling animation
        current_time = time.time()
        time_offset = current_time - self.start_time

        # Set uniforms
        self.shader_program["scanline_intensity"] = self.scanline_intensity
        self.shader_program["scanline_count"] = self.scanline_count
        self.shader_program["time_offset"] = time_offset
        self.shader_program["signal_strength"] = signal_value
        self.shader_program["curvature"] = self.curvature
        self.shader_program["roll_speed"] = self.roll_speed
