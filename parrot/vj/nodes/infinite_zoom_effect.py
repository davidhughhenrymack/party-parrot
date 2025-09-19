#!/usr/bin/env python3

import time
import random
import math
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class InfiniteZoomEffect(PostProcessEffectBase):
    """
    An infinite zoom effect that continuously zooms into the center of the input buffer
    and layers smaller versions of itself on top, creating a recursive zoom tunnel effect.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        zoom_speed: float = 1.5,
        num_layers: int = 4,
        layer_scale_factor: float = 0.7,
        rotation_speed: float = 0.3,
        signal: FrameSignal = FrameSignal.freq_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            zoom_speed: Speed of the zoom animation (higher = faster)
            num_layers: Number of recursive layers to render (2-8 recommended)
            layer_scale_factor: Scale factor between layers (0.5-0.9 recommended)
            rotation_speed: Speed of rotation animation (0 = no rotation)
            signal: Which frame signal modulates the effect intensity
        """
        super().__init__(input_node)
        self.zoom_speed = zoom_speed
        self.num_layers = max(2, min(8, num_layers))  # Clamp between 2-8
        self.layer_scale_factor = max(
            0.3, min(0.95, layer_scale_factor)
        )  # Clamp between 0.3-0.95
        self.rotation_speed = rotation_speed
        self.signal = signal

        # Animation state
        self.zoom_offset = 0.0
        self.rotation_offset = 0.0
        self.last_time = time.time()

    def generate(self, vibe: Vibe):
        """Configure zoom parameters based on the vibe"""
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

        # Randomize zoom parameters
        self.zoom_speed = random.uniform(0.5, 3.0)  # Vary zoom speed
        self.num_layers = random.randint(2, 6)  # Vary number of layers
        self.layer_scale_factor = random.uniform(0.5, 0.85)  # Vary scale factor
        self.rotation_speed = random.uniform(
            -0.8, 0.8
        )  # Vary rotation (can be negative)

    def _get_fragment_shader(self) -> str:
        """Fragment shader for infinite zoom effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float zoom_offset;
        uniform float rotation_offset;
        uniform int num_layers;
        uniform float layer_scale_factor;
        uniform float signal_intensity;
        
        // Rotation matrix function
        mat2 rotate(float angle) {
            float c = cos(angle);
            float s = sin(angle);
            return mat2(c, -s, s, c);
        }
        
        void main() {
            vec2 center = vec2(0.5, 0.5);
            vec3 final_color = vec3(0.0);
            float total_weight = 0.0;
            
            // Base zoom factor that creates the infinite zoom effect
            float base_zoom = 1.0 + zoom_offset;
            
            // Modulate effect intensity with signal
            float effective_layers = float(num_layers) * (0.3 + 0.7 * signal_intensity);
            int actual_layers = max(1, int(effective_layers));
            
            for (int i = 0; i < actual_layers && i < 8; i++) {
                // Calculate scale for this layer
                float layer_scale = pow(layer_scale_factor, float(i));
                float zoom_factor = base_zoom * layer_scale;
                
                // Calculate rotation for this layer (each layer rotates slightly differently)
                float layer_rotation = rotation_offset * (1.0 + float(i) * 0.2);
                
                // Transform UV coordinates
                vec2 transformed_uv = uv - center;
                
                // Apply rotation
                transformed_uv = rotate(layer_rotation) * transformed_uv;
                
                // Apply zoom (zoom into center)
                transformed_uv = transformed_uv / zoom_factor;
                
                // Translate back to center
                transformed_uv = transformed_uv + center;
                
                // Check if we're within texture bounds
                if (transformed_uv.x >= 0.0 && transformed_uv.x <= 1.0 && 
                    transformed_uv.y >= 0.0 && transformed_uv.y <= 1.0) {
                    
                    // Sample the texture
                    vec3 layer_color = texture(input_texture, transformed_uv).rgb;
                    
                    // Weight decreases with layer depth for blending
                    float weight = pow(0.8, float(i)) * layer_scale;
                    
                    // Add some brightness variation per layer
                    float brightness_mod = 1.0 - float(i) * 0.1;
                    layer_color *= brightness_mod;
                    
                    final_color += layer_color * weight;
                    total_weight += weight;
                }
            }
            
            // Normalize and apply final color
            if (total_weight > 0.0) {
                color = final_color / total_weight;
                
                // Add slight vignette effect for depth
                vec2 vignette_uv = uv - center;
                float vignette = 1.0 - length(vignette_uv) * 0.3;
                color *= max(0.3, vignette);
                
                // Boost contrast slightly for more dramatic effect
                color = pow(color, vec3(1.1));
            } else {
                color = vec3(0.0);
            }
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set infinite zoom effect uniforms"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Clamp dt to prevent huge jumps
        dt = min(dt, 1.0 / 30.0)  # Max 30 FPS equivalent

        # Update animation offsets
        self.zoom_offset += self.zoom_speed * dt
        self.rotation_offset += self.rotation_speed * dt

        # Keep zoom_offset in a reasonable range to prevent precision issues
        # The modulo creates the infinite zoom effect - when we reach 1.0, we reset to 0.0
        # This creates a seamless loop because at zoom_offset=1.0, the outermost layer
        # becomes the same size as the original, creating perfect continuity
        self.zoom_offset = self.zoom_offset % 1.0

        # Get signal value (0.0 to 1.0) for effect modulation
        signal_value = frame[self.signal]

        # Set uniforms
        self.shader_program["zoom_offset"] = self.zoom_offset
        self.shader_program["rotation_offset"] = self.rotation_offset
        self.shader_program["num_layers"] = self.num_layers
        self.shader_program["layer_scale_factor"] = self.layer_scale_factor
        self.shader_program["signal_intensity"] = signal_value
