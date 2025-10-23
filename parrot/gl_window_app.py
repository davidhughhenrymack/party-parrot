#!/usr/bin/env python3

import time
import moderngl_window as mglw
import moderngl as mgl
from beartype import beartype
import numpy as np

from parrot.audio.audio_analyzer import AudioAnalyzer
from parrot.director.director import Director
from parrot.director.mode import Mode
from parrot.director.frame import Frame, FrameSignal
from parrot.state import State
from parrot.utils.dmx_utils import get_controller
from parrot.vj.vj_director import VJDirector
from parrot.director.signal_states import SignalStates
from parrot.utils.overlay_ui import OverlayUI
from parrot.keyboard_handler import KeyboardHandler
from parrot.utils.input_events import InputEvents
from parrot.director.themes import themes
from parrot.vj.vj_mode import VJMode
from parrot.patch_bay import venues


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
    signal_states = SignalStates()

    # Override mode if specified via args, otherwise use loaded/default mode
    if getattr(args, "rave", False):
        state.set_mode(Mode.rave)
        print("🎉 Starting in RAVE mode (from command line)")
    else:
        # Use the mode loaded from state.json or default
        print(f"🎉 Starting in {state.mode.name.upper()} mode")

    # Initialize audio analyzer
    audio_analyzer = AudioAnalyzer(signal_states)

    # Initialize VJ system
    vj_director = VJDirector(state)
    vj_director.setup(ctx)

    # Initialize director first (creates position manager)
    director = Director(state, vj_director)

    # Initialize fixture renderer (uses director's position manager)
    from parrot.vj.nodes.dmx_fixture_renderer import DMXFixtureRenderer

    fixture_renderer = DMXFixtureRenderer(
        state=state,
        position_manager=director.position_manager,
        width=1920,
        height=1080,
    )
    fixture_renderer.enter(ctx)

    # Initialize DMX with venue-specific configuration
    dmx = get_controller(state.venue)

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
        
        // Flip Y coordinate (OpenGL texture origin is bottom-left)
        vec2 flipped_uv = vec2(uv.x, 1.0 - uv.y);
        
        vec2 centered = (flipped_uv - 0.5);
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

        web_server = start_web_server(
            state,
            director=director,
            port=getattr(args, "web_port", 4040),
            threaded=False,  # Run in main thread
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
        print("🖥️  Starting with overlay visible")

    # Setup native macOS menu bar for settings
    def create_settings_menus():
        """Create native macOS menu bar with mode/theme/venue selection using PyObjC"""
        import sys

        if sys.platform != "darwin":
            print("⚠️  Menu bar only supported on macOS")
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
                    self.modes = list(Mode)
                    self.vj_modes = list(VJMode)
                    self.venues_list = list(venues)
                    self.themes = themes
                    # Store menu items for updating checkmarks
                    self.mode_items = []
                    self.vj_mode_items = []
                    self.venue_items = []
                    self.theme_items = []
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

            # Create Mode menu
            mode_menu = NSMenu.alloc().initWithTitle_("Mode")
            for idx, mode in enumerate(Mode):
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
                display_name = vj_mode.value.replace("_", " ").title()
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
            for idx, venue in enumerate(venues):
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
            print("⚠️  PyObjC not available, menu bar creation skipped")
            print("   Settings available via overlay (ENTER key)")
        except Exception as e:
            print(f"⚠️  Could not create menu bar: {e}")
            print(f"   Error details: {type(e).__name__}")
            print("   Settings still available via overlay (ENTER key)")

    create_settings_menus()

    # Screenshot mode
    screenshot_mode = getattr(args, "screenshot", False)
    screenshot_time = None
    if screenshot_mode:
        screenshot_time = time.perf_counter() + 0.5
        print("📸 Screenshot mode: will capture after 0.5s and exit")

    # Override fixture mode if specified via args, otherwise use loaded/default
    if getattr(args, "fixture_mode", False):
        state.set_show_fixture_mode(True)
        print("🔧 Starting in fixture mode (from command line)")
    elif state.show_fixture_mode:
        print("🔧 Starting in fixture mode (from saved state)")
    else:
        print("📺 Starting in VJ mode")

    def toggle_fixture_mode():
        state.set_show_fixture_mode(not state.show_fixture_mode)
        mode_str = "fixture" if state.show_fixture_mode else "VJ"
        print(f"🔀 Toggled to {mode_str} mode")

    # Setup keyboard handler on the underlying pyglet window
    keyboard_handler = KeyboardHandler(
        director,
        overlay,
        signal_states,
        state,
        show_fixture_mode_callback=toggle_fixture_mode,
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

    print("⌨️  Keyboard shortcuts:")
    print(
        "   SPACE: Regenerate all  |  S: Full shift lighting only  |  O: Full shift VJ only"
    )
    print("   ENTER: Toggle overlay  |  \\: Toggle fixture/VJ mode")
    print(
        "   C/D: Navigate lighting modes (C=up towards rave, D=down towards blackout)"
    )
    print("   E/F: Navigate VJ modes (E=down towards blackout, F=up towards full_rave)")
    print("   LEFT/RIGHT: Navigate VJ modes (alternative)")
    print("   I: Small Blinder  |  G: Big Blinder  |  H: Strobe  |  J: Pulse")
    print("🖱️  Mouse: Drag to rotate/tilt camera  |  Scroll to zoom (in fixture mode)")

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
        print("🌐 Web server integrated into main thread")

    # Track time for delta time calculations
    last_frame_time = time.perf_counter()

    while not window.is_closing:
        current_time = time.perf_counter()
        dt = current_time - last_frame_time
        last_frame_time = current_time

        # Update manual dimmer fade (progressive fade when M/K held)
        keyboard_handler.update_manual_dimmer(dt)

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

        # Update audio at intervals
        if time.perf_counter() - last_audio_update >= audio_update_interval:
            frame = audio_analyzer.analyze_audio()
            if frame:
                state.process_gui_updates()
                director.step(frame)
                director.render(dmx)
            last_audio_update = time.perf_counter()

        # Get VJ frame data
        frame_data, scheme_data = vj_director.get_latest_frame_data()
        if not frame_data:
            frame_data = Frame({signal: 0.0 for signal in FrameSignal})
            scheme_data = director.scheme.render()

        # Get current window size
        window_width, window_height = window.size

        # Render based on mode (fixture or VJ)
        if state.show_fixture_mode:
            rendered_fbo = fixture_renderer.render(frame_data, scheme_data, ctx)
        else:
            rendered_fbo = vj_director.render(ctx, frame_data, scheme_data)

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

                # Render to screen with proper viewport
                display_quad.render(mgl.TRIANGLE_STRIP)
            except Exception as e:
                print(f"Error displaying to screen: {e}")

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

    # Cleanup
    print("\n👋 Shutting down...")
    state.save_state()
    audio_analyzer.cleanup()
    vj_director.cleanup()

    # Cleanup fixture renderer
    fixture_renderer.exit()

    # Shutdown overlay before destroying window to avoid OpenGL context issues
    overlay.shutdown()

    # Destroy window last to ensure OpenGL context is still valid during cleanup
    window.destroy()
