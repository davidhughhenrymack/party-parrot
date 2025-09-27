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

    def print_self(self) -> str:
        """Return class name with current signal in brackets"""
        return f"{self.__class__.__name__} [{self.signal.name}]"

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

        # Special responses to specific Frame signals
        strobe_value = frame[FrameSignal.strobe]
        big_blinder_value = frame[FrameSignal.big_blinder]
        pulse_value = frame[FrameSignal.pulse]

        # Calculate time offset for animation
        current_time = time.time()
        time_offset = (current_time - self.start_time) * self.shift_speed

        # Modify parameters based on special signals
        shift_strength = self.shift_strength
        effective_signal = signal_value

        # STROBE: Extreme rapid shifting
        if strobe_value > 0.5:
            shift_strength = self.shift_strength * 3.0  # Triple the shift strength
            time_offset *= 8.0  # Much faster animation
            effective_signal = 1.0  # Maximum intensity

        # BIG BLINDER: Massive displacement
        elif big_blinder_value > 0.5:
            shift_strength = self.shift_strength * 5.0  # Extreme shift
            effective_signal = big_blinder_value

        # PULSE: Sharp, instant shifts
        elif pulse_value > 0.5:
            # Create sharp, non-smooth shifts during pulse
            pulse_time = int(current_time * 10.0)  # Discrete time steps
            time_offset = float(pulse_time)
            shift_strength = self.shift_strength * 2.0
            effective_signal = pulse_value

        # Set uniforms
        self.shader_program["shift_strength"] = shift_strength
        self.shader_program["time_offset"] = time_offset
        self.shader_program["signal_strength"] = effective_signal
        self.shader_program["vertical_shift"] = self.vertical_shift
