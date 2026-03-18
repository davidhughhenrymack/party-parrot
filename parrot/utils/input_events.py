#!/usr/bin/env python3
"""
Singleton input event system for handling mouse and keyboard events.
Allows 3D renderers and other components to receive input events.
"""

from beartype import beartype
from beartype.typing import Callable, Optional


@beartype
class InputEvents:
    """Singleton class for distributing input events to registered handlers"""

    _instance: Optional["InputEvents"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # Mouse state
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.mouse_down = False
        self.mouse_drag_start_x = 0.0
        self.mouse_drag_start_y = 0.0

        # Registered callbacks. Returning True consumes the event.
        self.on_mouse_drag: list[Callable[[float, float], bool | None]] = []
        self.on_mouse_press: list[Callable[[float, float], bool | None]] = []
        self.on_mouse_release: list[Callable[[float, float], bool | None]] = []
        self.on_mouse_scroll: list[Callable[[float, float], bool | None]] = []

    def handle_mouse_press(self, x: float, y: float):
        """Called when mouse button is pressed"""
        self.mouse_down = True
        self.mouse_drag_start_x = x
        self.mouse_drag_start_y = y
        self.mouse_x = x
        self.mouse_y = y

        for callback in list(self.on_mouse_press):
            if callback(x, y):
                break

    def handle_mouse_release(self, x: float, y: float):
        """Called when mouse button is released"""
        self.mouse_down = False
        self.mouse_x = x
        self.mouse_y = y

        for callback in list(self.on_mouse_release):
            if callback(x, y):
                break

    def handle_mouse_drag(self, x: float, y: float):
        """Called when mouse is dragged"""
        if not self.mouse_down:
            return

        # Calculate delta from drag start
        dx = x - self.mouse_x
        dy = y - self.mouse_y

        self.mouse_x = x
        self.mouse_y = y

        for callback in list(self.on_mouse_drag):
            if callback(dx, dy):
                break

    def register_mouse_drag_callback(
        self, callback: Callable[[float, float], bool | None]
    ):
        """Register a callback for mouse drag events"""
        self.on_mouse_drag.append(callback)

    def register_mouse_press_callback(
        self, callback: Callable[[float, float], bool | None]
    ):
        """Register a callback for mouse press events"""
        self.on_mouse_press.append(callback)

    def register_mouse_release_callback(
        self, callback: Callable[[float, float], bool | None]
    ):
        """Register a callback for mouse release events"""
        self.on_mouse_release.append(callback)

    def handle_mouse_scroll(self, scroll_x: float, scroll_y: float):
        """Called when mouse wheel is scrolled"""
        for callback in list(self.on_mouse_scroll):
            if callback(scroll_x, scroll_y):
                break

    def register_mouse_scroll_callback(
        self, callback: Callable[[float, float], bool | None]
    ):
        """Register a callback for mouse scroll events"""
        self.on_mouse_scroll.append(callback)

    @classmethod
    def get_instance(cls) -> "InputEvents":
        """Get the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
