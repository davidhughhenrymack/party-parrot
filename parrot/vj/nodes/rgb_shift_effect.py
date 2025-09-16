#!/usr/bin/env python3

import time
import math
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class RGBShiftEffect(PostProcessEffectBase):
    """
    RGB channel shifting effect that creates chromatic aberration glitches.
    Separates and shifts RGB channels to create retro VHS/analog distortion effects.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        shift_strength: float = 0.01,
        shift_speed: float = 2.0,
        vertical_shift: bool = False,
        signal: FrameSignal = FrameSignal.freq_all,
    ):
        """
        Args:
            input_node: The node that provides the video input
            shift_strength: Maximum shift distance (0.0 = none, 0.1 = extreme)
            shift_speed: Speed of shift animation
            vertical_shift: If True, also apply vertical shifting
            signal: Which frame signal controls shift intensity
        """
        super().__init__(input_node)
        self.shift_strength = shift_strength
        self.shift_speed = shift_speed
        self.vertical_shift = vertical_shift
        self.signal = signal

        # Animation state
        self.start_time = time.time()

    def generate(self, vibe: Vibe):
        """Configure RGB shift parameters based on the vibe"""
        # Could randomize shift patterns based on vibe
        pass

    def _get_fragment_shader(self) -> str:
        """Fragment shader for RGB shift effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float shift_strength;
        uniform float time_offset;
        uniform float signal_strength;
        uniform bool vertical_shift;
        
        void main() {
            // Calculate dynamic shift amounts based on time and signal
            float red_shift_x = sin(time_offset * 1.3) * shift_strength * signal_strength;
            float blue_shift_x = sin(time_offset * 0.8 + 3.14159) * shift_strength * signal_strength;
            float green_shift_x = sin(time_offset * 1.1 + 1.57) * shift_strength * signal_strength * 0.5;
            
            vec2 red_offset = vec2(red_shift_x, 0.0);
            vec2 green_offset = vec2(green_shift_x, 0.0);
            vec2 blue_offset = vec2(blue_shift_x, 0.0);
            
            // Add vertical shifting if enabled
            if (vertical_shift) {
                float red_shift_y = cos(time_offset * 0.7) * shift_strength * signal_strength * 0.3;
                float blue_shift_y = cos(time_offset * 0.9 + 1.57) * shift_strength * signal_strength * 0.3;
                
                red_offset.y += red_shift_y;
                blue_offset.y += blue_shift_y;
            }
            
            // Sample each channel with its offset
            vec2 red_uv = clamp(uv + red_offset, 0.0, 1.0);
            vec2 green_uv = clamp(uv + green_offset, 0.0, 1.0);
            vec2 blue_uv = clamp(uv + blue_offset, 0.0, 1.0);
            
            float red_channel = texture(input_texture, red_uv).r;
            float green_channel = texture(input_texture, green_uv).g;
            float blue_channel = texture(input_texture, blue_uv).b;
            
            color = vec3(red_channel, green_channel, blue_channel);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set RGB shift effect uniforms"""
        # Get signal value for shift intensity
        signal_value = frame[self.signal]

        # Calculate time offset for animation
        current_time = time.time()
        time_offset = (current_time - self.start_time) * self.shift_speed

        # Set uniforms
        self.shader_program["shift_strength"] = self.shift_strength
        self.shader_program["time_offset"] = time_offset
        self.shader_program["signal_strength"] = signal_value
        self.shader_program["vertical_shift"] = self.vertical_shift
