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


@beartype
class VideoPlayer(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A video player node that plays videos from a specified directory.
    Automatically cycles through videos in the selected video group.
    """

    def __init__(self, fn_group: str = "bg", video_group: Optional[str] = None):
        super().__init__([])
        self.fn_group = fn_group
        self.video_group = video_group
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

    def enter(self):
        """Initialize video resources"""
        # Don't select videos here - wait for generate() to be called
        pass

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
        width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"▶️  {os.path.basename(video_path)} ({width}x{height})")
        self.current_video_path = video_path

    def _setup_gl_resources(self, ctx: mgl.Context, width: int, height: int):
        """Setup OpenGL resources for video rendering"""
        if self.texture and (
            self.texture.width != width or self.texture.height != height
        ):
            # Release old resources if dimensions changed
            if self.texture:
                self.texture.release()
            if self.framebuffer:
                self.framebuffer.release()
            self.texture = None
            self.framebuffer = None

        if not self.texture:
            self.texture = ctx.texture((width, height), 3)  # RGB texture
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

            # Simple fragment shader
            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec3 color;
            uniform sampler2D video_texture;
            
            void main() {
                color = texture(video_texture, uv).rgb;
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
                self.texture = context.texture((1920, 1080), 3)
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
                height, width = cv_frame.shape[:2]

                # Setup GL resources
                self._setup_gl_resources(context, width, height)

                # Upload frame to texture
                self.texture.write(cv_frame.tobytes())

                self.last_frame_time = current_time

        # Render to framebuffer
        if self.framebuffer and self.quad_vao and self.shader_program:
            self.framebuffer.use()
            context.clear(0.0, 0.0, 0.0)
            self.texture.use(0)
            self.shader_program["video_texture"] = 0
            self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer
