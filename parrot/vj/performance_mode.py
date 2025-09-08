"""
High-performance VJ mode optimized for butter smooth frame rates
Prioritizes 60 FPS over effect complexity
"""

from typing import Dict, List, Callable
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.base import SolidLayer
from parrot.vj.layers.video import VideoLayer
from parrot.vj.layers.text import TextLayer
from parrot.vj.layers.pyramid import GoldenPyramidsLayer, MegaPyramidLayer
from parrot.vj.interpreters.alpha_fade import AlphaFade, AlphaFlash
from parrot.vj.interpreters.video_selector import VideoSelectorBeat
from parrot.vj.interpreters.text_animator import TextPulse
from parrot.vj.interpreters.pyramid_effects import PyramidPulse, PyramidMetallic
from parrot.vj.config import CONFIG


def create_performance_gentle_layers(width: int, height: int) -> List:
    """Create optimized layers for gentle mode - smooth 60 FPS"""
    return [
        SolidLayer("background", color=(0, 0, 0), alpha=255, z_order=0),
        VideoLayer("video", CONFIG["video_directory"], loop=True, z_order=1),
        TextLayer("DEAD SEXY", name="text", alpha_mask=True, z_order=2),
        # Only one pyramid layer for performance
        GoldenPyramidsLayer("golden", pyramid_count=2),  # Minimal pyramids
    ]


def create_performance_rave_layers(width: int, height: int) -> List:
    """Create optimized layers for rave mode - smooth 30+ FPS"""
    return [
        SolidLayer("background", color=(0, 0, 0), alpha=255, z_order=0),
        VideoLayer("video", CONFIG["video_directory"], loop=True, z_order=1),
        TextLayer("DEAD SEXY", name="text", alpha_mask=True, z_order=2),
        # Balanced pyramid setup for performance
        GoldenPyramidsLayer("golden", pyramid_count=4),
        MegaPyramidLayer("mega", "chrome"),  # One dramatic centerpiece
    ]


def create_performance_gentle_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create optimized interpreters for gentle mode"""
    video_layers = [l for l in layers if isinstance(l, VideoLayer)]
    text_layers = [l for l in layers if isinstance(l, TextLayer)]
    pyramid_layers = [l for l in layers if hasattr(l, "pyramids")]

    interpreters = []

    # Minimal video effects
    if video_layers:
        interpreters.append(AlphaFade(video_layers, args, min_alpha=0.3, max_alpha=0.8))

    # Static text
    if text_layers:
        interpreters.append(TextPulse(text_layers, args))

    # Minimal pyramid effects
    if pyramid_layers:
        interpreters.extend(
            [
                PyramidPulse(pyramid_layers, args, pulse_intensity=1.0),
                PyramidMetallic(pyramid_layers, args, reflection_speed=1.0),
            ]
        )

    return interpreters


def create_performance_rave_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create optimized interpreters for rave mode"""
    video_layers = [l for l in layers if isinstance(l, VideoLayer)]
    text_layers = [l for l in layers if isinstance(l, TextLayer)]
    pyramid_layers = [l for l in layers if hasattr(l, "pyramids")]

    interpreters = []

    # Core video effects
    if video_layers:
        interpreters.extend(
            [
                AlphaFlash(
                    video_layers, args, threshold=0.6, flash_alpha=1.0, base_alpha=0.4
                ),
                VideoSelectorBeat(video_layers, args),
            ]
        )

    # Core text effects
    if text_layers:
        interpreters.append(TextPulse(text_layers, args))

    # Core pyramid effects
    if pyramid_layers:
        interpreters.extend(
            [
                PyramidPulse(pyramid_layers, args, pulse_intensity=2.0),
                PyramidMetallic(pyramid_layers, args, reflection_speed=2.0),
            ]
        )

    return interpreters


# Performance mode interpretations
performance_mode_interpretations: Dict[Mode, Dict[str, Callable]] = {
    Mode.blackout: {
        "layers": lambda w, h: [
            SolidLayer("background", color=(0, 0, 0), alpha=255, z_order=0)
        ],
        "interpreters": lambda layers, args: [],
    },
    Mode.gentle: {
        "layers": create_performance_gentle_layers,
        "interpreters": create_performance_gentle_interpreters,
    },
    Mode.rave: {
        "layers": create_performance_rave_layers,
        "interpreters": create_performance_rave_interpreters,
    },
}


def create_performance_vj_renderer(
    mode: Mode, args: InterpreterArgs, width: int = 1920, height: int = 1080
):
    """Create optimized VJ renderer for smooth performance"""
    from parrot.vj.renderer import ModernGLRenderer

    if mode not in performance_mode_interpretations:
        mode = Mode.gentle

    mode_config = performance_mode_interpretations[mode]

    # Create renderer
    renderer = ModernGLRenderer(width=width, height=height)

    # Create optimized layers
    layers = mode_config["layers"](width, height)
    for layer in layers:
        renderer.add_layer(layer)

    # Create optimized interpreters
    interpreters = mode_config["interpreters"](layers, args)
    renderer.interpreters = interpreters

    print(
        f"🚀 Performance VJ Renderer: {len(layers)} layers, {len(interpreters)} interpreters"
    )

    return renderer
