"""Overlay UI for Party Parrot using ImGui"""

import imgui
from beartype import beartype
from parrot.director.mode import Mode
from parrot.state import State
from parrot.utils.imgui_moderngl import ImGuiModernGLRenderer


@beartype
class OverlayUI:
    """ImGui overlay UI for mode selection and control"""

    def __init__(self, ctx, pyglet_window, state: State):
        self.state = state
        self.visible = False

        # Initialize ImGui
        imgui.create_context()

        # Create renderer
        self.renderer = ImGuiModernGLRenderer(ctx, pyglet_window)

        # UI dimensions (doubled from original 250x200)
        self.window_width = 500
        self.window_height = 400
        self.button_width = 440
        self.button_height = 60

    def toggle(self):
        """Toggle overlay visibility"""
        self.visible = not self.visible
        print(f"🖥️  Overlay {'shown' if self.visible else 'hidden'}")

    def show(self):
        """Show the overlay"""
        self.visible = True

    def hide(self):
        """Hide the overlay"""
        self.visible = False

    def render(self):
        """Render the overlay UI if visible"""
        if not self.visible:
            return

        imgui.new_frame()

        # Double the font scale for better readability
        imgui.get_io().font_global_scale = 2.0

        # Create the overlay window
        imgui.set_next_window_position(20, 20, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(
            self.window_width, self.window_height, imgui.FIRST_USE_EVER
        )

        imgui.begin("Party Parrot Control", True)

        imgui.text("Mode Selection")
        imgui.separator()

        # Mode toggle buttons
        current_mode = self.state.mode

        for mode in Mode:
            is_selected = current_mode == mode
            if is_selected:
                imgui.push_style_color(imgui.COLOR_BUTTON, 0.2, 0.6, 0.2, 1.0)
                imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.2, 0.7, 0.2, 1.0)
                imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 0.2, 0.8, 0.2, 1.0)

            if imgui.button(mode.name.upper(), self.button_width, self.button_height):
                self.state.set_mode(mode)
                print(f"🎵 Mode changed to: {mode.name}")

            if is_selected:
                imgui.pop_style_color(3)

        imgui.end()

        # Render ImGui
        imgui.render()
        self.renderer.render(imgui.get_draw_data())

    def shutdown(self):
        """Cleanup resources"""
        self.renderer.shutdown()
