"""
Shader effect interpreters for trippy rave visuals
"""

import math
import random
from typing import List
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class ShaderIntensity(VJInterpreterBase):
    """Controls shader layer intensity based on audio"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        intensity_signal: FrameSignal = FrameSignal.freq_all,
        min_intensity: float = 0.2,
        max_intensity: float = 1.0,
    ):
        super().__init__(layers, args)
        self.intensity_signal = intensity_signal
        self.min_intensity = min_intensity
        self.max_intensity = max_intensity

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update shader intensity based on audio"""
        signal_value = frame[self.intensity_signal]

        # Map to intensity range
        intensity = (
            self.min_intensity
            + (self.max_intensity - self.min_intensity) * signal_value
        )

        # Apply to shader layers
        for layer in self.shader_layers:
            layer.set_alpha(intensity)

    def __str__(self) -> str:
        return f"🌈ShaderIntensity({self.intensity_signal.name})"


class ShaderCycler(VJInterpreterBase):
    """Cycles through different shader effects"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        cycle_speed: float = 0.02,
        switch_on_beat: bool = True,
    ):
        super().__init__(layers, args)
        self.cycle_speed = cycle_speed
        self.switch_on_beat = switch_on_beat
        self.cycle_phase = 0.0
        self.current_shader_index = 0
        self.last_beat_signal = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Cycle through shader effects"""
        energy = frame[FrameSignal.freq_all]
        beat_signal = frame[FrameSignal.freq_high]

        # Update cycle
        effective_speed = self.cycle_speed * (1 + energy)
        self.cycle_phase += effective_speed

        # Switch on beat if enabled
        if self.switch_on_beat and beat_signal > 0.7 and self.last_beat_signal <= 0.7:
            self._switch_shader()

        self.last_beat_signal = beat_signal

        # Enable/disable shaders based on current selection
        for i, layer in enumerate(self.shader_layers):
            if i == self.current_shader_index:
                layer.set_enabled(True)
                layer.set_alpha(0.7 + 0.3 * energy)
            else:
                layer.set_enabled(False)

    def _switch_shader(self):
        """Switch to next shader"""
        if self.shader_layers:
            self.current_shader_index = (self.current_shader_index + 1) % len(
                self.shader_layers
            )

    def __str__(self) -> str:
        if self.shader_layers:
            current_name = self.shader_layers[self.current_shader_index].name
            return f"🔄ShaderCycler({current_name}, {self.current_shader_index+1}/{len(self.shader_layers)})"
        else:
            return f"🔄ShaderCycler(no shaders)"


class ShaderMixer(VJInterpreterBase):
    """Mixes multiple shader effects together"""

    hype = 80

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, mix_speed: float = 0.03
    ):
        super().__init__(layers, args)
        self.mix_speed = mix_speed
        self.mix_phase = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Mix shader effects based on audio"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update mix phase
        self.mix_phase += self.mix_speed * (1 + energy)

        # Calculate mix ratios for each shader
        for i, layer in enumerate(self.shader_layers):
            # Each shader gets different mix pattern
            phase_offset = i * (math.pi * 2 / max(1, len(self.shader_layers)))
            mix_value = math.sin(self.mix_phase + phase_offset) * 0.5 + 0.5

            # Audio influence
            if i % 3 == 0:
                mix_value *= 0.4 + bass * 1.2
            elif i % 3 == 1:
                mix_value *= 0.4 + treble * 1.2
            else:
                mix_value *= 0.4 + energy * 1.2

            layer.set_alpha(mix_value)

    def __str__(self) -> str:
        return f"🎨ShaderMixer({len(self.shader_layers)} shaders, {self.mix_phase:.1f})"


class ShaderGlitcher(VJInterpreterBase):
    """Adds glitch effects to shader layers"""

    hype = 85

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        glitch_probability: float = 0.03,
        glitch_intensity: float = 0.8,
    ):
        super().__init__(layers, args)
        self.glitch_probability = glitch_probability
        self.glitch_intensity = glitch_intensity
        self.glitch_active = False
        self.glitch_frames_remaining = 0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply glitch effects to shaders"""
        energy = frame[FrameSignal.freq_all]
        treble = frame[FrameSignal.freq_high]

        # Trigger glitch
        if not self.glitch_active and random.random() < self.glitch_probability * (
            1 + energy
        ):
            self.glitch_active = True
            self.glitch_frames_remaining = random.randint(3, 8)

        # Update glitch
        if self.glitch_active:
            self.glitch_frames_remaining -= 1
            if self.glitch_frames_remaining <= 0:
                self.glitch_active = False

            # Apply glitch effects
            for layer in self.shader_layers:
                if hasattr(layer, "energy_uniform"):
                    # Boost energy for glitch effect
                    layer.energy_uniform = min(
                        1.0, energy + self.glitch_intensity * 0.5
                    )

                # Random alpha modulation
                glitch_alpha = 0.3 + random.random() * 0.7
                layer.set_alpha(glitch_alpha)
        else:
            # Normal operation
            for layer in self.shader_layers:
                layer.set_alpha(0.7 + 0.3 * energy)

    def __str__(self) -> str:
        status = "GLITCHING" if self.glitch_active else "normal"
        return f"📺ShaderGlitcher({status}, {len(self.shader_layers)} shaders)"


class ShaderBeat(VJInterpreterBase):
    """Shader effects that respond to beats"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        beat_threshold: float = 0.7,
        beat_boost: float = 0.5,
        beat_duration: int = 10,
    ):
        super().__init__(layers, args)
        self.beat_threshold = beat_threshold
        self.beat_boost = beat_boost
        self.beat_duration = beat_duration
        self.beat_frames_remaining = 0
        self.last_beat_signal = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update shader effects on beats"""
        beat_signal = frame[FrameSignal.freq_high]

        # Detect beat
        if (
            beat_signal > self.beat_threshold
            and self.last_beat_signal <= self.beat_threshold
        ):
            self.beat_frames_remaining = self.beat_duration

        self.last_beat_signal = beat_signal

        # Apply beat effects
        if self.beat_frames_remaining > 0:
            self.beat_frames_remaining -= 1

            # Beat boost intensity
            boost_factor = (
                self.beat_frames_remaining / self.beat_duration
            ) * self.beat_boost

            for layer in self.shader_layers:
                # Boost shader intensity on beats
                beat_alpha = 0.8 + boost_factor
                layer.set_alpha(beat_alpha)

                # Boost energy uniform if available
                if hasattr(layer, "energy_uniform"):
                    layer.energy_uniform = min(1.0, layer.energy_uniform + boost_factor)
        else:
            # Normal intensity
            energy = frame[FrameSignal.freq_all]
            for layer in self.shader_layers:
                layer.set_alpha(0.6 + 0.4 * energy)

    def __str__(self) -> str:
        status = (
            f"BEAT ({self.beat_frames_remaining})"
            if self.beat_frames_remaining > 0
            else "waiting"
        )
        return f"🥁ShaderBeat({status})"


class ShaderWarp(VJInterpreterBase):
    """Warps shader effects based on audio"""

    hype = 90

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, warp_strength: float = 1.0
    ):
        super().__init__(layers, args)
        self.warp_strength = warp_strength
        self.warp_phase = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply warping effects to shaders"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update warp phase
        self.warp_phase += 0.05 * (1 + energy * 2)

        # Apply warp effects to shaders
        for layer in self.shader_layers:
            # Intensity warping
            warp_intensity = (
                0.5 + 0.5 * math.sin(self.warp_phase + bass * 5) * self.warp_strength
            )
            layer.set_alpha(warp_intensity)

            # If layer has audio uniforms, modify them for warp effect
            if hasattr(layer, "bass_uniform"):
                layer.bass_uniform = bass * (0.5 + 0.5 * math.sin(self.warp_phase * 2))
            if hasattr(layer, "treble_uniform"):
                layer.treble_uniform = treble * (
                    0.5 + 0.5 * math.cos(self.warp_phase * 1.5)
                )
            if hasattr(layer, "energy_uniform"):
                layer.energy_uniform = energy * (
                    0.7 + 0.3 * math.sin(self.warp_phase * 3)
                )

    def __str__(self) -> str:
        return f"🌀ShaderWarp({self.warp_phase:.1f}, {len(self.shader_layers)} shaders)"


class ShaderStorm(VJInterpreterBase):
    """Creates chaotic shader storm effects"""

    hype = 95

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        storm_threshold: float = 0.8,
        storm_duration: int = 60,
    ):
        super().__init__(layers, args)
        self.storm_threshold = storm_threshold
        self.storm_duration = storm_duration
        self.storm_active = False
        self.storm_frames_remaining = 0
        self.last_energy = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create shader storm on high energy"""
        energy = frame[FrameSignal.freq_all]

        # Trigger storm on energy spike
        if energy > self.storm_threshold and self.last_energy <= self.storm_threshold:
            self.storm_active = True
            self.storm_frames_remaining = self.storm_duration

        self.last_energy = energy

        # Update storm
        if self.storm_active:
            self.storm_frames_remaining -= 1
            if self.storm_frames_remaining <= 0:
                self.storm_active = False

            # Chaotic shader effects during storm
            for i, layer in enumerate(self.shader_layers):
                # Random intensity fluctuations
                chaos_alpha = 0.5 + random.random() * 0.5
                layer.set_alpha(chaos_alpha)

                # Chaos audio values
                if hasattr(layer, "bass_uniform"):
                    layer.bass_uniform = min(
                        1.0, frame[FrameSignal.freq_low] + random.uniform(-0.3, 0.5)
                    )
                if hasattr(layer, "treble_uniform"):
                    layer.treble_uniform = min(
                        1.0, frame[FrameSignal.freq_high] + random.uniform(-0.3, 0.5)
                    )
                if hasattr(layer, "energy_uniform"):
                    layer.energy_uniform = min(1.0, energy + random.uniform(0.0, 0.3))
        else:
            # Normal operation
            for layer in self.shader_layers:
                layer.set_alpha(0.6 + 0.4 * energy)

    def __str__(self) -> str:
        if self.storm_active:
            return f"🌪️ShaderStorm(STORM! {self.storm_frames_remaining}f)"
        else:
            return f"🌪️ShaderStorm(calm)"


class ShaderColorSync(VJInterpreterBase):
    """Syncs shader colors with color scheme"""

    hype = 50

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        color_transition_speed: float = 0.02,
    ):
        super().__init__(layers, args)
        self.color_transition_speed = color_transition_speed
        self.color_phase = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Sync shader colors with scheme"""
        energy = frame[FrameSignal.freq_all]

        # Update color transition
        self.color_phase += self.color_transition_speed * (1 + energy)

        # Apply color scheme to shaders
        for layer in self.shader_layers:
            if hasattr(layer, "color1_uniform"):
                layer.color1_uniform = scheme.fg.rgb
            if hasattr(layer, "color2_uniform"):
                layer.color2_uniform = scheme.bg.rgb
            if hasattr(layer, "color3_uniform"):
                layer.color3_uniform = scheme.bg_contrast.rgb

    def __str__(self) -> str:
        return f"🎨ShaderColorSync({self.color_phase:.1f})"


class ShaderPulse(VJInterpreterBase):
    """Creates pulsing effects in shaders"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        pulse_frequency: float = 2.0,
        pulse_amplitude: float = 0.4,
    ):
        super().__init__(layers, args)
        self.pulse_frequency = pulse_frequency
        self.pulse_amplitude = pulse_amplitude
        self.pulse_phase = 0.0

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create pulsing shader effects"""
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Update pulse
        effective_frequency = self.pulse_frequency * (0.5 + 1.5 * bass)
        self.pulse_phase += effective_frequency * 0.1

        # Calculate pulse value
        pulse_value = math.sin(self.pulse_phase) * 0.5 + 0.5
        pulse_intensity = self.pulse_amplitude * pulse_value * (0.5 + 0.5 * energy)

        # Apply pulse to shaders
        for layer in self.shader_layers:
            base_alpha = 0.6 + 0.4 * energy
            pulsed_alpha = base_alpha + pulse_intensity
            layer.set_alpha(min(1.0, pulsed_alpha))

    def __str__(self) -> str:
        return f"💓ShaderPulse({self.pulse_frequency:.1f}Hz, {self.pulse_phase:.1f})"


class ShaderReactive(VJInterpreterBase):
    """Makes shaders highly reactive to audio"""

    hype = 85

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, reactivity: float = 2.0
    ):
        super().__init__(layers, args)
        self.reactivity = reactivity

        # Filter for shader layers
        self.shader_layers = [
            layer for layer in layers if hasattr(layer, "shader_source")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Make shaders highly reactive to audio"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Apply reactive effects
        for i, layer in enumerate(self.shader_layers):
            # Different shaders react to different frequencies
            if i % 3 == 0:
                # React to bass
                reactive_alpha = 0.3 + bass * self.reactivity
            elif i % 3 == 1:
                # React to treble
                reactive_alpha = 0.3 + treble * self.reactivity
            else:
                # React to overall energy
                reactive_alpha = 0.3 + energy * self.reactivity

            layer.set_alpha(min(1.0, reactive_alpha))

            # Boost shader uniforms for reactivity
            if hasattr(layer, "bass_uniform"):
                layer.bass_uniform = min(1.0, bass * self.reactivity)
            if hasattr(layer, "treble_uniform"):
                layer.treble_uniform = min(1.0, treble * self.reactivity)
            if hasattr(layer, "energy_uniform"):
                layer.energy_uniform = min(1.0, energy * self.reactivity)

    def __str__(self) -> str:
        return f"🎵ShaderReactive({self.reactivity:.1f}x, {len(self.shader_layers)} shaders)"
