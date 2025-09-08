"""
Pyramid effect interpreters for ravey metallic pyramid visuals
Controls floating, pulsing, and formation behaviors
"""

import math
import random
from typing import List
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class PyramidPulse(VJInterpreterBase):
    """Makes pyramids pulse dramatically to bass"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        pulse_intensity: float = 2.0,
        pulse_speed: float = 3.0,
    ):
        super().__init__(layers, args)
        self.pulse_intensity = pulse_intensity
        self.pulse_speed = pulse_speed
        self.pulse_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pyramid pulsing based on bass"""
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Update pulse phase
        self.pulse_phase += self.pulse_speed * 0.1 * (1 + energy)

        # Calculate pulse multiplier
        pulse_multiplier = (
            1.0 + math.sin(self.pulse_phase) * 0.5 * self.pulse_intensity * bass
        )

        # Apply to pyramid layers
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for pyramid in layer.pyramids:
                    pyramid.pulse_intensity = bass * self.pulse_intensity
                    # Boost bass sensitivity during pulse
                    pyramid.bass_sensitivity = 1.0 + pulse_multiplier * 0.5

            # Boost layer alpha during pulse
            layer.set_alpha(0.7 + 0.3 * pulse_multiplier)

    def __str__(self) -> str:
        return f"🔺PyramidPulse({self.pulse_intensity:.1f}x, {len(self.pyramid_layers)} layers)"


class PyramidFloat(VJInterpreterBase):
    """Controls pyramid floating behavior"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        float_speed: float = 1.5,
        float_range: float = 0.4,
    ):
        super().__init__(layers, args)
        self.float_speed = float_speed
        self.float_range = float_range
        self.float_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pyramid floating based on treble"""
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update float phase
        self.float_phase += self.float_speed * 0.02 * (1 + treble)

        # Apply floating to pyramids
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for i, pyramid in enumerate(layer.pyramids):
                    # Each pyramid floats with slight offset
                    phase_offset = i * 0.5
                    float_offset = (
                        math.sin(self.float_phase + phase_offset)
                        * self.float_range
                        * treble
                    )

                    pyramid.float_amplitude = 0.2 + float_offset
                    # Adjust Z position for floating effect
                    pyramid.z = pyramid.base_z + float_offset * 0.3

    def __str__(self) -> str:
        return f"🎈PyramidFloat({self.float_speed:.1f}x, {len(self.pyramid_layers)} layers)"


class PyramidSpin(VJInterpreterBase):
    """Controls pyramid rotation speeds"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        spin_multiplier: float = 2.0,
        sync_rotation: bool = False,
    ):
        super().__init__(layers, args)
        self.spin_multiplier = spin_multiplier
        self.sync_rotation = sync_rotation
        self.master_rotation = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pyramid rotation based on energy"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update master rotation if synced
        if self.sync_rotation:
            self.master_rotation += 0.05 * energy * self.spin_multiplier

        # Apply rotation to pyramids
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for pyramid in layer.pyramids:
                    if self.sync_rotation:
                        # Synchronized rotation
                        pyramid.rotation_speed = self.spin_multiplier * (0.5 + energy)
                        pyramid.rotation_y = self.master_rotation
                    else:
                        # Individual rotation based on audio
                        pyramid.rotation_speed = self.spin_multiplier * (
                            0.5 + bass * pyramid.bass_sensitivity + treble * 0.5
                        )

    def __str__(self) -> str:
        sync_status = "synced" if self.sync_rotation else "individual"
        return f"🌀PyramidSpin({self.spin_multiplier:.1f}x, {sync_status}, {len(self.pyramid_layers)} layers)"


class PyramidFormation(VJInterpreterBase):
    """Controls pyramid formation and arrangement"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        formation_speed: float = 1.0,
        morph_formations: bool = True,
    ):
        super().__init__(layers, args)
        self.formation_speed = formation_speed
        self.morph_formations = morph_formations
        self.formation_phase = 0.0
        self.current_formation = 0
        self.formations = ["circle", "grid", "spiral", "random"]

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pyramid formations"""
        energy = frame[FrameSignal.freq_all]
        bass = frame[FrameSignal.freq_low]

        # Update formation phase
        self.formation_phase += self.formation_speed * 0.01 * (1 + energy)

        # Switch formation on high energy
        if self.morph_formations and energy > 0.8 and bass > 0.7:
            if random.random() < 0.05:  # 5% chance per frame during high energy
                self._switch_formation()

        # Apply formation effects
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids") and len(layer.pyramids) > 1:
                self._apply_formation_movement(layer.pyramids, energy)

    def _switch_formation(self):
        """Switch to a new formation"""
        self.current_formation = (self.current_formation + 1) % len(self.formations)
        print(
            f"🔺 Pyramid formation switched to: {self.formations[self.current_formation]}"
        )

    def _apply_formation_movement(self, pyramids: List, energy: float):
        """Apply formation-based movement to pyramids"""
        formation = self.formations[self.current_formation]

        if formation == "circle":
            # Arrange in rotating circle
            for i, pyramid in enumerate(pyramids):
                angle = (i / len(pyramids)) * math.pi * 2 + self.formation_phase
                radius = 0.25 + 0.15 * energy

                target_x = 0.5 + radius * math.cos(angle)
                target_y = 0.5 + radius * math.sin(angle)

                # Smooth movement toward target
                pyramid.x += (target_x - pyramid.x) * 0.02
                pyramid.y += (target_y - pyramid.y) * 0.02

        elif formation == "grid":
            # Arrange in grid pattern
            grid_size = int(math.sqrt(len(pyramids))) + 1
            for i, pyramid in enumerate(pyramids):
                grid_x = i % grid_size
                grid_y = i // grid_size

                target_x = 0.2 + (grid_x / grid_size) * 0.6
                target_y = 0.2 + (grid_y / grid_size) * 0.6

                pyramid.x += (target_x - pyramid.x) * 0.03
                pyramid.y += (target_y - pyramid.y) * 0.03

        elif formation == "spiral":
            # Arrange in spiral
            for i, pyramid in enumerate(pyramids):
                t = i / len(pyramids)
                angle = t * math.pi * 4 + self.formation_phase
                radius = 0.1 + t * 0.3

                target_x = 0.5 + radius * math.cos(angle)
                target_y = 0.5 + radius * math.sin(angle)

                pyramid.x += (target_x - pyramid.x) * 0.025
                pyramid.y += (target_y - pyramid.y) * 0.025

        elif formation == "random":
            # Random movement
            for pyramid in pyramids:
                if random.random() < 0.01:  # Occasional random movement
                    pyramid.x += random.uniform(-0.05, 0.05) * energy
                    pyramid.y += random.uniform(-0.05, 0.05) * energy

                    # Keep in bounds
                    pyramid.x = max(0.1, min(0.9, pyramid.x))
                    pyramid.y = max(0.1, min(0.9, pyramid.y))

    def __str__(self) -> str:
        formation = self.formations[self.current_formation]
        return f"🔺PyramidFormation({formation}, {len(self.pyramid_layers)} layers)"


class PyramidMetallic(VJInterpreterBase):
    """Controls metallic finish intensity and reflection"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        reflection_speed: float = 2.0,
        metal_cycle: bool = False,
    ):
        super().__init__(layers, args)
        self.reflection_speed = reflection_speed
        self.metal_cycle = metal_cycle
        self.reflection_phase = 0.0
        self.metal_types = ["gold", "silver", "copper", "chrome", "bronze", "platinum"]
        self.metal_cycle_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update metallic finish effects"""
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update reflection phase
        self.reflection_phase += self.reflection_speed * 0.05 * (1 + treble)

        # Update metal cycling
        if self.metal_cycle:
            self.metal_cycle_phase += 0.02 * energy

        # Apply metallic effects
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for i, pyramid in enumerate(layer.pyramids):
                    # Update reflection
                    pyramid.reflection_phase = self.reflection_phase + i * 0.5
                    pyramid.metallic_intensity = 0.5 + 0.5 * treble

                    # Cycle metal types if enabled
                    if self.metal_cycle and random.random() < 0.01:
                        pyramid.metal_type = random.choice(self.metal_types)

    def __str__(self) -> str:
        cycle_status = "cycling" if self.metal_cycle else "fixed"
        return f"✨PyramidMetallic({cycle_status}, {len(self.pyramid_layers)} layers)"


class PyramidSwarm(VJInterpreterBase):
    """Creates swarming behavior for pyramids"""

    hype = 85

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        swarm_speed: float = 1.0,
        swarm_tightness: float = 0.3,
    ):
        super().__init__(layers, args)
        self.swarm_speed = swarm_speed
        self.swarm_tightness = swarm_tightness
        self.swarm_center_x = 0.5
        self.swarm_center_y = 0.5
        self.swarm_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update pyramid swarming behavior"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update swarm center (moves with music)
        self.swarm_phase += self.swarm_speed * 0.03 * (1 + energy)
        self.swarm_center_x = 0.5 + 0.2 * math.sin(self.swarm_phase) * treble
        self.swarm_center_y = 0.5 + 0.2 * math.cos(self.swarm_phase * 1.3) * bass

        # Apply swarming to pyramids
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for pyramid in layer.pyramids:
                    # Calculate attraction to swarm center
                    dx = self.swarm_center_x - pyramid.x
                    dy = self.swarm_center_y - pyramid.y

                    # Apply swarm force
                    force_strength = self.swarm_tightness * energy * 0.01
                    pyramid.x += dx * force_strength
                    pyramid.y += dy * force_strength

                    # Add some randomness
                    pyramid.x += random.uniform(-0.005, 0.005) * treble
                    pyramid.y += random.uniform(-0.005, 0.005) * bass

                    # Keep in bounds
                    pyramid.x = max(0.05, min(0.95, pyramid.x))
                    pyramid.y = max(0.05, min(0.95, pyramid.y))

    def __str__(self) -> str:
        return f"🐝PyramidSwarm({self.swarm_tightness:.1f}, center={self.swarm_center_x:.2f},{self.swarm_center_y:.2f})"


class PyramidPortal(VJInterpreterBase):
    """Creates portal/tunnel effects with pyramids"""

    hype = 90

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        portal_speed: float = 2.0,
        portal_intensity: float = 1.5,
    ):
        super().__init__(layers, args)
        self.portal_speed = portal_speed
        self.portal_intensity = portal_intensity
        self.portal_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create portal effect with pyramids"""
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Update portal phase
        self.portal_phase += self.portal_speed * 0.05 * (1 + bass * 2)

        # Apply portal effects
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for i, pyramid in enumerate(layer.pyramids):
                    # Calculate distance from center
                    dx = pyramid.x - 0.5
                    dy = pyramid.y - 0.5
                    distance = math.sqrt(dx * dx + dy * dy)

                    # Portal pull effect
                    portal_pull = self.portal_intensity * bass * 0.01
                    pyramid.x += -dx * portal_pull
                    pyramid.y += -dy * portal_pull

                    # Z movement for tunnel effect
                    z_wave = math.sin(self.portal_phase + distance * 10) * 0.2 * energy
                    pyramid.z = pyramid.base_z + z_wave

                    # Size variation for depth
                    depth_scale = 0.5 + 0.5 * (1 - distance)
                    pyramid.scale = pyramid.base_size * depth_scale * (1 + bass * 0.5)

    def __str__(self) -> str:
        return f"🌀PyramidPortal({self.portal_intensity:.1f}x, {len(self.pyramid_layers)} layers)"


class PyramidStorm(VJInterpreterBase):
    """Creates chaotic pyramid storm effects"""

    hype = 95

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        storm_threshold: float = 0.8,
        chaos_intensity: float = 2.0,
    ):
        super().__init__(layers, args)
        self.storm_threshold = storm_threshold
        self.chaos_intensity = chaos_intensity
        self.storm_active = False
        self.storm_frames = 0
        self.last_energy = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create pyramid storm on high energy"""
        energy = frame[FrameSignal.freq_all]
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]

        # Trigger storm on energy spike
        if energy > self.storm_threshold and self.last_energy <= self.storm_threshold:
            self.storm_active = True
            self.storm_frames = 180  # 3 seconds at 60fps
            print(f"🌪️ PYRAMID STORM ACTIVATED!")

        self.last_energy = energy

        # Update storm
        if self.storm_active:
            self.storm_frames -= 1
            if self.storm_frames <= 0:
                self.storm_active = False
                print(f"🌪️ Pyramid storm ended")

            # Chaotic pyramid effects during storm
            for layer in self.pyramid_layers:
                if hasattr(layer, "pyramids"):
                    for pyramid in layer.pyramids:
                        # Chaotic movement
                        pyramid.x += random.uniform(-0.02, 0.02) * self.chaos_intensity
                        pyramid.y += random.uniform(-0.02, 0.02) * self.chaos_intensity
                        pyramid.z += random.uniform(-0.1, 0.1) * bass

                        # Chaotic rotation
                        pyramid.rotation_speed = (
                            random.uniform(1.0, 5.0) * self.chaos_intensity
                        )

                        # Chaotic scaling
                        chaos_scale = random.uniform(0.5, 2.0) * (1 + treble)
                        pyramid.scale = pyramid.base_size * chaos_scale

                        # Random metal changes
                        if random.random() < 0.1:
                            metals = ["gold", "silver", "rainbow", "chrome"]
                            pyramid.metal_type = random.choice(metals)

                        # Keep in bounds
                        pyramid.x = max(0.05, min(0.95, pyramid.x))
                        pyramid.y = max(0.05, min(0.95, pyramid.y))
                        pyramid.z = max(0.1, min(1.0, pyramid.z))
        else:
            # Normal operation - gentle movement
            for layer in self.pyramid_layers:
                if hasattr(layer, "pyramids"):
                    for pyramid in layer.pyramids:
                        # Gentle return to original positions
                        pyramid.rotation_speed *= 0.98  # Slow down
                        pyramid.scale = pyramid.base_size * (0.9 + 0.2 * energy)

    def __str__(self) -> str:
        if self.storm_active:
            return f"🌪️PyramidStorm(ACTIVE, {self.storm_frames} frames left)"
        else:
            return f"🌪️PyramidStorm(waiting for energy > {self.storm_threshold})"


class PyramidRave(VJInterpreterBase):
    """Ultimate rave pyramid effects - combines all behaviors"""

    hype = 100

    def __init__(self, layers: List[LayerBase], args: InterpreterArgs):
        super().__init__(layers, args)

        # Create sub-interpreters
        self.pulse_interp = PyramidPulse(layers, args, pulse_intensity=3.0)
        self.float_interp = PyramidFloat(layers, args, float_speed=2.0)
        self.spin_interp = PyramidSpin(layers, args, spin_multiplier=2.5)
        self.metallic_interp = PyramidMetallic(layers, args, metal_cycle=True)
        self.storm_interp = PyramidStorm(layers, args, chaos_intensity=3.0)

        self.mode_phase = 0.0
        self.current_mode = 0
        self.modes = ["pulse", "float", "spin", "storm"]

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Ultimate rave pyramid experience"""
        energy = frame[FrameSignal.freq_all]
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]

        # Update mode phase
        self.mode_phase += 0.02 * (1 + energy)

        # Switch modes based on audio
        if bass > 0.8 and treble > 0.7:
            # High energy - storm mode
            self.current_mode = 3
        elif bass > 0.6:
            # Bass heavy - pulse mode
            self.current_mode = 0
        elif treble > 0.6:
            # Treble heavy - spin mode
            self.current_mode = 2
        elif energy > 0.5:
            # Medium energy - float mode
            self.current_mode = 1

        # Apply current mode
        mode = self.modes[self.current_mode]

        if mode == "pulse":
            self.pulse_interp.step(frame, scheme)
        elif mode == "float":
            self.float_interp.step(frame, scheme)
        elif mode == "spin":
            self.spin_interp.step(frame, scheme)
        elif mode == "storm":
            self.storm_interp.step(frame, scheme)

        # Always apply metallic effects
        self.metallic_interp.step(frame, scheme)

        # Boost pyramid layer alpha during high energy
        pyramid_alpha = 0.6 + 0.4 * energy
        for layer in self.pyramid_layers:
            layer.set_alpha(pyramid_alpha)

    def __str__(self) -> str:
        mode = self.modes[self.current_mode]
        return f"🔺PyramidRave({mode} mode, {len(self.pyramid_layers)} layers)"


class PyramidBass(VJInterpreterBase):
    """Pyramids that respond specifically to bass drops"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        bass_threshold: float = 0.7,
        bass_boost: float = 3.0,
    ):
        super().__init__(layers, args)
        self.bass_threshold = bass_threshold
        self.bass_boost = bass_boost
        self.bass_active = False
        self.bass_frames = 0
        self.last_bass = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """React to bass drops with pyramid effects"""
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Detect bass drop
        if bass > self.bass_threshold and self.last_bass <= self.bass_threshold:
            self.bass_active = True
            self.bass_frames = 30  # Half second of bass effect

        self.last_bass = bass

        # Apply bass effects
        if self.bass_active:
            self.bass_frames -= 1
            if self.bass_frames <= 0:
                self.bass_active = False

            # Dramatic bass effects
            for layer in self.pyramid_layers:
                if hasattr(layer, "pyramids"):
                    for pyramid in layer.pyramids:
                        # Massive scale boost
                        pyramid.scale = pyramid.base_size * (1 + bass * self.bass_boost)

                        # Intense metallic reflection
                        pyramid.metallic_intensity = min(2.0, 1.0 + bass * 1.5)

                        # Rapid rotation
                        pyramid.rotation_speed = 3.0 + bass * 5.0

                # Boost layer alpha
                layer.set_alpha(0.9 + 0.1 * bass)
        else:
            # Normal operation
            for layer in self.pyramid_layers:
                layer.set_alpha(0.6 + 0.4 * energy)

    def __str__(self) -> str:
        if self.bass_active:
            return f"🔊PyramidBass(DROP! {self.bass_frames} frames left)"
        else:
            return f"🔊PyramidBass(waiting for bass > {self.bass_threshold})"


class PyramidHypnotic(VJInterpreterBase):
    """Hypnotic pyramid patterns for trance sections"""

    hype = 70

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, hypno_speed: float = 1.0
    ):
        super().__init__(layers, args)
        self.hypno_speed = hypno_speed
        self.hypno_phase = 0.0

        # Filter for pyramid layers
        self.pyramid_layers = [
            layer
            for layer in layers
            if hasattr(layer, "pyramids") or "pyramid" in layer.name.lower()
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create hypnotic pyramid patterns"""
        energy = frame[FrameSignal.freq_all]
        bass = frame[FrameSignal.freq_low]

        # Update hypnotic phase
        self.hypno_phase += self.hypno_speed * 0.03 * (0.8 + energy * 0.4)

        # Apply hypnotic effects
        for layer in self.pyramid_layers:
            if hasattr(layer, "pyramids"):
                for i, pyramid in enumerate(layer.pyramids):
                    # Synchronized rotation for hypnotic effect
                    pyramid.rotation_y = self.hypno_phase + i * 0.2
                    pyramid.rotation_x = self.hypno_phase * 0.7 + i * 0.1

                    # Synchronized scaling pulse
                    scale_wave = math.sin(self.hypno_phase * 2 + i * 0.5) * 0.3 * bass
                    pyramid.scale = pyramid.base_size * (1.0 + scale_wave)

                    # Hypnotic Z movement
                    z_wave = math.sin(self.hypno_phase * 1.5 + i * 0.3) * 0.2
                    pyramid.z = pyramid.base_z + z_wave

                    # Consistent metallic finish
                    pyramid.metallic_intensity = 0.8 + 0.2 * energy
                    pyramid.reflection_phase = self.hypno_phase + i * 0.1

    def __str__(self) -> str:
        return f"😵‍💫PyramidHypnotic({self.hypno_phase:.1f}, {len(self.pyramid_layers)} layers)"
