#!/usr/bin/env python3

import time
import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class NoiseEffect(PostProcessEffectBase):
    """
    Analog TV static/noise effect with various noise patterns.
    Creates authentic old-school television interference and static.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        noise_intensity: float = 0.3,
        noise_scale: float = 100.0,
        static_lines: bool = True,
        color_noise: bool = True,
        signal: FrameSignal = FrameSignal.sustained_high,
    ):
        """
        Args:
            input_node: The node that provides the video input
            noise_intensity: Strength of noise overlay (0.0 = none, 1.0 = full static)
            noise_scale: Scale of noise pattern (higher = finer grain)
            static_lines: Whether to include horizontal static lines
            color_noise: Whether to include color channel noise
            signal: Which frame signal controls noise intensity
        """
        super().__init__(input_node)
        self.noise_intensity = noise_intensity
        self.noise_scale = noise_scale
        self.static_lines = static_lines
        self.color_noise = color_noise
        self.signal = signal

        # Animation state
        self.start_time = time.time()
        self.noise_seed = random.random()

    def generate(self, vibe: Vibe):
        """Configure noise parameters based on the vibe"""
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

        # Update noise seed for variation
        if random.random() < 0.2:  # 20% chance to change seed
            self.noise_seed = random.random()

    def print_self(self) -> str:
        """Return class name with current signal in brackets"""
        return f"{self.__class__.__name__} [{self.signal.name}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for noise effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float noise_intensity;
        uniform float noise_scale;
        uniform bool static_lines;
        uniform bool color_noise;
        uniform float signal_strength;
        uniform float time_offset;
        uniform float noise_seed;
        
        // High-quality pseudo-random function
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        // Multi-octave noise
        float noise(vec2 st) {
            vec2 i = floor(st);
            vec2 f = fract(st);
            
            float a = random(i);
            float b = random(i + vec2(1.0, 0.0));
            float c = random(i + vec2(0.0, 1.0));
            float d = random(i + vec2(1.0, 1.0));
            
            vec2 u = f * f * (3.0 - 2.0 * f);
            
            return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
        }
        
        // Fractal noise for more complex patterns
        float fractal_noise(vec2 st) {
            float value = 0.0;
            float amplitude = 0.5;
            
            for (int i = 0; i < 4; i++) {
                value += amplitude * noise(st);
                st *= 2.0;
                amplitude *= 0.5;
            }
            
            return value;
        }
        
        // Smooth distance function for elliptical rounded rectangle
        float elliptical_rounded_rect(vec2 p, vec2 size, float radius) {
            vec2 d = abs(p) - size + radius;
            return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
        }
        
        // 2D rotation matrix
        mat2 rotate2d(float angle) {
            float c = cos(angle);
            float s = sin(angle);
            return mat2(c, -s, s, c);
        }
        
        // Generate dust specs at random positions
        float dust_specs(vec2 uv, float time_offset, float noise_seed) {
            float spec_contribution = 0.0;
            
            // Generate multiple dust specs
            for (int i = 0; i < 8; i++) {
                // Use different seeds for each spec
                vec2 spec_seed = vec2(float(i) * 17.3 + noise_seed * 100.0, float(i) * 23.7 + time_offset * 0.1);
                
                // Random position (slowly drifting)
                vec2 spec_pos = vec2(
                    random(spec_seed) + sin(time_offset * 0.05 + float(i)) * 0.1,
                    random(spec_seed + vec2(50.0, 0.0)) + cos(time_offset * 0.03 + float(i)) * 0.1
                );
                
                // Random size (elliptical)
                vec2 spec_size = vec2(
                    0.02 + random(spec_seed + vec2(100.0, 0.0)) * 0.08,  // width: 0.02-0.10
                    0.01 + random(spec_seed + vec2(150.0, 0.0)) * 0.04   // height: 0.01-0.05
                );
                
                // Random rotation
                float spec_rotation = random(spec_seed + vec2(200.0, 0.0)) * 6.28318; // 0 to 2π
                
                // Random color (white or black)
                float spec_color = random(spec_seed + vec2(250.0, 0.0)) > 0.5 ? 1.0 : 0.0;
                
                // Random opacity
                float spec_opacity = 0.1 + random(spec_seed + vec2(300.0, 0.0)) * 0.2; // 0.1-0.3
                
                // Transform UV to spec space
                vec2 spec_uv = uv - spec_pos;
                spec_uv = rotate2d(spec_rotation) * spec_uv;
                
                // Calculate distance to elliptical rounded rect
                float dist = elliptical_rounded_rect(spec_uv, spec_size, spec_size.y * 0.3);
                
                // Smooth falloff
                float spec_mask = 1.0 - smoothstep(0.0, spec_size.y * 0.2, dist);
                
                // Add to contribution
                if (spec_mask > 0.0) {
                    spec_contribution += spec_mask * spec_opacity * (spec_color * 2.0 - 1.0); // -1 to 1 range
                }
            }
            
            return spec_contribution;
        }
        
        void main() {
            // Sample base color
            vec3 base_color = texture(input_texture, uv).rgb;
            
            // Calculate dynamic noise intensity based on signal
            float dynamic_intensity = noise_intensity * (0.5 + signal_strength * 0.5);
            
            // Generate time-varying noise coordinates
            vec2 noise_coords = uv * noise_scale + vec2(time_offset * 10.0, noise_seed * 100.0);
            
            // Generate different types of noise
            float white_noise = random(noise_coords);
            float perlin_noise = fractal_noise(noise_coords * 0.1);
            
            // Combine noise types
            float combined_noise = mix(white_noise, perlin_noise, 0.3);
            
            // Add non-straight, discontinuous static lines with blur
            if (static_lines) {
                float line_contribution = 0.0;
                
                // Sample multiple points for blur effect
                for (int blur_y = -2; blur_y <= 2; blur_y++) {
                    for (int blur_x = -1; blur_x <= 1; blur_x++) {
                        vec2 sample_uv = uv + vec2(float(blur_x) * 0.002, float(blur_y) * 0.005);
                        float y_line = floor(sample_uv.y * 200.0);
                        
                        // Create wavy, non-straight lines
                        float wave_offset = sin(y_line * 0.1 + time_offset * 3.0) * 0.02;
                        float adjusted_x = sample_uv.x + wave_offset;
                        
                        // Make lines discontinuous - break them up into segments
                        float x_segment = floor(adjusted_x * 15.0); // Divide screen into horizontal segments
                        float segment_noise = random(vec2(x_segment, y_line + time_offset * 50.0));
                        
                        // Only show line segments randomly (not continuous across screen)
                        if (segment_noise > 0.7) { // 30% chance per segment
                            float line_noise = random(vec2(0.0, y_line + time_offset * 50.0));
                            if (line_noise > 0.95) { // 5% chance per line
                                // Vary the intensity of different line segments
                                float segment_intensity = random(vec2(x_segment + 100.0, y_line)) * 0.6 + 0.4;
                                
                                // Apply gaussian-like weighting for blur
                                float blur_weight = exp(-0.5 * (float(blur_x * blur_x) + float(blur_y * blur_y)));
                                line_contribution += segment_intensity * blur_weight;
                            }
                        }
                    }
                }
                
                // Normalize and apply the blurred line contribution
                line_contribution /= 15.0; // Normalize by number of samples
                combined_noise = mix(combined_noise, 1.0, 0.8 * line_contribution);
            }
            
            // Apply noise to image
            vec3 noisy_color = base_color;
            
            if (color_noise) {
                // Apply different noise to each color channel
                float r_noise = fractal_noise(noise_coords + vec2(100.0, 0.0));
                float g_noise = fractal_noise(noise_coords + vec2(0.0, 100.0));
                float b_noise = fractal_noise(noise_coords + vec2(50.0, 50.0));
                
                noisy_color.r = mix(base_color.r, r_noise, dynamic_intensity * 0.3);
                noisy_color.g = mix(base_color.g, g_noise, dynamic_intensity * 0.3);
                noisy_color.b = mix(base_color.b, b_noise, dynamic_intensity * 0.3);
            }
            
            // Add overall luminance noise
            float luma_noise = (combined_noise - 0.5) * dynamic_intensity;
            noisy_color += vec3(luma_noise);
            
            // Add dust specs
            float dust_contribution = dust_specs(uv, time_offset, noise_seed);
            noisy_color += vec3(dust_contribution * dynamic_intensity * 0.5);
            
            // Add signal dropout effect (random black bars)
            float dropout = random(vec2(uv.y * 50.0, time_offset * 5.0));
            if (dropout > 0.995 && signal_strength > 0.7) {
                noisy_color *= 0.1;
            }
            
            // Slight desaturation for authentic analog look
            float gray = dot(noisy_color, vec3(0.299, 0.587, 0.114));
            noisy_color = mix(noisy_color, vec3(gray), dynamic_intensity * 0.2);
            
            color = clamp(noisy_color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set noise effect uniforms"""
        # Get signal value for noise intensity
        signal_value = frame[self.signal]

        # Special responses to specific Frame signals
        strobe_value = frame[FrameSignal.strobe]
        big_blinder_value = frame[FrameSignal.big_blinder]
        pulse_value = frame[FrameSignal.pulse]

        # Calculate time offset for animation
        current_time = time.time()
        time_offset = current_time - self.start_time

        # Modify parameters based on special signals
        noise_intensity = self.noise_intensity
        noise_scale = self.noise_scale
        effective_signal = signal_value

        # STROBE: Rapid flickering noise
        if strobe_value > 0.5:
            noise_intensity = min(1.0, self.noise_intensity * 2.0)  # Double intensity
            time_offset *= 20.0  # Very fast animation
            effective_signal = 1.0
            # Change noise seed rapidly during strobe
            self.noise_seed = (current_time * 10.0) % 1.0

        # BIG BLINDER: Heavy static interference
        elif big_blinder_value > 0.5:
            noise_intensity = min(1.0, self.noise_intensity * 3.0)  # Triple intensity
            noise_scale = self.noise_scale * 0.5  # Coarser noise
            effective_signal = big_blinder_value

        # PULSE: Sharp noise bursts
        elif pulse_value > 0.5:
            # Create burst-like noise during pulse
            noise_intensity = min(1.0, self.noise_intensity * 1.5)
            effective_signal = pulse_value
            # Discrete noise seed changes
            pulse_seed = int(current_time * 5.0)
            self.noise_seed = (pulse_seed * 0.1) % 1.0

        # Set uniforms
        self.shader_program["noise_intensity"] = noise_intensity
        self.shader_program["noise_scale"] = noise_scale
        self.shader_program["static_lines"] = self.static_lines
        self.shader_program["color_noise"] = self.color_noise
        self.shader_program["signal_strength"] = effective_signal
        self.shader_program["time_offset"] = time_offset
        self.shader_program["noise_seed"] = self.noise_seed
