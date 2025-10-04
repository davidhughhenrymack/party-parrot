#!/usr/bin/env python3

import json
import os
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase
from parrot.patch_bay import venue_patches
from parrot.fixtures.base import FixtureBase, FixtureGroup
from parrot.vj.renderers.factory import create_renderer
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.room_3d import Room3DRenderer
from parrot.state import State
from typing import Optional
import moderngl as mgl


@beartype
class DMXFixtureRenderer(GenerativeEffectBase):
    """
    Renders DMX fixtures on screen using OpenGL, similar to the legacy GUI.
    Each fixture renderer draws itself based on current DMX state.
    Shows fixture positions, colors, beams, etc in real-time.
    """

    def __init__(
        self,
        state: State,
        width: int = 1920,
        height: int = 1080,
        canvas_width: int = 1200,
        canvas_height: int = 1200,
    ):
        """
        Args:
            state: Global state object (provides current venue)
            width: Width of the effect (render resolution)
            height: Height of the effect (render resolution)
            canvas_width: Width of the fixture canvas (legacy GUI coordinate space)
            canvas_height: Height of the fixture canvas (legacy GUI coordinate space)
        """
        super().__init__(width, height)
        self.state = state
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Subscribe to venue changes to reload fixtures
        self.state.events.on_venue_change += self._on_venue_change

        # Load fixtures and create renderers for each
        self.renderers: list[FixtureRenderer] = []
        self.room_renderer: Optional[Room3DRenderer] = None
        self.depth_texture: Optional[mgl.Texture] = None

        self._load_fixtures()
        self._load_positions()

    def _setup_gl_resources(
        self, context: mgl.Context, width: int = 1920, height: int = 1080
    ):
        """Override to add depth buffer for 3D rendering"""
        if not self.texture:
            self.texture = context.texture((width, height), 3)  # RGB texture
            self.depth_texture = context.depth_texture((width, height))
            self.framebuffer = context.framebuffer(
                color_attachments=[self.texture], depth_attachment=self.depth_texture
            )

        if not self.shader_program:
            vertex_shader = self._get_vertex_shader()
            fragment_shader = self._get_fragment_shader()
            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            self.quad_vao = self._create_fullscreen_quad(context)

    def _on_venue_change(self, venue):
        """Reload fixtures when venue changes"""
        self._load_fixtures()
        self._load_positions()

    def _load_fixtures(self):
        """Load fixtures from the current venue's patch bay, create renderers, and flatten groups"""
        fixtures = []
        print(f"loading fixtures for {self.state.venue}")
        # Get fixtures from current venue in state (live fixtures)
        for item in venue_patches[self.state.venue]:
            if isinstance(item, FixtureGroup):
                # Add all fixtures from the group
                for fixture in item.fixtures:
                    fixtures.append(fixture)
            else:
                # Individual fixture
                fixtures.append(item)

        # Store fixtures temporarily - will create renderers after room_renderer is initialized
        self._fixtures = fixtures
        self.renderers = []

    def _load_positions(self):
        """Load fixture positions from JSON file (legacy GUI format)"""
        filename = f"{self.state.venue.name}_gui.json"

        if not os.path.exists(filename):
            # Use default positions if no saved file
            self._generate_default_positions()
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)

            # Load positions from saved data
            for renderer in self.renderers:
                if renderer.fixture.id in data:
                    pos_data = data[renderer.fixture.id]
                    x = float(pos_data.get("x", 0))
                    y = float(pos_data.get("y", 0))
                    z = float(pos_data.get("z", 3))  # Default height of 3
                    renderer.set_position(x, y, z)
                else:
                    # Fixture not in saved data, use default
                    self._set_default_position(renderer)
        except Exception as e:
            print(f"Error loading fixture positions: {e}")
            self._generate_default_positions()

    def _generate_default_positions(self):
        """Generate default positions for fixtures (grid layout)"""
        fixture_margin = 10.0
        x = fixture_margin
        y = fixture_margin
        max_row_height = 0.0

        for renderer in self.renderers:
            width, height = renderer.size

            # Check if we need to wrap to next row
            if x + width > self.canvas_width - fixture_margin:
                x = fixture_margin
                y += max_row_height + fixture_margin
                max_row_height = 0.0

            renderer.set_position(x, y)

            x += width + fixture_margin
            max_row_height = max(max_row_height, height)

    def _set_default_position(self, renderer: FixtureRenderer):
        """Set default position for a single renderer"""
        # Just place at origin for now
        renderer.set_position(10.0, 10.0)

    def generate(self, vibe: Vibe):
        """Configure renderer based on vibe"""
        # This renderer doesn't change behavior based on vibe
        # It always shows the fixtures as they are
        pass

    def print_self(self) -> str:
        return format_node_status(
            self.__class__.__name__,
            emoji="💡",
            num_fixtures=len(self.renderers),
        )

    def _get_fragment_shader(self) -> str:
        """Simple passthrough shader - actual rendering is done by individual fixture renderers"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        
        void main() {
            // Just black - fixtures render themselves
            color = vec3(0.0, 0.0, 0.0);
        }
        """

    def render(self, frame: Frame, scheme: ColorScheme, context):
        """Override base render to use 3D room rendering"""
        if not self.framebuffer:
            self._setup_gl_resources(context, self.width, self.height)

        # Initialize room renderer if needed
        if self.room_renderer is None:
            self.room_renderer = Room3DRenderer(context, self.width, self.height)

            # Now create renderers with room_renderer
            if hasattr(self, "_fixtures"):
                self.renderers = [
                    create_renderer(fixture, self.room_renderer)
                    for fixture in self._fixtures
                ]
                # Load positions for the newly created renderers
                self._load_positions()

        # Update camera rotation based on frame time
        self.room_renderer.update_camera(frame.time)

        self.framebuffer.use()

        # Clear both color and depth buffers for proper 3D rendering
        context.clear(0.0, 0.0, 0.0)
        if self.framebuffer.depth_attachment:
            context.clear(depth=1.0)

        # Enable depth testing for 3D rendering with proper depth sorting
        context.enable(context.DEPTH_TEST)
        context.depth_func = "<"  # Standard OpenGL LESS comparison

        # Render floor grid
        self.room_renderer.render_floor()

        # Render each fixture in 3D (all renderers are now 3D)
        canvas_size = (float(self.canvas_width), float(self.canvas_height))
        for renderer in self.renderers:
            renderer.render(context, canvas_size, frame)

        context.disable(context.DEPTH_TEST)

        return self.framebuffer

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Not used - rendering is done in custom render() method"""
        pass
