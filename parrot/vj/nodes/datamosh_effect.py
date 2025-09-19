#!/usr/bin/env python3

import time
import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class DatamoshEffect(PostProcessEffectBase):
    """
    A datamoshing effect that creates glitchy pixel displacement and corruption.
    Simulates digital compression artifacts and data corruption for retro glitch aesthetics.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        displacement_strength: float = 0.05,
        corruption_intensity: float = 0.3,
        glitch_frequency: float = 0.8,
        signal: FrameSignal = FrameSignal.freq_high,
    ):
        """
        Args:
            input_node: The node that provides the video input
            displacement_strength: How much to displace pixels (0.0 = none, 1.0 = extreme)
            corruption_intensity: Intensity of color corruption (0.0 = none, 1.0 = max)
            glitch_frequency: How often glitches occur (0.0 = never, 1.0 = always)
            signal: Which frame signal triggers stronger glitches
        """
        super().__init__(input_node)
        self.displacement_strength = displacement_strength
        self.corruption_intensity = corruption_intensity
        self.glitch_frequency = glitch_frequency
        self.signal = signal

        # State for glitch timing
        self.last_glitch_time = time.time()
        self.glitch_seed = random.random()

    def generate(self, vibe: Vibe):
        """Configure datamosh parameters based on the vibe"""
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

        # Update glitch seed periodically for variation
        if random.random() < 0.1:  # 10% chance to change seed
            self.glitch_seed = random.random()

    def _get_fragment_shader(self) -> str:
        """Fragment shader for datamosh effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float displacement_strength;
        uniform float corruption_intensity;
        uniform float glitch_frequency;
        uniform float time_seed;
        uniform float signal_strength;
        
        // Pseudo-random function
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        // Generate noise pattern
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
        
        void main() {
            vec2 displaced_uv = uv;
            
            // Create glitch zones based on signal and frequency
            float glitch_zone = step(1.0 - glitch_frequency * signal_strength, 
                                   noise(vec2(uv.y * 20.0, time_seed * 10.0)));
            
            if (glitch_zone > 0.5) {
                // Horizontal displacement (datamosh-style)
                float displacement_x = (noise(vec2(uv.y * 50.0, time_seed)) - 0.5) * 
                                     displacement_strength * signal_strength;
                
                // Vertical displacement (less common but adds variety)
                float displacement_y = (noise(vec2(uv.x * 30.0, time_seed * 1.5)) - 0.5) * 
                                     displacement_strength * 0.3 * signal_strength;
                
                displaced_uv.x += displacement_x;
                displaced_uv.y += displacement_y;
            }
            
            // Clamp UV coordinates
            displaced_uv = clamp(displaced_uv, 0.0, 1.0);
            
            // Sample the displaced texture
            vec3 base_color = texture(input_texture, displaced_uv).rgb;
            
            // Add color corruption in glitch zones
            if (glitch_zone > 0.5) {
                // RGB channel shifting
                float r_shift = (noise(vec2(uv.x * 100.0, time_seed * 2.0)) - 0.5) * 
                              corruption_intensity * 0.02;
                float b_shift = (noise(vec2(uv.x * 80.0, time_seed * 2.5)) - 0.5) * 
                              corruption_intensity * 0.02;
                
                vec2 r_uv = clamp(displaced_uv + vec2(r_shift, 0.0), 0.0, 1.0);
                vec2 b_uv = clamp(displaced_uv + vec2(b_shift, 0.0), 0.0, 1.0);
                
                base_color.r = texture(input_texture, r_uv).r;
                base_color.b = texture(input_texture, b_uv).b;
                
                // Add digital noise
                float digital_noise = noise(uv * 200.0 + time_seed * 50.0) * 
                                    corruption_intensity * 0.3;
                base_color += vec3(digital_noise);
                
                // Quantize colors for digital artifact look
                base_color = floor(base_color * 8.0) / 8.0;
            }
            
            color = clamp(base_color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set datamosh effect uniforms"""
        # Get signal value for glitch intensity
        signal_value = frame[self.signal]

        # Special responses to specific Frame signals
        strobe_value = frame[FrameSignal.strobe]
        big_blinder_value = frame[FrameSignal.big_blinder]
        pulse_value = frame[FrameSignal.pulse]

        # Update time-based seed for animation
        current_time = time.time()
        time_factor = (current_time - self.last_glitch_time) * 0.5

        # Modify parameters based on special signals
        displacement_strength = self.displacement_strength
        corruption_intensity = self.corruption_intensity
        glitch_frequency = self.glitch_frequency
        effective_signal = signal_value
        time_seed = self.glitch_seed + time_factor

        # STROBE: Rapid glitch bursts
        if strobe_value > 0.5:
            displacement_strength = self.displacement_strength * 2.0
            corruption_intensity = min(1.0, self.corruption_intensity * 2.0)
            glitch_frequency = min(
                1.0, self.glitch_frequency * 3.0
            )  # More frequent glitches
            effective_signal = 1.0
            # Rapid seed changes for chaotic effect
            time_seed = current_time * 10.0

        # BIG BLINDER: Massive corruption
        elif big_blinder_value > 0.5:
            displacement_strength = (
                self.displacement_strength * 4.0
            )  # Extreme displacement
            corruption_intensity = min(1.0, self.corruption_intensity * 3.0)
            glitch_frequency = 1.0  # Full screen corruption
            effective_signal = big_blinder_value

        # PULSE: Sharp glitch spikes
        elif pulse_value > 0.5:
            # Create sharp, discrete glitch patterns
            displacement_strength = self.displacement_strength * 1.5
            corruption_intensity = min(1.0, self.corruption_intensity * 1.8)
            effective_signal = pulse_value
            # Discrete time steps for sharp transitions
            time_seed = float(int(current_time * 8.0))

        # Set uniforms
        self.shader_program["displacement_strength"] = displacement_strength
        self.shader_program["corruption_intensity"] = corruption_intensity
        self.shader_program["glitch_frequency"] = glitch_frequency
        self.shader_program["time_seed"] = time_seed
        self.shader_program["signal_strength"] = effective_signal
