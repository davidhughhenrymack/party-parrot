#!/usr/bin/env python3

import time
import math
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


@beartype
class LaserScanHeads(GenerativeEffectBase):
    """
    Laser scanning heads effect that emulates club laser fixtures with rotating
    beams. Creates four laser heads positioned at the corners of the screen, each
    projecting multiple triangular beams that rotate and spread based on the music.
    Responds to the strobe signal with intensity and rotation speed.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        num_heads: int = 4,
        beams_per_head: int = 12,
        base_rotation_speed: float = 0.4,
        base_tilt_speed: float = 0.3,
        base_beam_spread: float = 0.25,
        attack_time: float = 0.08,  # Fast attack (80ms)
        decay_time: float = 0.4,  # Medium decay (400ms)
    ):
        """
        Args:
            width: Width of the effect
            height: Height of the effect
            num_heads: Number of laser heads (fixed at 4 for corner placement)
            beams_per_head: Number of beams per laser head
            base_rotation_speed: Base pan rotation speed (radians per second)
            base_tilt_speed: Base tilt speed (radians per second)
            base_beam_spread: Base angular spread of beam cluster (radians)
            attack_time: Time to fade in (seconds)
            decay_time: Time to fade out (seconds)
        """
        super().__init__(width, height)
        self.num_heads = num_heads
        self.beams_per_head = beams_per_head
        self.base_rotation_speed = base_rotation_speed
        self.base_tilt_speed = base_tilt_speed
        self.base_beam_spread = base_beam_spread
        self.attack_time = attack_time
        self.decay_time = decay_time
        self.mode_opacity_multiplier = 1.0  # Mode-based intensity reduction

        # Track blinder intensity with attack/decay
        self.blinder_level = 0.0
        self.blinder_target = 0.0

        # Track rotation and tilt state for 3D-like movement
        self.pan_angle = 0.0
        self.tilt_angle = 0.0
        self.last_update_time = time.time()

        # Head placement configuration (set in generate)
        self.head_placement_scheme = "corners"  # corners, bottom_row, or top_row

    def generate(self, vibe: Vibe):
        """Configure laser head parameters based on the vibe"""
        from parrot.director.mode import Mode
        import random

        if vibe.mode == Mode.rave:
            self.beams_per_head = 16  # More beams for rave mode
            self.base_rotation_speed = 0.6  # Faster rotation
            self.base_tilt_speed = 0.4  # Faster tilt
            self.base_beam_spread = 0.35  # Wider spread
            self.attack_time = 0.05  # Very fast attack
            self.decay_time = 0.3  # Fast decay
            self.mode_opacity_multiplier = 1.0  # Full intensity
            # Randomly choose number of heads and placement for rave
            self.num_heads = random.choice([4, 6, 8])
            self.head_placement_scheme = random.choice(
                ["corners", "bottom_row", "top_row"]
            )
        elif vibe.mode == Mode.chill:
            self.beams_per_head = 8  # Fewer beams
            self.base_rotation_speed = 0.15  # Slower rotation
            self.base_tilt_speed = 0.1  # Slower tilt
            self.base_beam_spread = 0.15  # Narrower spread
            self.attack_time = 0.15  # Slower attack
            self.decay_time = 0.6  # Slower decay
            self.mode_opacity_multiplier = 0.3  # Very subtle in chill
            self.num_heads = 4
            self.head_placement_scheme = "corners"
        elif vibe.mode == Mode.gentle:
            self.beams_per_head = 10  # Medium beams
            self.base_rotation_speed = 0.25  # Medium rotation
            self.base_tilt_speed = 0.2  # Medium tilt
            self.base_beam_spread = 0.20  # Medium spread
            self.attack_time = 0.1  # Medium attack
            self.decay_time = 0.5  # Medium decay
            self.mode_opacity_multiplier = 0.5  # Reduced in gentle
            self.num_heads = random.choice([4, 6])
            self.head_placement_scheme = random.choice(["corners", "bottom_row"])
        elif vibe.mode == Mode.blackout:
            self.beams_per_head = 0
            self.mode_opacity_multiplier = 0.0  # No lasers in blackout
            self.num_heads = 0
        else:
            self.beams_per_head = 12
            self.base_rotation_speed = 0.4
            self.base_tilt_speed = 0.3
            self.base_beam_spread = 0.25
            self.attack_time = 0.08
            self.decay_time = 0.4
            self.mode_opacity_multiplier = 0.8
            self.num_heads = 4
            self.head_placement_scheme = "corners"

    def print_self(self) -> str:
        return format_node_status(
            self.__class__.__name__,
            emoji="🔦",
            beams_per_head=self.beams_per_head,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for laser scanning heads rendering"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        
        uniform int num_heads;
        uniform int beams_per_head;
        uniform float pan_angle;
        uniform float tilt_angle;
        uniform float beam_spread;
        uniform float blinder_intensity;
        uniform vec2 resolution;
        uniform vec3 laser_color_fg;
        uniform vec3 laser_color_bg;
        uniform float mode_opacity_multiplier;
        uniform int placement_scheme;  // 0=corners, 1=bottom_row, 2=top_row
        uniform float time;
        
        const float PI = 3.14159265359;
        
        // Simple hash function for pseudo-random values
        float hash(float n) {
            return fract(sin(n) * 43758.5453123);
        }
        
        // 2D noise function for fog/atmospheric effects
        float noise2d(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            
            // Smooth interpolation
            vec2 u = f * f * (3.0 - 2.0 * f);
            
            // Four corners of a tile
            float a = hash(i.x + i.y * 57.0);
            float b = hash(i.x + 1.0 + i.y * 57.0);
            float c = hash(i.x + (i.y + 1.0) * 57.0);
            float d = hash(i.x + 1.0 + (i.y + 1.0) * 57.0);
            
            // Bilinear interpolation
            return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
        }
        
        // Fractal Brownian Motion for more complex fog noise
        float fbm(vec2 p) {
            float value = 0.0;
            float amplitude = 0.5;
            float frequency = 1.0;
            
            for (int i = 0; i < 3; i++) {
                value += amplitude * noise2d(p * frequency);
                frequency *= 2.0;
                amplitude *= 0.5;
            }
            
            return value;
        }
        
        // 2D rotation matrix
        mat2 rotate2d(float angle) {
            float c = cos(angle);
            float s = sin(angle);
            return mat2(c, -s, s, c);
        }
        
        // SDF for a triangle (pointing up along +Y axis)
        float triangle_sdf(vec2 p, float beam_length, float beam_width) {
            // Transform to make triangle point along +Y
            p.y = -p.y;
            
            // Three vertices of the triangle
            vec2 tip = vec2(0.0, beam_length);
            vec2 left_base = vec2(-beam_width / 2.0, 0.0);
            vec2 right_base = vec2(beam_width / 2.0, 0.0);
            
            // Calculate edge vectors
            vec2 edge_left_to_tip = tip - left_base;
            vec2 edge_right_to_left = right_base - left_base;
            vec2 edge_tip_to_right = tip - right_base;
            
            // Calculate distances to the three edges using cross product for inside/outside test
            float d1 = dot(p - tip, normalize(left_base - tip));
            float d2 = dot(p - left_base, normalize(right_base - left_base));
            float d3 = dot(p - right_base, normalize(tip - right_base));
            
            // Inside if all distances are negative (all half-space tests pass)
            float inside_dist = max(max(d1, d2), d3);
            
            // For outside distance, calculate distance to nearest edge
            vec2 to_tip = p - tip;
            vec2 to_left = p - left_base;
            vec2 to_right = p - right_base;
            
            // Calculate length of edges
            float edge1_len = distance(tip, left_base);
            float edge2_len = distance(right_base, left_base);
            float edge3_len = distance(tip, right_base);
            
            // Calculate distance to each edge
            vec2 edge1_dir = normalize(left_base - tip);
            float proj1 = clamp(dot(to_tip, edge1_dir), 0.0, edge1_len);
            float outside_dist1 = distance(to_tip, edge1_dir * proj1);
            
            vec2 edge2_dir = normalize(right_base - left_base);
            float proj2 = clamp(dot(to_left, edge2_dir), 0.0, edge2_len);
            float outside_dist2 = distance(to_left, edge2_dir * proj2);
            
            vec2 edge3_dir = normalize(tip - right_base);
            float proj3 = clamp(dot(to_right, edge3_dir), 0.0, edge3_len);
            float outside_dist3 = distance(to_right, edge3_dir * proj3);
            
            float outside_dist = min(min(outside_dist1, outside_dist2), outside_dist3);
            
            return inside_dist > 0.0 ? outside_dist : -inside_dist;
        }
        
        // Exponential falloff for glow
        float exp_glow(float dist, float radius, float intensity) {
            return intensity * exp(-dist / radius);
        }
        
        // Render a single laser beam (triangle with glow) with fog noise
        vec3 render_beam(vec2 p, float angle, float tilt_offset, vec3 beam_color, float beam_id) {
            // Apply 3D-like rotation: combine pan angle with tilt offset
            float effective_angle = angle + tilt_offset;
            
            // Rotate point to beam's angle
            vec2 rotated_p = rotate2d(-effective_angle) * p;
            
            // Beam dimensions - Very narrow beams
            float beam_length = 2.0;  // Very long beams
            float beam_width = 0.0008;  // Ultra-thin triangular beams (even narrower)
            
            // Calculate triangle SDF
            float dist = triangle_sdf(rotated_p, beam_length, beam_width);
            
            // Core beam (sharp and bright) - no noise on the core
            float core = 1.0 - smoothstep(-beam_width * 0.3, 0.0, dist);
            
            // Subtle glow around beam
            float glow = exp_glow(abs(dist), 0.006, 0.5);
            float outer_glow = exp_glow(abs(dist), 0.015, 0.2);
            
            // Add fog noise to the glow components
            // Use position along beam and perpendicular distance for noise coordinates
            vec2 noise_coord = vec2(rotated_p.y * 3.0 + time * 0.2, abs(dist) * 50.0 + beam_id);
            float fog_noise = fbm(noise_coord) * 0.4 + 0.6; // Range: 0.6 to 1.0
            
            // Apply fog noise more strongly to outer glow, less to inner glow
            float noisy_glow = glow * (fog_noise * 0.3 + 0.7); // Inner glow: subtle noise
            float noisy_outer_glow = outer_glow * fog_noise; // Outer glow: more noise
            
            // Combine core (clean) and glows (noisy)
            float intensity = core * 2.0 + noisy_glow + noisy_outer_glow * 0.3;
            
            return beam_color * intensity;
        }
        
        // Render all beams from a single laser head with 3D-like movement
        vec3 render_laser_head(vec2 head_pos, vec2 uv_pos, int head_id) {
            vec3 final_color = vec3(0.0);
            
            // Calculate position relative to laser head
            vec2 p = uv_pos - head_pos;
            
            // Each head has a phase offset for varied circular movement
            float head_phase = float(head_id) * PI * 0.5;
            
            // Calculate tilt offset that creates circular 3D-like movement
            // This simulates the head tilting as it pans, creating depth
            float tilt_offset = sin(tilt_angle + head_phase) * 0.4;
            
            // Calculate base angle for each beam based on beam spread
            float angle_step = beam_spread / float(beams_per_head - 1);
            float start_angle = -beam_spread / 2.0;
            
            // Render each beam with alternating colors
            for (int i = 0; i < beams_per_head; i++) {
                float beam_angle = start_angle + float(i) * angle_step + pan_angle + head_phase;
                
                // Alternate between fg and bg colors for variety
                float color_selector = hash(float(head_id * 100 + i));
                vec3 beam_color = mix(laser_color_fg, laser_color_bg, step(0.5, color_selector));
                
                // Unique ID for each beam for noise variation
                float beam_id = float(head_id * beams_per_head + i);
                
                vec3 beam_contribution = render_beam(p, beam_angle, tilt_offset, beam_color, beam_id);
                final_color += beam_contribution;
            }
            
            return final_color;
        }
        
        void main() {
            vec3 final_color = vec3(0.0);
            
            // Calculate aspect ratio for proper positioning
            float aspect = resolution.x / resolution.y;
            vec2 aspect_uv = uv;
            aspect_uv.x *= aspect;
            
            // Only render if blinder signal is active
            if (blinder_intensity > 0.1 && beams_per_head > 0 && num_heads > 0) {
                // Define head positions based on placement scheme
                vec2 head_positions[8];  // Max 8 heads
                float center_x = aspect / 2.0;
                
                if (placement_scheme == 0) {
                    // Corners placement (4 heads)
                    head_positions[0] = vec2(center_x - aspect * 0.35, 0.92);  // Top left
                    head_positions[1] = vec2(center_x + aspect * 0.35, 0.92);  // Top right
                    head_positions[2] = vec2(center_x - aspect * 0.35, 0.08);  // Bottom left
                    head_positions[3] = vec2(center_x + aspect * 0.35, 0.08);  // Bottom right
                } else if (placement_scheme == 1) {
                    // Bottom row placement (4-8 heads)
                    float bottom_y = 0.08;
                    for (int i = 0; i < 8; i++) {
                        if (i < num_heads) {
                            float t = float(i) / float(num_heads - 1);
                            float x = center_x + (t - 0.5) * aspect * 0.8;
                            head_positions[i] = vec2(x, bottom_y);
                        }
                    }
                } else if (placement_scheme == 2) {
                    // Top row placement (4-8 heads)
                    float top_y = 0.92;
                    for (int i = 0; i < 8; i++) {
                        if (i < num_heads) {
                            float t = float(i) / float(num_heads - 1);
                            float x = center_x + (t - 0.5) * aspect * 0.8;
                            head_positions[i] = vec2(x, top_y);
                        }
                    }
                }
                
                // Render beams from each head with unique head ID
                for (int i = 0; i < num_heads; i++) {
                    if (i < 8) {  // Safety check
                        vec3 head_contribution = render_laser_head(head_positions[i], aspect_uv, i);
                        final_color += head_contribution;
                    }
                }
                
                // Apply blinder intensity
                final_color *= blinder_intensity;
            }
            
            // Apply mode-based opacity multiplier and clamp
            color = clamp(final_color * mode_opacity_multiplier, 0.0, 2.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set laser scanning heads effect uniforms"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Get signal values
        small_blinder_signal = frame[FrameSignal.small_blinder]
        freq_high_signal = frame[FrameSignal.freq_high]

        # Set target based on signal
        self.blinder_target = 1.0 if small_blinder_signal > 0.5 else 0.0

        # Apply attack/decay to blinder level
        if self.blinder_target > self.blinder_level:
            # Attack: fade in
            attack_rate = 1.0 / self.attack_time if self.attack_time > 0 else 999.0
            self.blinder_level = min(
                self.blinder_level + attack_rate * dt, self.blinder_target
            )
        else:
            # Decay: fade out
            decay_rate = 1.0 / self.decay_time if self.decay_time > 0 else 999.0
            self.blinder_level = max(
                self.blinder_level - decay_rate * dt, self.blinder_target
            )

        # Update pan rotation based on blinder level (not raw signal)
        # Pan speed increases with intensity
        pan_speed_multiplier = (
            1.0 + self.blinder_level * 4.0
        )  # Up to 5x speed when active
        self.pan_angle += self.base_rotation_speed * pan_speed_multiplier * dt

        # Update tilt for 3D-like circular movement
        # Tilt creates the illusion of beams sweeping around the audience in 3D space
        tilt_speed_multiplier = 1.0 + freq_high_signal * 2.0
        self.tilt_angle += self.base_tilt_speed * tilt_speed_multiplier * dt

        # Beam spread responds to high frequency signal - wider spread with music
        beam_spread = self.base_beam_spread * (1.0 + freq_high_signal * 2.0)

        # Use smoothed blinder level
        blinder_intensity = self.blinder_level

        # Use color scheme for laser colors - both fg and bg
        laser_fg_rgb = scheme.fg.rgb
        laser_bg_rgb = scheme.bg.rgb

        # Convert placement scheme to int for shader
        placement_scheme_map = {"corners": 0, "bottom_row": 1, "top_row": 2}
        placement_int = placement_scheme_map.get(self.head_placement_scheme, 0)

        # Set uniforms
        self.shader_program["num_heads"] = self.num_heads
        self.shader_program["beams_per_head"] = self.beams_per_head
        self.shader_program["pan_angle"] = self.pan_angle
        self.shader_program["tilt_angle"] = self.tilt_angle
        self.shader_program["beam_spread"] = beam_spread
        self.shader_program["blinder_intensity"] = blinder_intensity
        self.shader_program["resolution"] = (float(self.width), float(self.height))
        self.shader_program["laser_color_fg"] = laser_fg_rgb
        self.shader_program["laser_color_bg"] = laser_bg_rgb
        self.shader_program["mode_opacity_multiplier"] = self.mode_opacity_multiplier
        self.shader_program["placement_scheme"] = placement_int
        self.shader_program["time"] = current_time
