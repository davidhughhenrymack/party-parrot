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
class PixelateEffect(PostProcessEffectBase):
    """
    Signal-driven pixelation effect that reduces resolution for retro 8-bit/16-bit aesthetics.
    Creates chunky pixel blocks with optional color quantization.
    When signal strength is 0, passes through the original image unchanged.
    Pixelation intensity is directly proportional to signal strength.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        pixel_size: float = 8.0,
        color_depth: int = 16,
        dither: bool = True,
        signal: FrameSignal = FrameSignal.freq_low,
    ):
        """
        Args:
            input_node: The node that provides the video input
            pixel_size: Size of pixels (higher = more pixelated)
            color_depth: Number of colors per channel (2-256, lower = more retro)
            dither: Whether to apply dithering for smoother gradients
            signal: Which frame signal controls pixelation intensity
        """
        super().__init__(input_node)
        self.pixel_size = pixel_size
        self.color_depth = max(2, min(256, color_depth))
        self.dither = dither
        self.signal = signal

        # Animation state
        self.start_time = time.time()

    def generate(self, vibe: Vibe):
        """Configure pixelate parameters based on the vibe"""
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
        """Fragment shader for pixelate effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float pixel_size;
        uniform float color_depth;
        uniform bool dither;
        uniform float signal_strength;
        uniform vec2 texture_size;
        
        // Dithering pattern (Bayer matrix)
        float dither_pattern(vec2 pos) {
            int x = int(mod(pos.x, 4.0));
            int y = int(mod(pos.y, 4.0));
            
            int index = x + y * 4;
            float bayer[16] = float[16](
                0.0/16.0,  8.0/16.0,  2.0/16.0, 10.0/16.0,
               12.0/16.0,  4.0/16.0, 14.0/16.0,  6.0/16.0,
                3.0/16.0, 11.0/16.0,  1.0/16.0,  9.0/16.0,
               15.0/16.0,  7.0/16.0, 13.0/16.0,  5.0/16.0
            );
            
            return bayer[index];
        }
        
        void main() {
            // If no signal, just pass through the original texture
            if (signal_strength <= 0.0) {
                color = texture(input_texture, uv).rgb;
                return;
            }
            
            // Calculate dynamic pixel size based on signal strength
            // Signal strength directly controls pixelation intensity
            float dynamic_pixel_size = pixel_size * signal_strength;
            
            // If pixel size is too small, just use original texture
            if (dynamic_pixel_size < 1.0) {
                color = texture(input_texture, uv).rgb;
                return;
            }
            
            // Calculate pixel grid coordinates
            vec2 pixel_coords = floor(uv * texture_size / dynamic_pixel_size) * dynamic_pixel_size;
            vec2 pixel_uv = pixel_coords / texture_size;
            
            // Sample the texture at the pixel center
            vec3 pixel_color = texture(input_texture, pixel_uv + vec2(dynamic_pixel_size * 0.5) / texture_size).rgb;
            
            // Apply color quantization based on signal strength
            if (color_depth < 256.0 && signal_strength > 0.3) {
                vec3 quantized = pixel_color;
                
                if (dither) {
                    // Apply dithering before quantization
                    vec2 screen_pos = uv * texture_size;
                    float dither_value = (dither_pattern(screen_pos) - 0.5) / color_depth;
                    quantized += vec3(dither_value);
                }
                
                // Quantize colors with intensity based on signal
                float quantize_strength = signal_strength;
                quantized = floor(quantized * (color_depth * quantize_strength)) / (color_depth * quantize_strength);
                pixel_color = clamp(quantized, 0.0, 1.0);
            }
            
            // Add slight retro color shift for authenticity, but only when pixelating
            if (signal_strength > 0.1) {
                pixel_color.r *= 1.05;
                pixel_color.g *= 0.98;
                pixel_color.b *= 1.02;
            }
            
            color = clamp(pixel_color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set pixelate effect uniforms"""
        # Get signal value for dynamic pixelation
        signal_value = frame[self.signal]

        # Set uniforms
        self.shader_program["pixel_size"] = self.pixel_size
        self.shader_program["color_depth"] = float(self.color_depth)
        self.shader_program["dither"] = self.dither
        self.shader_program["signal_strength"] = signal_value

        # Set texture size for pixel calculations
        if self.framebuffer:
            self.shader_program["texture_size"] = (
                float(self.framebuffer.width),
                float(self.framebuffer.height),
            )
