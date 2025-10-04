#!/usr/bin/env python3
"""Test 3D room rendering functionality"""

import pytest
import moderngl as mgl
import numpy as np
from PIL import Image
import os

from parrot.vj.nodes.dmx_fixture_renderer import DMXFixtureRenderer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import scheme_halloween
from parrot.patch_bay import venues
from parrot.state import State
from parrot.utils.colour import Color


class Test3DRoomRender:
    """Test 3D room rendering with fixtures as cubes"""

    @pytest.fixture
    def gl_context(self):
        """Create standalone GL context"""
        try:
            ctx = mgl.create_context(standalone=True, backend="egl")
            yield ctx
        except Exception:
            ctx = mgl.create_context(standalone=True)
            yield ctx
        finally:
            ctx.release()

    @pytest.fixture
    def state(self):
        """Create state with mtn lotus venue"""
        state = State()
        state.set_venue(venues.mtn_lotus)
        return state

    @pytest.fixture
    def renderer(self, state):
        """Create 3D DMX fixture renderer"""
        return DMXFixtureRenderer(
            state=state,
            width=1920,
            height=1080,
            canvas_width=1200,
            canvas_height=1200,
        )

    def test_3d_room_renders_successfully(self, gl_context, renderer):
        """Test that 3D room rendering works without errors"""
        # Setup renderer
        renderer.enter(gl_context)

        # Set some fixtures to be visible
        for i, fixture_renderer in enumerate(renderer.renderers[:3]):
            try:
                fixture = fixture_renderer.fixture
                fixture.set_dimmer(255)
                if hasattr(fixture, "set_color"):
                    colors = [Color("red"), Color("blue"), Color("green")]
                    fixture.set_color(colors[i % len(colors)])
            except Exception:
                pass  # Some fixtures might not support all operations

        # Create test frame
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.6,
            }
        )
        scheme = scheme_halloween[0]

        # Render should not raise exceptions
        fbo = renderer.render(frame, scheme, gl_context)
        assert fbo is not None

        # Cleanup
        renderer.exit()

    def test_3d_room_saves_png(self, gl_context, renderer):
        """Test that 3D room rendering can save to PNG"""
        # Setup renderer
        renderer.enter(gl_context)

        # Set some fixtures to be visible
        for i, fixture_renderer in enumerate(renderer.renderers[:5]):
            try:
                fixture = fixture_renderer.fixture
                fixture.set_dimmer(255)
                if hasattr(fixture, "set_color"):
                    colors = [
                        Color("red"),
                        Color("blue"),
                        Color("green"),
                        Color("yellow"),
                        Color("purple"),
                    ]
                    fixture.set_color(colors[i % len(colors)])
            except Exception:
                pass

        # Create test frame
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.6,
                FrameSignal.strobe: 0.3,
            }
        )
        scheme = scheme_halloween[0]

        # Render
        fbo = renderer.render(frame, scheme, gl_context)

        # Read pixels and save to PNG
        texture = fbo.color_attachments[0]
        data = texture.read()
        pixels = np.frombuffer(data, dtype=np.uint8).reshape((1080, 1920, 3))

        # Flip vertically (OpenGL coordinates)
        pixels = np.flipud(pixels)

        # Save to PNG
        os.makedirs("test_output", exist_ok=True)
        img = Image.fromarray(pixels, mode="RGB")
        img.save("test_output/mtn_lotus_3d_room_test.png")

        # Verify file was created
        assert os.path.exists("test_output/mtn_lotus_3d_room_test.png")

        # Cleanup
        renderer.exit()

    def test_room_renderer_has_floor_grid(self, gl_context, renderer):
        """Test that room renderer creates floor grid geometry"""
        renderer.enter(gl_context)

        # Create a simple frame to trigger room renderer initialization
        frame = Frame({})
        scheme = scheme_halloween[0]

        # This will initialize the room renderer
        fbo = renderer.render(frame, scheme, gl_context)

        # Room renderer should now be initialized
        assert renderer.room_renderer is not None

        # Should have floor geometry
        assert hasattr(renderer.room_renderer, "floor_vertices")
        assert hasattr(renderer.room_renderer, "floor_colors")
        assert len(renderer.room_renderer.floor_vertices) > 0

        renderer.exit()

    def test_fixture_positions_loaded(self, gl_context, renderer):
        """Test that fixture positions are loaded from JSON"""
        renderer.enter(gl_context)

        # Render once to initialize renderers
        frame = Frame({})
        scheme = scheme_halloween[0]
        fbo = renderer.render(frame, scheme, gl_context)

        # Should have loaded fixtures
        assert len(renderer.renderers) > 0

        # Check that positions are set (not all at origin)
        positions = [r.position for r in renderer.renderers]
        unique_positions = set(positions)

        # Should have some variety in positions
        assert len(unique_positions) > 1

        renderer.exit()

    def test_camera_rotation(self, gl_context, renderer):
        """Test that camera rotates around the room"""
        renderer.enter(gl_context)

        # Set some fixtures to be visible
        for i, fixture_renderer in enumerate(renderer.renderers[:3]):
            try:
                fixture = fixture_renderer.fixture
                fixture.set_dimmer(255)
                if hasattr(fixture, "set_color"):
                    fixture.set_color(Color("red"))
            except Exception:
                pass

        scheme = scheme_halloween[0]

        # Render at different times
        times = [0.0, 5.0, 10.0]
        frames_data = []

        for time in times:
            frame = Frame({FrameSignal.freq_low: 0.8})
            frame.time = time

            fbo = renderer.render(frame, scheme, gl_context)
            data = fbo.color_attachments[0].read()
            frames_data.append(data)

        # Verify that frames are different (camera rotated)
        # Compare first and last frame
        assert frames_data[0] != frames_data[-1], "Camera should rotate between frames"

        # Verify room renderer has updated camera angle
        assert renderer.room_renderer is not None
        assert renderer.room_renderer.camera_angle != 0.0

        renderer.exit()

    def test_coordinate_mapping(self, gl_context, renderer):
        """Test that 2D fixture coordinates map correctly to 3D room space"""
        renderer.enter(gl_context)

        # Render once to initialize room_renderer
        frame = Frame({})
        scheme = scheme_halloween[0]
        fbo = renderer.render(frame, scheme, gl_context)

        # Test coordinate mapping for [0-500] range
        room_renderer = renderer.room_renderer
        assert room_renderer is not None

        # Test corners of the [0-500] space
        # Bottom-left: (0, 0) -> should map to (-5, 0, -5)
        x, y, z = room_renderer.convert_2d_to_3d(0.0, 0.0, 500.0, 500.0)
        assert abs(x - (-5.0)) < 0.01
        assert abs(y - 0.0) < 0.01
        assert abs(z - (-5.0)) < 0.01

        # Top-right: (500, 500) -> should map to (5, 0, 5)
        x, y, z = room_renderer.convert_2d_to_3d(500.0, 500.0, 500.0, 500.0)
        assert abs(x - 5.0) < 0.01
        assert abs(y - 0.0) < 0.01
        assert abs(z - 5.0) < 0.01

        # Center: (250, 250) -> should map to (0, 0, 0)
        x, y, z = room_renderer.convert_2d_to_3d(250.0, 250.0, 500.0, 500.0)
        assert abs(x - 0.0) < 0.01
        assert abs(y - 0.0) < 0.01
        assert abs(z - 0.0) < 0.01

        renderer.exit()

    def test_dark_fixtures_remain_visible(self, gl_context, renderer):
        """Test that fixtures remain visible even when dark (dimmer=0)"""
        renderer.enter(gl_context)

        # Set some fixtures to dark (dimmer=0)
        for i, fixture_renderer in enumerate(renderer.renderers[:3]):
            try:
                fixture = fixture_renderer.fixture
                fixture.set_dimmer(0)  # Fully dark
            except Exception:
                pass

        scheme = scheme_halloween[0]
        frame = Frame({})

        # Render should succeed without errors
        fbo = renderer.render(frame, scheme, gl_context)
        assert fbo is not None

        # Read pixels to verify something was rendered
        data = fbo.color_attachments[0].read()
        pixels = np.frombuffer(data, dtype=np.uint8)

        # Verify that there are some non-black pixels (dark fixtures + floor grid)
        # Even dark fixtures should render as dim gray (0.1 brightness = 25/255)
        non_black_pixels = np.sum(pixels > 0)
        assert non_black_pixels > 0, "Dark fixtures should still be visible"

        renderer.exit()
