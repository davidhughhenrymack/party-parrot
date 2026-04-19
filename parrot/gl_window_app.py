#!/usr/bin/env python3

import io
import time
from urllib.parse import urlparse
import moderngl_window as mglw
import moderngl as mgl
from beartype import beartype
import numpy as np
from typing import Any

from parrot.audio.audio_analyzer import AudioAnalyzer
from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import MODES_BY_HYPE
from parrot.gl_display_mode import EditorDisplayMode
from parrot.state import State
from parrot.utils.dmx_utils import Universe, get_controller
from parrot.vj.dmx_heatmap_renderer import DmxHeatmapRenderer
from parrot.vj.vj_director import VJDirector
from parrot.utils.overlay_ui import OverlayUI
from parrot.keyboard_handler import KeyboardHandler
from parrot.utils.input_events import InputEvents
from parrot.director.themes import themes
from parrot.vj.vj_mode import VJMode, vj_mode_menu_label
from parrot.runtime_venue_client import RuntimeVenueClient
from parrot.venue_runtime import get_runtime_venues


@beartype
def _encode_texture_rgb_as_jpeg(tex: Any) -> bytes | None:
    """Read a color texture from the VJ/offscreen FBO and return JPEG bytes.

    The VJ pipeline's final framebuffer is RGBA (see LayerCompose.final_texture),
    but earlier fixture/DMX previews hand us RGB textures. Read exactly as many
    bytes as the texture stores (1 byte/channel), tell PIL the matching mode,
    and convert to RGB before JPEG encoding. Using a 3-byte stride on a 4-byte
    texture shears every row and produces an interlaced/striped preview in the
    web client.
    """
    from PIL import Image

    w, h = tex.size
    if w < 2 or h < 2:
        return None
    components = int(getattr(tex, "components", 3))
    if components == 4:
        mode = "RGBA"
    elif components == 3:
        mode = "RGB"
    elif components == 1:
        mode = "L"
    else:
        # Unsupported channel count (e.g. 2-channel RG); skip rather than shear.
        return None
    raw = tex.read(alignment=1)
    img = Image.frombuffer(mode, (w, h), raw, "raw", mode, 0, 1)
    if mode != "RGB":
        img = img.convert("RGB")
    # moderngl returns this VJ FBO's bytes already top-down, so no vertical flip
    # is needed to get a naturally-oriented JPEG for the web preview.
    max_w = 1280
    if w > max_w:
        nh = max(2, int(round(h * (max_w / w))))
        img = img.resize((max_w, nh), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


def run_gl_window_app(args):
    """Run Party Parrot with modern GL window"""
    # Create window using moderngl_window
    window_cls = mglw.get_local_window_cls("pyglet")
    window = window_cls(
        title="Party Parrot",
        size=(1920, 1080),
        resizable=True,
        vsync=True,
        fullscreen=getattr(args, "vj_fullscreen", False),
        gl_version=(3, 3),
    )

    ctx = window.ctx

    # Initialize state and components
    state = State()
    # Use the single SignalStates owned by State so keyboard shortcuts, audio
    # analyzer, and remote-control effect pushes all fire the same signals.
    signal_states = state.signal_states

    runtime_client = None
    venue_service_url = getattr(args, "venue_service_url", None)
    if venue_service_url:
        runtime_client = RuntimeVenueClient(state, venue_service_url)
        try:
            runtime_client.bootstrap()
            state.process_gui_updates()
        except Exception as exc:
            print(f"⚠️  Venue service bootstrap failed: {exc}")
        runtime_client.start()

    # Initialize audio analyzer
    audio_analyzer = AudioAnalyzer(signal_states)

    # Initialize VJ system
    vj_director = VJDirector(state)
    vj_director.setup(ctx)

    # Initialize director first (creates position manager)
    director = Director(state, vj_director)

    # Remote control "shift" buttons come in over websocket; State queues
    # them and fires these events on the main thread.
    state.events.on_shift_lighting_only_request += director.shift_lighting_only
    state.events.on_shift_color_scheme_request += director.shift_color_scheme
    state.events.on_shift_vj_only_request += director.shift_vj_only

    # Initialize fixture renderer (uses director's position manager)
    from parrot.vj.nodes.fixture_visualization import FixtureVisualization

    fixture_renderer = FixtureVisualization(
        state=state,
        position_manager=director.position_manager,
        vj_director=vj_director,
        width=1920,
        height=1080,
    )
    fixture_renderer.enter(ctx)

    dmx_heatmap_renderer = DmxHeatmapRenderer()
    dmx_heatmap_renderer.enter(ctx)

    # Initialize DMX with venue-specific configuration
    dmx_ref = {"controller": get_controller(state.venue)}

    def refresh_dmx_controller(_):
        dmx_ref["controller"] = get_controller(state.venue)

    state.events.on_venue_change += refresh_dmx_controller

    # Setup display shader
    vertex_shader = """
    #version 330
    in vec2 in_position;
    in vec2 in_texcoord;
    out vec2 uv;
    
    void main() {
        gl_Position = vec4(in_position, 0.0, 1.0);
        uv = in_texcoord;
    }
    """

    fragment_shader = """
    #version 330
    in vec2 uv;
    out vec3 color;
    uniform sampler2D source_texture;
    uniform vec2 source_size;
    uniform vec2 target_size;
    // 0 = VJ / fixture (legacy Y flip for correct on-screen orientation). 1 = DMX heatmap only (no flip).
    uniform int u_dmx_heatmap;
    
    void main() {
        float src_aspect = source_size.x / source_size.y;
        float dst_aspect = target_size.x / target_size.y;
        
        float scale_x = 1.0;
        float scale_y = 1.0;
        if (src_aspect > dst_aspect) {
            scale_x = src_aspect / dst_aspect;
        } else {
            scale_y = dst_aspect / src_aspect;
        }
        
        vec2 tex_uv = uv;
        if (u_dmx_heatmap == 0) {
            tex_uv = vec2(uv.x, 1.0 - uv.y);
        }
        vec2 centered = (tex_uv - 0.5);
        centered.x /= scale_x;
        centered.y /= scale_y;
        vec2 cover_uv = centered + 0.5;
        
        color = texture(source_texture, cover_uv).rgb;
    }
    """

    display_shader = ctx.program(
        vertex_shader=vertex_shader, fragment_shader=fragment_shader
    )

    vertices = np.array(
        [
            -1.0,
            -1.0,
            0.0,
            0.0,
            1.0,
            -1.0,
            1.0,
            0.0,
            -1.0,
            1.0,
            0.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        ],
        dtype=np.float32,
    )

    vbo = ctx.buffer(vertices.tobytes())
    display_quad = ctx.vertex_array(
        display_shader, [(vbo, "2f 2f", "in_position", "in_texcoord")]
    )

    # Start web server if not disabled (integrated into main thread)
    web_server = None
    if not getattr(args, "no_web", False):
        from parrot.api import start_web_server

        editor_port = urlparse(venue_service_url).port if venue_service_url else 4041
        web_server = start_web_server(
            state,
            port=getattr(args, "web_port", 4040),
            threaded=False,  # Run in main thread
            editor_port=editor_port or 4041,
        )

    # Timing
    last_audio_update = time.perf_counter()
    audio_update_interval = 0.03

    # Check if we're in debug frame capture mode
    debug_frame_mode = getattr(args, "debug_frame", False)

    # Main render loop
    import pyglet

    # Get the underlying pyglet window for input handling
    pyglet_window = None
    for w in pyglet.app.windows:
        pyglet_window = w
        break

    # Initialize overlay UI
    overlay = OverlayUI(pyglet_window, state)

    # Check for start-with-overlay flag
    if getattr(args, "start_with_overlay", False):
        overlay.show()

    # Setup native macOS menu bar for settings
    def create_settings_menus():
        """Create native macOS menu bar with mode/theme/venue selection using PyObjC"""
        import sys

        if sys.platform != "darwin":
            return

        try:
            from AppKit import NSApplication, NSMenu, NSMenuItem
            from Foundation import NSObject
            import objc

            # Get the shared application
            app = NSApplication.sharedApplication()
            main_menu = app.mainMenu()

            # Create a unified delegate class for all menu callbacks
            class SettingsMenuDelegate(NSObject):
                def initWithState_(self, state_obj):
                    self = objc.super(SettingsMenuDelegate, self).init()
                    if self is None:
                        return None
                    self.state = state_obj
                    self.modes = list(MODES_BY_HYPE)
                    self.vj_modes = list(VJMode)
                    self.venues_list = list(get_runtime_venues(self.state))
                    self.themes = themes
                    # Store menu items for updating checkmarks
                    self.mode_items = []
                    self.vj_mode_items = []
                    self.venue_items = []
                    self.theme_items = []
                    self.venue_menu = None
                    return self

                def updateModeCheckmarks(self):
                    """Update checkmarks for mode menu items"""
                    for idx, item in enumerate(self.mode_items):
                        item.setState_(1 if self.modes[idx] == self.state.mode else 0)

                def updateVJModeCheckmarks(self):
                    """Update checkmarks for VJ mode menu items"""
                    for idx, item in enumerate(self.vj_mode_items):
                        item.setState_(
                            1 if self.vj_modes[idx] == self.state.vj_mode else 0
                        )

                def updateVenueCheckmarks(self):
                    """Update checkmarks for venue menu items"""
                    for idx, item in enumerate(self.venue_items):
                        item.setState_(
                            1 if self.venues_list[idx] == self.state.venue else 0
                        )

                def rebuildVenueMenu(self):
                    """Refresh Venue submenu when the runtime venue list changes."""
                    if self.venue_menu is None:
                        return
                    self.venues_list = list(get_runtime_venues(self.state))
                    self.venue_menu.removeAllItems()
                    self.venue_items = []
                    for idx, venue in enumerate(self.venues_list):
                        display_name = venue.name.replace("_", " ").title()
                        menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                            display_name,
                            objc.selector(self.selectVenue_, signature=b"v@:@"),
                            "",
                        )
                        menu_item.setTag_(idx)
                        menu_item.setTarget_(self)
                        self.venue_menu.addItem_(menu_item)
                        self.venue_items.append(menu_item)
                    self.updateVenueCheckmarks()

                def updateThemeCheckmarks(self):
                    """Update checkmarks for theme menu items"""
                    for idx, item in enumerate(self.theme_items):
                        item.setState_(1 if self.themes[idx] == self.state.theme else 0)

                def selectMode_(self, sender):
                    tag = sender.tag()
                    if 0 <= tag < len(self.modes):
                        selected_mode = self.modes[tag]
                        self.state.set_mode(selected_mode)
                        self.updateModeCheckmarks()
                        print(f"🎵 Mode changed to: {selected_mode.name}")

                def selectVJMode_(self, sender):
                    tag = sender.tag()
                    if 0 <= tag < len(self.vj_modes):
                        selected_vj_mode = self.vj_modes[tag]
                        self.state.set_vj_mode(selected_vj_mode)
                        self.updateVJModeCheckmarks()
                        print(f"📺 VJ Mode changed to: {selected_vj_mode.value}")

                def selectVenue_(self, sender):
                    tag = sender.tag()
                    if 0 <= tag < len(self.venues_list):
                        selected_venue = self.venues_list[tag]
                        self.state.set_venue(selected_venue)
                        self.updateVenueCheckmarks()
                        print(f"🏛️  Venue changed to: {selected_venue.name}")

                def selectTheme_(self, sender):
                    tag = sender.tag()
                    if 0 <= tag < len(self.themes):
                        selected_theme = self.themes[tag]
                        self.state.set_theme(selected_theme)
                        self.updateThemeCheckmarks()
                        print(f"🎨 Theme changed to: {selected_theme.name}")

            # Create the delegate
            delegate = SettingsMenuDelegate.alloc().initWithState_(state)

            # Create Mode menu — iterate MODES_BY_HYPE (not raw `Mode`) so item
            # indices align with `delegate.modes` used for checkmark + selection.
            # If these drift, the menu checks the wrong item on startup.
            mode_menu = NSMenu.alloc().initWithTitle_("Mode")
            for idx, mode in enumerate(MODES_BY_HYPE):
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    mode.name.capitalize(),
                    objc.selector(delegate.selectMode_, signature=b"v@:@"),
                    "",
                )
                menu_item.setTag_(idx)
                menu_item.setTarget_(delegate)
                mode_menu.addItem_(menu_item)
                delegate.mode_items.append(menu_item)

            mode_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Mode", None, ""
            )
            mode_menu_item.setSubmenu_(mode_menu)
            main_menu.addItem_(mode_menu_item)
            delegate.updateModeCheckmarks()

            # Create VJ Mode menu
            vj_mode_menu = NSMenu.alloc().initWithTitle_("VJ Mode")
            for idx, vj_mode in enumerate(VJMode):
                display_name = vj_mode_menu_label(vj_mode)
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    display_name,
                    objc.selector(delegate.selectVJMode_, signature=b"v@:@"),
                    "",
                )
                menu_item.setTag_(idx)
                menu_item.setTarget_(delegate)
                vj_mode_menu.addItem_(menu_item)
                delegate.vj_mode_items.append(menu_item)

            vj_mode_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "VJ Mode", None, ""
            )
            vj_mode_menu_item.setSubmenu_(vj_mode_menu)
            main_menu.addItem_(vj_mode_menu_item)
            delegate.updateVJModeCheckmarks()

            # Create Venue menu
            venue_menu = NSMenu.alloc().initWithTitle_("Venue")
            runtime_venues = list(get_runtime_venues(state))
            for idx, venue in enumerate(runtime_venues):
                display_name = venue.name.replace("_", " ").title()
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    display_name,
                    objc.selector(delegate.selectVenue_, signature=b"v@:@"),
                    "",
                )
                menu_item.setTag_(idx)
                menu_item.setTarget_(delegate)
                venue_menu.addItem_(menu_item)
                delegate.venue_items.append(menu_item)

            venue_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Venue", None, ""
            )
            venue_menu_item.setSubmenu_(venue_menu)
            main_menu.addItem_(venue_menu_item)
            delegate.venue_menu = venue_menu
            state.events.on_available_venues_change += lambda *_args: delegate.rebuildVenueMenu()
            delegate.updateVenueCheckmarks()

            # Create Theme menu with keyboard shortcuts
            theme_menu = NSMenu.alloc().initWithTitle_("Theme")
            for idx, theme in enumerate(themes):
                shortcut = f"{idx + 1}" if idx < 9 else ""
                menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    theme.name,
                    objc.selector(delegate.selectTheme_, signature=b"v@:@"),
                    shortcut,
                )
                menu_item.setTag_(idx)
                menu_item.setTarget_(delegate)
                theme_menu.addItem_(menu_item)
                delegate.theme_items.append(menu_item)

            theme_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Theme", None, ""
            )
            theme_menu_item.setSubmenu_(theme_menu)
            main_menu.addItem_(theme_menu_item)
            delegate.updateThemeCheckmarks()

            # Store delegate reference to prevent garbage collection
            pyglet_window._settings_menu_delegate = delegate

        except ImportError:
            print("⚠️  Menu bar: PyObjC not available (overlay: ENTER)")
        except Exception as e:
            print(f"⚠️  Menu bar: {e}")

    create_settings_menus()

    # Screenshot mode
    screenshot_mode = getattr(args, "screenshot", False)
    screenshot_time = None
    if screenshot_mode:
        screenshot_time = time.perf_counter() + 0.5
        print("📸 Screenshot mode: will capture after 0.5s and exit")

    def update_cursor_visibility():
        """Hide cursor in VJ/video mode; show for DMX heatmap and fixture scene."""
        if pyglet_window:
            pyglet_window.set_mouse_visible(
                state.editor_display_mode != EditorDisplayMode.VJ
            )

    def cycle_display_mode():
        state.cycle_editor_display_mode()
        update_cursor_visibility()

    # Setup keyboard handler on the underlying pyglet window
    keyboard_handler = KeyboardHandler(
        director,
        overlay,
        signal_states,
        state,
        show_fixture_mode_callback=cycle_display_mode,
    )

    # Setup mouse handler for input events
    input_events = InputEvents.get_instance()

    class MouseHandler:
        """Handle mouse events and forward to input events system"""

        def on_mouse_press(self, x, y, button, modifiers):
            # Only handle left mouse button
            if button == pyglet.window.mouse.LEFT:
                input_events.handle_mouse_press(float(x), float(y))

        def on_mouse_release(self, x, y, button, modifiers):
            # Only handle left mouse button
            if button == pyglet.window.mouse.LEFT:
                input_events.handle_mouse_release(float(x), float(y))

        def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
            # Only handle left mouse button drag
            if buttons & pyglet.window.mouse.LEFT:
                input_events.handle_mouse_drag(float(x), float(y))

        def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
            # Forward scroll events for camera zoom
            input_events.handle_mouse_scroll(float(scroll_x), float(scroll_y))

    mouse_handler = MouseHandler()

    # Access the underlying pyglet window and register the handlers
    for w in pyglet.app.windows:
        w.push_handlers(keyboard_handler)
        w.push_handlers(mouse_handler)

    # Activate window to ensure it gets focus on macOS
    if pyglet_window:
        pyglet_window.activate()

    # Set initial cursor visibility based on fixture mode
    update_cursor_visibility()

    # Subscribe to fixture mode changes to update cursor
    state.events.on_show_fixture_mode_change += (
        lambda show_fixture: update_cursor_visibility()
    )

    frame_counter = 0

    # Schedule web server request handling if enabled
    if web_server:
        import select

        def handle_web_requests(dt):
            """Handle web server requests in the main thread"""
            try:
                # Check if there are pending requests (non-blocking)
                ready = select.select([web_server.socket], [], [], 0.0)
                if ready[0]:
                    web_server.handle_request()
            except Exception as e:
                # Silently ignore errors to avoid spamming console
                pass

        # Schedule to check for web requests every 50ms
        pyglet.clock.schedule_interval(handle_web_requests, 0.05)

    # Track window size for resize detection
    last_window_size = window.size
    # VJ preview push cadence: ~5 fps. The actual HTTP upload is async on a
    # background thread inside `RuntimeVenueClient`, so this interval only
    # governs how often we pay the GPU readback + JPEG encode cost on the GL
    # thread. 0.2s feels live in the browser without saturating the network.
    _VJ_PREVIEW_PUSH_INTERVAL_SEC = 0.2
    last_vj_preview_push_mono = -1000.0

    while not window.is_closing:
        current_time = time.perf_counter()

        # Check if we should take screenshot
        if screenshot_mode and screenshot_time and current_time >= screenshot_time:
            print("\n📸 Capturing screenshot...")
            from PIL import Image

            window_w, window_h = window.size
            ctx.screen.use()
            screen_data = ctx.screen.read()
            screen_img = Image.frombuffer(
                "RGB", (window_w, window_h), screen_data, "raw", "RGB", 0, 1
            )
            screen_img = screen_img.transpose(Image.FLIP_TOP_BOTTOM)
            screen_img.save("test_output/screenshot.png")
            print(f"✅ Saved screenshot: {window_w}x{window_h}")
            print("🛑 Exiting after screenshot")
            break

        # Drain venue/runtime queues every frame. Do not tie this to audio frames: when the
        # analyzer returns None (no mic, silence, or startup), queued WebSocket snapshots would
        # otherwise never apply and the 3D room would stay on Room3DRenderer defaults (10×10).
        state.process_gui_updates()

        # Update audio at intervals
        if time.perf_counter() - last_audio_update >= audio_update_interval:
            frame = audio_analyzer.analyze_audio()
            if frame:
                director.step(frame)
                director.render(dmx_ref["controller"])
                if runtime_client is not None:
                    runtime_client.maybe_push_fixture_runtime_state()
            last_audio_update = time.perf_counter()

        # Get VJ frame data
        frame_data, scheme_data = vj_director.get_latest_frame_data()
        if not frame_data:
            frame_data = Frame({signal: 0.0 for signal in FrameSignal})
            scheme_data = director.scheme.render()

        # Get current window size
        window_width, window_height = window.size

        # Check if window was resized and update renderers
        if (window_width, window_height) != last_window_size:
            fixture_renderer.resize(ctx, window_width, window_height)
            last_window_size = (window_width, window_height)

        # We want the web preview to keep streaming VJ frames regardless of
        # which view the desktop operator is currently looking at (fixture
        # scene, DMX heatmap, or VJ). So on every frame where a preview push
        # is due, we render the VJ pipeline into its offscreen FBO for the
        # upload even if the screen is showing something else. When the
        # desktop *is* in VJ mode we render VJ unconditionally and reuse that
        # FBO for both the on-screen blit and the web preview.
        now_mono = time.perf_counter()
        vj_preview_due = (
            runtime_client is not None
            and (now_mono - last_vj_preview_push_mono) >= _VJ_PREVIEW_PUSH_INTERVAL_SEC
        )
        vj_preview_fbo = None

        if state.editor_display_mode == EditorDisplayMode.FIXTURE_SCENE:
            rendered_fbo = fixture_renderer.render(frame_data, scheme_data, ctx)
            if vj_preview_due:
                vj_preview_fbo = vj_director.render(ctx, frame_data, scheme_data)
        elif state.editor_display_mode == EditorDisplayMode.VJ:
            rendered_fbo = vj_director.render(ctx, frame_data, scheme_data)
            vj_preview_fbo = rendered_fbo
        else:
            snap = dmx_ref["controller"].snapshot_universe(Universe.default)
            rendered_fbo = dmx_heatmap_renderer.render(
                ctx, snap, window_width, window_height
            )
            if vj_preview_due:
                vj_preview_fbo = vj_director.render(ctx, frame_data, scheme_data)

        # Bind the window's default framebuffer (screen) and render to it
        ctx.screen.use()
        ctx.clear(0.0, 0.0, 0.0)

        # IMPORTANT: Set viewport to full window size before rendering
        ctx.viewport = (0, 0, window_width, window_height)

        if rendered_fbo and rendered_fbo.color_attachments:
            try:
                source_texture = rendered_fbo.color_attachments[0]
                source_width, source_height = source_texture.size

                # Bind texture and set uniforms
                source_texture.use(0)
                display_shader["source_texture"] = 0
                display_shader["source_size"].value = (
                    float(source_width),
                    float(source_height),
                )
                display_shader["target_size"].value = (
                    float(window_width),
                    float(window_height),
                )
                display_shader["u_dmx_heatmap"] = (
                    1
                    if state.editor_display_mode == EditorDisplayMode.DMX_HEATMAP
                    else 0
                )

                # Render to screen with proper viewport
                display_quad.render(mgl.TRIANGLE_STRIP)
            except Exception as e:
                print(f"Error displaying to screen: {e}")

        if (
            runtime_client is not None
            and vj_preview_due
            and vj_preview_fbo is not None
            and vj_preview_fbo.color_attachments
        ):
            jpeg = _encode_texture_rgb_as_jpeg(vj_preview_fbo.color_attachments[0])
            if jpeg is not None:
                runtime_client.queue_vj_preview_jpeg(jpeg)
            # Advance the cadence timer whether or not encoding succeeded so a
            # pathological frame (e.g. zero-size texture) doesn't cause us to
            # hammer the encoder every tick.
            last_vj_preview_push_mono = now_mono

        # Restore viewport before rendering overlay (imgui manages its own viewport)
        ctx.viewport = (0, 0, window_width, window_height)

        # Render overlay UI
        overlay.render()

        # Swap buffers and poll events
        window.swap_buffers()
        window.ctx.finish()  # Wait for rendering to complete

        # Debug frame capture mode (after swap so we see what's displayed)
        if debug_frame_mode:
            frame_counter += 1
            if frame_counter == 20:
                print("\n📸 Capturing frame 20...")
                # Save what VJ rendered
                if rendered_fbo and rendered_fbo.color_attachments:
                    from PIL import Image

                    tex = rendered_fbo.color_attachments[0]
                    w, h = tex.size
                    data = tex.read()
                    img = Image.frombuffer("RGB", (w, h), data, "raw", "RGB", 0, 1)
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)
                    img.save("test_output/debug_vj_render.png")
                    print(f"✅ Saved VJ render: {w}x{h}")

                    # Check texture data
                    pixels = np.frombuffer(data, dtype=np.uint8).reshape(h, w, 3)
                    print(
                        f"  VJ texture brightness: min={pixels.min()}, max={pixels.max()}, mean={pixels.mean():.1f}"
                    )

                # Read back buffer (what was just displayed)
                try:
                    window_w, window_h = window.size
                    ctx.screen.use()
                    screen_data = ctx.screen.read()
                    screen_img = Image.frombuffer(
                        "RGB", (window_w, window_h), screen_data, "raw", "RGB", 0, 1
                    )
                    screen_img = screen_img.transpose(Image.FLIP_TOP_BOTTOM)
                    screen_img.save("test_output/debug_window_screen.png")
                    print(f"✅ Saved window screen: {window_w}x{window_h}")

                    # Check screen data
                    screen_pixels = np.frombuffer(screen_data, dtype=np.uint8).reshape(
                        window_h, window_w, 3
                    )

                    print(
                        f"  Screen brightness: min={screen_pixels.min()}, max={screen_pixels.max()}, mean={screen_pixels.mean():.1f}"
                    )
                except Exception as e:
                    print(f"⚠️  Could not capture window screen: {e}")

                print("🛑 Exiting after frame 20 capture")
                break

        # Process window events (keyboard, mouse, etc)
        for w in pyglet.app.windows:
            w.dispatch_events()

    # Cleanup. Runtime state (mode/vj_mode/venue) is persisted by parrot_cloud's
    # control_state DB, so there's nothing to write locally on shutdown.
    print("\n👋 Shutting down...")
    audio_analyzer.cleanup()
    vj_director.cleanup()

    # Cleanup fixture renderer
    fixture_renderer.exit()

    # Shutdown overlay before destroying window to avoid OpenGL context issues
    overlay.shutdown()

    # Destroy window last to ensure OpenGL context is still valid during cleanup
    window.destroy()
