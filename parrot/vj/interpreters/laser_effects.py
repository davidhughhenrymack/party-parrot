"""
Laser effect interpreters for concert-style laser shows
"""

import math
import random
from typing import List, Tuple, Optional
import numpy as np
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class ConcertLasers(VJInterpreterBase):
    """Concert-style laser beams that fan out and respond to audio"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_lasers: int = 8,
        fan_angle: float = 120.0,  # Degrees
        laser_length: float = 0.8,
        beam_width: int = 3,
        origin_point: Tuple[float, float] = (0.5, 0.9),
    ):  # Bottom center
        super().__init__(layers, args)
        self.num_lasers = num_lasers
        self.fan_angle = math.radians(fan_angle)  # Convert to radians
        self.laser_length = laser_length
        self.beam_width = beam_width
        self.origin_x, self.origin_y = origin_point

        # Laser state
        self.lasers = []
        self.rotation_phase = 0.0
        self.intensity_phase = 0.0
        self.color_cycle_phase = 0.0

        # Initialize lasers
        self._initialize_lasers()

        # Filter for layers that can render lasers
        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def _initialize_lasers(self):
        """Initialize laser beam configurations"""
        self.lasers = []

        for i in range(self.num_lasers):
            # Calculate base angle for even distribution
            if self.num_lasers == 1:
                base_angle = 0.0  # Straight up
            else:
                angle_step = self.fan_angle / (self.num_lasers - 1)
                base_angle = -self.fan_angle / 2 + i * angle_step

            self.lasers.append(
                {
                    "id": i,
                    "base_angle": base_angle,
                    "current_angle": base_angle,
                    "intensity": 0.0,
                    "color": (1.0, 0.0, 0.0),  # Start with red
                    "length": self.laser_length,
                    "width": self.beam_width,
                    "movement_phase": random.random() * math.pi * 2,
                    "movement_speed": random.uniform(0.02, 0.05),
                    "flicker_phase": random.random() * math.pi * 2,
                    "enabled": True,
                }
            )

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update laser effects based on audio"""
        # Get audio signals
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]
        sustained = frame[FrameSignal.sustained_low]

        # Update global phases
        self.rotation_phase += 0.01 * (1 + energy)
        self.intensity_phase += 0.05 * (1 + sustained)
        self.color_cycle_phase += 0.02

        # Get colors from scheme
        scheme_colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        # Update each laser
        for i, laser in enumerate(self.lasers):
            # Movement - each laser moves independently
            laser["movement_phase"] += laser["movement_speed"] * (1 + energy * 2)

            # Calculate movement offset
            movement_range = 0.3 * energy  # More movement with higher energy
            movement_offset = movement_range * math.sin(laser["movement_phase"])

            # Update angle with movement
            laser["current_angle"] = laser["base_angle"] + movement_offset

            # Intensity - flicker and respond to audio
            laser["flicker_phase"] += 0.1 + treble * 0.5

            # Base intensity from sustained energy
            base_intensity = 0.2 + 0.8 * sustained

            # Add flicker
            flicker = 0.1 * math.sin(laser["flicker_phase"])

            # Add beat response
            beat_boost = 0.0
            if i % 2 == 0:  # Even lasers respond to bass
                beat_boost = 0.3 * bass
            else:  # Odd lasers respond to treble
                beat_boost = 0.3 * treble

            laser["intensity"] = max(
                0.0, min(1.0, base_intensity + flicker + beat_boost)
            )

            # Color cycling through scheme
            color_index = (i + int(self.color_cycle_phase)) % len(scheme_colors)
            laser["color"] = scheme_colors[color_index]

            # Length varies with energy
            laser["length"] = self.laser_length * (0.6 + 0.4 * energy)

            # Enable/disable based on energy (some lasers turn off at low energy)
            if i < self.num_lasers // 2:  # First half always enabled
                laser["enabled"] = True
            else:  # Second half only enabled at higher energy
                laser["enabled"] = energy > 0.3

        # Apply laser effects to compatible layers
        self._apply_laser_effects()

    def _apply_laser_effects(self):
        """Apply laser effects to layers"""
        # Store laser data on layers for rendering
        for layer in self.laser_layers:
            if hasattr(layer, "_laser_beams"):
                layer._laser_beams = self.get_laser_info()

            # For layers that support direct effects
            if hasattr(layer, "set_alpha"):
                # Overall alpha based on average laser intensity
                avg_intensity = sum(
                    laser["intensity"] for laser in self.lasers if laser["enabled"]
                ) / max(1, len(self.lasers))
                layer.set_alpha(0.3 + 0.7 * avg_intensity)

    def get_laser_info(self) -> List[dict]:
        """Get current laser beam information for rendering"""
        return [laser.copy() for laser in self.lasers if laser["enabled"]]

    def calculate_laser_endpoints(
        self,
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """Calculate start and end points for all laser beams"""
        endpoints = []

        for laser in self.lasers:
            if not laser["enabled"]:
                continue

            # Start point (origin)
            start_x = self.origin_x
            start_y = self.origin_y

            # End point based on angle and length
            angle = (
                laser["current_angle"] + math.pi / 2
            )  # +90° since 0° is right, we want up

            end_x = start_x + laser["length"] * math.cos(angle)
            end_y = start_y - laser["length"] * math.sin(
                angle
            )  # Negative because screen Y is inverted

            # Clamp to screen bounds
            end_x = max(0.0, min(1.0, end_x))
            end_y = max(0.0, min(1.0, end_y))

            endpoints.append(((start_x, start_y), (end_x, end_y)))

        return endpoints

    def __str__(self) -> str:
        active_lasers = sum(1 for laser in self.lasers if laser["enabled"])
        return f"🔴ConcertLasers({active_lasers}/{self.num_lasers} active)"


class LaserScan(VJInterpreterBase):
    """Scanning laser effect that sweeps across the screen"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_beams: int = 4,
        scan_speed: float = 0.05,
        scan_range: float = 160.0,
    ):  # Degrees
        super().__init__(layers, args)
        self.num_beams = num_beams
        self.scan_speed = scan_speed
        self.scan_range = math.radians(scan_range)
        self.scan_phase = 0.0
        self.scan_direction = 1

        # Beam configurations
        self.beams = []
        for i in range(num_beams):
            self.beams.append(
                {
                    "id": i,
                    "offset": i * (self.scan_range / num_beams),
                    "intensity": 0.0,
                    "color": (1.0, 0.0, 0.0),
                    "length": 0.9,
                    "width": 2,
                }
            )

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update scanning laser effect"""
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update scan phase
        effective_speed = self.scan_speed * (0.5 + 1.5 * energy)
        self.scan_phase += effective_speed * self.scan_direction

        # Reverse direction at limits
        if self.scan_phase > self.scan_range / 2:
            self.scan_direction = -1
        elif self.scan_phase < -self.scan_range / 2:
            self.scan_direction = 1

        # Update beams
        for i, beam in enumerate(self.beams):
            # Position based on scan phase + offset
            beam_angle = self.scan_phase + beam["offset"]
            beam["current_angle"] = beam_angle

            # Intensity based on treble and position
            base_intensity = 0.3 + 0.7 * treble

            # Beams at center of scan are brighter
            center_distance = abs(beam_angle) / (self.scan_range / 2)
            position_factor = 1.0 - center_distance * 0.5

            beam["intensity"] = base_intensity * position_factor

            # Color from scheme
            color_index = i % 3
            if color_index == 0:
                beam["color"] = scheme.fg.rgb
            elif color_index == 1:
                beam["color"] = scheme.bg.rgb
            else:
                beam["color"] = scheme.bg_contrast.rgb

        # Apply to layers
        self._apply_scan_effects()

    def _apply_scan_effects(self):
        """Apply scanning effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_scan_beams"):
                layer._scan_beams = self.beams.copy()

            # Average intensity for layer alpha
            if hasattr(layer, "set_alpha"):
                avg_intensity = sum(beam["intensity"] for beam in self.beams) / len(
                    self.beams
                )
                layer.set_alpha(0.4 + 0.6 * avg_intensity)

    def get_beam_info(self) -> List[dict]:
        """Get current beam information"""
        return self.beams.copy()

    def __str__(self) -> str:
        direction = "→" if self.scan_direction > 0 else "←"
        return f"🔍LaserScan({direction} {self.scan_phase:.1f})"


class LaserMatrix(VJInterpreterBase):
    """Matrix of laser beams creating grid patterns"""

    hype = 85

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        grid_size: Tuple[int, int] = (6, 4),  # horizontal x vertical
        pulse_speed: float = 0.08,
    ):
        super().__init__(layers, args)
        self.grid_width, self.grid_height = grid_size
        self.pulse_speed = pulse_speed
        self.pulse_phase = 0.0

        # Create laser grid
        self.laser_grid = []
        for y in range(self.grid_height):
            row = []
            for x in range(self.grid_width):
                row.append(
                    {
                        "x": x / (self.grid_width - 1) if self.grid_width > 1 else 0.5,
                        "y": (
                            y / (self.grid_height - 1) if self.grid_height > 1 else 0.5
                        ),
                        "intensity": 0.0,
                        "color": (1.0, 0.0, 0.0),
                        "phase_offset": random.random() * math.pi * 2,
                        "enabled": True,
                    }
                )
            self.laser_grid.append(row)

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update laser matrix effect"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update pulse phase
        self.pulse_phase += self.pulse_speed * (1 + energy)

        # Get scheme colors
        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        # Update each laser in the grid
        for y, row in enumerate(self.laser_grid):
            for x, laser in enumerate(row):
                # Wave patterns across the grid
                wave_phase = self.pulse_phase + laser["phase_offset"]

                # Different wave patterns
                if (x + y) % 2 == 0:
                    # Diagonal wave
                    wave_factor = math.sin(wave_phase + (x + y) * 0.5)
                else:
                    # Circular wave from center
                    center_x = self.grid_width / 2
                    center_y = self.grid_height / 2
                    distance = math.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
                    wave_factor = math.sin(wave_phase + distance * 0.8)

                # Intensity based on wave and audio
                base_intensity = 0.2 + 0.6 * energy
                wave_intensity = 0.2 * (wave_factor + 1.0) / 2.0  # 0-0.2 range

                # Different corners respond to different frequencies
                if x < self.grid_width / 2 and y < self.grid_height / 2:
                    audio_boost = 0.4 * bass  # Top-left: bass
                elif x >= self.grid_width / 2 and y < self.grid_height / 2:
                    audio_boost = 0.4 * treble  # Top-right: treble
                elif x < self.grid_width / 2:
                    audio_boost = 0.4 * bass  # Bottom-left: bass
                else:
                    audio_boost = 0.4 * treble  # Bottom-right: treble

                laser["intensity"] = min(
                    1.0, base_intensity + wave_intensity + audio_boost
                )

                # Color cycling
                color_index = (x + y + int(self.pulse_phase)) % len(colors)
                laser["color"] = colors[color_index]

                # Enable/disable based on intensity threshold
                laser["enabled"] = laser["intensity"] > 0.3

        # Apply to layers
        self._apply_matrix_effects()

    def _apply_matrix_effects(self):
        """Apply matrix effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_laser_matrix"):
                layer._laser_matrix = {
                    "grid": [row.copy() for row in self.laser_grid],
                    "grid_size": (self.grid_width, self.grid_height),
                }

            # Overall layer intensity
            if hasattr(layer, "set_alpha"):
                total_intensity = sum(
                    laser["intensity"]
                    for row in self.laser_grid
                    for laser in row
                    if laser["enabled"]
                )
                avg_intensity = total_intensity / (self.grid_width * self.grid_height)
                layer.set_alpha(0.4 + 0.6 * avg_intensity)

    def get_matrix_info(self) -> dict:
        """Get laser matrix information"""
        return {
            "grid": [row.copy() for row in self.laser_grid],
            "grid_size": (self.grid_width, self.grid_height),
            "pulse_phase": self.pulse_phase,
        }

    def __str__(self) -> str:
        active_count = sum(
            1 for row in self.laser_grid for laser in row if laser["enabled"]
        )
        total_count = self.grid_width * self.grid_height
        return f"🔳LaserMatrix({active_count}/{total_count} active)"


class LaserChase(VJInterpreterBase):
    """Chasing laser effects that follow the beat"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_chasers: int = 6,
        chase_speed: float = 0.1,
        trail_length: int = 3,
    ):
        super().__init__(layers, args)
        self.num_chasers = num_chasers
        self.chase_speed = chase_speed
        self.trail_length = trail_length
        self.chase_phase = 0.0
        self.beat_trigger = False
        self.last_beat_signal = 0.0

        # Create chasers
        self.chasers = []
        for i in range(num_chasers):
            self.chasers.append(
                {
                    "id": i,
                    "position": i / num_chasers,  # 0-1 position around circle
                    "intensity": 0.0,
                    "color": (1.0, 0.0, 0.0),
                    "trail": [],  # Previous positions for trail effect
                    "speed_modifier": random.uniform(0.8, 1.2),
                }
            )

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update chasing laser effect"""
        beat_signal = frame[FrameSignal.freq_high]
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Detect beats for chase triggers
        if beat_signal > 0.7 and self.last_beat_signal <= 0.7:
            self.beat_trigger = True
        self.last_beat_signal = beat_signal

        # Update chase phase
        if self.beat_trigger:
            # Fast chase on beat
            self.chase_phase += self.chase_speed * 5
            self.beat_trigger = False
        else:
            # Normal chase speed
            self.chase_phase += self.chase_speed * (0.5 + 1.5 * energy)

        # Get scheme colors
        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        # Update chasers
        for i, chaser in enumerate(self.chasers):
            # Update position
            old_position = chaser["position"]
            chaser["position"] = (
                self.chase_phase * chaser["speed_modifier"] + i / self.num_chasers
            ) % 1.0

            # Add to trail
            chaser["trail"].append(
                {"position": old_position, "intensity": chaser["intensity"] * 0.8}
            )

            # Limit trail length
            if len(chaser["trail"]) > self.trail_length:
                chaser["trail"].pop(0)

            # Intensity based on audio
            base_intensity = 0.4 + 0.6 * energy

            # Add bass boost for some chasers
            if i % 2 == 0:
                base_intensity += 0.3 * bass

            chaser["intensity"] = min(1.0, base_intensity)

            # Color from scheme
            chaser["color"] = colors[i % len(colors)]

        # Apply to layers
        self._apply_chase_effects()

    def _apply_chase_effects(self):
        """Apply chase effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_laser_chasers"):
                layer._laser_chasers = [chaser.copy() for chaser in self.chasers]

            # Layer alpha from average intensity
            if hasattr(layer, "set_alpha"):
                avg_intensity = sum(
                    chaser["intensity"] for chaser in self.chasers
                ) / len(self.chasers)
                layer.set_alpha(0.5 + 0.5 * avg_intensity)

    def get_chase_info(self) -> List[dict]:
        """Get chaser information"""
        return [chaser.copy() for chaser in self.chasers]

    def __str__(self) -> str:
        return f"🏃LaserChase({self.num_chasers} chasers, {self.chase_phase:.1f})"


class LaserBurst(VJInterpreterBase):
    """Explosive laser burst effects on high energy"""

    hype = 90

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        burst_threshold: float = 0.8,
        max_burst_lasers: int = 16,
        burst_duration: int = 20,
    ):
        super().__init__(layers, args)
        self.burst_threshold = burst_threshold
        self.max_burst_lasers = max_burst_lasers
        self.burst_duration = burst_duration

        # Burst state
        self.is_bursting = False
        self.burst_frames_remaining = 0
        self.burst_lasers = []
        self.last_energy = 0.0

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update laser burst effect"""
        energy = (
            frame[FrameSignal.freq_low]
            + frame[FrameSignal.freq_high]
            + frame[FrameSignal.freq_all]
        ) / 3.0

        # Trigger burst on energy spike
        if energy > self.burst_threshold and self.last_energy <= self.burst_threshold:
            self._trigger_burst(energy, scheme)

        # Update burst
        if self.is_bursting:
            self._update_burst(frame, scheme)

        self.last_energy = energy

        # Apply to layers
        self._apply_burst_effects()

    def _trigger_burst(self, energy: float, scheme: ColorScheme):
        """Trigger a laser burst"""
        self.is_bursting = True
        self.burst_frames_remaining = self.burst_duration

        # Create burst lasers
        num_burst_lasers = int(self.max_burst_lasers * energy)
        self.burst_lasers = []

        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        for i in range(num_burst_lasers):
            angle = (i / num_burst_lasers) * math.pi * 2  # Full circle

            self.burst_lasers.append(
                {
                    "angle": angle,
                    "length": random.uniform(0.3, 0.8),
                    "intensity": random.uniform(0.7, 1.0),
                    "color": random.choice(colors),
                    "width": random.randint(1, 4),
                    "decay_rate": random.uniform(0.02, 0.05),
                }
            )

    def _update_burst(self, frame: Frame, scheme: ColorScheme):
        """Update ongoing burst effect"""
        self.burst_frames_remaining -= 1

        if self.burst_frames_remaining <= 0:
            self.is_bursting = False
            self.burst_lasers = []
            return

        # Update burst lasers
        for laser in self.burst_lasers:
            # Decay intensity
            laser["intensity"] *= 1.0 - laser["decay_rate"]

            # Expand length slightly
            laser["length"] = min(1.0, laser["length"] + 0.01)

        # Remove very dim lasers
        self.burst_lasers = [
            laser for laser in self.burst_lasers if laser["intensity"] > 0.1
        ]

    def _apply_burst_effects(self):
        """Apply burst effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_burst_lasers"):
                layer._burst_lasers = self.burst_lasers.copy()

            # Intense alpha during burst
            if hasattr(layer, "set_alpha"):
                if self.is_bursting:
                    burst_intensity = self.burst_frames_remaining / self.burst_duration
                    layer.set_alpha(0.8 + 0.2 * burst_intensity)
                else:
                    layer.set_alpha(0.3)

    def get_burst_info(self) -> dict:
        """Get burst information"""
        return {
            "is_bursting": self.is_bursting,
            "frames_remaining": self.burst_frames_remaining,
            "lasers": self.burst_lasers.copy(),
        }

    def __str__(self) -> str:
        if self.is_bursting:
            return f"💥LaserBurst(BURSTING! {len(self.burst_lasers)} beams)"
        else:
            return f"💥LaserBurst(ready)"


class LaserTunnel(VJInterpreterBase):
    """Tunnel effect with lasers creating depth illusion"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_rings: int = 8,
        tunnel_speed: float = 0.03,
        ring_spacing: float = 0.1,
    ):
        super().__init__(layers, args)
        self.num_rings = num_rings
        self.tunnel_speed = tunnel_speed
        self.ring_spacing = ring_spacing
        self.tunnel_phase = 0.0

        # Create tunnel rings
        self.rings = []
        for i in range(num_rings):
            ring_size = 0.1 + i * 0.08  # Rings get larger toward back
            self.rings.append(
                {
                    "size": ring_size,
                    "position": i * ring_spacing,
                    "intensity": 0.0,
                    "color": (1.0, 0.0, 0.0),
                    "rotation": random.random() * math.pi * 2,
                }
            )

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update laser tunnel effect"""
        sustained = frame[FrameSignal.sustained_low]
        energy = frame[FrameSignal.freq_all]

        # Update tunnel movement
        self.tunnel_phase += self.tunnel_speed * (0.5 + 1.5 * sustained)

        # Update rings
        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        for i, ring in enumerate(self.rings):
            # Move ring forward
            ring["position"] -= self.tunnel_speed * (1 + energy)

            # Reset ring when it reaches the front
            if ring["position"] < 0:
                ring["position"] = (self.num_rings - 1) * self.ring_spacing
                ring["rotation"] = random.random() * math.pi * 2

            # Intensity based on position (closer = brighter)
            distance_factor = 1.0 - (
                ring["position"] / (self.num_rings * self.ring_spacing)
            )
            ring["intensity"] = (0.3 + 0.7 * distance_factor) * (0.5 + 0.5 * energy)

            # Color based on position
            color_index = i % len(colors)
            ring["color"] = colors[color_index]

            # Rotate ring
            ring["rotation"] += 0.02 * (1 + energy)

        # Apply to layers
        self._apply_tunnel_effects()

    def _apply_tunnel_effects(self):
        """Apply tunnel effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_laser_tunnel"):
                layer._laser_tunnel = {
                    "rings": self.rings.copy(),
                    "phase": self.tunnel_phase,
                }

            # Layer alpha from tunnel depth
            if hasattr(layer, "set_alpha"):
                # Closer rings contribute more to alpha
                weighted_intensity = (
                    sum(
                        ring["intensity"]
                        * (
                            1.0
                            - ring["position"] / (self.num_rings * self.ring_spacing)
                        )
                        for ring in self.rings
                    )
                    / self.num_rings
                )
                layer.set_alpha(0.4 + 0.6 * weighted_intensity)

    def get_tunnel_info(self) -> dict:
        """Get tunnel information"""
        return {
            "rings": self.rings.copy(),
            "phase": self.tunnel_phase,
            "num_rings": self.num_rings,
        }

    def __str__(self) -> str:
        return f"🌀LaserTunnel({self.tunnel_phase:.1f})"


class LaserSpiral(VJInterpreterBase):
    """Spiral laser effects"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_spirals: int = 3,
        spiral_speed: float = 0.04,
        spiral_tightness: float = 2.0,
    ):
        super().__init__(layers, args)
        self.num_spirals = num_spirals
        self.spiral_speed = spiral_speed
        self.spiral_tightness = spiral_tightness
        self.spiral_phase = 0.0

        # Create spirals
        self.spirals = []
        for i in range(num_spirals):
            self.spirals.append(
                {
                    "id": i,
                    "phase_offset": i * (math.pi * 2 / num_spirals),
                    "direction": 1 if i % 2 == 0 else -1,  # Alternating directions
                    "intensity": 0.0,
                    "color": (1.0, 0.0, 0.0),
                    "points": [],  # Points along the spiral
                }
            )

        self.laser_layers = [layer for layer in layers if hasattr(layer, "render")]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update spiral laser effect"""
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update spiral phase
        self.spiral_phase += self.spiral_speed * (1 + treble)

        # Get colors
        colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        # Update spirals
        for i, spiral in enumerate(self.spirals):
            effective_phase = (
                self.spiral_phase * spiral["direction"] + spiral["phase_offset"]
            )

            # Generate spiral points
            spiral["points"] = []
            num_points = 20  # Points along spiral

            for point_i in range(num_points):
                t = point_i / num_points  # 0-1 parameter

                # Spiral equation
                angle = effective_phase + t * self.spiral_tightness * math.pi * 2
                radius = t * 0.4  # Spiral outward

                x = 0.5 + radius * math.cos(angle)
                y = 0.5 + radius * math.sin(angle)

                # Intensity decreases toward outside
                point_intensity = (1.0 - t) * (0.5 + 0.5 * energy)

                spiral["points"].append({"x": x, "y": y, "intensity": point_intensity})

            # Overall spiral properties
            spiral["intensity"] = 0.4 + 0.6 * energy
            spiral["color"] = colors[i % len(colors)]

        # Apply to layers
        self._apply_spiral_effects()

    def _apply_spiral_effects(self):
        """Apply spiral effects to layers"""
        for layer in self.laser_layers:
            if hasattr(layer, "_laser_spirals"):
                layer._laser_spirals = [spiral.copy() for spiral in self.spirals]

            # Layer alpha from spiral intensity
            if hasattr(layer, "set_alpha"):
                avg_intensity = sum(
                    spiral["intensity"] for spiral in self.spirals
                ) / len(self.spirals)
                layer.set_alpha(0.3 + 0.7 * avg_intensity)

    def get_spiral_info(self) -> List[dict]:
        """Get spiral information"""
        return [spiral.copy() for spiral in self.spirals]

    def __str__(self) -> str:
        return f"🌀LaserSpiral({self.num_spirals} spirals, {self.spiral_phase:.1f})"
