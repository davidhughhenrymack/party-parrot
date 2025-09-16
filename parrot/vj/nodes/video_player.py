#!/usr/bin/env python3

import os
import random
import time
from typing import List, Optional
import cv2
import numpy as np
import moderngl as mgl
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class VideoPlayer(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A video player node that plays videos from a specified directory.
    Automatically cycles through videos in the selected video group.
    """

    def __init__(
        self,
        fn_group: str = "bg",
        video_group: Optional[str] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        super().__init__([])
        self.fn_group = fn_group
        self.video_group = video_group
        self.width = width
        self.height = height
        self.current_video_path: Optional[str] = None
        self.video_capture: Optional[cv2.VideoCapture] = None
        self.video_files: List[str] = []
        self.current_video_index = 0
        self.texture: Optional[mgl.Texture] = None
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.quad_vao: Optional[mgl.VertexArray] = None
        self.shader_program: Optional[mgl.Program] = None
        self.last_frame_time = 0
        self.fps = 30  # Default FPS, will be updated from video
        self._context: Optional[mgl.Context] = None
        # Video scaling properties
        self.video_width = 0
        self.video_height = 0
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def enter(self, context: mgl.Context):
        """Initialize video resources"""
        # Store context for later use in _setup_gl_resources
        self._context = context
        # Don't select videos here - wait for generate() to be called

    def exit(self):
        """Clean up video resources"""
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        if self.texture:
            self.texture.release()
            self.texture = None
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        self._context = None

    def generate(self, vibe: Vibe):
        """Select a new video group based on the vibe"""
        self._select_video_group()
        self._load_next_video()

    def _select_video_group(self):
        """Select a video group directory"""
        media_path = os.path.join("media", "videos", self.fn_group)
        if not os.path.exists(media_path):
            print(f"Warning: Media path {media_path} does not exist")
            self.video_files = []
            return

        # Get all subdirectories (video groups)
        video_groups = [
            d
            for d in os.listdir(media_path)
            if os.path.isdir(os.path.join(media_path, d))
        ]

        if not video_groups:
            print(f"Warning: No video groups found in {media_path}")
            self.video_files = []
            return

        # Select video group
        if self.video_group and self.video_group in video_groups:
            selected_group = self.video_group
        else:
            selected_group = random.choice(video_groups)

        group_path = os.path.join(media_path, selected_group)

        # Get all video files in the selected group
        video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        self.video_files = [
            os.path.join(group_path, f)
            for f in os.listdir(group_path)
            if os.path.splitext(f.lower())[1] in video_extensions
        ]

        if self.video_files:
            self.video_files.sort()  # Consistent ordering
            print(f"🎥 {selected_group}: {len(self.video_files)} videos")
        else:
            print(f"Warning: No video files found in {group_path}")

    def _load_next_video(self):
        """Load the next video in the sequence"""
        if not self.video_files:
            return

        if self.video_capture:
            self.video_capture.release()

        video_path = self.video_files[self.current_video_index]
        self.video_capture = cv2.VideoCapture(video_path)

        if not self.video_capture.isOpened():
            print(f"Error: Could not open video {video_path}")
            self.current_video_index = (self.current_video_index + 1) % len(
                self.video_files
            )
            return

        # Get video properties
        self.fps = self.video_capture.get(cv2.CAP_PROP_FPS) or 30
        self.video_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Calculate scaling to cover the target area while preserving aspect ratio
        self._calculate_scaling()

        print(
            f"▶️  {os.path.basename(video_path)} ({self.video_width}x{self.video_height}) -> ({self.width}x{self.height})"
        )
        self.current_video_path = video_path

    def _calculate_scaling(self):
        """Calculate scaling and offset to cover target area while preserving aspect ratio"""
        if self.video_width == 0 or self.video_height == 0:
            self.scale_factor = 1.0
            self.offset_x = 0.0
            self.offset_y = 0.0
            return

        # Calculate aspect ratios
        video_aspect = self.video_width / self.video_height
        target_aspect = self.width / self.height

        if video_aspect > target_aspect:
            # Video is wider than target - scale by height and crop sides
            self.scale_factor = self.height / self.video_height
            scaled_width = self.video_width * self.scale_factor
            self.offset_x = (scaled_width - self.width) / (
                2 * scaled_width
            )  # Normalize to texture coords
            self.offset_y = 0.0
        else:
            # Video is taller than target - scale by width and crop top/bottom
            self.scale_factor = self.width / self.video_width
            scaled_height = self.video_height * self.scale_factor
            self.offset_x = 0.0
            self.offset_y = (scaled_height - self.height) / (
                2 * scaled_height
            )  # Normalize to texture coords

    def _setup_gl_resources(self, ctx: mgl.Context):
        """Setup OpenGL resources for video rendering"""
        if self.texture and (
            self.texture.width != self.width or self.texture.height != self.height
        ):
            # Release old resources if dimensions changed
            if self.texture:
                self.texture.release()
            if self.framebuffer:
                self.framebuffer.release()
            self.texture = None
            self.framebuffer = None

        if not self.texture:
            self.texture = ctx.texture((self.width, self.height), 3)  # RGB texture
            self.framebuffer = ctx.framebuffer(color_attachments=[self.texture])

        if not self.shader_program:
            # Simple vertex shader
            vertex_shader = """
            #version 330 core
            in vec2 in_position;
            in vec2 in_texcoord;
            out vec2 uv;
            
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
                uv = in_texcoord;
            }
            """

            # Fragment shader with scaling and cropping
            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec3 color;
            uniform sampler2D video_texture;
            uniform float scale_factor;
            uniform vec2 offset;
            
            void main() {
                // Apply scaling and offset to center and crop the video
                vec2 scaled_uv = (uv - 0.5) / scale_factor + 0.5 + offset;
                
                // Check if we're outside the video bounds
                if (scaled_uv.x < 0.0 || scaled_uv.x > 1.0 || scaled_uv.y < 0.0 || scaled_uv.y > 1.0) {
                    color = vec3(0.0, 0.0, 0.0);  // Black for areas outside video
                } else {
                    color = texture(video_texture, scaled_uv).rgb;
                }
            }
            """

            self.shader_program = ctx.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            # Create fullscreen quad with corrected texture coordinates
            # Flip V coordinates to match video frame orientation (0,0 at top-left)
            vertices = np.array(
                [
                    # Position  # TexCoord
                    -1.0,
                    -1.0,
                    0.0,
                    0.0,  # Bottom-left -> (0,0) in texture
                    1.0,
                    -1.0,
                    1.0,
                    0.0,  # Bottom-right -> (1,0) in texture
                    -1.0,
                    1.0,
                    0.0,
                    1.0,  # Top-left -> (0,1) in texture
                    1.0,
                    1.0,
                    1.0,
                    1.0,  # Top-right -> (1,1) in texture
                ],
                dtype=np.float32,
            )

            vbo = ctx.buffer(vertices.tobytes())
            self.quad_vao = ctx.vertex_array(
                self.shader_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
            )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render the current video frame"""
        if not self.video_capture or not self.video_files:
            # Return empty framebuffer or create a black one
            if not self.framebuffer:
                self.texture = context.texture((self.width, self.height), 3)
                self.framebuffer = context.framebuffer(color_attachments=[self.texture])
            return self.framebuffer

        # Check if we need to advance to next frame based on FPS
        current_time = time.time()
        frame_duration = 1.0 / self.fps

        if current_time - self.last_frame_time >= frame_duration:
            ret, cv_frame = self.video_capture.read()

            if not ret:
                # Video ended, load next video
                self.current_video_index = (self.current_video_index + 1) % len(
                    self.video_files
                )
                self._load_next_video()
                if self.video_capture:
                    ret, cv_frame = self.video_capture.read()

            if ret:
                # Convert BGR to RGB
                cv_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)

                # Setup GL resources (using target dimensions)
                self._setup_gl_resources(context)

                # Create a temporary texture for the video frame
                video_texture = context.texture(
                    (self.video_width, self.video_height), 3
                )
                video_texture.write(cv_frame.tobytes())

                # Render the scaled video to our framebuffer
                self._render_scaled_video(context, video_texture)

                # Clean up temporary texture
                video_texture.release()

                self.last_frame_time = current_time

        return self.framebuffer

    def _render_scaled_video(self, context: mgl.Context, video_texture: mgl.Texture):
        """Render the video texture to the framebuffer with scaling and cropping"""
        if not self.framebuffer or not self.quad_vao or not self.shader_program:
            return

        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Bind video texture
        video_texture.use(0)

        # Set uniforms
        self.shader_program["video_texture"] = 0

        # Calculate shader uniforms for proper scaling
        # We need to invert the scaling logic for the shader
        video_aspect = self.video_width / self.video_height
        target_aspect = self.width / self.height

        if video_aspect > target_aspect:
            # Video is wider - we'll crop the sides
            shader_scale = target_aspect / video_aspect
            shader_offset_x = 0.0
            shader_offset_y = 0.0
        else:
            # Video is taller - we'll crop top/bottom
            shader_scale = video_aspect / target_aspect
            shader_offset_x = 0.0
            shader_offset_y = 0.0

        self.shader_program["scale_factor"] = shader_scale
        self.shader_program["offset"] = (shader_offset_x, shader_offset_y)

        # Render
        self.quad_vao.render(mgl.TRIANGLE_STRIP)
