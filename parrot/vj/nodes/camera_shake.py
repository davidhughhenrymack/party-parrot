#!/usr/bin/env python3

import time
import math
import random
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class CameraShake(PostProcessEffectBase):
    """
    A camera shake effect that creates jitter and blur based on low frequencies.
    The low frequencies cause camera position jitter with motion blur that correlates with shake intensity.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        shake_intensity: float = 1.0,
        shake_frequency: float = 8.0,
        blur_intensity: float = 0.8,
        signal: FrameSignal = FrameSignal.freq_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            shake_intensity: Maximum shake amplitude in pixels
            shake_frequency: Frequency multiplier for shake oscillation
            blur_intensity: How much blur to apply based on shake (0.0 = no blur, 1.0 = max blur)
            signal: Which frame signal triggers the shake
        """
        super().__init__(input_node)
        self.shake_intensity = shake_intensity
        self.shake_frequency = shake_frequency
        self.blur_intensity = blur_intensity
        self.signal = signal

        # State variables for smooth shake motion
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.shake_velocity_x = 0.0
        self.shake_velocity_y = 0.0
        self.last_time = time.time()
        self.phase_offset_x = random.uniform(0, 2 * math.pi)
        self.phase_offset_y = random.uniform(0, 2 * math.pi)

    def generate(self, vibe: Vibe):
        """Configure shake parameters based on the vibe"""
        # Randomly pick a signal from available Frame signals
        available_signals = [
            FrameSignal.freq_all,
            FrameSignal.freq_high,
            FrameSignal.freq_low,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
            FrameSignal.strobe,
            FrameSignal.small_blinder,
            FrameSignal.pulse,
        ]
        self.signal = random.choice(available_signals)

        # Randomize shake parameters
        self.shake_intensity = random.uniform(0.5, 3.0)  # Vary shake intensity
        self.shake_frequency = random.uniform(4.0, 15.0)  # Vary shake frequency
        self.blur_intensity = random.uniform(0.3, 1.2)  # Vary blur intensity

        # Reset phase offsets for variety
        self.phase_offset_x = random.uniform(0, 2 * math.pi)
        self.phase_offset_y = random.uniform(0, 2 * math.pi)

    def print_self(self) -> str:
        """Return class name with current signal and shake parameters"""
        return f"🫨 {Fore.CYAN}{self.__class__.__name__}{Style.RESET_ALL} [{Fore.YELLOW}{self.signal.name}{Style.RESET_ALL}, intensity:{Fore.WHITE}{self.shake_intensity:.1f}{Style.RESET_ALL}, freq:{Fore.WHITE}{self.shake_frequency:.1f}{Style.RESET_ALL}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for camera shake and blur effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform vec2 shake_offset;
        uniform float blur_amount;
        
        void main() {
            // Apply shake offset to UV coordinates
            vec2 shaken_uv = uv + shake_offset;
            
            // Check if we're outside the texture bounds after shake
            if (shaken_uv.x < 0.0 || shaken_uv.x > 1.0 || shaken_uv.y < 0.0 || shaken_uv.y > 1.0) {
                color = vec3(0.0); // Black outside bounds
                return;
            }
            
            // Apply motion blur based on shake intensity
            if (blur_amount > 0.001) {
                vec3 blur_color = vec3(0.0);
                float total_weight = 0.0;
                
                // Directional blur in the direction of shake
                int blur_samples = int(blur_amount * 12.0) + 1;
                vec2 blur_direction = normalize(shake_offset + vec2(0.001)); // Avoid zero vector
                float blur_step = blur_amount * 0.01;
                
                for (int i = -blur_samples; i <= blur_samples; i++) {
                    vec2 offset = blur_direction * float(i) * blur_step;
                    vec2 sample_uv = shaken_uv + offset;
                    
                    // Only sample if within bounds
                    if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 && 
                        sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
                        // Weight samples more heavily near center
                        float weight = 1.0 - abs(float(i)) / float(blur_samples + 1);
                        blur_color += texture(input_texture, sample_uv).rgb * weight;
                        total_weight += weight;
                    }
                }
                
                if (total_weight > 0.0) {
                    color = blur_color / total_weight;
                } else {
                    color = texture(input_texture, shaken_uv).rgb;
                }
            } else {
                // No blur, just sample the shaken texture
                color = texture(input_texture, shaken_uv).rgb;
            }
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set shake and blur effect uniforms"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Clamp dt to prevent huge jumps
        dt = min(dt, 1.0 / 30.0)  # Max 30 FPS equivalent

        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]

        # Generate shake motion using multiple oscillators for more organic feel
        time_factor = current_time * self.shake_frequency

        # Primary shake oscillation
        shake_x_primary = math.sin(time_factor + self.phase_offset_x) * signal_value
        shake_y_primary = (
            math.cos(time_factor * 0.7 + self.phase_offset_y) * signal_value
        )

        # Secondary higher frequency shake for jitter
        shake_x_secondary = (
            math.sin(time_factor * 2.3 + self.phase_offset_x * 1.5) * signal_value * 0.3
        )
        shake_y_secondary = (
            math.cos(time_factor * 1.8 + self.phase_offset_y * 1.2) * signal_value * 0.3
        )

        # Combine oscillations
        target_shake_x = (shake_x_primary + shake_x_secondary) * self.shake_intensity
        target_shake_y = (shake_y_primary + shake_y_secondary) * self.shake_intensity

        # Apply some velocity-based smoothing for more natural motion
        shake_diff_x = target_shake_x - self.shake_x
        shake_diff_y = target_shake_y - self.shake_y

        # Add velocity with damping
        self.shake_velocity_x += shake_diff_x * 15.0 * dt
        self.shake_velocity_y += shake_diff_y * 15.0 * dt
        self.shake_velocity_x *= 0.8  # Damping
        self.shake_velocity_y *= 0.8  # Damping

        # Update shake position
        self.shake_x += self.shake_velocity_x * dt
        self.shake_y += self.shake_velocity_y * dt

        # Convert shake to UV offset (normalize by texture size)
        if self.framebuffer:
            shake_offset_x = self.shake_x / float(self.framebuffer.width)
            shake_offset_y = self.shake_y / float(self.framebuffer.height)
        else:
            shake_offset_x = self.shake_x / 1920.0
            shake_offset_y = self.shake_y / 1080.0

        # Calculate blur amount based on shake velocity and signal strength
        velocity_magnitude = math.sqrt(
            self.shake_velocity_x**2 + self.shake_velocity_y**2
        )
        blur_amount = min(
            velocity_magnitude * 0.1 * self.blur_intensity * signal_value, 1.0
        )

        # Set uniforms
        self.shader_program["shake_offset"] = (shake_offset_x, shake_offset_y)
        self.shader_program["blur_amount"] = blur_amount
