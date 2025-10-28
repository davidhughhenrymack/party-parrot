#!/usr/bin/env python3

import pytest
import moderngl as mgl
import tempfile
import shutil
import os

from parrot.vj.nodes.fixture_visualization import FixtureVisualization
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.state import State
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.patch_bay import venues
from parrot.vj.vj_director import VJDirector


class TestDMXFixtureRenderer:
    """Test DMXFixtureRenderer with venue changes"""

    def setup_method(self):
        """Set up test fixtures before each test method - use temp dir to avoid writing to state.json"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up after each test method"""
        os.chdir(self.original_cwd)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @pytest.fixture
    def gl_context(self):
        """Create a real OpenGL context for testing"""
        try:
            context = mgl.create_context(standalone=True, backend="egl")
            yield context
        except Exception:
            try:
                context = mgl.create_context(standalone=True)
                yield context
            except Exception as e:
                raise RuntimeError(f"OpenGL context creation failed: {e}")

    @pytest.fixture
    def state(self):
        """Create a state object"""
        return State()

    @pytest.fixture
    def position_manager(self, state):
        """Create a position manager"""
        return FixturePositionManager(state)

    @pytest.fixture
    def vj_director(self, state, gl_context):
        """Create a VJ director"""
        director = VJDirector(state)
        director.setup(gl_context)
        return director

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_fixture_renderer_initial_load(
        self, gl_context, state, position_manager, vj_director
    ):
        """Test that fixtures are loaded on init"""
        renderer = FixtureVisualization(
            state=state,
            position_manager=position_manager,
            vj_director=vj_director,
            width=256,
            height=256,
        )

        # Fixtures should be stored, renderers created after first render
        assert hasattr(renderer, "_fixtures")
        assert len(renderer._fixtures) > 0

    def test_venue_change_recreates_renderers(
        self, gl_context, state, position_manager, vj_director, color_scheme
    ):
        """Test that changing venue recreates renderers properly"""
        # Set initial venue to dmack
        state.set_venue(venues.dmack)

        renderer = FixtureVisualization(
            state=state,
            position_manager=position_manager,
            vj_director=vj_director,
            width=256,
            height=256,
        )

        # Do initial render to create renderers
        frame = Frame(values={})
        fb = renderer.render(frame, color_scheme, gl_context)

        initial_fixture_count = len(renderer.renderers)
        assert initial_fixture_count > 0, "Should have renderers after first render"

        # Change venue to mtn_lotus (has different fixtures)
        state.set_venue(venues.mtn_lotus)

        # Verify fixtures were reloaded
        assert hasattr(renderer, "_fixtures")
        new_fixture_count = len(renderer._fixtures)

        # Render again - this should recreate renderers
        fb = renderer.render(frame, color_scheme, gl_context)

        # Check that renderers were recreated
        assert (
            len(renderer.renderers) > 0
        ), "Renderers should be recreated after venue change"
        assert (
            len(renderer.renderers) == new_fixture_count
        ), "Renderer count should match fixture count"

    def test_fixture_renderer_resize(
        self, gl_context, state, position_manager, vj_director, color_scheme
    ):
        """Test that renderer properly resizes its framebuffers"""
        renderer = FixtureVisualization(
            state=state,
            position_manager=position_manager,
            vj_director=vj_director,
            width=1920,
            height=1080,
        )
        renderer.enter(gl_context)

        frame = Frame(values={})

        # Initial render
        fb = renderer.render(frame, color_scheme, gl_context)
        assert fb.width == 1920, "Initial width should be 1920"
        assert fb.height == 1080, "Initial height should be 1080"

        # Resize to larger - just verify framebuffers are resized
        renderer.resize(gl_context, 2560, 1440)
        assert renderer.width == 2560, "Renderer width should be 2560"
        assert renderer.height == 1440, "Renderer height should be 1440"
        assert renderer.framebuffer.width == 2560, "Framebuffer width should be 2560"
        assert renderer.framebuffer.height == 1440, "Framebuffer height should be 1440"

        # Resize to smaller
        renderer.resize(gl_context, 1280, 720)
        assert renderer.width == 1280, "Renderer width should be 1280"
        assert renderer.height == 720, "Renderer height should be 720"
        assert renderer.framebuffer.width == 1280, "Framebuffer width should be 1280"
        assert renderer.framebuffer.height == 720, "Framebuffer height should be 720"

    def test_fixture_renderer_with_vj_billboard(
        self, gl_context, state, position_manager, vj_director, color_scheme
    ):
        """Test that renderer renders VJ content on billboard via vj_director"""
        renderer = FixtureVisualization(
            state=state,
            position_manager=position_manager,
            vj_director=vj_director,
            width=1920,
            height=1080,
        )
        renderer.enter(gl_context)

        frame = Frame(values={})

        # Render - VJ director will be called internally to get VJ texture
        fb = renderer.render(frame, color_scheme, gl_context)
        assert fb.width == 1920, "Should render at expected resolution"
        assert fb.height == 1080, "Should render at expected resolution"

    def test_multiple_venue_changes(
        self, gl_context, state, position_manager, vj_director, color_scheme
    ):
        """Test multiple venue changes work correctly"""
        # Set initial venue
        state.set_venue(venues.dmack)

        renderer = FixtureVisualization(
            state=state,
            position_manager=position_manager,
            vj_director=vj_director,
            width=256,
            height=256,
        )

        frame = Frame(values={})

        # Initial render
        fb = renderer.render(frame, color_scheme, gl_context)
        count_1 = len(renderer.renderers)
        assert count_1 > 0

        # Change to mtn_lotus
        state.set_venue(venues.mtn_lotus)
        fb = renderer.render(frame, color_scheme, gl_context)
        count_2 = len(renderer.renderers)
        assert count_2 > 0

        # Change to crux_test
        state.set_venue(venues.crux_test)
        fb = renderer.render(frame, color_scheme, gl_context)
        count_3 = len(renderer.renderers)
        assert count_3 > 0

        # Change back to dmack
        state.set_venue(venues.dmack)
        fb = renderer.render(frame, color_scheme, gl_context)
        count_4 = len(renderer.renderers)
        assert count_4 > 0
        assert (
            count_4 == count_1
        ), "Should have same fixture count when returning to initial venue"
