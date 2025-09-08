"""
Halloween-themed VJ mode interpretations for "Dead Sexy" party
"""

import random
from typing import Dict, List, Callable
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.base import SolidLayer
from parrot.vj.renderer import ModernGLRenderer
from parrot.vj.layers.video import VideoLayer
from parrot.vj.layers.text import TextLayer
from parrot.vj.layers.halloween import (
    LightningLayer,
    BloodOverlay,
    SpookyLightingLayer,
    HalloweenParticles,
    HorrorColorGrade,
)
from parrot.vj.layers.laser import LaserLayer, LaserHaze
from parrot.vj.interpreters.alpha_fade import AlphaFade, AlphaFlash, AlphaPulse
from parrot.vj.interpreters.video_selector import VideoSelectorBeat, VideoSelectorHype
from parrot.vj.interpreters.text_animator import TextStatic
from parrot.vj.interpreters.halloween_effects import (
    LightningFlash,
    BloodDrip,
    HorrorContrast,
    DeadSexyTextHorror,
    SpookyLighting,
    BloodSplatter,
    EerieBreathing,
    HalloweenGlitch,
    HalloweenStrobeEffect,
    CreepyCrawl,
    PumpkinPulse,
    HorrorTextScream,
)
from parrot.vj.interpreters.color_lighting import (
    ColorSchemeLighting,
    RedLighting,
    DynamicColorLighting,
    SelectiveLighting,
    StrobeLighting,
    ColorChannelSeparation,
)
from parrot.vj.interpreters.laser_effects import (
    ConcertLasers,
    LaserScan,
    LaserMatrix,
    LaserChase,
    LaserBurst,
    LaserSpiral,
)
from parrot.vj.interpreters.strobe_effects import (
    StrobeFlash,
    BeatStrobe,
    AudioReactiveStrobe,
    HighSpeedStrobe,
    ColorStrobe,
)
from parrot.vj.config import CONFIG


def _create_horror_text_layer(
    text: str, name: str, z_order: int, width: int, height: int
) -> "TextLayer":
    """Create a TextLayer with the best available horror font"""
    text_layer = TextLayer(
        text=text,
        name=name,
        alpha_mask=True,
        z_order=z_order,
        width=width,
        height=height,
        font_size=max(72, min(200, height // 4)),  # Scale font with height
    )

    # Use horror font if available, otherwise bold
    try:
        text_layer.use_horror_font()
    except:
        try:
            text_layer.use_bold_font()
        except:
            pass  # Use default font

    # Add spooky effects
    text_layer.set_outline(3, (0, 0, 0))  # Black outline
    text_layer.set_shadow((5, 5), (139, 0, 0, 120))  # Dark red shadow

    return text_layer


def create_dead_sexy_blackout_layers(width: int, height: int) -> List:
    """Create layers for Halloween blackout mode"""
    return [
        SolidLayer(
            "darkness",
            color=(0, 0, 0),
            alpha=255,
            z_order=0,
        ),
        _create_horror_text_layer(
            "DEAD SEXY", "spooky_text", z_order=1, width=width, height=height
        ),
    ]


def create_dead_sexy_gentle_layers(width: int, height: int) -> List:
    """Create layers for Halloween gentle mode - eerie atmosphere"""
    return [
        # Base black background
        SolidLayer(
            "darkness",
            color=(5, 0, 5),
            alpha=255,
            z_order=0,
        ),
        # Video layer with Halloween content
        VideoLayer(
            "halloween_video",
            CONFIG["video_directory"],
            loop=True,
            z_order=1,
        ),
        # Spooky lighting layer
        SpookyLightingLayer(
            "ghost_lights", z_order=2, width=width, height=height, num_lights=4
        ),
        # Floating particles
        HalloweenParticles(
            "spooky_particles", z_order=3, width=width, height=height, max_particles=8
        ),
        # Horror color grading
        HorrorColorGrade("horror_tint", z_order=4, width=width, height=height),
        # Laser effects for atmosphere
        LaserHaze(
            "spooky_haze", z_order=5, width=width, height=height, haze_density=0.2
        ),
        LaserLayer("ghost_lasers", z_order=6, width=width, height=height),
        # "DEAD SEXY" text with alpha masking and horror font
        _create_horror_text_layer(
            "DEAD SEXY", "dead_sexy_text", z_order=10, width=width, height=height
        ),
    ]


def create_dead_sexy_rave_layers(width: int, height: int) -> List:
    """Create layers for Halloween rave mode - intense horror effects"""
    return [
        # Deep dark background
        SolidLayer(
            "abyss", color=(10, 0, 0), alpha=255, z_order=0, width=width, height=height
        ),
        # Video layer
        VideoLayer(
            "horror_video",
            CONFIG["video_directory"],
            loop=True,
            z_order=1,
        ),
        # Blood overlay
        BloodOverlay("blood_effects", z_order=2, width=width, height=height),
        # Intense spooky lighting
        SpookyLightingLayer(
            "demon_lights", z_order=3, width=width, height=height, num_lights=8
        ),
        # Lightning effects
        LightningLayer("lightning", z_order=4, width=width, height=height),
        # More particles for chaos
        HalloweenParticles(
            "chaos_particles", z_order=5, width=width, height=height, max_particles=25
        ),
        # Strong horror color grading
        HorrorColorGrade("blood_tint", z_order=6, width=width, height=height),
        # Intense laser show
        LaserHaze(
            "demon_haze", z_order=7, width=width, height=height, haze_density=0.4
        ),
        LaserLayer(
            "demon_lasers", z_order=8, width=width, height=height, beam_intensity=1.0
        ),
        # "DEAD SEXY" text with dramatic effects and horror font
        _create_horror_text_layer(
            "DEAD SEXY", "screaming_text", z_order=15, width=width, height=height
        ),
    ]


def create_dead_sexy_blackout_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create interpreters for Halloween blackout mode"""
    # Filter layers
    text_layers = [l for l in layers if hasattr(l, "text")]

    return [
        # Subtle eerie breathing effect
        (
            EerieBreathing(text_layers, args)
            if text_layers
            else EerieBreathing(layers, args)
        ),
    ]


def create_dead_sexy_gentle_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create interpreters for Halloween gentle mode"""
    # Separate layers by type
    video_layers = [l for l in layers if "video" in l.name.lower()]
    text_layers = [l for l in layers if hasattr(l, "text")]
    lighting_layers = [l for l in layers if "light" in l.name.lower()]
    particle_layers = [l for l in layers if "particle" in l.name.lower()]
    blood_layers = [l for l in layers if "blood" in l.name.lower()]
    laser_layers = [l for l in layers if "laser" in l.name.lower()]

    interpreters = []

    # Video effects - gentle but spooky
    if video_layers:
        interpreters.append(
            AlphaFade(
                video_layers,
                args,
                signal=FrameSignal.sustained_low,
                min_alpha=0.4,
                max_alpha=0.8,
                smoothing=0.03,
            )
        )

        # Occasional horror-themed video switching
        interpreters.append(
            VideoSelectorBeat(
                video_layers,
                args,
                beat_signal=FrameSignal.freq_high,
                beat_threshold=0.75,
                cooldown_frames=180,
            )  # Less frequent
        )

        # Gentle horror lighting effects
        interpreters.append(
            random.choice(
                [
                    RedLighting(
                        video_layers, args, red_intensity=1.5
                    ),  # Blood-red lighting
                    ColorSchemeLighting(
                        video_layers, args, color_source="fg", intensity=1.3
                    ),
                    SelectiveLighting(
                        video_layers,
                        args,
                        target_color=(0.8, 0.1, 0.1),
                        enhancement_factor=1.4,
                    ),
                ]
            )
        )

    # Text effects - creepy movement
    if text_layers:
        interpreters.append(
            random.choice(
                [
                    DeadSexyTextHorror(
                        text_layers, args, shake_intensity=0.03, grow_factor=0.2
                    ),
                    CreepyCrawl(text_layers, args, crawl_speed=0.015),
                    EerieBreathing(text_layers, args, breath_speed=0.02),
                ]
            )
        )

    # Lighting effects
    if lighting_layers:
        interpreters.append(SpookyLighting(lighting_layers, args))

    # Blood effects - minimal in gentle mode
    if blood_layers:
        interpreters.append(
            BloodDrip(blood_layers, args, drip_threshold=0.8, drip_speed=0.01)
        )

    # Gentle laser effects
    if laser_layers:
        interpreters.append(
            random.choice(
                [
                    ConcertLasers(laser_layers, args, num_lasers=4, fan_angle=90.0),
                    LaserSpiral(laser_layers, args, num_spirals=2, spiral_speed=0.02),
                ]
            )
        )

    return interpreters


def create_dead_sexy_rave_interpreters(layers: List, args: InterpreterArgs) -> List:
    """Create interpreters for Halloween rave mode - intense horror"""
    # Separate layers by type
    video_layers = [l for l in layers if "video" in l.name.lower()]
    text_layers = [l for l in layers if hasattr(l, "text")]
    lightning_layers = [l for l in layers if "lightning" in l.name.lower()]
    blood_layers = [l for l in layers if "blood" in l.name.lower()]
    lighting_layers = [l for l in layers if "light" in l.name.lower()]
    particle_layers = [l for l in layers if "particle" in l.name.lower()]
    laser_layers = [l for l in layers if "laser" in l.name.lower()]

    interpreters = []

    # Video effects - intense and reactive
    if video_layers:
        video_effect = random.choice(
            [
                AlphaFlash(
                    video_layers,
                    args,
                    signal=FrameSignal.freq_high,
                    threshold=0.6,
                    flash_alpha=1.0,
                    base_alpha=0.3,
                ),
                AlphaPulse(
                    video_layers,
                    args,
                    signal=FrameSignal.freq_low,
                    pulse_speed=0.25,
                    min_alpha=0.2,
                    max_alpha=1.0,
                ),
                HorrorContrast(
                    video_layers, args, contrast_range=(0.2, 3.0), response_speed=0.2
                ),
            ]
        )
        interpreters.append(video_effect)

        # Aggressive video switching
        interpreters.append(
            VideoSelectorHype(
                video_layers, args, energy_threshold=0.7, cooldown_frames=60
            )
        )

    # Text effects - dramatic and scary
    if text_layers:
        text_effect = random.choice(
            [
                HorrorTextScream(
                    text_layers,
                    args,
                    scream_threshold=0.75,
                    max_scale=3.0,
                    shake_intensity=0.2,
                ),
                DeadSexyTextHorror(
                    text_layers,
                    args,
                    shake_intensity=0.08,
                    grow_factor=0.6,
                    pulse_speed=0.25,
                ),
                HalloweenGlitch(
                    text_layers, args, glitch_probability=0.05, glitch_intensity=0.8
                ),
                CreepyCrawl(text_layers, args, crawl_speed=0.04),
            ]
        )
        interpreters.append(text_effect)

    # Lightning effects - dramatic flashes
    if lightning_layers:
        interpreters.append(
            LightningFlash(
                lightning_layers,
                args,
                energy_threshold=0.7,
                flash_duration=4,
                flash_intensity=1.0,
            )
        )

    # Blood effects - intense splattering
    if blood_layers:
        blood_effect = random.choice(
            [
                BloodSplatter(blood_layers, args, splatter_threshold=0.6),
                BloodDrip(blood_layers, args, drip_threshold=0.5, drip_speed=0.04),
            ]
        )
        interpreters.append(blood_effect)

    # Lighting effects - chaotic movement
    if lighting_layers:
        interpreters.append(SpookyLighting(lighting_layers, args))

    # Intense video lighting effects for rave mode
    if video_layers:
        interpreters.append(
            random.choice(
                [
                    StrobeLighting(
                        video_layers, args, strobe_speed=1.2
                    ),  # Fast Halloween strobe
                    DynamicColorLighting(
                        video_layers, args, intensity_range=(2.0, 4.0), beat_boost=True
                    ),
                    RedLighting(
                        video_layers, args, red_intensity=3.0
                    ),  # Intense blood lighting
                    ColorChannelSeparation(
                        video_layers, args, separation_intensity=2.5
                    ),
                    SelectiveLighting(
                        video_layers,
                        args,
                        target_color=(1.0, 0.0, 0.0),
                        enhancement_factor=3.0,
                    ),
                ]
            )
        )

    # Additional atmospheric effects
    atmospheric_layers = [l for l in layers if l.z_order < 10]  # Lower layers
    if atmospheric_layers:
        atmospheric_effect = random.choice(
            [
                HalloweenStrobeEffect(atmospheric_layers, args),
                PumpkinPulse(atmospheric_layers, args, pulse_speed=0.12),
                HalloweenGlitch(
                    atmospheric_layers,
                    args,
                    glitch_probability=0.03,
                    glitch_intensity=0.6,
                ),
            ]
        )
        interpreters.append(atmospheric_effect)

    # INTENSE laser show for rave mode
    if laser_layers:
        interpreters.append(
            random.choice(
                [
                    ConcertLasers(
                        laser_layers, args, num_lasers=12, fan_angle=150.0
                    ),  # Wide fan
                    LaserMatrix(
                        laser_layers, args, grid_size=(8, 6), pulse_speed=0.15
                    ),  # Dense matrix
                    LaserBurst(
                        laser_layers, args, burst_threshold=0.7, max_burst_lasers=20
                    ),  # Explosive
                    LaserChase(
                        laser_layers, args, num_chasers=8, chase_speed=0.2
                    ),  # Fast chase
                    LaserScan(
                        laser_layers, args, num_beams=6, scan_speed=0.08
                    ),  # Rapid scan
                ]
            )
        )

    # INTENSE strobing for maximum rave chaos
    strobe_layers = [l for l in layers if l.z_order < 12]  # Most layers except text
    if strobe_layers:
        interpreters.append(
            random.choice(
                [
                    HighSpeedStrobe(
                        strobe_layers, args, base_frequency=30.0, max_frequency=60.0
                    ),
                    AudioReactiveStrobe(strobe_layers, args),
                    BeatStrobe(
                        strobe_layers, args, beat_threshold=0.6, strobe_duration=4
                    ),
                    ColorStrobe(strobe_layers, args, strobe_speed=0.8),
                    StrobeFlash(
                        strobe_layers, args, strobe_frequency=20.0, strobe_intensity=1.0
                    ),
                ]
            )
        )

    return interpreters


# Halloween mode interpretations
halloween_mode_interpretations: Dict[Mode, Dict[str, Callable]] = {
    Mode.blackout: {
        "layers": create_dead_sexy_blackout_layers,
        "interpreters": create_dead_sexy_blackout_interpreters,
    },
    Mode.gentle: {
        "layers": create_dead_sexy_gentle_layers,
        "interpreters": create_dead_sexy_gentle_interpreters,
    },
    Mode.rave: {
        "layers": create_dead_sexy_rave_layers,
        "interpreters": create_dead_sexy_rave_interpreters,
    },
}


def create_halloween_vj_renderer(
    mode: Mode, args: InterpreterArgs, width: int = None, height: int = None
) -> ModernGLRenderer:
    """Create a Halloween-themed VJ renderer

    Args:
        mode: The current mode
        args: Interpreter arguments
        width: Display width (defaults to config)
        height: Display height (defaults to config)

    Returns:
        ModernGLRenderer: Halloween-configured renderer with spooky layers
    """
    if width is None:
        width = CONFIG["default_resolution"][0]
    if height is None:
        height = CONFIG["default_resolution"][1]

    # Create renderer
    renderer = ModernGLRenderer(width, height)

    # Get Halloween layers and interpreters
    if mode in halloween_mode_interpretations:
        mode_config = halloween_mode_interpretations[mode]
        layers = mode_config["layers"](width, height)
        interpreters = mode_config["interpreters"](layers, args)
    else:
        # Fallback to regular blackout
        layers = create_dead_sexy_blackout_layers(width, height)
        interpreters = create_dead_sexy_blackout_interpreters(layers, args)

    # Add layers to renderer
    for layer in layers:
        renderer.add_layer(layer)

    # Store interpreters and layers for external access
    renderer.interpreters = interpreters
    renderer.layers_list = layers

    return renderer


def get_halloween_effect_descriptions() -> Dict[str, str]:
    """Get descriptions of all Halloween effects for UI/debugging"""
    return {
        "LightningFlash": "⚡ Dramatic lightning flashes on high energy",
        "BloodDrip": "🩸 Blood dripping effects triggered by bass",
        "BloodSplatter": "🩸 Blood splatters on beat hits",
        "HorrorContrast": "🌑 Dynamic contrast adjustment for horror atmosphere",
        "DeadSexyTextHorror": "💀 Spooky 'DEAD SEXY' text with breathing and scare modes",
        "HorrorTextScream": "😱 Text 'screams' with explosive scaling and shaking",
        "SpookyLighting": "🕯️ Moving ghost lights with eerie colors",
        "HalloweenGlitch": "📺 Digital glitch effects for supernatural feel",
        "GhostlyFade": "👻 Ethereal fading in and out",
        "EerieBreathing": "🫁 Slow breathing effect for atmosphere",
        "HalloweenStrobe": "🎃 Halloween-colored strobing",
        "CreepyCrawl": "🕷️ Text crawls in creepy patterns",
        "PumpkinPulse": "🎃 Pumpkin-orange pulsing effects",
        "LightningLayer": "⚡ Visual lightning bolts across screen",
        "BloodOverlay": "🩸 Blood splatter and drip visuals",
        "SpookyLightingLayer": "🕯️ Multiplicative lighting with moving elements",
        "HalloweenParticles": "🦇 Floating bats, skulls, spiders, and ghosts",
        "HorrorColorGrade": "🩸 Red-tinted color grading for horror atmosphere",
        "ConcertLasers": "🔴 Concert-style laser beams that fan out from origin",
        "LaserScan": "🔍 Scanning laser beams that sweep across screen",
        "LaserMatrix": "🔳 Matrix of pulsing laser points in grid patterns",
        "LaserChase": "🏃 Chasing lasers with trail effects around circular paths",
        "LaserBurst": "💥 Explosive radial laser bursts on energy spikes",
        "LaserSpiral": "🌀 Rotating spiral laser patterns",
        "LaserLayer": "🔴 High-quality laser beam rendering with glow effects",
        "LaserHaze": "🌫️ Atmospheric haze that makes laser beams visible",
    }


def get_halloween_mode_summary() -> Dict[str, str]:
    """Get summary of each Halloween mode"""
    return {
        "blackout": "🖤 Minimal effects - just eerie breathing text in darkness",
        "gentle": "👻 Atmospheric horror - floating particles, ghost lights, gentle lasers, subtle blood",
        "rave": "😈 INTENSE HORROR - lightning, blood splatters, screaming text, explosive laser shows, chaos!",
    }


# Helper function to enable Halloween mode
def enable_halloween_mode():
    """Enable Halloween mode by replacing the standard VJ interpretations"""
    from parrot.vj import vj_interpretations

    # Backup original interpretations
    if not hasattr(vj_interpretations, "_original_interpretations"):
        vj_interpretations._original_interpretations = (
            vj_interpretations.vj_mode_interpretations.copy()
        )

    # Replace with Halloween interpretations
    vj_interpretations.vj_mode_interpretations = halloween_mode_interpretations
    vj_interpretations.create_vj_renderer = create_halloween_vj_renderer

    print("🎃 HALLOWEEN MODE ENABLED - DEAD SEXY PARTY READY! 🎃")
    print("Mode effects:")
    for mode, description in get_halloween_mode_summary().items():
        print(f"  {mode}: {description}")


def disable_halloween_mode():
    """Disable Halloween mode and restore original interpretations"""
    from parrot.vj import vj_interpretations

    if hasattr(vj_interpretations, "_original_interpretations"):
        vj_interpretations.vj_mode_interpretations = (
            vj_interpretations._original_interpretations
        )
        print("Halloween mode disabled - restored normal VJ effects")
    else:
        print("Halloween mode was not enabled")


def create_halloween_effect_demo():
    """Create a demo showcasing all Halloween effects"""
    from parrot.director.frame import Frame
    from parrot.director.color_scheme import ColorScheme
    from parrot.utils.colour import Color

    # Create test layers
    layers = create_dead_sexy_rave_layers(800, 600)
    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Create all Halloween interpreters
    all_interpreters = [
        LightningFlash(layers, args),
        BloodSplatter(layers, args),
        HorrorTextScream(layers, args),
        HalloweenGlitch(layers, args),
        PumpkinPulse(layers, args),
        CreepyCrawl(layers, args),
    ]

    # Test with high energy frame
    frame = Frame(
        {
            FrameSignal.freq_low: 0.9,
            FrameSignal.freq_high: 0.8,
            FrameSignal.freq_all: 0.85,
            FrameSignal.strobe: 1.0,
        }
    )

    scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))

    print("🎃 Halloween Effects Demo:")
    for interp in all_interpreters:
        print(f"  {interp}")
        interp.step(frame, scheme)

    return layers, all_interpreters
