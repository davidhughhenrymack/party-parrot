import random
from typing import Dict, List, Callable
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.base import SolidLayer
from parrot.vj.renderer import ModernGLRenderer
from parrot.vj.layers.video import VideoLayer
from parrot.vj.layers.text import TextLayer
from parrot.vj.interpreters.alpha_fade import (
    AlphaFade,
    AlphaFlash,
    AlphaPulse,
    AlphaStatic,
)
from parrot.vj.interpreters.video_selector import (
    VideoSelector,
    VideoSelectorBeat,
    VideoSelectorTimed,
    VideoSelectorHype,
)
from parrot.vj.interpreters.text_animator import (
    TextAnimator,
    TextPulse,
    TextColorCycle,
    TextFlash,
    TextStatic,
)
from parrot.vj.interpreters.color_lighting import (
    ColorSchemeLighting,
    RedLighting,
    BlueLighting,
    DynamicColorLighting,
    SelectiveLighting,
    StrobeLighting,
    WarmCoolLighting,
    SpotlightEffect,
    ColorChannelSeparation,
)
from parrot.vj.interpreters.strobe_effects import (
    StrobeFlash,
    ColorStrobe,
    BeatStrobe,
    RandomStrobe,
    HighSpeedStrobe,
    AudioReactiveStrobe,
    StrobeBlackout,
    RGBChannelStrobe,
)
from parrot.vj.interpreters.pyramid_effects import (
    PyramidPulse,
    PyramidFloat,
    PyramidSpin,
    PyramidMetallic,
    PyramidSwarm,
    PyramidPortal,
    PyramidStorm,
    PyramidBass,
    PyramidHypnotic,
    PyramidRave,
)
from parrot.vj.layers.pyramid import (
    GoldenPyramidsLayer,
    SilverPyramidsLayer,
    RainbowPyramidsLayer,
    MegaPyramidLayer,
    PyramidSwarmLayer,
    PyramidFormationLayer,
    PyramidPortalLayer,
)
from parrot.vj.config import CONFIG


# Layer factory functions for each mode
def create_blackout_layers(width: int, height: int) -> List:
    """Create layers for blackout mode"""
    return [
        SolidLayer(
            "background",
            color=(0, 0, 0),
            alpha=255,
            z_order=0,
        )
    ]


def create_gentle_layers(width: int, height: int) -> List:
    """Create layers for gentle mode"""
    return [
        # Layer 0: Black background
        SolidLayer(
            "background",
            color=(0, 0, 0),
            alpha=255,
            z_order=0,
        ),
        # Layer 1: Video with alpha fade based on sustained low frequencies
        VideoLayer(
            "video",
            CONFIG["video_directory"],
            loop=True,
            z_order=1,
        ),
        # Layer 2: "DEAD SEXY" text with alpha masking
        TextLayer("DEAD SEXY", name="text", alpha_mask=True, z_order=2),
        # Layer 3: Gentle floating golden pyramids
        GoldenPyramidsLayer("gentle_pyramids", pyramid_count=4),
    ]


def create_rave_layers(width: int, height: int) -> List:
    """Create core layers for rave mode - optimized for performance"""
    return [
        # Layer 0: Black background
        SolidLayer(
            "background",
            color=(0, 0, 0),
            alpha=255,
            z_order=0,
        ),
        # Layer 1: Video overlay with effects
        VideoLayer(
            "video",
            CONFIG["video_directory"],
            loop=True,
            z_order=1,
        ),
        # Layer 2: "DEAD SEXY" text with alpha masking on top
        TextLayer("DEAD SEXY", name="text", alpha_mask=True, z_order=2),
    ]


# Interpreter factory functions for each mode
def create_blackout_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create interpreters for blackout mode"""
    return [
        # Just keep everything static and black
        AlphaStatic(layers, args, alpha=1.0)
    ]


def create_gentle_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create interpreters for gentle mode"""
    # Separate layers by type for targeted interpretation
    video_layers = [l for l in layers if isinstance(l, VideoLayer)]
    text_layers = [l for l in layers if isinstance(l, TextLayer)]
    pyramid_layers = [
        l for l in layers if hasattr(l, "pyramids") or "pyramid" in l.name.lower()
    ]

    interpreters = []

    # Video layer: gentle alpha fade based on sustained low frequencies
    if video_layers:
        interpreters.append(
            AlphaFade(
                video_layers,
                args,
                signal=FrameSignal.sustained_low,
                min_alpha=0.3,
                max_alpha=0.8,
                smoothing=0.05,
            )
        )

        # Occasional video switching
        interpreters.append(
            VideoSelectorTimed(video_layers, args, switch_interval=45.0)
        )

        # Gentle color lighting
        interpreters.append(
            random.choice(
                [
                    ColorSchemeLighting(
                        video_layers, args, color_source="fg", intensity=1.2
                    ),
                    WarmCoolLighting(video_layers, args, transition_speed=0.01),
                    SelectiveLighting(video_layers, args, enhancement_factor=1.3),
                ]
            )
        )

    # Text layer: static with color from scheme
    if text_layers:
        interpreters.append(TextStatic(text_layers, args))

    # Pyramid layers: gentle floating and pulsing
    if pyramid_layers:
        interpreters.extend(
            [
                PyramidFloat(pyramid_layers, args, float_speed=1.0, float_range=0.3),
                PyramidPulse(
                    pyramid_layers, args, pulse_intensity=1.5, pulse_speed=2.0
                ),
                PyramidMetallic(
                    pyramid_layers, args, reflection_speed=1.5, metal_cycle=False
                ),
            ]
        )

    return interpreters


def create_rave_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create core interpreters for rave mode - black bg, video overlay, text masking, strobe/color effects"""
    # Separate layers by type
    video_layers = [l for l in layers if isinstance(l, VideoLayer)]
    text_layers = [l for l in layers if isinstance(l, TextLayer)]
    all_layers = layers  # All layers for strobe effects

    interpreters = []

    # Video overlay effects - responds to audio energy
    if video_layers:
        interpreters.extend(
            [
                # Video alpha flashes with music
                AlphaFlash(
                    video_layers,
                    args,
                    signal=FrameSignal.freq_all,
                    threshold=0.5,
                    flash_alpha=1.0,
                    base_alpha=0.6,
                ),
                # Beat-synchronized video switching
                VideoSelectorBeat(
                    video_layers, args, beat_signal=FrameSignal.freq_high
                ),
                # Color effects on video overlay
                random.choice(
                    [
                        ColorSchemeLighting(
                            video_layers, args, color_source="fg", intensity=1.8
                        ),
                        DynamicColorLighting(video_layers, args, cycle_speed=0.04),
                        RedLighting(video_layers, args, red_intensity=2.0),
                        BlueLighting(video_layers, args, blue_intensity=2.0),
                    ]
                ),
            ]
        )

    # Text masking - "DEAD SEXY" with alpha masking on top
    if text_layers:
        interpreters.append(
            random.choice(
                [
                    TextPulse(text_layers, args, pulse_signal=FrameSignal.freq_high),
                    TextFlash(
                        text_layers,
                        args,
                        flash_signal=FrameSignal.freq_high,
                        flash_threshold=0.7,
                    ),
                    TextColorCycle(text_layers, args, cycle_speed=0.03),
                ]
            )
        )

    # Strobe effects for rave energy
    if all_layers:
        interpreters.append(
            random.choice(
                [
                    StrobeFlash(all_layers, args, strobe_frequency=12.0),
                    BeatStrobe(all_layers, args, beat_threshold=0.6),
                    AudioReactiveStrobe(all_layers, args),
                ]
            )
        )

    return interpreters


# Mode interpretations mapping
vj_mode_interpretations: Dict[Mode, Dict[str, Callable]] = {
    Mode.blackout: {
        "layers": create_blackout_layers,
        "interpreters": create_blackout_interpreters,
    },
    Mode.gentle: {
        "layers": create_gentle_layers,
        "interpreters": create_gentle_interpreters,
    },
    Mode.rave: {"layers": create_rave_layers, "interpreters": create_rave_interpreters},
}


def get_vj_setup(
    mode: Mode, args: InterpreterArgs, width: int = None, height: int = None
):
    """Get VJ layers and interpreters for a given mode

    Args:
        mode: The current mode
        args: Interpreter arguments
        width: Display width (defaults to config)
        height: Display height (defaults to config)

    Returns:
        tuple: (layers, interpreters) for the mode
    """
    if width is None:
        width = CONFIG["default_resolution"][0]
    if height is None:
        height = CONFIG["default_resolution"][1]

    if mode not in vj_mode_interpretations:
        # Fallback to blackout mode
        mode = Mode.blackout

    mode_config = vj_mode_interpretations[mode]

    # Create layers
    layers = mode_config["layers"](width, height)

    # Create interpreters
    interpreters = mode_config["interpreters"](layers, args)

    return layers, interpreters


def create_vj_renderer(
    mode: Mode, args: InterpreterArgs, width: int = None, height: int = None
) -> ModernGLRenderer:
    """Create a complete VJ renderer for a given mode

    Args:
        mode: The current mode
        args: Interpreter arguments
        width: Display width (defaults to config)
        height: Display height (defaults to config)

    Returns:
        ModernGLRenderer: Configured renderer with layers
    """
    if width is None:
        width = CONFIG["default_resolution"][0]
    if height is None:
        height = CONFIG["default_resolution"][1]

    # Create renderer
    renderer = ModernGLRenderer(width, height)

    # Get layers and interpreters
    layers, interpreters = get_vj_setup(mode, args, width, height)

    # Add layers to renderer
    for layer in layers:
        renderer.add_layer(layer)

    # Store interpreters on the renderer for external access
    renderer.interpreters = interpreters
    renderer.layers_list = layers  # Keep reference to layers list

    return renderer
