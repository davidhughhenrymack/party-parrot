"""Overlay UI for Party Parrot using ImGui"""

import imgui
from imgui.integrations.pyglet import create_renderer
from beartype import beartype
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode
from parrot.state import State
from parrot.patch_bay import (
    get_all_venues,
    get_supported_fixture_types,
    get_venue_display_name,
)
from parrot.venue_editor import VenueEditorController
from parrot.director.themes import themes


@beartype
class OverlayUI:
    """ImGui overlay UI for mode selection and control"""

    def __init__(
        self, pyglet_window, state: State, editor: VenueEditorController
    ):
        self.state = state
        self.editor = editor
        self.visible = False
        self.pyglet_window = pyglet_window
        self._first_render = True
        self.editor_status = ""
        self.new_venue_name = ""
        self.new_light_address = 1
        self.fixture_type_options = get_supported_fixture_types()
        self.selected_fixture_type_idx = 0
        self.floor_size_input = self.editor.get_floor_size_feet()
        self._last_venue_name = self.state.venue.name

        # Initialize ImGui context
        imgui.create_context()

        # Create renderer using official pyglet integration
        # This auto-detects the appropriate renderer and handles all input callbacks
        self.renderer = create_renderer(pyglet_window, attach_callbacks=True)

        # UI dimensions (doubled from original 250x200, increased for venue/theme/vj_mode)
        self.window_width = 500
        self.window_height = 920
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

        if self._last_venue_name != self.state.venue.name:
            self.floor_size_input = self.editor.get_floor_size_feet()
            self._last_venue_name = self.state.venue.name

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

            # VJ Mode selection
            imgui.text("VJ Mode (Visuals)")
            vj_modes = list(VJMode)
            vj_mode_names = [m.name.replace("_", " ").title() for m in vj_modes]
            current_vj_mode_idx = vj_modes.index(self.state.vj_mode)
            clicked, new_vj_mode_idx = imgui.combo(
                "##vj_mode", current_vj_mode_idx, vj_mode_names
            )
            if clicked and new_vj_mode_idx != current_vj_mode_idx:
                self.state.set_vj_mode(vj_modes[new_vj_mode_idx])
                print(f"🎬 VJ Mode changed to: {vj_mode_names[new_vj_mode_idx]}")

            imgui.spacing()
            imgui.separator()
            imgui.spacing()

            # Venue selection
            imgui.text("Venue")
            venue_options = get_all_venues()
            venue_names = [get_venue_display_name(venue) for venue in venue_options]
            current_venue_idx = venue_options.index(self.state.venue)
            clicked, new_venue_idx = imgui.combo(
                "##venue", current_venue_idx, venue_names
            )
            if clicked and new_venue_idx != current_venue_idx:
                self.state.set_venue(venue_options[new_venue_idx])
                self.floor_size_input = self.editor.get_floor_size_feet()

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

            if self.state.show_fixture_mode:
                imgui.spacing()
                imgui.separator()
                imgui.spacing()
                imgui.text("3D Venue Editor")

                selected_label = self.editor.get_selected_label()
                imgui.text(f"Selected: {selected_label}")
                selection_options = self.editor.get_selection_options()
                selection_labels = [label for _, label in selection_options]
                current_selection_key = self.editor.get_selected_key()
                current_selection_idx = 0
                for idx, (key, _) in enumerate(selection_options):
                    if key == current_selection_key:
                        current_selection_idx = idx
                        break
                clicked, new_selection_idx = imgui.combo(
                    "Target", current_selection_idx, selection_labels
                )
                if clicked and new_selection_idx != current_selection_idx:
                    self.editor.select_target_by_key(
                        selection_options[new_selection_idx][0]
                    )
                if imgui.button("Prev Target", 138, 36):
                    prev_index = (current_selection_idx - 1) % len(selection_options)
                    self.editor.select_target_by_key(selection_options[prev_index][0])
                imgui.same_line()
                if imgui.button("Next Target", 138, 36):
                    next_index = (current_selection_idx + 1) % len(selection_options)
                    self.editor.select_target_by_key(selection_options[next_index][0])
                imgui.same_line()
                if imgui.button("Video Wall", 138, 36):
                    self.editor.select_target_by_key("__video_wall__")

                for mode_name, label in (
                    ("select", "Select"),
                    ("move", "Move"),
                    ("rotate", "Rotate"),
                ):
                    if self.editor.get_mode() == mode_name:
                        imgui.push_style_color(imgui.COLOR_BUTTON, 0.2, 0.45, 0.8, 1.0)
                        imgui.push_style_color(
                            imgui.COLOR_BUTTON_HOVERED, 0.25, 0.55, 0.9, 1.0
                        )
                        imgui.push_style_color(
                            imgui.COLOR_BUTTON_ACTIVE, 0.25, 0.65, 1.0, 1.0
                        )
                    if imgui.button(label, 138, 44):
                        self.editor.set_mode(mode_name)
                    if self.editor.get_mode() == mode_name:
                        imgui.pop_style_color(3)
                    if mode_name != "rotate":
                        imgui.same_line()

                imgui.spacing()
                imgui.text_wrapped(
                    "Select a light or the video wall in the 3D view, then use move or rotate mode to drag the axis gizmo handles."
                )
                if imgui.button("-1 ft", 100, 36):
                    self.floor_size_input = max(1.0, self.floor_size_input - 1.0)
                imgui.same_line()
                if imgui.button("+1 ft", 100, 36):
                    self.floor_size_input += 1.0
                imgui.same_line()
                if imgui.button("+5 ft", 100, 36):
                    self.floor_size_input += 5.0

                changed, self.floor_size_input = imgui.input_float(
                    "Floor size (ft)", self.floor_size_input, 1.0, 5.0, "%.1f"
                )
                if imgui.button("Apply Floor Size", 220, 40):
                    self.editor.set_floor_size_feet(max(1.0, self.floor_size_input))
                    self.floor_size_input = self.editor.get_floor_size_feet()
                    self.editor_status = "Floor size updated."

                imgui.spacing()
                imgui.text("Add Light")
                fixture_type_names = [label for _, label in self.fixture_type_options]
                clicked, self.selected_fixture_type_idx = imgui.combo(
                    "Fixture type",
                    self.selected_fixture_type_idx,
                    fixture_type_names,
                )
                changed, self.new_light_address = imgui.input_int(
                    "DMX address", self.new_light_address
                )
                if imgui.button("Add Light", 220, 44):
                    fixture_type = self.fixture_type_options[
                        self.selected_fixture_type_idx
                    ][0]
                    try:
                        self.editor.add_light(fixture_type, int(self.new_light_address))
                        self.editor_status = "Light added."
                    except ValueError as exc:
                        self.editor_status = str(exc)

                imgui.spacing()
                imgui.text("Add Venue")
                changed, self.new_venue_name = imgui.input_text(
                    "Venue name", self.new_venue_name, 128
                )
                if imgui.button("Create Venue", 220, 44):
                    try:
                        self.editor.add_venue(self.new_venue_name)
                        self.new_venue_name = ""
                        self.floor_size_input = self.editor.get_floor_size_feet()
                        self.editor_status = "Venue created."
                    except ValueError as exc:
                        self.editor_status = str(exc)

                if self.editor_status:
                    imgui.spacing()
                    imgui.text_wrapped(self.editor_status)

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
