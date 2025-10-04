#!/usr/bin/env python3

from abc import abstractmethod
from beartype import beartype
from typing import Optional, Any
import numpy as np
import math

from parrot.fixtures.base import FixtureBase
from parrot.director.frame import Frame


@beartype
class FixtureRenderer:
    """
    Base class for rendering individual DMX fixtures using OpenGL in 3D.
    Each renderer knows how to draw its fixture type with color, dimmer, etc.
    Now renders in 3D room space with gray bodies and colored bulbs/beams.
    """

    def __init__(self, fixture: FixtureBase, room_renderer: Optional[Any] = None):
        self.fixture = fixture
        self.position = (0.0, 0.0)  # (x, y) in canvas coordinates
        self.size = self._get_default_size()
        self.room_renderer = room_renderer  # Room3DRenderer instance
        self.cube_size = 0.8  # Size of fixture body cube

    def set_position(self, x: float, y: float):
        """Set the position of the fixture in canvas coordinates"""
        self.position = (x, y)

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
        """Get effective dimmer including strobe effect"""
        dimmer = self.get_dimmer()
        strobe = self.get_strobe()

        if strobe > 0.04:  # strobe > 10/255
            # Strobe effect from legacy code
            dimmer = dimmer * (1.0 + math.sin(frame.time * 30 * strobe * 4) / 2)

        return dimmer

    def get_3d_position(
        self, canvas_size: tuple[float, float]
    ) -> tuple[float, float, float]:
        """Convert 2D canvas position to 3D room coordinates"""
        if self.room_renderer is None:
            return (0.0, 0.0, 0.0)

        x, y = self.position
        return self.room_renderer.convert_2d_to_3d(x, y, canvas_size[0], canvas_size[1])

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

    @abstractmethod
    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """
        Render this fixture to the current framebuffer in 3D.

        Args:
            context: ModernGL context
            canvas_size: (width, height) of the canvas
            frame: Current frame with timing and signal data
        """
        pass
