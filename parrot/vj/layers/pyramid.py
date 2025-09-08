"""
Ravey pyramid layers with metallic finishes that float and pulse to music
Perfect for Dead Sexy Halloween rave visuals
"""

import math
import random
import time
from typing import Optional, List, Tuple
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


class Pyramid:
    """A single 3D pyramid with position, rotation, and metallic finish"""

    def __init__(
        self,
        x: float,
        y: float,
        z: float,
        size: float,
        metal_type: str = "gold",
        rotation_speed: float = 1.0,
    ):
        # Position
        self.x = x
        self.y = y
        self.z = z
        self.base_z = z  # Original Z position

        # Size and scale
        self.size = size
        self.base_size = size
        self.scale = 1.0

        # Rotation
        self.rotation_x = random.uniform(0, math.pi * 2)
        self.rotation_y = random.uniform(0, math.pi * 2)
        self.rotation_z = random.uniform(0, math.pi * 2)
        self.rotation_speed = rotation_speed

        # Metallic finish
        self.metal_type = metal_type
        self.metallic_intensity = 1.0
        self.reflection_phase = random.uniform(0, math.pi * 2)

        # Pulsing
        self.pulse_phase = random.uniform(0, math.pi * 2)
        self.pulse_intensity = 0.0

        # Floating
        self.float_phase = random.uniform(0, math.pi * 2)
        self.float_amplitude = random.uniform(0.1, 0.3)

        # Audio responsiveness
        self.bass_sensitivity = random.uniform(0.5, 1.5)
        self.treble_sensitivity = random.uniform(0.5, 1.5)

    def get_metallic_color(
        self, base_color: Tuple[float, float, float]
    ) -> Tuple[int, int, int]:
        """Get metallic finish color based on type and lighting"""
        r, g, b = base_color

        # Metallic color bases
        metal_colors = {
            "gold": (1.0, 0.8, 0.2),
            "silver": (0.9, 0.9, 0.95),
            "copper": (0.8, 0.5, 0.2),
            "chrome": (0.95, 0.95, 1.0),
            "bronze": (0.7, 0.4, 0.1),
            "platinum": (0.85, 0.85, 0.9),
            "titanium": (0.6, 0.6, 0.7),
            "rainbow": (
                abs(math.sin(time.time())),
                abs(math.cos(time.time())),
                abs(math.sin(time.time() * 1.5)),
            ),
        }

        metal_r, metal_g, metal_b = metal_colors.get(self.metal_type, (0.8, 0.8, 0.8))

        # Apply metallic reflection
        reflection = 0.5 + 0.5 * math.sin(self.reflection_phase + time.time() * 2)
        reflection *= self.metallic_intensity

        # Combine base color with metallic finish
        final_r = min(1.0, (r * 0.3 + metal_r * 0.7) * (0.5 + reflection * 0.5))
        final_g = min(1.0, (g * 0.3 + metal_g * 0.7) * (0.5 + reflection * 0.5))
        final_b = min(1.0, (b * 0.3 + metal_b * 0.7) * (0.5 + reflection * 0.5))

        return (int(final_r * 255), int(final_g * 255), int(final_b * 255))

    def update(self, frame: Frame, dt: float):
        """Update pyramid animation based on audio"""
        # Audio signals
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update rotation
        self.rotation_x += (
            self.rotation_speed * dt * (0.5 + treble * self.treble_sensitivity)
        )
        self.rotation_y += self.rotation_speed * dt * 0.7 * (0.5 + energy)
        self.rotation_z += self.rotation_speed * dt * 0.3

        # Update floating
        self.float_phase += dt * 2.0 * (0.8 + energy * 0.4)
        self.z = self.base_z + math.sin(self.float_phase) * self.float_amplitude

        # Update pulsing
        self.pulse_phase += dt * 4.0 * (1 + bass * 2)
        self.pulse_intensity = bass * self.bass_sensitivity
        self.scale = self.base_size * (
            1.0 + math.sin(self.pulse_phase) * 0.3 * self.pulse_intensity
        )

        # Update metallic reflection
        self.reflection_phase += dt * 3.0 * (0.5 + energy)
        self.metallic_intensity = 0.7 + 0.3 * energy

    def get_2d_points(self, width: int, height: int) -> List[Tuple[int, int]]:
        """Get 2D projected points for rendering"""
        # Simple 3D to 2D projection
        # Pyramid vertices (base + apex)
        vertices_3d = [
            # Base square
            (-0.5, -0.5, 0),
            (0.5, -0.5, 0),
            (0.5, 0.5, 0),
            (-0.5, 0.5, 0),
            # Apex
            (0, 0, 1),
        ]

        # Apply rotation
        rotated = []
        for vx, vy, vz in vertices_3d:
            # Rotate around X axis
            y1 = vy * math.cos(self.rotation_x) - vz * math.sin(self.rotation_x)
            z1 = vy * math.sin(self.rotation_x) + vz * math.cos(self.rotation_x)

            # Rotate around Y axis
            x2 = vx * math.cos(self.rotation_y) + z1 * math.sin(self.rotation_y)
            z2 = -vx * math.sin(self.rotation_y) + z1 * math.cos(self.rotation_y)

            # Rotate around Z axis
            x3 = x2 * math.cos(self.rotation_z) - y1 * math.sin(self.rotation_z)
            y3 = x2 * math.sin(self.rotation_z) + y1 * math.cos(self.rotation_z)

            rotated.append((x3, y3, z2))

        # Project to 2D
        points_2d = []
        for vx, vy, vz in rotated:
            # Scale by pyramid size
            vx *= self.scale
            vy *= self.scale
            vz *= self.scale

            # Simple perspective projection
            perspective = 1.0 / (1.0 + self.z + vz * 0.5)

            # Convert to screen coordinates
            screen_x = int(self.x * width + vx * perspective * 100)
            screen_y = int(self.y * height + vy * perspective * 100)

            points_2d.append((screen_x, screen_y))

        return points_2d


class PyramidLayer(LayerBase):
    """Layer that renders floating, pulsing metallic pyramids"""

    def __init__(
        self,
        name: str = "pyramids",
        pyramid_count: int = 8,
        metal_types: List[str] = None,
        z_order: int = 4,
    ):
        super().__init__(name, z_order)

        self.pyramid_count = pyramid_count
        self.metal_types = metal_types or ["gold", "silver", "copper", "chrome"]
        self.pyramids: List[Pyramid] = []
        self.last_time = time.time()

        # Create pyramids
        self._create_pyramids()

    def _create_pyramids(self):
        """Create the pyramid collection"""
        self.pyramids = []

        for i in range(self.pyramid_count):
            # Random position
            x = random.uniform(0.1, 0.9)
            y = random.uniform(0.1, 0.9)
            z = random.uniform(0.2, 0.8)

            # Random size
            size = random.uniform(0.8, 2.0)

            # Random metal type
            metal_type = random.choice(self.metal_types)

            # Random rotation speed
            rotation_speed = random.uniform(0.5, 2.0)

            pyramid = Pyramid(x, y, z, size, metal_type, rotation_speed)
            self.pyramids.append(pyramid)

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render floating metallic pyramids"""
        if not self.enabled:
            return None

        # Create transparent background
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Calculate delta time
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Audio signals
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update and render each pyramid
        for pyramid in self.pyramids:
            pyramid.update(frame, dt)
            self._render_pyramid(texture, pyramid, scheme, energy)

        return texture

    def _render_pyramid(
        self, texture: np.ndarray, pyramid: Pyramid, scheme: ColorScheme, energy: float
    ):
        """Render a single pyramid to the texture"""
        # Get 2D projected points
        points = pyramid.get_2d_points(self.width, self.height)

        if len(points) != 5:
            return

        # Base color from scheme
        base_color = (
            scheme.fg.red / 255.0,
            scheme.fg.green / 255.0,
            scheme.fg.blue / 255.0,
        )

        # Get metallic color
        metallic_color = pyramid.get_metallic_color(base_color)

        # Draw pyramid faces
        self._draw_pyramid_faces(texture, points, metallic_color, pyramid, energy)

    def _draw_pyramid_faces(
        self,
        texture: np.ndarray,
        points: List[Tuple[int, int]],
        color: Tuple[int, int, int],
        pyramid: Pyramid,
        energy: float,
    ):
        """Draw pyramid faces with metallic shading"""
        if len(points) < 5:
            return

        base_points = points[:4]  # Base square
        apex_point = points[4]  # Apex

        # Calculate face brightness based on "lighting"
        light_dir = (0.5, 0.3, 1.0)  # Simulated light direction

        # Draw each triangular face (base to apex)
        faces = [
            (base_points[0], base_points[1], apex_point),  # Front
            (base_points[1], base_points[2], apex_point),  # Right
            (base_points[2], base_points[3], apex_point),  # Back
            (base_points[3], base_points[0], apex_point),  # Left
        ]

        for i, face in enumerate(faces):
            # Calculate face lighting
            face_brightness = 0.4 + 0.6 * (i / len(faces))  # Vary by face
            face_brightness *= 0.5 + 0.5 * energy  # Audio reactive

            # Apply metallic reflection
            reflection = 0.3 + 0.7 * math.sin(pyramid.reflection_phase + i)

            # Final face color
            r = int(color[0] * face_brightness * (0.7 + reflection * 0.3))
            g = int(color[1] * face_brightness * (0.7 + reflection * 0.3))
            b = int(color[2] * face_brightness * (0.7 + reflection * 0.3))

            # Alpha based on distance and energy
            alpha = int(255 * (0.6 + 0.4 * energy) * (0.8 + 0.2 * pyramid.z))

            face_color = (r, g, b, alpha)

            # Draw triangle face
            self._draw_triangle(texture, face[0], face[1], face[2], face_color)

        # Draw base (if visible)
        if pyramid.z > 0.3:  # Only if pyramid is "above" viewer
            base_brightness = 0.2 + 0.3 * energy
            base_color = (
                int(color[0] * base_brightness),
                int(color[1] * base_brightness),
                int(color[2] * base_brightness),
                int(128 * (0.5 + 0.5 * energy)),
            )
            self._draw_quad(texture, base_points, base_color)

    def _draw_triangle(
        self,
        texture: np.ndarray,
        p1: Tuple[int, int],
        p2: Tuple[int, int],
        p3: Tuple[int, int],
        color: Tuple[int, int, int, int],
    ):
        """Draw a filled triangle with the given color"""
        # Simple triangle rasterization
        points = [p1, p2, p3]

        # Find bounding box
        min_x = max(0, min(p[0] for p in points))
        max_x = min(self.width - 1, max(p[0] for p in points))
        min_y = max(0, min(p[1] for p in points))
        max_y = min(self.height - 1, max(p[1] for p in points))

        # Fill triangle using barycentric coordinates
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if self._point_in_triangle(x, y, p1, p2, p3):
                    # Blend with existing pixel
                    self._blend_pixel(texture, x, y, color)

    def _draw_quad(
        self,
        texture: np.ndarray,
        points: List[Tuple[int, int]],
        color: Tuple[int, int, int, int],
    ):
        """Draw a filled quadrilateral"""
        if len(points) != 4:
            return

        # Draw as two triangles
        self._draw_triangle(texture, points[0], points[1], points[2], color)
        self._draw_triangle(texture, points[0], points[2], points[3], color)

    def _point_in_triangle(
        self,
        px: int,
        py: int,
        p1: Tuple[int, int],
        p2: Tuple[int, int],
        p3: Tuple[int, int],
    ) -> bool:
        """Check if point is inside triangle using barycentric coordinates"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3

        # Calculate barycentric coordinates
        denom = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(denom) < 1e-10:
            return False

        a = ((y2 - y3) * (px - x3) + (x3 - x2) * (py - y3)) / denom
        b = ((y3 - y1) * (px - x3) + (x1 - x3) * (py - y3)) / denom
        c = 1 - a - b

        return 0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1

    def _blend_pixel(
        self, texture: np.ndarray, x: int, y: int, color: Tuple[int, int, int, int]
    ):
        """Blend a pixel with alpha compositing"""
        if 0 <= x < self.width and 0 <= y < self.height:
            r, g, b, a = color
            alpha = a / 255.0

            # Alpha blending
            current = texture[y, x]
            texture[y, x] = [
                int(current[0] * (1 - alpha) + r * alpha),
                int(current[1] * (1 - alpha) + g * alpha),
                int(current[2] * (1 - alpha) + b * alpha),
                min(255, int(current[3] + a * 0.5)),  # Additive alpha
            ]

    def cleanup(self):
        """Clean up pyramid resources"""
        pass  # No special cleanup needed for pyramids


class GoldenPyramidsLayer(PyramidLayer):
    """Golden metallic pyramids for luxury rave feel"""

    def __init__(self, name: str = "golden_pyramids", pyramid_count: int = 6):
        super().__init__(name, pyramid_count, ["gold", "bronze", "copper"], z_order=5)

        # Override some pyramids for golden theme
        for pyramid in self.pyramids:
            pyramid.metal_type = random.choice(["gold", "bronze", "copper"])
            pyramid.rotation_speed *= random.uniform(0.8, 1.2)


class SilverPyramidsLayer(PyramidLayer):
    """Silver/chrome metallic pyramids for futuristic feel"""

    def __init__(self, name: str = "silver_pyramids", pyramid_count: int = 5):
        super().__init__(
            name, pyramid_count, ["silver", "chrome", "platinum"], z_order=6
        )

        # Override for silver theme
        for pyramid in self.pyramids:
            pyramid.metal_type = random.choice(["silver", "chrome", "platinum"])
            pyramid.rotation_speed *= random.uniform(1.2, 1.8)  # Faster rotation


class RainbowPyramidsLayer(PyramidLayer):
    """Rainbow metallic pyramids for psychedelic rave"""

    def __init__(self, name: str = "rainbow_pyramids", pyramid_count: int = 10):
        super().__init__(name, pyramid_count, ["rainbow", "gold", "silver"], z_order=7)

        # Override for rainbow theme
        for i, pyramid in enumerate(self.pyramids):
            if i % 3 == 0:
                pyramid.metal_type = "rainbow"
            else:
                pyramid.metal_type = random.choice(["gold", "silver"])
            pyramid.rotation_speed *= random.uniform(1.5, 2.5)  # Very fast


class MegaPyramidLayer(PyramidLayer):
    """Single massive pyramid that dominates the screen"""

    def __init__(self, name: str = "mega_pyramid", metal_type: str = "gold"):
        super().__init__(name, 1, [metal_type], z_order=8)

        # Create one massive pyramid
        self.pyramids = [
            Pyramid(
                x=0.5,  # Center
                y=0.5,  # Center
                z=0.5,
                size=4.0,  # Much larger
                metal_type=metal_type,
                rotation_speed=0.8,  # Slower, more majestic
            )
        ]

        # Make it extra responsive
        self.pyramids[0].bass_sensitivity = 2.0
        self.pyramids[0].treble_sensitivity = 1.5
        self.pyramids[0].float_amplitude = 0.1  # Less floating, more stable


class PyramidSwarmLayer(PyramidLayer):
    """Swarm of small fast pyramids for high-energy sections"""

    def __init__(self, name: str = "pyramid_swarm", metal_type: str = "silver"):
        super().__init__(name, 20, [metal_type], z_order=3)

        # Create swarm of small fast pyramids
        for pyramid in self.pyramids:
            pyramid.size = random.uniform(0.3, 0.8)  # Smaller
            pyramid.base_size = pyramid.size
            pyramid.rotation_speed = random.uniform(2.0, 4.0)  # Much faster
            pyramid.bass_sensitivity = random.uniform(1.0, 3.0)  # Very responsive
            pyramid.float_amplitude = random.uniform(0.2, 0.5)  # More floating
            pyramid.metal_type = metal_type


class PyramidFormationLayer(PyramidLayer):
    """Pyramids arranged in geometric formations"""

    def __init__(self, name: str = "pyramid_formation", formation: str = "circle"):
        super().__init__(name, 0, ["gold", "silver"], z_order=5)  # Will be overridden

        self.formation = formation
        self.formation_phase = 0.0
        self.formation_speed = 1.0

        # Create formation
        self._create_formation()

    def _create_formation(self):
        """Create pyramids in geometric formation"""
        self.pyramids = []

        if self.formation == "circle":
            count = 8
            for i in range(count):
                angle = (i / count) * math.pi * 2
                radius = 0.3

                x = 0.5 + radius * math.cos(angle)
                y = 0.5 + radius * math.sin(angle)
                z = 0.5

                metal_type = "gold" if i % 2 == 0 else "silver"
                pyramid = Pyramid(x, y, z, 1.2, metal_type, 1.0)
                self.pyramids.append(pyramid)

        elif self.formation == "grid":
            for i in range(3):
                for j in range(3):
                    x = 0.2 + (i / 2) * 0.6
                    y = 0.2 + (j / 2) * 0.6
                    z = 0.4 + (i + j) * 0.1

                    metal_type = ["gold", "silver", "copper"][(i + j) % 3]
                    pyramid = Pyramid(x, y, z, 1.0, metal_type, 0.8)
                    self.pyramids.append(pyramid)

        elif self.formation == "spiral":
            count = 12
            for i in range(count):
                t = i / count
                angle = t * math.pi * 4  # Two full rotations
                radius = 0.1 + t * 0.3

                x = 0.5 + radius * math.cos(angle)
                y = 0.5 + radius * math.sin(angle)
                z = 0.3 + t * 0.4

                metal_type = ["rainbow", "gold", "silver"][i % 3]
                pyramid = Pyramid(x, y, z, 0.8 + t * 0.4, metal_type, 1.5)
                self.pyramids.append(pyramid)

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render formation with additional movement"""
        if not self.enabled:
            return None

        # Update formation rotation
        energy = frame[FrameSignal.freq_all]
        self.formation_phase += self.formation_speed * 0.02 * (1 + energy)

        # Rotate entire formation
        center_x, center_y = 0.5, 0.5
        for pyramid in self.pyramids:
            # Rotate around center
            dx = pyramid.x - center_x
            dy = pyramid.y - center_y

            new_x = (
                center_x
                + dx * math.cos(self.formation_phase)
                - dy * math.sin(self.formation_phase)
            )
            new_y = (
                center_y
                + dx * math.sin(self.formation_phase)
                + dy * math.cos(self.formation_phase)
            )

            pyramid.x = new_x
            pyramid.y = new_y

        # Render normally
        return super().render(frame, scheme)


class PyramidPortalLayer(PyramidLayer):
    """Pyramids that create a portal/tunnel effect"""

    def __init__(self, name: str = "pyramid_portal"):
        super().__init__(name, 15, ["chrome", "silver", "platinum"], z_order=9)

        # Create pyramids in tunnel formation
        self.pyramids = []
        for i in range(15):
            # Create tunnel effect
            z_depth = i / 14  # 0 to 1
            radius = 0.1 + z_depth * 0.4

            # Multiple pyramids at each depth
            for j in range(max(1, int(6 * (1 - z_depth)))):
                angle = (j / max(1, int(6 * (1 - z_depth)))) * math.pi * 2

                x = 0.5 + radius * math.cos(angle)
                y = 0.5 + radius * math.sin(angle)
                z = z_depth

                size = 0.5 + z_depth * 1.5
                pyramid = Pyramid(x, y, z, size, "chrome", 2.0)
                pyramid.bass_sensitivity = 3.0  # Very responsive
                self.pyramids.append(pyramid)


# Mock pyramid layer for when rendering is too intensive
class MockPyramidLayer(LayerBase):
    """Mock pyramid layer with simple geometric patterns"""

    def __init__(self, name: str = "mock_pyramids", pyramid_count: int = 5):
        super().__init__(name, z_order=4)
        self.pyramid_count = pyramid_count
        self.frame_count = 0
        self.pulse_phase = 0.0

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render simple pyramid-like shapes"""
        if not self.enabled:
            return None

        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Audio signals
        bass = frame[FrameSignal.freq_low]
        energy = frame[FrameSignal.freq_all]

        # Update animation
        self.frame_count += 1
        self.pulse_phase += 0.1 * (1 + energy)

        # Draw simple pyramid shapes
        for i in range(self.pyramid_count):
            # Position
            x = int(self.width * (0.2 + (i / self.pyramid_count) * 0.6))
            y = int(self.height * (0.3 + 0.4 * math.sin(self.pulse_phase + i)))

            # Size based on audio
            base_size = int(30 + 20 * bass + 10 * math.sin(self.pulse_phase + i * 2))

            # Color from scheme
            color_intensity = int(255 * (0.5 + 0.5 * energy))
            r = int(scheme.fg.red * color_intensity / 255)
            g = int(scheme.fg.green * color_intensity / 255)
            b = int(scheme.fg.blue * color_intensity / 255)

            # Draw simple triangle (pyramid top view)
            self._draw_simple_triangle(texture, x, y, base_size, (r, g, b, 200))

    def _draw_simple_triangle(
        self,
        texture: np.ndarray,
        cx: int,
        cy: int,
        size: int,
        color: Tuple[int, int, int, int],
    ):
        """Draw a simple triangle centered at (cx, cy)"""
        # Triangle points
        height = int(size * 0.866)  # Equilateral triangle height

        points = [
            (cx, cy - height // 2),  # Top
            (cx - size // 2, cy + height // 2),  # Bottom left
            (cx + size // 2, cy + height // 2),  # Bottom right
        ]

        # Simple triangle fill
        for y in range(
            max(0, cy - height // 2), min(self.height, cy + height // 2 + 1)
        ):
            for x in range(max(0, cx - size // 2), min(self.width, cx + size // 2 + 1)):
                if self._point_in_simple_triangle(x, y, points):
                    # Simple alpha blend
                    if 0 <= x < self.width and 0 <= y < self.height:
                        alpha = color[3] / 255.0
                        current = texture[y, x]
                        texture[y, x] = [
                            int(current[0] * (1 - alpha) + color[0] * alpha),
                            int(current[1] * (1 - alpha) + color[1] * alpha),
                            int(current[2] * (1 - alpha) + color[2] * alpha),
                            min(255, int(current[3] + color[3] * 0.5)),
                        ]

    def _point_in_simple_triangle(
        self, px: int, py: int, points: List[Tuple[int, int]]
    ) -> bool:
        """Simple point-in-triangle test"""
        if len(points) != 3:
            return False

        x1, y1 = points[0]
        x2, y2 = points[1]
        x3, y3 = points[2]

        # Use cross product method
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

        d1 = sign((px, py), points[0], points[1])
        d2 = sign((px, py), points[1], points[2])
        d3 = sign((px, py), points[2], points[0])

        has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
        has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)

        return not (has_neg and has_pos)

    def cleanup(self):
        """Clean up mock pyramid resources"""
        pass  # No special cleanup needed
