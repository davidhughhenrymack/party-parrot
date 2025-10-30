#!/usr/bin/env python3

from abc import abstractmethod
from beartype import beartype
from typing import Optional, Any
import numpy as np
import math

from parrot.fixtures.base import FixtureBase
from parrot.director.frame import Frame


def quaternion_identity() -> np.ndarray:
    """Return identity quaternion (no rotation)"""
    return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)


def quaternion_from_axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    """Create quaternion from axis-angle representation"""
    axis = axis / np.linalg.norm(axis)
    half_angle = angle / 2.0
    return np.array(
        [
            axis[0] * math.sin(half_angle),
            axis[1] * math.sin(half_angle),
            axis[2] * math.sin(half_angle),
            math.cos(half_angle),
        ],
        dtype=np.float32,
    )


def quaternion_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """Multiply two quaternions"""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array(
        [
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        ],
        dtype=np.float32,
    )


def quaternion_rotate_vector(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate a vector by a quaternion"""
    # Convert vector to quaternion [v.x, v.y, v.z, 0]
    v_quat = np.array([v[0], v[1], v[2], 0.0], dtype=np.float32)

    # Conjugate of q
    q_conj = np.array([-q[0], -q[1], -q[2], q[3]], dtype=np.float32)

    # Rotate: q * v * q_conj
    temp = quaternion_multiply(q, v_quat)
    result = quaternion_multiply(temp, q_conj)

    return np.array([result[0], result[1], result[2]], dtype=np.float32)


@beartype
class FixtureRenderer:
    """
    Base class for rendering individual DMX fixtures using OpenGL in 3D.
    Each renderer knows how to draw its fixture type with color, dimmer, etc.
    Now renders in 3D room space with gray bodies and colored bulbs/beams.
    """

    def __init__(self, fixture: FixtureBase, room_renderer: Optional[Any] = None):
        self.fixture = fixture
        self.position = (0.0, 0.0, 3.0)  # (x, y, z) - z is height
        self.size = self._get_default_size()
        self.room_renderer = room_renderer  # Room3DRenderer instance
        self.cube_size = 0.8  # Size of fixture body cube

        # Orientation quaternion - identity means pointing down room at audience
        # Default orientation: Z-axis points toward audience (negative Z in room coords)
        self.orientation = quaternion_identity()

    def set_position(self, x: float, y: float, z: float = 3.0):
        """Set the position of the fixture in canvas coordinates (x, y) and height (z)"""
        self.position = (x, y, z)

    @abstractmethod
    def _get_default_size(self) -> tuple[float, float]:
        """Get the default size (width, height) for this fixture type"""
        pass

    def get_bounds(self) -> tuple[float, float, float, float]:
        """Get fixture bounds as (x, y, width, height)"""
        x, y = self.position
        w, h = self.size
        return (x, y, w, h)

    def get_color(self) -> tuple[float, float, float]:
        """Get RGB color from fixture (0-1 range)"""
        color = self.fixture.get_color()
        return (color.red, color.green, color.blue)

    def get_dimmer(self) -> float:
        """Get dimmer value (0-1 range)"""
        return self.fixture.get_dimmer() / 255.0

    def get_strobe(self) -> float:
        """Get strobe value (0-1 range)"""
        try:
            strobe = self.fixture.get_strobe()
            return strobe / 255.0
        except:
            return 0.0

    def get_effective_dimmer(self, frame: Frame) -> float:
        """Get effective dimmer including strobe effect
        
        If dimmer > 0 and strobe > 0, applies a true strobe effect (on/off toggle).
        Otherwise returns the base dimmer value.
        """
        dimmer = self.get_dimmer()
        strobe = self.get_strobe()

        # Apply strobe effect: if dimmer > 0 and strobe > 0, toggle beam on/off
        if dimmer > 0.0 and strobe > 0.0:
            # Strobe speed: higher strobe values = faster strobe
            # Scale strobe (0-1) to reasonable strobe speed range (5-30 Hz)
            strobe_speed = 5.0 + strobe * 25.0
            # Use integer division to create discrete on/off toggle
            is_on = int(frame.time * strobe_speed) % 2 == 1
            return dimmer if is_on else 0.0

        return dimmer

    def get_3d_position(
        self, canvas_size: tuple[float, float]
    ) -> tuple[float, float, float]:
        """Convert 2D canvas position to 3D room coordinates"""
        if self.room_renderer is None:
            return (0.0, 0.0, 0.0)

        x, y, z = self.position
        return self.room_renderer.convert_2d_to_3d(
            x, y, z, canvas_size[0], canvas_size[1]
        )

    def get_oriented_offset(self, offset: tuple[float, float, float]) -> np.ndarray:
        """Apply orientation quaternion to a local offset vector

        Args:
            offset: Local offset (x, y, z) relative to fixture center
                   With identity orientation: +Z points toward audience

        Returns:
            Rotated offset in world space
        """
        offset_vec = np.array(offset, dtype=np.float32)
        return quaternion_rotate_vector(self.orientation, offset_vec)

    def get_render_color(
        self, frame: Frame, is_bulb: bool = False
    ) -> tuple[float, float, float]:
        """Get color with dimmer and minimum brightness applied

        Args:
            frame: Current frame
            is_bulb: If True, make brighter for bulb rendering
        """
        color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        # Always render with at least minimum brightness so fixtures don't disappear
        min_brightness = 0.1

        if dimmer < 0.01:
            # Fixture is dark - show as dim gray
            return (min_brightness, min_brightness, min_brightness)
        else:
            # Apply dimmer to color brightness, ensuring minimum visibility
            brightness = max(dimmer, min_brightness)

            # Make bulbs brighter by boosting the color
            if is_bulb:
                brightness = min(brightness * 1.5, 1.0)  # 50% brighter, capped at 1.0

            return (color[0] * brightness, color[1] * brightness, color[2] * brightness)

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """
        Render only the opaque Blinn-Phong parts of this fixture (cubes, boxes, etc).
        This is called during the opaque rendering pass.

        Args:
            context: ModernGL context
            canvas_size: (width, height) of the canvas
            frame: Current frame with timing and signal data
        """
        # Automatically render DMX address after rendering the fixture
        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """
        Render only the emissive parts of this fixture (bulbs and beams).
        These are materials that emit light and should receive bloom effect.
        Override this for proper emissive rendering. Default: do nothing.

        Args:
            context: ModernGL context
            canvas_size: (width, height) of the canvas
            frame: Current frame with timing and signal data
        """
        # Default: do nothing
        pass

    def render_dmx_address(self, canvas_size: tuple[float, float]):
        """
        Render the DMX address as small text near the fixture.
        This should be called by subclasses after rendering the fixture body.

        Args:
            canvas_size: (width, height) of the canvas
        """
        if self.room_renderer is None:
            return

        # Get the 3D position of the fixture
        room_pos = self.get_3d_position(canvas_size)

        # Render the DMX address text slightly above and to the right of the fixture
        # Position the text above the fixture
        text_pos = (room_pos[0], room_pos[1] + self.cube_size + 0.1, room_pos[2])

        # Use the room renderer's local position context manager
        with self.room_renderer.local_position(room_pos):
            self.room_renderer.render_text_label(
                text=str(self.fixture.address),
                position=(0.0, self.cube_size + 0.1, 0.0),  # Slightly above fixture
                color=(0.8, 0.8, 0.8),  # Light gray
                size=0.2,  # Small text
            )
