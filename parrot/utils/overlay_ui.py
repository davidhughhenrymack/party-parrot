"""Overlay UI for Party Parrot using ImGui"""

import imgui
from imgui.integrations.pyglet import create_renderer
from beartype import beartype
from parrot.director.mode import Mode
from parrot.state import State
from parrot.patch_bay import venues
from parrot.director.themes import themes


@beartype
class OverlayUI:
    """ImGui overlay UI for mode selection and control"""

    def __init__(self, pyglet_window, state: State):
        self.state = state
        self.visible = False
        self.pyglet_window = pyglet_window
        self._first_render = True

        # Initialize ImGui context
        imgui.create_context()

        # Create renderer using official pyglet integration
        # This auto-detects the appropriate renderer and handles all input callbacks
        self.renderer = create_renderer(pyglet_window, attach_callbacks=True)

        # UI dimensions (doubled from original 250x200, increased for venue/theme)
        self.window_width = 500
        self.window_height = 550
        self.button_width = 440
        self.button_height = 60

    def toggle(self):
        """Toggle overlay visibility"""
        self.visible = not self.visible
        if self.visible:
            # Reset first render flag when showing overlay
            # to ensure proper IO state initialization
            self._first_render = True
        print(f"🖥️  Overlay {'shown' if self.visible else 'hidden'}")

    def show(self):
        """Show the overlay"""
        self.visible = True
        # Reset first render flag to ensure proper IO state initialization
        self._first_render = True

    def hide(self):
        """Hide the overlay"""
        self.visible = False

    def render(self):
        """Render the overlay UI if visible"""
        if not self.visible:
            return

        # Fix for first-render mouse input issue:
        # Event callbacks only fire when events happen. If the mouse hasn't moved
        # since the overlay became visible, ImGui doesn't know where it is and
        # won't respond to clicks. Manually sync mouse position from window state.
        if self._first_render:
            io = imgui.get_io()
            try:
                x, y = self.pyglet_window._mouse_x, self.pyglet_window._mouse_y
                # Convert from pyglet (bottom-left) to ImGui (top-left) coordinates
                io.mouse_pos = (x, self.pyglet_window.height - y)
            except (AttributeError, TypeError):
                # Fallback if mouse position unavailable
                io.mouse_pos = (
                    self.pyglet_window.width / 2,
                    self.pyglet_window.height / 2,
                )
            self._first_render = False

        imgui.new_frame()

        # Double the font scale for better readability
        imgui.get_io().font_global_scale = 2.0

        # Create the overlay window
        imgui.set_next_window_position(20, 20, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(
            self.window_width, self.window_height, imgui.FIRST_USE_EVER
        )

        # Begin window with close button - capture if window should remain open
        expanded, opened = imgui.begin("Party Parrot Control", True)

        # If user clicked the (x) button, toggle visibility
        if not opened:
            self.visible = False
            print("🖥️  Overlay hidden")

        if expanded:
            imgui.text("Mode Selection")
            imgui.separator()

            # Mode toggle buttons
            current_mode = self.state.mode

            for mode in Mode:
                is_selected = current_mode == mode
                if is_selected:
                    imgui.push_style_color(imgui.COLOR_BUTTON, 0.2, 0.6, 0.2, 1.0)
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON_HOVERED, 0.2, 0.7, 0.2, 1.0
                    )
                    imgui.push_style_color(
                        imgui.COLOR_BUTTON_ACTIVE, 0.2, 0.8, 0.2, 1.0
                    )

                if imgui.button(
                    mode.name.upper(), self.button_width, self.button_height
                ):
                    self.state.set_mode(mode)
                    print(f"🎵 Mode changed to: {mode.name}")

                if is_selected:
                    imgui.pop_style_color(3)

            imgui.spacing()
            imgui.separator()
            imgui.spacing()

            # Venue selection
            imgui.text("Venue")
            venue_names = [v.name for v in venues]
            current_venue_idx = list(venues).index(self.state.venue)
            clicked, new_venue_idx = imgui.combo(
                "##venue", current_venue_idx, venue_names
            )
            if clicked and new_venue_idx != current_venue_idx:
                self.state.set_venue(list(venues)[new_venue_idx])
                print(f"🏛️  Venue changed to: {venue_names[new_venue_idx]}")

            imgui.spacing()

            # Theme/Color Scheme selection
            imgui.text("Color Scheme")
            theme_names = [t.name for t in themes]
            current_theme_idx = themes.index(self.state.theme)
            clicked, new_theme_idx = imgui.combo(
                "##theme", current_theme_idx, theme_names
            )
            if clicked and new_theme_idx != current_theme_idx:
                self.state.set_theme(themes[new_theme_idx])
                print(f"🎨 Color scheme changed to: {theme_names[new_theme_idx]}")

        imgui.end()

        # Render ImGui
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def shutdown(self):
        """Cleanup resources"""
        try:
            self.renderer.shutdown()
        except Exception as e:
            # Ignore OpenGL errors during shutdown as the context may already be destroyed
            if "GLError" in str(type(e)) or "invalid value" in str(e):
                print(f"⚠️  Ignoring OpenGL error during imgui shutdown: {e}")
            else:
                # Re-raise non-OpenGL errors
                raise
