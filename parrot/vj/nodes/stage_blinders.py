#!/usr/bin/env python3

import time
import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


@beartype
class StageBlinders(GenerativeEffectBase):
    """
    Stage blinder lights effect that emulates the bright white blinder lights
    at rock concerts. Creates a line of white circles with blur across the bottom
    of the screen. Responds to big_blinder and small_blinder signals with
    attack and decay fade in/out behavior.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        num_blinders: int = 8,
        attack_time: float = 0.05,  # Fast attack (50ms)
        decay_time: float = 0.3,  # Medium decay (300ms)
        opacity_multiplier: float = 1.0,
    ):
        """
        Args:
            width: Width of the effect
            height: Height of the effect
            num_blinders: Number of blinder circles
            attack_time: Time to fade in (seconds)
            decay_time: Time to fade out (seconds)
            opacity_multiplier: Overall opacity/intensity multiplier
        """
        super().__init__(width, height)
        self.num_blinders = num_blinders
        self.attack_time = attack_time
        self.decay_time = decay_time
        self.mode_opacity_multiplier = opacity_multiplier
        self.use_color_scheme = False  # Whether to use color scheme fg or white

        # Track blinder state
        self.big_blinder_level = 0.0
        self.small_blinder_level = 0.0
        self.big_blinder_target = 0.0
        self.small_blinder_target = 0.0
        self.last_update_time = time.time()

    def generate(self, vibe: Vibe):
        """Configure blinder parameters based on the vibe"""
        # 50% chance to use color scheme fg color instead of white
        self.use_color_scheme = random.random() < 0.5

    def print_self(self) -> str:
        return format_node_status(
            self.__class__.__name__,
            emoji="💡",
            num_blinders=self.num_blinders,
            use_color_scheme=self.use_color_scheme,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for stage blinders rendering"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        
        uniform int num_blinders;
        uniform float big_blinder_level;
        uniform float small_blinder_level;
        uniform vec2 resolution;
        uniform float mode_opacity_multiplier;
        uniform vec3 blinder_color;
        
        // Smooth circle SDF
        float circle_sdf(vec2 p, float radius) {
            return length(p) - radius;
        }
        
        // Smooth falloff for blur effect
        float smooth_circle(vec2 p, float radius, float blur) {
            float dist = circle_sdf(p, radius);
            return 1.0 - smoothstep(-blur, blur, dist);
        }
        
        // Exponential falloff for outer glow
        float exp_glow(vec2 p, float radius, float intensity) {
            float dist = length(p);
            return intensity * exp(-dist / radius);
        }
        
        void main() {
            vec3 final_color = vec3(0.0);
            
            // Calculate aspect ratio for proper circles
            float aspect = resolution.x / resolution.y;
            vec2 aspect_uv = uv;
            aspect_uv.x *= aspect;
            
            // Position blinders at bottom of screen (y = 0.15 in UV space)
            float blinder_y = 0.15;
            
            // Calculate center x position in aspect-corrected space
            float center_x = aspect / 2.0;
            
            // Calculate spread width (80% of total width)
            float spread_width = aspect * 0.8;
            
            // Render big blinders
            if (big_blinder_level > 0.01) {
                // Big blinder circle size
                float circle_radius = 0.06;
                float medium_blur_radius = 0.04;
                float high_blur_radius = 0.15;
                
                // Calculate spacing to spread blinders evenly across spread_width
                float spacing = spread_width / float(num_blinders + 1);
                float start_x = center_x - spread_width / 2.0;
                
                for (int i = 0; i < num_blinders; i++) {
                    float blinder_x = start_x + spacing * float(i + 1);
                    vec2 blinder_pos = vec2(blinder_x, blinder_y);
                    vec2 p = aspect_uv - blinder_pos;
                    
                    // Core circle with medium blur
                    float core = smooth_circle(p, circle_radius, medium_blur_radius);
                    
                    // Outer glow with high blur (lower opacity)
                    float glow = exp_glow(p, high_blur_radius, 0.4);
                    
                    // Combine core and glow
                    float intensity = core + glow;
                    
                    // Use blinder_color (either white or color scheme fg)
                    final_color += blinder_color * intensity * big_blinder_level;
                }
            }
            
            // Render small blinders (smaller but with MORE blur/glow like big blinders)
            if (small_blinder_level > 0.01) {
                // Small blinder circle size (60% of big blinder size)
                float circle_radius = 0.036;
                float medium_blur_radius = 0.024;
                // INCREASED blur/glow radius to match big blinder's full-screen effect
                float high_blur_radius = 0.15;  // Same as big blinder
                
                // Calculate spacing to spread blinders evenly across spread_width
                float spacing = spread_width / float(num_blinders + 1);
                float start_x = center_x - spread_width / 2.0;
                
                for (int i = 0; i < num_blinders; i++) {
                    float blinder_x = start_x + spacing * float(i + 1);
                    vec2 blinder_pos = vec2(blinder_x, blinder_y);
                    vec2 p = aspect_uv - blinder_pos;
                    
                    // Core circle with medium blur
                    float core = smooth_circle(p, circle_radius, medium_blur_radius);
                    
                    // Outer glow with high blur - INCREASED glow intensity
                    float glow = exp_glow(p, high_blur_radius, 0.45);  // Increased from 0.3 to 0.45
                    
                    // Combine core and glow
                    float intensity = core + glow;
                    
                    // Use blinder_color (70% brightness of big blinders)
                    final_color += blinder_color * intensity * small_blinder_level * 0.7;
                }
            }
            
            // Apply mode-based opacity multiplier
            // Use softer clamping to preserve color saturation in bright areas
            vec3 adjusted = final_color * mode_opacity_multiplier;
            
            // Preserve color hue even in bright areas by clamping per-channel with color-aware scaling
            float max_component = max(max(adjusted.r, adjusted.g), adjusted.b);
            if (max_component > 2.0) {
                // Scale down to preserve color ratios while allowing some overexposure
                adjusted = adjusted * (2.0 / max_component);
            }
            
            color = adjusted;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set stage blinders effect uniforms"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Get signal values - only big blinder now (small blinder is for laser heads)
        big_blinder_signal = frame[FrameSignal.big_blinder]

        # Set targets based on signals
        self.big_blinder_target = 1.0 if big_blinder_signal > 0.5 else 0.0
        # Small blinder no longer used - set to 0
        self.small_blinder_target = 0.0

        # Apply attack/decay to big blinder
        if self.big_blinder_target > self.big_blinder_level:
            # Attack: fade in
            attack_rate = 1.0 / self.attack_time if self.attack_time > 0 else 999.0
            self.big_blinder_level = min(
                self.big_blinder_level + attack_rate * dt, self.big_blinder_target
            )
        else:
            # Decay: fade out
            decay_rate = 1.0 / self.decay_time if self.decay_time > 0 else 999.0
            self.big_blinder_level = max(
                self.big_blinder_level - decay_rate * dt, self.big_blinder_target
            )

        # Small blinder is always off (used by laser heads now)
        self.small_blinder_level = 0.0

        # Determine blinder color based on use_color_scheme flag
        if self.use_color_scheme:
            blinder_color = scheme.fg.rgb  # Use color scheme foreground color
        else:
            blinder_color = (1.0, 1.0, 1.0)  # Use white

        # Set uniforms
        self.shader_program["num_blinders"] = self.num_blinders
        self.shader_program["big_blinder_level"] = self.big_blinder_level
        self.shader_program["small_blinder_level"] = self.small_blinder_level
        self.shader_program["resolution"] = (float(self.width), float(self.height))
        self.shader_program["mode_opacity_multiplier"] = self.mode_opacity_multiplier
        self.shader_program["blinder_color"] = blinder_color
