#!/usr/bin/env python3
"""
Example usage of the LayerCompose node with video layers and text overlays.
This demonstrates how to compose layers using their alpha channels.
"""

from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.layer_compose import LayerCompose

# Example composition as mentioned in the user's request:
# A text layer applied over a video layer from video_player.py


def create_example_canvas():
    """
    Create an example canvas composition with multiple layers.

    This demonstrates the layer composition pattern where:
    - Black provides a solid background
    - VideoPlayer provides the main video content
    - Additional layers (like text overlays) can be added on top
    """

    # Create the layers
    background = Black()
    video_layer = VideoPlayer(fn_group="bg", video_group="test_group")

    # TODO: Add text overlay layer when implemented
    # text_overlay = TextOverlay(text="Party Parrot", position=(100, 100))

    # Compose the layers (bottom to top)
    canvas = LayerCompose(
        background,  # Bottom layer - solid black background
        video_layer,  # Middle layer - video content
        # text_overlay   # Top layer - text overlay with alpha blending
    )

    return canvas


def create_multi_video_canvas():
    """
    Create a canvas with multiple video layers for complex compositions.
    """

    # Create multiple video layers
    bg_video = VideoPlayer(fn_group="bg", video_group="test_group")
    # fg_video = VideoPlayer(fn_group="fg", video_group="effects")

    # Compose with alpha blending
    canvas = LayerCompose(
        Black(),  # Background
        bg_video,  # Main video
        # fg_video       # Overlay video with alpha blending
    )

    return canvas


# Usage example:
# canvas = create_example_canvas()
# canvas.enter_recursive(gl_context)
# canvas.generate_recursive(vibe)
# framebuffer = canvas.render(frame, scheme, gl_context)
