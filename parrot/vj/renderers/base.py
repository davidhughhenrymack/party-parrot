#!/usr/bin/env python3

from abc import abstractmethod
from beartype import beartype
from typing import Optional
import numpy as np
import math

from parrot.fixtures.base import FixtureBase
from parrot.director.frame import Frame


@beartype
class FixtureRenderer:
    """
    Base class for rendering individual DMX fixtures using OpenGL.
    Each renderer knows how to draw its fixture type with color, dimmer, etc.
    Similar to legacy GUI renderers but using OpenGL.
    """

    def __init__(self, fixture: FixtureBase):
        self.fixture = fixture
        self.position = (0.0, 0.0)  # (x, y) in canvas coordinates
        self.size = self._get_default_size()

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

    @abstractmethod
    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """
        Render this fixture to the current framebuffer.
        Similar to legacy GUI render(canvas, frame) but using OpenGL.

        Args:
            context: ModernGL context
            canvas_size: (width, height) of the canvas
            frame: Current frame with timing and signal data
        """
        pass
