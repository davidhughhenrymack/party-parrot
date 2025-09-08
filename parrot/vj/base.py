from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Generic, TypeVar
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs

T = TypeVar("T", bound="LayerBase")


class LayerBase(ABC):
    """Base class for all VJ layers"""

    def __init__(self, name: str, z_order: int = 0):
        self.name = name
        self.z_order = z_order  # Higher values render on top
        self.alpha = 1.0
        self.enabled = True
        self._texture_data: Optional[np.ndarray] = None
        # Size will be set by renderer
        self.width = 1920  # Default, will be overridden
        self.height = 1080  # Default, will be overridden

    @abstractmethod
    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render this layer and return RGBA texture data as numpy array

        Returns:
            np.ndarray: RGBA texture data of shape (height, width, 4) with values 0-255
                       or None if layer should not be rendered
        """
        pass

    def set_alpha(self, alpha: float):
        """Set the alpha (transparency) of this layer"""
        self.alpha = max(0.0, min(1.0, alpha))

    def get_alpha(self) -> float:
        """Get the current alpha value"""
        return self.alpha

    def set_enabled(self, enabled: bool):
        """Enable or disable this layer"""
        self.enabled = enabled

    def is_enabled(self) -> bool:
        """Check if this layer is enabled"""
        return self.enabled

    def set_size(self, width: int, height: int):
        """Set the size of this layer (called by renderer)"""
        self.width = width
        self.height = height

    def get_size(self) -> Tuple[int, int]:
        """Get the size of this layer"""
        return (self.width, self.height)

    def resize(self, width: int, height: int):
        """Resize this layer"""
        self.width = width
        self.height = height

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


class VJInterpreterBase(Generic[T], ABC):
    """Base class for VJ interpreters that control layer behavior"""

    has_rainbow = False
    hype = 0

    def __init__(self, layers: List[T], args: InterpreterArgs):
        self.layers = layers
        self.interpreter_args = args

    @abstractmethod
    def step(self, frame: Frame, scheme: ColorScheme):
        """Update the layers based on the current frame and color scheme"""
        pass

    def exit(self, frame: Frame, scheme: ColorScheme):
        """Called when this interpreter is being replaced"""
        pass

    def get_hype(self):
        """Get the hype level of this interpreter"""
        return self.__class__.hype

    @classmethod
    def acceptable(cls, args: InterpreterArgs) -> bool:
        """Check if this interpreter is acceptable for the given args"""
        from parrot.interpreters.base import acceptable_test

        return acceptable_test(args, cls.hype, cls.has_rainbow)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"


# VJRenderer is now implemented in renderer.py
# Import it there directly to avoid circular imports


class SolidLayer(LayerBase):
    """A simple solid color layer"""

    def __init__(
        self,
        name: str = "solid",
        color: Tuple[int, int, int] = (0, 0, 0),
        alpha: int = 255,
        z_order: int = 0,
    ):
        super().__init__(name, z_order)
        self.color = color
        self.layer_alpha = alpha

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render a solid color"""
        if not self.enabled:
            return None

        # Create solid color texture
        texture = np.full(
            (self.height, self.width, 4),
            (*self.color, self.layer_alpha),
            dtype=np.uint8,
        )
        return texture

    def set_color(self, color: Tuple[int, int, int]):
        """Set the solid color"""
        self.color = color

    def set_layer_alpha(self, alpha: int):
        """Set the layer's base alpha (0-255)"""
        self.layer_alpha = max(0, min(255, alpha))
