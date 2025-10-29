#!/usr/bin/env python3

from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase
from parrot.patch_bay import venue_patches, get_manual_group
from parrot.fixtures.base import FixtureBase, FixtureGroup
from parrot.vj.renderers.factory import create_renderer
from parrot.vj.renderers.base import (
    FixtureRenderer,
    quaternion_from_axis_angle,
    quaternion_rotate_vector,
)
from parrot.vj.renderers.room_3d import Room3DRenderer
from parrot.vj.renderers.motionstrip import MotionstripRenderer
from parrot.vj.renderers.laser import LaserRenderer
from parrot.state import State
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.vj.shaders import kawase_blur, composite
from parrot.vj.vj_director import VJDirector
from typing import Optional
import moderngl as mgl
import numpy as np
import math


@beartype
class FixtureVisualization(GenerativeEffectBase):
    """
    Renders DMX fixtures on screen using OpenGL, similar to the legacy GUI.
    Each fixture renderer draws itself based on current DMX state.
    Shows fixture positions, colors, beams, etc in real-time.
    """

    def __init__(
        self,
        state: State,
        position_manager: FixturePositionManager,
        vj_director: VJDirector,
        width: int = 1920,
        height: int = 1080,
        canvas_width: int = 1200,
        canvas_height: int = 1200,
    ):
        """
        Args:
            state: Global state object (provides current venue)
            position_manager: Manager for fixture positions (shared with director)
            vj_director: VJ director for rendering VJ content on billboard
            width: Width of the effect (render resolution)
            height: Height of the effect (render resolution)
            canvas_width: Width of the fixture canvas (legacy GUI coordinate space)
            canvas_height: Height of the fixture canvas (legacy GUI coordinate space)
        """
        super().__init__(width, height)
        self.state = state
        self.position_manager = position_manager
        self.vj_director = vj_director
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Subscribe to venue changes to reload fixtures
        self.state.events.on_venue_change += self._on_venue_change

        # Load fixtures and create renderers for each
        self.renderers: list[FixtureRenderer] = []
        self.room_renderer: Optional[Room3DRenderer] = None
        self.depth_texture: Optional[mgl.Texture] = None

        # Bloom effect parameters
        self.bloom_alpha = (
            4.0  # Bloom contribution (increased for visibility, emissive removed)
        )
        self.kawase_iterations = 5  # Number of blur passes

        # Additional framebuffers for multi-pass rendering
        self.opaque_texture: Optional[mgl.Texture] = None  # Keep opaque pass separate
        self.opaque_framebuffer: Optional[mgl.Framebuffer] = None
        self.emissive_framebuffer: Optional[mgl.Framebuffer] = None
        self.emissive_texture: Optional[mgl.Texture] = None
        self.bloom_framebuffer: Optional[mgl.Framebuffer] = None
        self.bloom_texture: Optional[mgl.Texture] = None
        self.bloom_temp_framebuffer: Optional[mgl.Framebuffer] = None
        self.bloom_temp_texture: Optional[mgl.Texture] = None

        # Shader programs for post-processing
        self.kawase_shader: Optional[mgl.Program] = None
        self.composite_shader: Optional[mgl.Program] = None

        self._load_fixtures()

    def _setup_gl_resources(
        self, context: mgl.Context, width: int = 1920, height: int = 1080
    ):
        """Override to add depth buffer for 3D rendering and bloom framebuffers"""
        if not self.texture:
            # Opaque framebuffer (Blinn-Phong geometry) - kept separate
            self.opaque_texture = context.texture((width, height), 3)
            self.depth_texture = context.depth_texture((width, height))
            self.opaque_framebuffer = context.framebuffer(
                color_attachments=[self.opaque_texture],
                depth_attachment=self.depth_texture,
            )

            # Main output framebuffer (final composite)
            self.texture = context.texture((width, height), 3)
            self.framebuffer = context.framebuffer(
                color_attachments=[self.texture], depth_attachment=self.depth_texture
            )

            # Emissive framebuffer (shares depth buffer for proper occlusion)
            self.emissive_texture = context.texture((width, height), 3)
            self.emissive_framebuffer = context.framebuffer(
                color_attachments=[self.emissive_texture],
                depth_attachment=self.depth_texture,  # Share depth from opaque pass
            )

            # Bloom framebuffers for ping-pong blur
            self.bloom_texture = context.texture((width, height), 3)
            self.bloom_framebuffer = context.framebuffer(
                color_attachments=[self.bloom_texture]
            )

            self.bloom_temp_texture = context.texture((width, height), 3)
            self.bloom_temp_framebuffer = context.framebuffer(
                color_attachments=[self.bloom_temp_texture]
            )

        if not self.shader_program:
            vertex_shader = self._get_vertex_shader()
            fragment_shader = self._get_fragment_shader()
            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.kawase_shader:
            # Kawase blur shader for bloom effect
            self.kawase_shader = context.program(
                vertex_shader=kawase_blur.get_vertex_shader(),
                fragment_shader=kawase_blur.get_fragment_shader(),
            )

        if not self.composite_shader:
            # Composite shader for final image
            self.composite_shader = context.program(
                vertex_shader=composite.get_vertex_shader(),
                fragment_shader=composite.get_fragment_shader(),
            )

        if not self.quad_vao:
            self.quad_vao = self._create_fullscreen_quad(context)
            # Create separate VAOs for kawase and composite shaders
            self.kawase_quad_vao = self._create_quad_for_shader(
                context, self.kawase_shader
            )
            self.composite_quad_vao = self._create_quad_for_shader(
                context, self.composite_shader
            )

    def _on_venue_change(self, venue):
        """Reload fixtures when venue changes (position manager handles positions)"""
        self._load_fixtures()

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

        # Also include manual fixtures (actor/performance lights)
        manual_group = get_manual_group(self.state.venue)
        if manual_group is not None:
            for fixture in manual_group.fixtures:
                fixtures.append(fixture)

        # Store fixtures temporarily - will create renderers after room_renderer is initialized
        self._fixtures = fixtures
        self.renderers = []

    def _apply_positions_to_renderers(self):
        """Apply positions from fixture objects to renderers (positions were set by position manager)"""
        for renderer in self.renderers:
            fixture = renderer.fixture
            # Get position from fixture (set by position manager)
            position = self.position_manager.get_fixture_position(fixture)
            if position:
                x, y, z = position
                renderer.set_position(x, y, z)

            # Get orientation from fixture
            orientation = self.position_manager.get_fixture_orientation(fixture)
            if orientation is not None:
                renderer.orientation = orientation

    def _collect_fixture_lights(
        self, frame: Frame
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float, float]]]:
        """Collect light data from all fixtures for dynamic lighting

        Returns:
            List of (position, color_rgba) tuples where:
            - position is (x, y, z) in world space
            - color_rgba is (r, g, b, intensity) in 0-1 range
        """
        lights = []
        canvas_size = (float(self.canvas_width), float(self.canvas_height))

        for renderer in self.renderers:
            # Special handling for motionstrip fixtures - each bulb is a separate light source
            if isinstance(renderer, MotionstripRenderer):
                lights.extend(
                    self._collect_motionstrip_lights(renderer, frame, canvas_size)
                )
                continue

            # Get effective dimmer (includes strobe effect)
            dimmer = renderer.get_effective_dimmer(frame)

            # Skip if light is off or very dim
            if dimmer < 0.01:
                continue

            # Get color (RGB 0-1)
            color = renderer.get_color()

            # Get 3D position in world space
            world_pos = renderer.get_3d_position(canvas_size)

            # Create light entry: position, (r, g, b, intensity)
            lights.append((world_pos, (color[0], color[1], color[2], dimmer)))

        return lights

    def _collect_motionstrip_lights(
        self,
        renderer: MotionstripRenderer,
        frame: Frame,
        canvas_size: tuple[float, float],
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float, float]]]:
        """Collect light data from each bulb in a motionstrip fixture

        Returns:
            List of (position, color_rgba) tuples for each bulb
        """
        lights = []
        fixture = renderer.fixture

        # Get fixture base position in world space
        fixture_world_pos = renderer.get_3d_position(canvas_size)

        # Calculate pan rotation (same logic as MotionstripRenderer)
        pan_rotation_deg = renderer._get_pan_rotation()
        pan_rotation_rad = math.radians(pan_rotation_deg)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quaternion = quaternion_from_axis_angle(x_axis, pan_rotation_rad)

        # Motionstrip geometry parameters (matching render_emissive)
        body_height = renderer.cube_size * 0.2
        body_depth = renderer.cube_size * 0.3
        bulb_spacing = 0.22
        num_bulbs = renderer._num_bulbs
        start_offset_x = -(num_bulbs - 1) * bulb_spacing / 2
        bulb_forward_distance = body_depth * 0.7

        # Get all bulbs from fixture
        bulbs = fixture.get_bulbs()

        for i, bulb in enumerate(bulbs):
            try:
                # Get bulb color
                bulb_color_obj = bulb.get_color()
                if hasattr(bulb_color_obj, "red"):
                    r, g, b = (
                        bulb_color_obj.red,
                        bulb_color_obj.green,
                        bulb_color_obj.blue,
                    )
                elif hasattr(bulb_color_obj, "r"):
                    r, g, b = (
                        bulb_color_obj.r / 255.0,
                        bulb_color_obj.g / 255.0,
                        bulb_color_obj.b / 255.0,
                    )
                else:
                    r, g, b = (1.0, 1.0, 1.0)

                # Get bulb dimmer
                bulb_dimmer = bulb.get_dimmer() / 255.0
                fixture_dimmer = renderer.get_dimmer()
                effective_intensity = bulb_dimmer * fixture_dimmer

                # Skip if bulb is off or very dim
                if effective_intensity < 0.01:
                    continue

                # Calculate bulb position in local space (matching render_emissive)
                bulb_x_local = start_offset_x + i * bulb_spacing
                bulb_y_local = body_height / 2
                bulb_z_local = bulb_forward_distance
                bulb_local_pos = np.array(
                    [bulb_x_local, bulb_y_local, bulb_z_local], dtype=np.float32
                )

                # Transform to world space:
                # 1. Apply pan rotation (around X-axis)
                # 2. Apply fixture orientation
                # 3. Add fixture world position

                # Apply pan rotation
                bulb_pos_rotated = quaternion_rotate_vector(
                    pan_quaternion, bulb_local_pos
                )

                # Apply fixture orientation
                bulb_pos_oriented = quaternion_rotate_vector(
                    renderer.orientation, bulb_pos_rotated
                )

                # Add fixture world position
                bulb_world_pos = (
                    fixture_world_pos[0] + bulb_pos_oriented[0],
                    fixture_world_pos[1] + bulb_pos_oriented[1],
                    fixture_world_pos[2] + bulb_pos_oriented[2],
                )

                # Create light entry: position, (r, g, b, intensity)
                lights.append((bulb_world_pos, (r, g, b, effective_intensity)))
            except Exception:
                pass  # Skip bulbs that can't be processed

        return lights

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

    def render(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: mgl.Context,
    ) -> mgl.Framebuffer:
        """Override base render to use 4-pass rendering with bloom

        Args:
            frame: Current frame data
            scheme: Color scheme
            context: OpenGL context

        Returns:
            Framebuffer containing the final composited render

        Note:
            Renders VJ content on a billboard by calling self.vj_director.render()
        """
        if not self.framebuffer:
            self._setup_gl_resources(context, self.width, self.height)

        # Render VJ content to get texture for billboard
        vj_fbo = self.vj_director.render(context, frame, scheme)
        vj_texture = (
            vj_fbo.color_attachments[0] if vj_fbo and vj_fbo.color_attachments else None
        )

        # Extract average color from VJ texture for global lighting and video wall light
        global_light_color = (0.15, 0.15, 0.15)  # Default dim white
        video_wall_color = None  # Will be (r, g, b, intensity) or None

        if vj_texture:
            try:
                # Read texture data and compute average
                raw_data = vj_texture.read()
                pixels = np.frombuffer(raw_data, dtype=np.uint8).reshape(
                    (vj_texture.height, vj_texture.width, 3)
                )
                # Downsample for performance (every 16th pixel)
                sampled = pixels[::16, ::16, :]
                avg_color = np.mean(sampled, axis=(0, 1)) / 255.0
                # Scale down for subtle lighting effect
                global_light_color = tuple(avg_color * 0.3)

                # Calculate video wall light (stronger than ambient)
                # Intensity based on brightness (luminance)
                brightness = (
                    0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]
                )
                video_wall_color = (
                    avg_color[0],
                    avg_color[1],
                    avg_color[2],
                    brightness,
                )
            except Exception:
                pass  # Fall back to default if reading fails

        # Initialize room renderer if needed
        if self.room_renderer is None:
            self.room_renderer = Room3DRenderer(
                context, self.width, self.height, show_floor=True
            )

        # Create or recreate renderers if fixtures changed (venue change)
        if hasattr(self, "_fixtures") and len(self.renderers) != len(self._fixtures):
            self.renderers = [
                create_renderer(fixture, self.room_renderer)
                for fixture in self._fixtures
            ]
            # Apply positions from fixtures (set by position manager) to renderers
            self._apply_positions_to_renderers()

        # Update camera rotation based on frame time
        self.room_renderer.update_camera(frame.time)

        # Set global lighting based on VJ content
        self.room_renderer.set_global_light_color(global_light_color)

        # Collect and set dynamic lights from fixtures
        fixture_lights = self._collect_fixture_lights(frame)

        # Add video wall as a light source if it's active
        if video_wall_color is not None:
            # Video wall position (center of billboard at back of room)
            billboard_height = 6.0
            video_wall_pos = (0.0, billboard_height / 2.0, -4.5)
            fixture_lights.append((video_wall_pos, video_wall_color))

        self.room_renderer.set_dynamic_lights(fixture_lights)

        canvas_size = (float(self.canvas_width), float(self.canvas_height))

        # === PASS 1: Render opaque Blinn-Phong geometry ===
        self.opaque_framebuffer.use()
        context.clear(0.0, 0.0, 0.0)
        if self.opaque_framebuffer.depth_attachment:
            context.clear(depth=1.0)

        context.enable(context.DEPTH_TEST)
        context.depth_func = "<"

        # Render floor grid
        self.room_renderer.render_floor()

        # Render DJ booth (table and figure)
        self.room_renderer.render_dj_booth()

        # Render VJ output on billboard at back of room (upstage behind DJ)
        if vj_texture:
            # Large billboard at back of room, floor to ceiling
            billboard_width = 10.0  # Wide screen
            billboard_height = 6.0  # Floor to near-ceiling
            # Position: centered horizontally (x=0), bottom at floor + half height
            y_pos = billboard_height / 2.0

            self.room_renderer.render_billboard(
                texture=vj_texture,
                position=(0.0, y_pos, -4.5),  # Back of room, centered, floor to ceiling
                width=billboard_width,
                height=billboard_height,
                normal=(0.0, 0.0, 1.0),  # Face forward toward audience
            )

        # Render fixture bodies (Blinn-Phong materials)
        for renderer in self.renderers:
            renderer.render_opaque(context, canvas_size, frame)

        # === PASS 2: Render emissive materials (bulbs and beams, excluding lasers) ===
        self.emissive_framebuffer.use()
        context.clear(0.0, 0.0, 0.0)
        # Don't clear depth - use depth from opaque pass for occlusion

        # Keep depth test enabled but disable depth writes
        context.depth_mask = False

        # Enable additive blending for emissive materials
        context.enable(context.BLEND)
        context.blend_func = context.SRC_ALPHA, context.ONE

        # Render emissive materials (bulbs and beams, but skip lasers - they render sharp)
        for renderer in self.renderers:
            if not isinstance(renderer, LaserRenderer):
                renderer.render_emissive(context, canvas_size, frame)

        # Restore depth writes
        context.depth_mask = True
        context.disable(context.BLEND)
        context.disable(context.DEPTH_TEST)

        # === PASS 3: Apply Kawase blur to create bloom ===
        self._apply_kawase_blur(context)

        # === PASS 4: Composite final image ===
        self._composite_final_image(context)

        # === PASS 5: Render sharp laser beams directly to final framebuffer (no blur) ===
        self.framebuffer.use()
        # Re-enable depth test and blending for lasers
        context.enable(context.DEPTH_TEST)
        context.depth_func = "<"
        context.depth_mask = False  # Don't write depth for lasers
        context.enable(context.BLEND)
        context.blend_func = context.SRC_ALPHA, context.ONE

        # Render lasers directly to final framebuffer (sharp, no blur)
        for renderer in self.renderers:
            if isinstance(renderer, LaserRenderer):
                renderer.render_emissive(context, canvas_size, frame)

        # Restore state
        context.depth_mask = True
        context.disable(context.BLEND)
        context.disable(context.DEPTH_TEST)

        return self.framebuffer

    def _apply_kawase_blur(self, context: mgl.Context):
        """Apply iterative Kawase blur to emissive texture for bloom effect"""
        if not self.kawase_shader or not self.emissive_texture:
            return

        # Ping-pong between bloom_framebuffer and bloom_temp_framebuffer
        # Start with emissive texture as input
        current_input = self.emissive_texture
        current_output = self.bloom_framebuffer

        texel_size = (1.0 / self.width, 1.0 / self.height)

        for i in range(self.kawase_iterations):
            current_output.use()
            context.clear(0.0, 0.0, 0.0)

            # Bind input texture
            current_input.use(0)

            # Set uniforms
            self.kawase_shader["inputTexture"] = 0
            self.kawase_shader["texelSize"] = texel_size
            # Offset increases more gradually with each iteration for smoother blur
            # Start smaller and increase more gradually to avoid streaks
            self.kawase_shader["offset"] = 1.0 + i * 2.0

            # Render fullscreen quad
            self.kawase_quad_vao.render(mgl.TRIANGLE_STRIP)

            # Ping-pong: output becomes input for next iteration
            if i < self.kawase_iterations - 1:
                if current_output == self.bloom_framebuffer:
                    current_input = self.bloom_texture
                    current_output = self.bloom_temp_framebuffer
                else:
                    current_input = self.bloom_temp_texture
                    current_output = self.bloom_framebuffer

        # Final result is in bloom_framebuffer/bloom_texture

    def _composite_final_image(self, context: mgl.Context):
        """Composite opaque, emissive, and bloom textures into final image"""
        if not self.composite_shader:
            return

        # Render to main output framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Bind textures for composite
        self.opaque_texture.use(0)  # Opaque (Blinn-Phong)
        self.bloom_texture.use(1)  # Bloom

        # Set uniforms
        self.composite_shader["opaqueTexture"] = 0
        self.composite_shader["bloomTexture"] = 1
        self.composite_shader["bloomAlpha"] = self.bloom_alpha

        # Render fullscreen quad
        self.composite_quad_vao.render(mgl.TRIANGLE_STRIP)

    def _create_quad_for_shader(
        self, context: mgl.Context, shader: mgl.Program
    ) -> mgl.VertexArray:
        """Create a fullscreen quad VAO for a specific shader"""
        vertices = np.array(
            [
                # Position  # TexCoord
                -1.0,
                -1.0,
                0.0,
                0.0,  # Bottom-left
                1.0,
                -1.0,
                1.0,
                0.0,  # Bottom-right
                -1.0,
                1.0,
                0.0,
                1.0,  # Top-left
                1.0,
                1.0,
                1.0,
                1.0,  # Top-right
            ],
            dtype=np.float32,
        )
        vbo = context.buffer(vertices.tobytes())
        return context.vertex_array(
            shader, [(vbo, "2f 2f", "in_position", "in_texcoord")]
        )

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Not used - rendering is done in custom render() method"""
        pass

    def resize(self, context: mgl.Context, width: int, height: int):
        """Resize all framebuffers to match new dimensions"""
        # Don't resize if dimensions haven't changed
        if (
            self.width == width
            and self.height == height
            and self.framebuffer is not None
        ):
            return

        # Update dimensions
        self.width = width
        self.height = height

        # Clean up existing framebuffers
        if self.opaque_framebuffer:
            self.opaque_framebuffer.release()
        if self.opaque_texture:
            self.opaque_texture.release()
        if self.depth_texture:
            self.depth_texture.release()
        if self.framebuffer:
            self.framebuffer.release()
        if self.texture:
            self.texture.release()
        if self.emissive_framebuffer:
            self.emissive_framebuffer.release()
        if self.emissive_texture:
            self.emissive_texture.release()
        if self.bloom_framebuffer:
            self.bloom_framebuffer.release()
        if self.bloom_texture:
            self.bloom_texture.release()
        if self.bloom_temp_framebuffer:
            self.bloom_temp_framebuffer.release()
        if self.bloom_temp_texture:
            self.bloom_temp_texture.release()

        # Clear references
        self.opaque_framebuffer = None
        self.opaque_texture = None
        self.depth_texture = None
        self.framebuffer = None
        self.texture = None
        self.emissive_framebuffer = None
        self.emissive_texture = None
        self.bloom_framebuffer = None
        self.bloom_texture = None
        self.bloom_temp_framebuffer = None
        self.bloom_temp_texture = None

        # Recreate with new dimensions
        self._setup_gl_resources(context, width, height)

        # Resize room renderer if it exists
        if self.room_renderer:
            self.room_renderer.width = width
            self.room_renderer.height = height
