"""
Strobing effect interpreters for VJ layers, similar to fixture strobe effects
"""

import math
import random
import time
from typing import List, Tuple, Optional
import numpy as np
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class StrobeFlash(VJInterpreterBase):
    """Basic strobing effect that flashes layers on/off"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_frequency: float = 10.0,  # Hz
        strobe_intensity: float = 1.0,
        trigger_signal: FrameSignal = FrameSignal.strobe,
    ):
        super().__init__(layers, args)
        self.strobe_frequency = strobe_frequency
        self.strobe_intensity = strobe_intensity
        self.trigger_signal = trigger_signal

        # Strobe state
        self.strobe_active = False
        self.strobe_phase = 0.0
        self.frame_count = 0
        self.target_fps = 60  # Assume 60 FPS

        # Calculate frames per strobe cycle
        self.frames_per_cycle = max(1, int(self.target_fps / self.strobe_frequency))

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update strobing effect"""
        self.frame_count += 1

        # Check trigger signal
        trigger_value = frame[self.trigger_signal]
        self.strobe_active = trigger_value > 0.5

        if self.strobe_active:
            # Calculate strobe on/off state
            cycle_position = (
                self.frame_count % self.frames_per_cycle
            ) / self.frames_per_cycle
            strobe_on = cycle_position < 0.5  # On for first half of cycle

            # Apply strobe effect
            for layer in self.layers:
                if strobe_on:
                    # Strobe ON - full intensity
                    layer.set_alpha(self.strobe_intensity)

                    # Use bright colors from scheme
                    if hasattr(layer, "set_color"):
                        strobe_color = scheme.fg.rgb
                        bright_color = tuple(int(c * 255) for c in strobe_color)
                        layer.set_color(bright_color)
                else:
                    # Strobe OFF - very low intensity
                    layer.set_alpha(0.1)
        else:
            # No strobe - normal operation
            for layer in self.layers:
                layer.set_alpha(1.0)

    def set_strobe_frequency(self, frequency: float):
        """Set strobe frequency in Hz"""
        self.strobe_frequency = max(0.1, min(60.0, frequency))
        self.frames_per_cycle = max(1, int(self.target_fps / self.strobe_frequency))

    def __str__(self) -> str:
        status = "ON" if self.strobe_active else "OFF"
        return f"⚡StrobeFlash({self.strobe_frequency:.1f}Hz, {status})"


class ColorStrobe(VJInterpreterBase):
    """Color strobing that cycles through different colors"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_colors: List[Tuple[int, int, int]] = None,
        strobe_speed: float = 0.3,
        trigger_signal: FrameSignal = FrameSignal.strobe,
    ):
        super().__init__(layers, args)
        self.strobe_colors = strobe_colors or [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 255),  # White
            (255, 0, 255),  # Magenta
            (255, 255, 0),  # Yellow
            (0, 255, 255),  # Cyan
            (0, 0, 0),  # Black (off)
        ]
        self.strobe_speed = strobe_speed
        self.trigger_signal = trigger_signal

        # State
        self.strobe_active = False
        self.color_phase = 0.0
        self.current_color_index = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update color strobing"""
        # Check trigger
        trigger_value = frame[self.trigger_signal]
        energy = frame[FrameSignal.freq_all]

        self.strobe_active = trigger_value > 0.5

        if self.strobe_active:
            # Fast color cycling when strobing
            effective_speed = self.strobe_speed * 10
        else:
            # Slow cycling based on energy when not strobing
            effective_speed = self.strobe_speed * (0.5 + 1.5 * energy)

        self.color_phase += effective_speed

        # Update color index
        new_color_index = int(self.color_phase) % len(self.strobe_colors)
        if new_color_index != self.current_color_index:
            self.current_color_index = new_color_index

        current_color = self.strobe_colors[self.current_color_index]

        # Apply color to layers
        for layer in self.layers:
            if hasattr(layer, "set_color"):
                layer.set_color(current_color)

            # Alpha strobing
            if self.strobe_active:
                # Rapid alpha strobing
                alpha_phase = self.color_phase * 4
                alpha = 0.3 + 0.7 * ((math.sin(alpha_phase) + 1.0) / 2.0)
                layer.set_alpha(alpha)
            else:
                # Normal alpha
                layer.set_alpha(0.8)

    def add_color(self, color: Tuple[int, int, int]):
        """Add a color to the strobe palette"""
        if color not in self.strobe_colors:
            self.strobe_colors.append(color)

    def set_colors_from_scheme(self, scheme: ColorScheme):
        """Set strobe colors from color scheme"""
        self.strobe_colors = [
            tuple(int(c * 255) for c in scheme.fg.rgb),
            tuple(int(c * 255) for c in scheme.bg.rgb),
            tuple(int(c * 255) for c in scheme.bg_contrast.rgb),
            (255, 255, 255),  # White
            (0, 0, 0),  # Black (off)
        ]

    def __str__(self) -> str:
        color_name = self._get_color_name(self.strobe_colors[self.current_color_index])
        status = "STROBING" if self.strobe_active else "cycling"
        return f"🌈ColorStrobe({color_name}, {status})"

    def _get_color_name(self, color: Tuple[int, int, int]) -> str:
        """Get simple color name"""
        r, g, b = color

        if r > 200 and g < 100 and b < 100:
            return "Red"
        elif g > 200 and r < 100 and b < 100:
            return "Green"
        elif b > 200 and r < 100 and g < 100:
            return "Blue"
        elif r > 200 and g > 200 and b > 200:
            return "White"
        elif r < 50 and g < 50 and b < 50:
            return "Black"
        elif r > 200 and g > 150 and b < 100:
            return "Orange"
        elif r > 100 and g < 150 and b > 100:
            return "Purple"
        else:
            return "Mixed"


class BeatStrobe(VJInterpreterBase):
    """Strobing synchronized to beat detection"""

    hype = 85

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        beat_signal: FrameSignal = FrameSignal.freq_high,
        beat_threshold: float = 0.7,
        strobe_duration: int = 8,  # Frames
        strobe_intensity: float = 1.0,
    ):
        super().__init__(layers, args)
        self.beat_signal = beat_signal
        self.beat_threshold = beat_threshold
        self.strobe_duration = strobe_duration
        self.strobe_intensity = strobe_intensity

        # State
        self.strobe_frames_remaining = 0
        self.last_beat_signal = 0.0
        self.beat_count = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update beat-synchronized strobing"""
        beat_value = frame[self.beat_signal]

        # Detect beat (rising edge)
        if (
            beat_value > self.beat_threshold
            and self.last_beat_signal <= self.beat_threshold
        ):
            self.strobe_frames_remaining = self.strobe_duration
            self.beat_count += 1

        self.last_beat_signal = beat_value

        # Apply strobe effect
        if self.strobe_frames_remaining > 0:
            self.strobe_frames_remaining -= 1

            # Strobe intensity decays over duration
            decay_factor = self.strobe_frames_remaining / self.strobe_duration
            current_intensity = self.strobe_intensity * (0.5 + 0.5 * decay_factor)

            # Flash effect
            flash_on = (
                self.strobe_frames_remaining % 4
            ) < 2  # 2 frames on, 2 frames off

            for layer in self.layers:
                if flash_on:
                    layer.set_alpha(current_intensity)

                    # Bright color from scheme
                    if hasattr(layer, "set_color"):
                        if self.beat_count % 2 == 0:
                            color = scheme.fg.rgb
                        else:
                            color = scheme.bg_contrast.rgb

                        bright_color = tuple(int(c * 255) for c in color)
                        layer.set_color(bright_color)
                else:
                    layer.set_alpha(0.2)  # Dim during off phase
        else:
            # No strobe - normal operation
            for layer in self.layers:
                layer.set_alpha(0.8)

    def __str__(self) -> str:
        status = (
            f"FLASHING ({self.strobe_frames_remaining})"
            if self.strobe_frames_remaining > 0
            else "ready"
        )
        return f"🥁BeatStrobe({status}, beats: {self.beat_count})"


class RandomStrobe(VJInterpreterBase):
    """Random strobing effects with varying intensity"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_probability: float = 0.05,  # Per frame probability
        min_duration: int = 3,
        max_duration: int = 12,
        energy_influence: bool = True,
    ):
        super().__init__(layers, args)
        self.strobe_probability = strobe_probability
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.energy_influence = energy_influence

        # State
        self.strobe_frames_remaining = 0
        self.strobe_pattern = []
        self.pattern_index = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update random strobing"""
        energy = frame[FrameSignal.freq_all]

        # Trigger random strobe
        if self.strobe_frames_remaining == 0:
            # Probability affected by energy if enabled
            effective_probability = self.strobe_probability
            if self.energy_influence:
                effective_probability *= 1 + energy * 2

            if random.random() < effective_probability:
                self._start_random_strobe()

        # Apply strobe pattern
        if self.strobe_frames_remaining > 0:
            self.strobe_frames_remaining -= 1

            # Get current pattern value
            pattern_value = self.strobe_pattern[
                self.pattern_index % len(self.strobe_pattern)
            ]
            self.pattern_index += 1

            for layer in self.layers:
                if pattern_value > 0:
                    # Strobe ON
                    layer.set_alpha(pattern_value)

                    # Random color from scheme
                    if hasattr(layer, "set_color"):
                        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]
                        color = random.choice(colors)
                        bright_color = tuple(int(c * 255) for c in color)
                        layer.set_color(bright_color)
                else:
                    # Strobe OFF
                    layer.set_alpha(0.1)
        else:
            # No strobe
            for layer in self.layers:
                layer.set_alpha(0.7)

    def _start_random_strobe(self):
        """Start a random strobe pattern"""
        duration = random.randint(self.min_duration, self.max_duration)
        self.strobe_frames_remaining = duration
        self.pattern_index = 0

        # Generate random strobe pattern
        self.strobe_pattern = []
        for _ in range(duration):
            if random.random() < 0.7:  # 70% chance of being on
                intensity = random.uniform(0.6, 1.0)
                self.strobe_pattern.append(intensity)
            else:
                self.strobe_pattern.append(0.0)  # Off

    def __str__(self) -> str:
        status = (
            f"ACTIVE ({self.strobe_frames_remaining})"
            if self.strobe_frames_remaining > 0
            else "waiting"
        )
        return f"🎲RandomStrobe({status})"


class HighSpeedStrobe(VJInterpreterBase):
    """Very fast strobing for intense moments"""

    hype = 95

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        base_frequency: float = 20.0,  # Hz
        max_frequency: float = 60.0,  # Hz
        trigger_threshold: float = 0.8,
    ):
        super().__init__(layers, args)
        self.base_frequency = base_frequency
        self.max_frequency = max_frequency
        self.trigger_threshold = trigger_threshold

        # State
        self.current_frequency = base_frequency
        self.strobe_phase = 0.0
        self.intensity_multiplier = 1.0
        self.target_fps = 60

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update high-speed strobing"""
        # Get trigger signals
        sustained_high = frame[FrameSignal.sustained_high]
        energy = frame[FrameSignal.freq_all]

        # Calculate strobe frequency based on energy
        if sustained_high > self.trigger_threshold:
            # High-speed strobe mode
            frequency_range = self.max_frequency - self.base_frequency
            self.current_frequency = self.base_frequency + frequency_range * energy
            self.intensity_multiplier = 1.2
        else:
            # Normal frequency
            self.current_frequency = self.base_frequency * (0.5 + 0.5 * energy)
            self.intensity_multiplier = 0.8

        # Update strobe phase
        self.strobe_phase += (self.current_frequency / self.target_fps) * math.pi * 2

        # Calculate strobe value
        strobe_value = (math.sin(self.strobe_phase) + 1.0) / 2.0
        strobe_alpha = strobe_value * self.intensity_multiplier

        # Apply to layers
        for layer in self.layers:
            layer.set_alpha(strobe_alpha)

            # Color intensity based on strobe
            if hasattr(layer, "set_color"):
                base_color = scheme.fg.rgb
                intensity_factor = 0.5 + 0.5 * strobe_value

                strobe_color = tuple(
                    int(c * 255 * intensity_factor) for c in base_color
                )
                layer.set_color(strobe_color)

    def __str__(self) -> str:
        return f"⚡HighSpeedStrobe({self.current_frequency:.1f}Hz)"


class PatternStrobe(VJInterpreterBase):
    """Strobing with predefined patterns"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        patterns: List[List[float]] = None,
        pattern_speed: float = 1.0,
        trigger_signal: FrameSignal = FrameSignal.strobe,
    ):
        super().__init__(layers, args)
        self.patterns = patterns or [
            [1.0, 0.0, 1.0, 0.0],  # Simple on/off
            [1.0, 1.0, 0.0, 0.0],  # Double flash
            [1.0, 0.5, 1.0, 0.0, 0.0, 0.0],  # Double with fade
            [1.0, 0.0, 0.5, 0.0, 1.0, 0.0, 0.0],  # Triple flash
            [1.0, 0.8, 0.6, 0.4, 0.2, 0.0],  # Fade down
            [0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4],  # Fade up and down
        ]
        self.pattern_speed = pattern_speed
        self.trigger_signal = trigger_signal

        # State
        self.strobe_active = False
        self.current_pattern_index = 0
        self.pattern_position = 0
        self.pattern_frame_count = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pattern strobing"""
        trigger_value = frame[self.trigger_signal]
        energy = frame[FrameSignal.freq_all]

        self.strobe_active = trigger_value > 0.5

        if self.strobe_active:
            # Advance pattern
            effective_speed = self.pattern_speed * (1 + energy)
            self.pattern_frame_count += effective_speed

            # Get current pattern
            pattern = self.patterns[self.current_pattern_index]
            self.pattern_position = int(self.pattern_frame_count) % len(pattern)

            # Get pattern value
            pattern_value = pattern[self.pattern_position]

            # Apply to layers
            for layer in self.layers:
                layer.set_alpha(pattern_value)

                if hasattr(layer, "set_color"):
                    # Color varies with pattern position
                    color_intensity = 0.5 + 0.5 * pattern_value
                    base_color = scheme.fg.rgb

                    pattern_color = tuple(
                        int(c * 255 * color_intensity) for c in base_color
                    )
                    layer.set_color(pattern_color)
        else:
            # Not strobing - maybe change pattern
            if random.random() < 0.01:  # 1% chance per frame to change pattern
                self.current_pattern_index = (self.current_pattern_index + 1) % len(
                    self.patterns
                )
                self.pattern_frame_count = 0

            # Normal alpha
            for layer in self.layers:
                layer.set_alpha(0.8)

    def add_pattern(self, pattern: List[float]):
        """Add a custom strobe pattern"""
        # Validate pattern
        if all(0.0 <= value <= 1.0 for value in pattern):
            self.patterns.append(pattern)

    def __str__(self) -> str:
        if self.strobe_active:
            pattern_len = len(self.patterns[self.current_pattern_index])
            return f"📋PatternStrobe(pattern {self.current_pattern_index+1}, {self.pattern_position+1}/{pattern_len})"
        else:
            return f"📋PatternStrobe(ready, {len(self.patterns)} patterns)"


class AudioReactiveStrobe(VJInterpreterBase):
    """Strobing that reacts to different audio frequencies"""

    hype = 90

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        bass_strobe: bool = True,
        treble_strobe: bool = True,
        sustained_strobe: bool = True,
    ):
        super().__init__(layers, args)
        self.bass_strobe = bass_strobe
        self.treble_strobe = treble_strobe
        self.sustained_strobe = sustained_strobe

        # Strobe states for different frequencies
        self.bass_strobe_phase = 0.0
        self.treble_strobe_phase = 0.0
        self.sustained_strobe_phase = 0.0

        # Intensity tracking
        self.bass_intensity = 0.0
        self.treble_intensity = 0.0
        self.sustained_intensity = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update audio-reactive strobing"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        sustained = frame[FrameSignal.sustained_low]

        # Update strobe phases based on audio
        if self.bass_strobe:
            self.bass_strobe_phase += bass * 0.8
            self.bass_intensity = bass

        if self.treble_strobe:
            self.treble_strobe_phase += treble * 1.2
            self.treble_intensity = treble

        if self.sustained_strobe:
            self.sustained_strobe_phase += sustained * 0.4
            self.sustained_intensity = sustained

        # Combine strobe effects
        total_strobe = 0.0
        active_strobes = 0

        if self.bass_strobe and bass > 0.3:
            bass_strobe_value = (math.sin(self.bass_strobe_phase * 4) + 1.0) / 2.0
            total_strobe += bass_strobe_value * bass
            active_strobes += 1

        if self.treble_strobe and treble > 0.3:
            treble_strobe_value = (math.sin(self.treble_strobe_phase * 6) + 1.0) / 2.0
            total_strobe += treble_strobe_value * treble
            active_strobes += 1

        if self.sustained_strobe and sustained > 0.3:
            sustained_strobe_value = (
                math.sin(self.sustained_strobe_phase * 2) + 1.0
            ) / 2.0
            total_strobe += sustained_strobe_value * sustained
            active_strobes += 1

        # Average if multiple strobes active
        if active_strobes > 0:
            final_strobe = total_strobe / active_strobes
        else:
            final_strobe = 0.5  # Default

        # Apply to layers
        for layer in self.layers:
            layer.set_alpha(0.3 + 0.7 * final_strobe)

            # Color mixing based on dominant frequency
            if hasattr(layer, "set_color"):
                if bass > treble and bass > sustained:
                    # Bass dominant - red
                    dominant_color = (1.0, 0.2, 0.2)
                elif treble > bass and treble > sustained:
                    # Treble dominant - blue/white
                    dominant_color = (0.8, 0.8, 1.0)
                else:
                    # Sustained dominant - green
                    dominant_color = (0.2, 1.0, 0.2)

                strobe_color = tuple(
                    int(c * 255 * (0.5 + 0.5 * final_strobe)) for c in dominant_color
                )
                layer.set_color(strobe_color)

    def __str__(self) -> str:
        active_modes = []
        if self.bass_strobe and self.bass_intensity > 0.3:
            active_modes.append("BASS")
        if self.treble_strobe and self.treble_intensity > 0.3:
            active_modes.append("TREBLE")
        if self.sustained_strobe and self.sustained_intensity > 0.3:
            active_modes.append("SUSTAINED")

        status = "+".join(active_modes) if active_modes else "idle"
        return f"🎵AudioReactiveStrobe({status})"


class LayerSelectiveStrobe(VJInterpreterBase):
    """Strobing that affects different layers independently"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_frequency: float = 8.0,
        layer_offset: float = 0.25,
    ):  # Phase offset between layers
        super().__init__(layers, args)
        self.strobe_frequency = strobe_frequency
        self.layer_offset = layer_offset

        # Individual layer states
        self.layer_phases = []
        self.layer_intensities = []

        for i, layer in enumerate(layers):
            self.layer_phases.append(i * layer_offset)
            self.layer_intensities.append(0.5)

        self.frame_count = 0
        self.target_fps = 60

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update selective layer strobing"""
        self.frame_count += 1

        # Check if strobing is active
        strobe_signal = frame[FrameSignal.strobe]
        energy = frame[FrameSignal.freq_all]

        strobe_active = strobe_signal > 0.5 or energy > 0.8

        if strobe_active:
            # Update each layer independently
            for i, layer in enumerate(self.layers):
                # Each layer has its own phase
                self.layer_phases[i] += (
                    (self.strobe_frequency / self.target_fps) * math.pi * 2
                )

                # Calculate strobe value for this layer
                strobe_value = (math.sin(self.layer_phases[i]) + 1.0) / 2.0

                # Apply energy influence
                effective_strobe = strobe_value * (0.5 + 0.5 * energy)

                layer.set_alpha(effective_strobe)

                # Different layers get different colors
                if hasattr(layer, "set_color"):
                    if i % 3 == 0:
                        color = scheme.fg.rgb
                    elif i % 3 == 1:
                        color = scheme.bg.rgb
                    else:
                        color = scheme.bg_contrast.rgb

                    layer_color = tuple(
                        int(c * 255 * (0.5 + 0.5 * effective_strobe)) for c in color
                    )
                    layer.set_color(layer_color)
        else:
            # No strobe - normal operation
            for layer in self.layers:
                layer.set_alpha(0.8)

    def __str__(self) -> str:
        avg_intensity = sum(self.layer_intensities) / max(
            1, len(self.layer_intensities)
        )
        return f"🔄LayerSelectiveStrobe({len(self.layers)} layers, {avg_intensity:.1f})"


class StrobeBlackout(VJInterpreterBase):
    """Strobing with blackout effects"""

    hype = 55

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        blackout_probability: float = 0.3,  # Probability of blackout vs flash
        flash_duration: int = 2,
        blackout_duration: int = 4,
    ):
        super().__init__(layers, args)
        self.blackout_probability = blackout_probability
        self.flash_duration = flash_duration
        self.blackout_duration = blackout_duration

        # State
        self.current_state = "normal"  # "normal", "flash", "blackout"
        self.state_frames_remaining = 0
        self.trigger_cooldown = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update strobe blackout effect"""
        strobe_signal = frame[FrameSignal.strobe]
        energy = frame[FrameSignal.freq_all]

        # Update cooldown
        if self.trigger_cooldown > 0:
            self.trigger_cooldown -= 1

        # Trigger new effect
        if (
            strobe_signal > 0.5
            and self.trigger_cooldown == 0
            and self.current_state == "normal"
        ):

            if random.random() < self.blackout_probability:
                # Trigger blackout
                self.current_state = "blackout"
                self.state_frames_remaining = self.blackout_duration
            else:
                # Trigger flash
                self.current_state = "flash"
                self.state_frames_remaining = self.flash_duration

            self.trigger_cooldown = 10  # Prevent rapid retriggering

        # Update current state
        if self.state_frames_remaining > 0:
            self.state_frames_remaining -= 1
        else:
            self.current_state = "normal"

        # Apply effect based on state
        for layer in self.layers:
            if self.current_state == "blackout":
                # Complete blackout
                layer.set_alpha(0.0)

            elif self.current_state == "flash":
                # Bright flash
                layer.set_alpha(1.0)

                if hasattr(layer, "set_color"):
                    # Bright white flash
                    layer.set_color((255, 255, 255))

            else:
                # Normal operation with slight energy modulation
                layer.set_alpha(0.6 + 0.4 * energy)

    def __str__(self) -> str:
        if self.current_state != "normal":
            return f"⚫StrobeBlackout({self.current_state.upper()} {self.state_frames_remaining})"
        else:
            return f"⚫StrobeBlackout(normal)"


class RGBChannelStrobe(VJInterpreterBase):
    """Strobing that affects RGB channels independently"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        channel_frequencies: Tuple[float, float, float] = (8.0, 12.0, 16.0),
        channel_signals: Tuple[FrameSignal, FrameSignal, FrameSignal] = None,
    ):
        super().__init__(layers, args)
        self.red_freq, self.green_freq, self.blue_freq = channel_frequencies

        # Default channel signals
        if channel_signals is None:
            self.channel_signals = (
                FrameSignal.freq_low,  # Red follows bass
                FrameSignal.freq_all,  # Green follows mid
                FrameSignal.freq_high,  # Blue follows treble
            )
        else:
            self.channel_signals = channel_signals

        # Channel phases
        self.red_phase = 0.0
        self.green_phase = 0.0
        self.blue_phase = 0.0

        self.target_fps = 60

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update RGB channel strobing"""
        # Get signal values
        red_signal = frame[self.channel_signals[0]]
        green_signal = frame[self.channel_signals[1]]
        blue_signal = frame[self.channel_signals[2]]

        # Update channel phases
        self.red_phase += (
            (self.red_freq / self.target_fps) * math.pi * 2 * (0.5 + 1.5 * red_signal)
        )
        self.green_phase += (
            (self.green_freq / self.target_fps)
            * math.pi
            * 2
            * (0.5 + 1.5 * green_signal)
        )
        self.blue_phase += (
            (self.blue_freq / self.target_fps) * math.pi * 2 * (0.5 + 1.5 * blue_signal)
        )

        # Calculate channel values
        red_strobe = (math.sin(self.red_phase) + 1.0) / 2.0
        green_strobe = (math.sin(self.green_phase) + 1.0) / 2.0
        blue_strobe = (math.sin(self.blue_phase) + 1.0) / 2.0

        # Apply to layers
        for layer in self.layers:
            if hasattr(layer, "set_color"):
                # Each channel strobes independently
                r = int(255 * red_strobe * (0.3 + 0.7 * red_signal))
                g = int(255 * green_strobe * (0.3 + 0.7 * green_signal))
                b = int(255 * blue_strobe * (0.3 + 0.7 * blue_signal))

                layer.set_color((r, g, b))

            # Overall alpha from combined channels
            combined_alpha = (red_strobe + green_strobe + blue_strobe) / 3.0
            layer.set_alpha(0.4 + 0.6 * combined_alpha)

    def __str__(self) -> str:
        return f"🌈RGBChannelStrobe(R:{self.red_freq:.0f}Hz G:{self.green_freq:.0f}Hz B:{self.blue_freq:.0f}Hz)"


class StrobeZoom(VJInterpreterBase):
    """Strobing with zoom/scale effects"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        zoom_range: Tuple[float, float] = (0.5, 2.0),
        strobe_frequency: float = 12.0,
    ):
        super().__init__(layers, args)
        self.min_zoom, self.max_zoom = zoom_range
        self.strobe_frequency = strobe_frequency

        # State
        self.strobe_phase = 0.0
        self.zoom_phase = 0.0
        self.target_fps = 60

        # Filter for layers that support scaling
        from parrot.vj.layers.text import TextLayer, MockTextLayer

        self.scalable_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update strobe zoom effect"""
        strobe_signal = frame[FrameSignal.strobe]
        energy = frame[FrameSignal.freq_all]

        strobe_active = strobe_signal > 0.5

        if strobe_active:
            # Update phases
            self.strobe_phase += (self.strobe_frequency / self.target_fps) * math.pi * 2
            self.zoom_phase += 0.1 * (1 + energy)

            # Calculate strobe and zoom values
            strobe_value = (math.sin(self.strobe_phase) + 1.0) / 2.0
            zoom_value = (math.sin(self.zoom_phase) + 1.0) / 2.0

            # Apply to all layers
            for layer in self.layers:
                # Alpha strobing
                layer.set_alpha(0.3 + 0.7 * strobe_value)

                # Color strobing
                if hasattr(layer, "set_color"):
                    base_color = scheme.fg.rgb
                    strobe_color = tuple(
                        int(c * 255 * (0.5 + 0.5 * strobe_value)) for c in base_color
                    )
                    layer.set_color(strobe_color)

            # Scale strobing for scalable layers
            current_zoom = self.min_zoom + (self.max_zoom - self.min_zoom) * zoom_value
            for layer in self.scalable_layers:
                if hasattr(layer, "set_scale"):
                    layer.set_scale(current_zoom)
        else:
            # Not strobing - reset to normal
            for layer in self.layers:
                layer.set_alpha(0.8)

            for layer in self.scalable_layers:
                if hasattr(layer, "set_scale"):
                    layer.set_scale(1.0)

    def __str__(self) -> str:
        strobe_signal = (
            "ACTIVE"
            if hasattr(self, "_last_strobe_active") and self._last_strobe_active
            else "ready"
        )
        return f"🔍StrobeZoom({strobe_signal}, {len(self.scalable_layers)} scalable)"
