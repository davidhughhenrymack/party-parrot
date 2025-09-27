#!/usr/bin/env python3

import time
import random
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class CameraZoom(PostProcessEffectBase):
    """
    A camera zoom effect that creates jerky zoom in/out motion with blur.
    Zoom is triggered by signal being high, returns to original when signal is low.
    Includes velocity-based motion and blur proportional to zoom level.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        max_zoom: float = 2.5,
        zoom_speed: float = 8.0,
        return_speed: float = 4.0,
        blur_intensity: float = 0.8,
        signal: FrameSignal = FrameSignal.freq_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            max_zoom: Maximum zoom level (1.0 = no zoom, 2.0 = 2x zoom)
            zoom_speed: Speed of zooming in when signal is high
            return_speed: Speed of returning to normal when signal is low
            blur_intensity: How much blur to apply based on zoom (0.0 = no blur, 1.0 = max blur)
            signal: Which frame signal triggers the zoom
        """
        super().__init__(input_node)
        self.max_zoom = max_zoom
        self.zoom_speed = zoom_speed
        self.return_speed = return_speed
        self.blur_intensity = blur_intensity
        self.signal = signal

        # State variables
        self.current_zoom = 1.0
        self.zoom_velocity = 0.0
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
        self.max_zoom = random.uniform(1.5, 4.0)  # Vary max zoom from 1.5x to 4x
        self.zoom_speed = random.uniform(3.0, 15.0)  # Vary zoom speed
        self.return_speed = random.uniform(2.0, 8.0)  # Vary return speed
        self.blur_intensity = random.uniform(0.2, 1.2)  # Vary blur intensity

    def print_self(self) -> str:
        """Return class name with current signal and zoom parameters"""
        return f"📹 {Fore.CYAN}{self.__class__.__name__}{Style.RESET_ALL} [{Fore.YELLOW}{self.signal.name}{Style.RESET_ALL}, zoom:{Fore.WHITE}{self.max_zoom:.1f}{Style.RESET_ALL}, speed:{Fore.WHITE}{self.zoom_speed:.1f}{Style.RESET_ALL}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for zoom and blur effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float zoom_factor;
        uniform float blur_amount;
        uniform vec2 texture_size;
        
        void main() {
            vec2 center = vec2(0.5, 0.5);
            
            // Calculate zoomed UV coordinates (zoom into center)
            vec2 zoom_uv = center + (uv - center) / zoom_factor;
            
            // Check if we're outside the texture bounds after zoom
            if (zoom_uv.x < 0.0 || zoom_uv.x > 1.0 || zoom_uv.y < 0.0 || zoom_uv.y > 1.0) {
                color = vec3(0.0); // Black outside bounds
                return;
            }
            
            // Apply blur based on zoom level
            if (blur_amount > 0.001) {
                vec3 blur_color = vec3(0.0);
                float total_weight = 0.0;
                
                // Simple box blur with variable kernel size
                int blur_samples = int(blur_amount * 8.0) + 1;
                float blur_step = blur_amount / texture_size.x;
                
                for (int x = -blur_samples; x <= blur_samples; x++) {
                    for (int y = -blur_samples; y <= blur_samples; y++) {
                        vec2 offset = vec2(float(x), float(y)) * blur_step;
                        vec2 sample_uv = zoom_uv + offset;
                        
                        // Only sample if within bounds
                        if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 && 
                            sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
                            float weight = 1.0;
                            blur_color += texture(input_texture, sample_uv).rgb * weight;
                            total_weight += weight;
                        }
                    }
                }
                
                if (total_weight > 0.0) {
                    color = blur_color / total_weight;
                } else {
                    color = texture(input_texture, zoom_uv).rgb;
                }
            } else {
                // No blur, just sample the zoomed texture
                color = texture(input_texture, zoom_uv).rgb;
            }
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set zoom and blur effect uniforms"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Clamp dt to prevent huge jumps
        dt = min(dt, 1.0 / 30.0)  # Max 30 FPS equivalent

        # Get signal value (0.0 to 1.0)
        signal_value = frame[self.signal]

        # Determine target zoom based on signal
        target_zoom = 1.0 + (self.max_zoom - 1.0) * signal_value

        # Apply velocity-based zoom with different speeds for zoom in/out
        zoom_diff = target_zoom - self.current_zoom

        if zoom_diff > 0:
            # Zooming in - use zoom_speed
            speed = self.zoom_speed
        else:
            # Zooming out - use return_speed
            speed = self.return_speed

        # Apply velocity with some damping for jerky motion
        self.zoom_velocity += zoom_diff * speed * dt
        self.zoom_velocity *= 0.85  # Damping factor for jerky motion

        # Update zoom
        self.current_zoom += self.zoom_velocity * dt

        # Clamp zoom to reasonable bounds
        self.current_zoom = max(0.5, min(self.max_zoom * 1.2, self.current_zoom))

        # Calculate blur amount based on zoom level and velocity
        zoom_blur = abs(self.current_zoom - 1.0) * self.blur_intensity
        velocity_blur = abs(self.zoom_velocity) * 0.1 * self.blur_intensity
        total_blur = min(zoom_blur + velocity_blur, 1.0)

        # Set uniforms
        self.shader_program["zoom_factor"] = self.current_zoom
        self.shader_program["blur_amount"] = total_blur

        # Set texture size for blur calculations
        if self.framebuffer:
            self.shader_program["texture_size"] = (
                float(self.framebuffer.width),
                float(self.framebuffer.height),
            )
