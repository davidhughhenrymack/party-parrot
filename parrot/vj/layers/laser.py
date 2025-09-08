"""
Laser rendering layer for concert-style laser effects
"""

import math
from typing import Optional, List, Tuple, Dict, Any
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


class LaserLayer(LayerBase):
    """Renders concert-style laser beams and effects"""

    def __init__(
        self,
        name: str = "lasers",
        z_order: int = 12,
        width: int = 1920,
        height: int = 1080,
        beam_glow: bool = True,
        beam_intensity: float = 0.8,
    ):
        super().__init__(name, z_order, width, height)
        self.beam_glow = beam_glow
        self.beam_intensity = beam_intensity

        # Laser data from interpreters
        self._laser_beams: List[dict] = []
        self._scan_beams: List[dict] = []
        self._laser_matrix: Optional[dict] = None
        self._laser_chasers: List[dict] = []
        self._burst_lasers: List[dict] = []
        self._laser_spirals: List[dict] = []
        self._laser_tunnel: Optional[dict] = None

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render all laser effects"""
        if not self.enabled:
            return None

        # Create laser texture
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Render different laser effects
        self._render_fan_lasers(texture)
        self._render_scan_beams(texture)
        self._render_laser_matrix(texture)
        self._render_chasers(texture)
        self._render_burst_lasers(texture)
        self._render_spirals(texture)
        self._render_tunnel(texture)

        # Return texture if any lasers were drawn
        return texture if np.any(texture) else None

    def _render_fan_lasers(self, texture: np.ndarray):
        """Render fanned-out laser beams"""
        if not hasattr(self, "_laser_beams") or not self._laser_beams:
            return

        for laser in self._laser_beams:
            if not laser.get("enabled", True):
                continue

            # Calculate beam endpoints
            start_x = 0.5  # Center bottom
            start_y = 0.9

            angle = laser["current_angle"] + math.pi / 2  # +90° for upward
            end_x = start_x + laser["length"] * math.cos(angle)
            end_y = start_y - laser["length"] * math.sin(angle)

            # Convert to pixel coordinates
            px1 = int(start_x * self.width)
            py1 = int(start_y * self.height)
            px2 = int(end_x * self.width)
            py2 = int(end_y * self.height)

            # Clamp to screen bounds
            px2 = max(0, min(self.width - 1, px2))
            py2 = max(0, min(self.height - 1, py2))

            # Draw laser beam
            self._draw_laser_beam(
                texture,
                px1,
                py1,
                px2,
                py2,
                laser["color"],
                laser["intensity"],
                laser["width"],
            )

    def _render_scan_beams(self, texture: np.ndarray):
        """Render scanning laser beams"""
        if not hasattr(self, "_scan_beams") or not self._scan_beams:
            return

        for beam in self._scan_beams:
            # Calculate beam from center to edge based on angle
            center_x = 0.5
            center_y = 0.5

            angle = beam["current_angle"]
            end_x = center_x + beam["length"] * math.cos(angle)
            end_y = center_y + beam["length"] * math.sin(angle)

            # Convert to pixels
            px1 = int(center_x * self.width)
            py1 = int(center_y * self.height)
            px2 = int(end_x * self.width)
            py2 = int(end_y * self.height)

            # Clamp
            px2 = max(0, min(self.width - 1, px2))
            py2 = max(0, min(self.height - 1, py2))

            self._draw_laser_beam(
                texture,
                px1,
                py1,
                px2,
                py2,
                beam["color"],
                beam["intensity"],
                beam["width"],
            )

    def _render_laser_matrix(self, texture: np.ndarray):
        """Render laser matrix grid"""
        if not hasattr(self, "_laser_matrix") or not self._laser_matrix:
            return

        grid = self._laser_matrix["grid"]
        grid_width, grid_height = self._laser_matrix["grid_size"]

        for y, row in enumerate(grid):
            for x, laser in enumerate(row):
                if not laser.get("enabled", True):
                    continue

                # Draw laser point/dot
                px = int(laser["x"] * self.width)
                py = int(laser["y"] * self.height)

                self._draw_laser_dot(
                    texture, px, py, laser["color"], laser["intensity"], size=4
                )

    def _render_chasers(self, texture: np.ndarray):
        """Render chasing laser effects"""
        if not hasattr(self, "_laser_chasers") or not self._laser_chasers:
            return

        for chaser in self._laser_chasers:
            # Convert position to screen coordinates (circular path)
            angle = chaser["position"] * math.pi * 2
            radius = 0.3

            x = 0.5 + radius * math.cos(angle)
            y = 0.5 + radius * math.sin(angle)

            px = int(x * self.width)
            py = int(y * self.height)

            # Draw main chaser
            self._draw_laser_dot(
                texture, px, py, chaser["color"], chaser["intensity"], size=6
            )

            # Draw trail
            for j, trail_point in enumerate(chaser["trail"]):
                trail_angle = trail_point["position"] * math.pi * 2
                trail_x = 0.5 + radius * math.cos(trail_angle)
                trail_y = 0.5 + radius * math.sin(trail_angle)

                trail_px = int(trail_x * self.width)
                trail_py = int(trail_y * self.height)

                trail_size = max(1, 6 - j * 2)  # Smaller toward tail
                self._draw_laser_dot(
                    texture,
                    trail_px,
                    trail_py,
                    chaser["color"],
                    trail_point["intensity"],
                    size=trail_size,
                )

    def _render_burst_lasers(self, texture: np.ndarray):
        """Render explosive laser burst"""
        if not hasattr(self, "_burst_lasers") or not self._burst_lasers:
            return

        center_x = 0.5
        center_y = 0.5

        for laser in self._burst_lasers:
            # Calculate beam endpoint
            end_x = center_x + laser["length"] * math.cos(laser["angle"])
            end_y = center_y + laser["length"] * math.sin(laser["angle"])

            # Convert to pixels
            px1 = int(center_x * self.width)
            py1 = int(center_y * self.height)
            px2 = int(end_x * self.width)
            py2 = int(end_y * self.height)

            # Clamp
            px2 = max(0, min(self.width - 1, px2))
            py2 = max(0, min(self.height - 1, py2))

            self._draw_laser_beam(
                texture,
                px1,
                py1,
                px2,
                py2,
                laser["color"],
                laser["intensity"],
                laser["width"],
            )

    def _render_spirals(self, texture: np.ndarray):
        """Render spiral laser effects"""
        if not hasattr(self, "_laser_spirals") or not self._laser_spirals:
            return

        for spiral in self._laser_spirals:
            for point in spiral["points"]:
                px = int(point["x"] * self.width)
                py = int(point["y"] * self.height)

                if 0 <= px < self.width and 0 <= py < self.height:
                    self._draw_laser_dot(
                        texture, px, py, spiral["color"], point["intensity"], size=3
                    )

    def _render_tunnel(self, texture: np.ndarray):
        """Render laser tunnel effect"""
        if not hasattr(self, "_laser_tunnel") or not self._laser_tunnel:
            return

        center_x = int(0.5 * self.width)
        center_y = int(0.5 * self.height)

        for ring in self._laser_tunnel["rings"]:
            # Draw ring as circle of laser dots
            ring_radius = int(ring["size"] * min(self.width, self.height) / 2)

            if ring_radius > 0:
                num_dots = max(8, ring_radius // 2)  # More dots for larger rings

                for dot_i in range(num_dots):
                    angle = ring["rotation"] + (dot_i / num_dots) * math.pi * 2

                    dot_x = center_x + ring_radius * math.cos(angle)
                    dot_y = center_y + ring_radius * math.sin(angle)

                    if 0 <= dot_x < self.width and 0 <= dot_y < self.height:
                        self._draw_laser_dot(
                            texture,
                            int(dot_x),
                            int(dot_y),
                            ring["color"],
                            ring["intensity"],
                            size=2,
                        )

    def _draw_laser_beam(
        self,
        texture: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: Tuple[float, float, float],
        intensity: float,
        width: int,
    ):
        """Draw a laser beam line"""
        if intensity <= 0:
            return

        # Convert color to 0-255 range
        r = int(color[0] * 255 * intensity)
        g = int(color[1] * 255 * intensity)
        b = int(color[2] * 255 * intensity)
        a = int(255 * intensity * self.beam_intensity)

        beam_color = [r, g, b, a]

        # Draw line using Bresenham's algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx == 0 and dy == 0:
            return

        x, y = x1, y1
        x_inc = 1 if x1 < x2 else -1
        y_inc = 1 if y1 < y2 else -1

        error = dx - dy

        while True:
            # Draw thick beam
            self._draw_thick_pixel(texture, x, y, beam_color, width)

            if x == x2 and y == y2:
                break

            e2 = 2 * error
            if e2 > -dy:
                error -= dy
                x += x_inc
            if e2 < dx:
                error += dx
                y += y_inc

    def _draw_thick_pixel(
        self, texture: np.ndarray, x: int, y: int, color: List[int], thickness: int
    ):
        """Draw a thick pixel for beam width"""
        half_thick = thickness // 2

        for dx in range(-half_thick, half_thick + 1):
            for dy in range(-half_thick, half_thick + 1):
                px = x + dx
                py = y + dy

                if 0 <= px < self.width and 0 <= py < self.height:
                    # Apply glow effect if enabled
                    if self.beam_glow:
                        distance = math.sqrt(dx * dx + dy * dy)
                        if distance <= thickness:
                            # Falloff for glow
                            glow_factor = 1.0 - (distance / thickness)
                            glow_color = [int(c * glow_factor) for c in color]

                            # Additive blending for glow effect with overflow protection
                            current = texture[py, px].astype(np.int32)
                            glow_color_int = [int(c) for c in glow_color]
                            for i in range(4):  # RGBA
                                texture[py, px, i] = min(
                                    255, max(0, current[i] + glow_color_int[i])
                                )
                    else:
                        texture[py, px] = color

    def _draw_laser_dot(
        self,
        texture: np.ndarray,
        x: int,
        y: int,
        color: Tuple[float, float, float],
        intensity: float,
        size: int,
    ):
        """Draw a laser dot/point"""
        if intensity <= 0:
            return

        # Convert color
        r = int(color[0] * 255 * intensity)
        g = int(color[1] * 255 * intensity)
        b = int(color[2] * 255 * intensity)
        a = int(255 * intensity * self.beam_intensity)

        dot_color = [r, g, b, a]

        # Draw circular dot with glow
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                px = x + dx
                py = y + dy

                if 0 <= px < self.width and 0 <= py < self.height:
                    distance = math.sqrt(dx * dx + dy * dy)

                    if distance <= size:
                        # Radial falloff
                        falloff = 1.0 - (distance / size) if size > 0 else 1.0
                        falloff_color = [int(c * falloff) for c in dot_color]

                        # Additive blending with overflow protection
                        current = texture[py, px].astype(np.int32)
                        falloff_color_int = [int(c) for c in falloff_color]
                        for i in range(4):
                            texture[py, px, i] = min(
                                255, max(0, current[i] + falloff_color_int[i])
                            )

    def set_beam_glow(self, glow: bool):
        """Enable or disable beam glow effect"""
        self.beam_glow = glow

    def set_beam_intensity(self, intensity: float):
        """Set overall beam intensity multiplier"""
        self.beam_intensity = max(0.0, min(1.0, intensity))

    def get_laser_stats(self) -> dict:
        """Get statistics about current laser effects"""
        stats = {
            "fan_beams": len(getattr(self, "_laser_beams", [])),
            "scan_beams": len(getattr(self, "_scan_beams", [])),
            "matrix_points": 0,
            "chasers": len(getattr(self, "_laser_chasers", [])),
            "burst_beams": len(getattr(self, "_burst_lasers", [])),
            "spirals": len(getattr(self, "_laser_spirals", [])),
            "tunnel_rings": 0,
        }

        # Count matrix points
        if hasattr(self, "_laser_matrix") and self._laser_matrix:
            grid = self._laser_matrix["grid"]
            stats["matrix_points"] = sum(
                1 for row in grid for laser in row if laser.get("enabled", True)
            )

        # Count tunnel rings
        if hasattr(self, "_laser_tunnel") and self._laser_tunnel:
            stats["tunnel_rings"] = len(self._laser_tunnel["rings"])

        return stats

    def __str__(self) -> str:
        stats = self.get_laser_stats()
        total_effects = sum(stats.values())
        return f"LaserLayer({total_effects} effects)"


class LaserHaze(LayerBase):
    """Atmospheric haze layer that makes lasers more visible"""

    def __init__(
        self,
        name: str = "laser_haze",
        z_order: int = 11,
        width: int = 1920,
        height: int = 1080,
        haze_density: float = 0.3,
    ):
        super().__init__(name, z_order, width, height)
        self.haze_density = haze_density
        self.haze_movement_phase = 0.0

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render atmospheric haze for laser visibility"""
        if not self.enabled:
            return None

        # Get audio for haze movement
        bass = frame[FrameSignal.freq_low]
        sustained = frame[FrameSignal.sustained_low]

        # Update haze movement
        self.haze_movement_phase += 0.01 * (1 + bass)

        # Create haze texture
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Base haze intensity from sustained energy
        base_haze = self.haze_density * (0.3 + 0.7 * sustained)

        # Create moving haze pattern
        for y in range(0, self.height, 4):  # Sample every 4 pixels for performance
            for x in range(0, self.width, 4):
                # Create subtle moving pattern
                wave1 = math.sin(x * 0.01 + self.haze_movement_phase)
                wave2 = math.sin(y * 0.01 + self.haze_movement_phase * 0.7)
                wave_factor = (wave1 + wave2) / 2.0

                # Haze intensity
                haze_intensity = base_haze * (0.7 + 0.3 * wave_factor)

                if haze_intensity > 0.05:
                    # Subtle gray haze
                    haze_alpha = int(haze_intensity * 60)  # Low alpha for subtlety
                    haze_color = [40, 40, 50, haze_alpha]  # Slightly blue-tinted

                    # Fill 4x4 block for performance
                    for dy in range(min(4, self.height - y)):
                        for dx in range(min(4, self.width - x)):
                            if y + dy < self.height and x + dx < self.width:
                                texture[y + dy, x + dx] = haze_color

        return texture if base_haze > 0.05 else None

    def set_haze_density(self, density: float):
        """Set haze density"""
        self.haze_density = max(0.0, min(1.0, density))

    def __str__(self) -> str:
        return f"🌫️LaserHaze({self.haze_density:.1f})"


class LaserBeamRenderer(LayerBase):
    """Specialized layer for rendering high-quality laser beams"""

    def __init__(
        self,
        name: str = "laser_beams",
        z_order: int = 13,
        width: int = 1920,
        height: int = 1080,
        anti_alias: bool = True,
        bloom_effect: bool = True,
    ):
        super().__init__(name, z_order, width, height)
        self.anti_alias = anti_alias
        self.bloom_effect = bloom_effect

        # Laser data storage
        self.beam_data: List[dict] = []

    def add_beam(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: Tuple[float, float, float],
        intensity: float,
        width: int = 2,
    ):
        """Add a laser beam to render"""
        self.beam_data.append(
            {
                "start": start,
                "end": end,
                "color": color,
                "intensity": intensity,
                "width": width,
            }
        )

    def clear_beams(self):
        """Clear all laser beams"""
        self.beam_data.clear()

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render high-quality laser beams"""
        if not self.enabled or not self.beam_data:
            return None

        # Create beam texture
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Render each beam
        for beam in self.beam_data:
            self._render_high_quality_beam(texture, beam)

        # Apply bloom effect if enabled
        if self.bloom_effect:
            texture = self._apply_bloom(texture)

        # Clear beams for next frame
        self.clear_beams()

        return texture if np.any(texture) else None

    def _render_high_quality_beam(self, texture: np.ndarray, beam: dict):
        """Render a single high-quality laser beam"""
        start_x, start_y = beam["start"]
        end_x, end_y = beam["end"]
        color = beam["color"]
        intensity = beam["intensity"]
        width = beam["width"]

        # Convert to pixel coordinates
        px1 = int(start_x * self.width)
        py1 = int(start_y * self.height)
        px2 = int(end_x * self.width)
        py2 = int(end_y * self.height)

        # Calculate beam vector
        dx = px2 - px1
        dy = py2 - py1
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Normalized perpendicular vector for beam width
        perp_x = -dy / length
        perp_y = dx / length

        # Draw beam with anti-aliasing if enabled
        if self.anti_alias:
            self._draw_antialiased_beam(
                texture, px1, py1, px2, py2, color, intensity, width, perp_x, perp_y
            )
        else:
            self._draw_simple_beam(texture, px1, py1, px2, py2, color, intensity, width)

    def _draw_antialiased_beam(
        self,
        texture: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: Tuple[float, float, float],
        intensity: float,
        width: int,
        perp_x: float,
        perp_y: float,
    ):
        """Draw anti-aliased laser beam"""
        # Convert color
        r = int(color[0] * 255 * intensity)
        g = int(color[1] * 255 * intensity)
        b = int(color[2] * 255 * intensity)

        # Draw beam with gradual falloff
        for t in range(int(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2))):
            # Interpolate along beam
            if t == 0:
                continue

            progress = t / math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            beam_x = int(x1 + progress * (x2 - x1))
            beam_y = int(y1 + progress * (y2 - y1))

            # Draw perpendicular line for beam width
            for w in range(-width, width + 1):
                px = int(beam_x + w * perp_x)
                py = int(beam_y + w * perp_y)

                if 0 <= px < self.width and 0 <= py < self.height:
                    # Distance-based falloff for smooth edges
                    distance_factor = 1.0 - abs(w) / width if width > 0 else 1.0

                    pixel_alpha = int(255 * intensity * distance_factor)
                    pixel_color = [r, g, b, pixel_alpha]

                    # Additive blending with overflow protection
                    current = texture[py, px].astype(np.int32)
                    pixel_color_int = [int(c) for c in pixel_color]
                    for i in range(4):
                        texture[py, px, i] = min(
                            255, max(0, current[i] + pixel_color_int[i])
                        )

    def _draw_simple_beam(
        self,
        texture: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: Tuple[float, float, float],
        intensity: float,
        width: int,
    ):
        """Draw simple laser beam without anti-aliasing"""
        # This is a simplified version - just draw a thick line
        r = int(color[0] * 255 * intensity)
        g = int(color[1] * 255 * intensity)
        b = int(color[2] * 255 * intensity)
        a = int(255 * intensity)

        beam_color = [r, g, b, a]

        # Simple line drawing
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steps = max(dx, dy)

        if steps == 0:
            return

        x_step = (x2 - x1) / steps
        y_step = (y2 - y1) / steps

        for i in range(steps):
            x = int(x1 + i * x_step)
            y = int(y1 + i * y_step)

            # Draw thick point
            for dx in range(-width // 2, width // 2 + 1):
                for dy in range(-width // 2, width // 2 + 1):
                    px = x + dx
                    py = y + dy

                    if 0 <= px < self.width and 0 <= py < self.height:
                        texture[py, px] = beam_color

    def _apply_bloom(self, texture: np.ndarray) -> np.ndarray:
        """Apply bloom effect to make lasers glow"""
        # Simple bloom: blur bright areas and add back to original
        # This is a simplified version - a full implementation would use proper Gaussian blur

        bloomed = texture.copy()

        # Find bright pixels
        brightness = texture[:, :, 0] + texture[:, :, 1] + texture[:, :, 2]
        bright_mask = brightness > 400  # Threshold for bloom

        if np.any(bright_mask):
            # Simple box blur for bloom effect
            kernel_size = 5
            half_kernel = kernel_size // 2

            for y in range(half_kernel, self.height - half_kernel):
                for x in range(half_kernel, self.width - half_kernel):
                    if bright_mask[y, x]:
                        # Apply bloom around bright pixel
                        bloom_color = texture[y, x] * 0.3  # Reduced intensity for bloom

                        for dy in range(-half_kernel, half_kernel + 1):
                            for dx in range(-half_kernel, half_kernel + 1):
                                px = x + dx
                                py = y + dy

                                if 0 <= px < self.width and 0 <= py < self.height:
                                    # Add bloom with overflow protection
                                    current = bloomed[py, px].astype(np.int32)
                                    bloom_int = [int(c) for c in bloom_color]
                                    for i in range(4):
                                        bloomed[py, px, i] = min(
                                            255, max(0, current[i] + bloom_int[i])
                                        )

        return bloomed

    def __str__(self) -> str:
        return f"LaserBeamRenderer({len(self.beam_data)} beams)"
