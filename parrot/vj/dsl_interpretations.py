"""
VJ Mode Interpretations using DSL syntax
Similar to mode_interpretations.py but for VJ effects
"""

from typing import Dict, List, Callable
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs

# Import DSL functions
from parrot.vj.dsl import (
    vj_randomize,
    vj_weighted_randomize,
    vj_combo,
    vj_with_args,
    for_video,
    for_text,
    for_laser,
    for_blood,
    for_lighting,
    for_particles,
    for_layer_type,
    signal_switch,
    energy_gate,
    time_limit,
    BloodOnBass,
    LightningOnTreble,
    StrobeOnManual,
    RedLightingOnBass,
    TextScreamOnEnergy,
    HorrorAtmosphere,
    IntenseHorror,
    LaserShow,
    StrobeShow,
    Black,
    DarkRed,
    HorrorVideo,
    DeadSexyText,
    BloodLayer,
    LaserLayer,
    ParticleLayer,
)

# Import all VJ interpreters
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
    ColorStrobe,
    BeatStrobe,
    RandomStrobe,
    HighSpeedStrobe,
    PatternStrobe,
    AudioReactiveStrobe,
    LayerSelectiveStrobe,
    StrobeBlackout,
    RGBChannelStrobe,
    StrobeZoom,
)

# Import layers
from parrot.vj.base import SolidLayer
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
from parrot.vj.layers.shader_layers import (
    TunnelShader,
    PlasmaShader,
    FractalShader,
    KaleidoscopeShader,
    WaveDistortionShader,
    PsychedelicShader,
    VortexShader,
    NoiseShader,
    HypnoticShader,
    GeometricShader,
    RainbowShader,
)
from parrot.vj.interpreters.shader_effects import (
    ShaderIntensity,
    ShaderMixer,
    ShaderReactive,
    ShaderBeat,
    ShaderGlitcher,
)


# Shader layer creation helpers
def TreppyTunnelLayer(width: int, height: int) -> "TunnelShader":
    """Create trippy tunnel shader layer"""
    return TunnelShader("trippy_tunnel", z_order=3, width=width, height=height)


def PsychedelicLayer(width: int, height: int) -> "PsychedelicShader":
    """Create psychedelic shader layer"""
    return PsychedelicShader("psychedelic", z_order=4, width=width, height=height)


def VortexLayer(width: int, height: int) -> "VortexShader":
    """Create vortex shader layer"""
    return VortexShader("vortex", z_order=5, width=width, height=height)


def KaleidoscopeLayer(width: int, height: int) -> "KaleidoscopeShader":
    """Create kaleidoscope shader layer"""
    return KaleidoscopeShader("kaleidoscope", z_order=6, width=width, height=height)


# DSL-style VJ mode interpretations
vj_dsl_mode_interpretations: Dict[Mode, Dict[str, List]] = {
    Mode.blackout: {
        "layers": lambda w, h: [
            Black(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            for_text(
                vj_randomize(
                    vj_with_args("EerieBreathing", EerieBreathing, breath_speed=0.01),
                    vj_with_args(
                        "GhostlyFade",
                        AlphaFade,
                        signal=FrameSignal.sustained_low,
                        min_alpha=0.2,
                        max_alpha=0.8,
                    ),
                    AlphaStatic,
                )
            ),
        ],
    },
    Mode.gentle: {
        "layers": lambda w, h: [
            DarkRed(w, h),  # Subtle dark red background
            HorrorVideo(w, h),
            SpookyLightingLayer(
                "ghost_lights", z_order=3, , num_lights=4
            ),
            ParticleLayer(w, h, max_particles=8),
            HorrorColorGrade("subtle_horror", z_order=5, ),
            LaserHaze("atmosphere", z_order=6, , haze_density=0.2),
            LaserLayer(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            # Video effects - gentle but spooky
            for_video(
                vj_combo(
                    vj_with_args(
                        "GentleAlpha",
                        AlphaFade,
                        signal=FrameSignal.sustained_low,
                        min_alpha=0.4,
                        max_alpha=0.8,
                        smoothing=0.03,
                    ),
                    vj_with_args(
                        "SlowVideoSwitch", VideoSelectorTimed, switch_interval=45.0
                    ),
                    vj_randomize(
                        vj_with_args("RedGlow", RedLighting, red_intensity=1.5),
                        vj_with_args(
                            "ColorScheme",
                            ColorSchemeLighting,
                            color_source="fg",
                            intensity=1.3,
                        ),
                        vj_with_args(
                            "SelectiveRed",
                            SelectiveLighting,
                            target_color=(0.8, 0.1, 0.1),
                            enhancement_factor=1.4,
                        ),
                    ),
                )
            ),
            # Text effects - creepy movement
            for_text(
                vj_randomize(
                    vj_with_args(
                        "HorrorText",
                        DeadSexyTextHorror,
                        shake_intensity=0.03,
                        grow_factor=0.2,
                    ),
                    vj_with_args("CreepyMovement", CreepyCrawl, crawl_speed=0.015),
                    vj_with_args("Breathing", EerieBreathing, breath_speed=0.02),
                )
            ),
            # Lighting effects
            for_lighting(SpookyLighting),
            # Gentle laser effects
            for_laser(
                vj_randomize(
                    vj_with_args(
                        "GentleFan", ConcertLasers, num_lasers=4, fan_angle=90.0
                    ),
                    vj_with_args(
                        "SoftSpiral", LaserSpiral, num_spirals=2, spiral_speed=0.02
                    ),
                )
            ),
            # Minimal blood effects
            for_blood(
                vj_with_args(
                    "SubtleBlood", BloodDrip, drip_threshold=0.8, drip_speed=0.01
                )
            ),
        ],
    },
    Mode.rave: {
        "layers": lambda w, h: [
            SolidLayer(
                "abyss", color=(10, 0, 0), alpha=255, z_order=0,             ),
            HorrorVideo(w, h),
            BloodLayer(w, h),
            SpookyLightingLayer(
                "demon_lights", z_order=3, , num_lights=8
            ),
            LightningLayer("lightning", z_order=4, ),
            ParticleLayer(w, h, max_particles=25),
            HorrorColorGrade("blood_tint", z_order=6, ),
            LaserHaze("demon_haze", z_order=7, , haze_density=0.4),
            LaserLayer(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            # Video effects - intense and reactive
            for_video(
                vj_combo(
                    vj_randomize(
                        vj_with_args(
                            "IntenseFlash",
                            AlphaFlash,
                            signal=FrameSignal.freq_high,
                            threshold=0.6,
                            flash_alpha=1.0,
                            base_alpha=0.3,
                        ),
                        vj_with_args(
                            "HeavyPulse",
                            AlphaPulse,
                            signal=FrameSignal.freq_low,
                            pulse_speed=0.25,
                            min_alpha=0.2,
                            max_alpha=1.0,
                        ),
                        vj_with_args(
                            "HorrorContrast",
                            HorrorContrast,
                            contrast_range=(0.2, 3.0),
                            response_speed=0.2,
                        ),
                    ),
                    vj_with_args(
                        "AggressiveSwitch",
                        VideoSelectorHype,
                        energy_threshold=0.7,
                        cooldown_frames=60,
                    ),
                    vj_randomize(
                        vj_with_args("IntenseStrobe", StrobeLighting, strobe_speed=1.2),
                        vj_with_args(
                            "DynamicColor",
                            DynamicColorLighting,
                            intensity_range=(2.0, 4.0),
                            beat_boost=True,
                        ),
                        vj_with_args("BloodLighting", RedLighting, red_intensity=3.0),
                        vj_with_args(
                            "ChannelSep",
                            ColorChannelSeparation,
                            separation_intensity=2.5,
                        ),
                        vj_with_args(
                            "SelectiveBlood",
                            SelectiveLighting,
                            target_color=(1.0, 0.0, 0.0),
                            enhancement_factor=3.0,
                        ),
                    ),
                )
            ),
            # Text effects - dramatic and scary
            for_text(
                vj_randomize(
                    vj_with_args(
                        "ScreamingText",
                        HorrorTextScream,
                        scream_threshold=0.75,
                        max_scale=3.0,
                        shake_intensity=0.2,
                    ),
                    vj_with_args(
                        "HorrorMode",
                        DeadSexyTextHorror,
                        shake_intensity=0.08,
                        grow_factor=0.6,
                        pulse_speed=0.25,
                    ),
                    vj_with_args(
                        "GlitchText",
                        HalloweenGlitch,
                        glitch_probability=0.05,
                        glitch_intensity=0.8,
                    ),
                    vj_with_args("CrawlingText", CreepyCrawl, crawl_speed=0.04),
                )
            ),
            # Lightning effects - dramatic flashes
            for_layer_type(
                "lightning",
                vj_with_args(
                    "LightningStorm",
                    LightningFlash,
                    energy_threshold=0.7,
                    flash_duration=4,
                    flash_intensity=1.0,
                ),
            ),
            # Blood effects - intense splattering
            for_blood(
                vj_randomize(
                    vj_with_args(
                        "BloodExplosion", BloodSplatter, splatter_threshold=0.6
                    ),
                    vj_with_args(
                        "BloodRain", BloodDrip, drip_threshold=0.5, drip_speed=0.04
                    ),
                )
            ),
            # Lighting effects - chaotic movement
            for_lighting(SpookyLighting),
            # INTENSE laser show
            for_laser(
                vj_randomize(
                    vj_with_args(
                        "WideFan", ConcertLasers, num_lasers=12, fan_angle=150.0
                    ),
                    vj_with_args(
                        "DenseMatrix", LaserMatrix, grid_size=(8, 6), pulse_speed=0.15
                    ),
                    vj_with_args(
                        "Explosive",
                        LaserBurst,
                        burst_threshold=0.7,
                        max_burst_lasers=20,
                    ),
                    vj_with_args(
                        "FastChase", LaserChase, num_chasers=8, chase_speed=0.2
                    ),
                    vj_with_args("RapidScan", LaserScan, num_beams=6, scan_speed=0.08),
                )
            ),
            # Atmospheric effects
            energy_gate(
                0.3,  # Only active above 30% energy
                vj_randomize(
                    vj_with_args("HalloweenStrobe", HalloweenStrobeEffect),
                    vj_with_args("PumpkinGlow", PumpkinPulse, pulse_speed=0.12),
                    vj_with_args(
                        "ChaosGlitch",
                        HalloweenGlitch,
                        glitch_probability=0.03,
                        glitch_intensity=0.6,
                    ),
                ),
            ),
            # INTENSE strobing for maximum chaos
            signal_switch(
                vj_randomize(
                    vj_with_args(
                        "HighSpeed",
                        HighSpeedStrobe,
                        base_frequency=30.0,
                        max_frequency=60.0,
                    ),
                    AudioReactiveStrobe,
                    vj_with_args(
                        "BeatSync", BeatStrobe, beat_threshold=0.6, strobe_duration=4
                    ),
                    vj_with_args("ColorCycle", ColorStrobe, strobe_speed=0.8),
                    vj_with_args(
                        "ManualStrobe",
                        StrobeFlash,
                        strobe_frequency=20.0,
                        strobe_intensity=1.0,
                    ),
                )
            ),
        ],
    },
}


def get_vj_dsl_setup(
    mode: Mode, args: InterpreterArgs, width: int = 1920, height: int = 1080
):
    """Get VJ setup using DSL configuration"""
    if mode not in vj_dsl_mode_interpretations:
        mode = Mode.blackout  # Fallback

    mode_config = vj_dsl_mode_interpretations[mode]

    # Create layers
    layers = mode_config["layers"](width, height)

    # Create interpreters
    interpreters = []
    for interpreter_factory in mode_config["interpreters"]:
        try:
            if callable(interpreter_factory):
                interpreter = interpreter_factory(layers, args)
                interpreters.append(interpreter)
            else:
                print(f"Warning: Invalid interpreter factory: {interpreter_factory}")
        except Exception as e:
            print(f"Failed to create interpreter {interpreter_factory}: {e}")

    return layers, interpreters


# Example of more complex DSL configurations
def create_epic_horror_combo():
    """Example of complex DSL combination"""
    return vj_combo(
        # Blood effects that only trigger on high bass
        for_blood(
            energy_gate(
                0.7,  # Only above 70% energy
                vj_weighted_randomize(
                    (
                        70,
                        vj_with_args(
                            "BloodExplosion", BloodSplatter, splatter_threshold=0.5
                        ),
                    ),
                    (30, vj_with_args("BloodRain", BloodDrip, drip_threshold=0.6)),
                ),
            )
        ),
        # Text that escalates with energy
        for_text(
            signal_switch(
                vj_randomize(
                    vj_with_args("Screaming", HorrorTextScream, scream_threshold=0.8),
                    vj_with_args("Crawling", CreepyCrawl, crawl_speed=0.03),
                    vj_with_args("Breathing", EerieBreathing, breath_speed=0.04),
                )
            )
        ),
        # Laser show that builds over time
        for_laser(
            time_limit(
                1800,  # 30 seconds at 60fps
                vj_combo(
                    vj_with_args("BuildingFan", ConcertLasers, num_lasers=8),
                    energy_gate(
                        0.8,
                        vj_with_args("BurstFinale", LaserBurst, max_burst_lasers=20),
                    ),
                ),
            )
        ),
    )


# Halloween-specific DSL shortcuts
def HalloweenBloodCombo(layers: List, args: InterpreterArgs):
    """Halloween blood effect combination"""
    return vj_combo(
        BloodOnBass,
        vj_with_args("BloodDrip", BloodDrip, drip_threshold=0.6),
        for_video(RedLightingOnBass),
    )(layers, args)


def HalloweenLightningCombo(layers: List, args: InterpreterArgs):
    """Halloween lightning effect combination"""
    return vj_combo(
        LightningOnTreble,
        for_video(vj_with_args("BlueLighting", BlueLighting, blue_intensity=1.8)),
        vj_with_args("LightningStrobe", StrobeFlash, strobe_frequency=25.0),
    )(layers, args)


def HalloweenTextCombo(layers: List, args: InterpreterArgs):
    """Halloween text effect combination"""
    return vj_combo(
        TextScreamOnEnergy,
        vj_randomize(
            vj_with_args("HorrorCrawl", CreepyCrawl, crawl_speed=0.03),
            vj_with_args("ScaryBreathing", EerieBreathing, breath_speed=0.03),
            vj_with_args("TextGlitch", HalloweenGlitch, glitch_probability=0.04),
        ),
        for_text(vj_with_args("ColorFlash", TextColorCycle, cycle_speed=0.04)),
    )(layers, args)


def HalloweenLaserCombo(layers: List, args: InterpreterArgs):
    """Halloween laser show combination"""
    return vj_combo(
        vj_weighted_randomize(
            (
                40,
                vj_with_args(
                    "HorrorFan", ConcertLasers, num_lasers=10, fan_angle=140.0
                ),
            ),
            (30, vj_with_args("ChaosMatrix", LaserMatrix, grid_size=(7, 5))),
            (20, vj_with_args("ExplosiveBurst", LaserBurst, burst_threshold=0.65)),
            (10, vj_with_args("HypnoticSpiral", LaserSpiral, num_spirals=3)),
        ),
        energy_gate(
            0.8,  # Intense effects only at high energy
            vj_randomize(
                vj_with_args("ChaosChase", LaserChase, num_chasers=6, chase_speed=0.15),
                vj_with_args("FastScan", LaserScan, num_beams=5, scan_speed=0.1),
            ),
        ),
    )(layers, args)


def HalloweenStrobeCombo(layers: List, args: InterpreterArgs):
    """Halloween strobe effect combination"""
    return vj_combo(
        StrobeOnManual,
        vj_randomize(
            vj_with_args(
                "HorrorBeat", BeatStrobe, beat_threshold=0.6, strobe_duration=6
            ),
            vj_with_args("AudioReactive", AudioReactiveStrobe),
            vj_with_args(
                "HighSpeed", HighSpeedStrobe, base_frequency=25.0, max_frequency=55.0
            ),
            vj_with_args("ColorCycle", ColorStrobe, strobe_speed=0.7),
        ),
        energy_gate(
            0.9,  # Ultra effects only at peak energy
            vj_with_args(
                "ChaosStrobe", RGBChannelStrobe, channel_frequencies=(15.0, 20.0, 25.0)
            ),
        ),
    )(layers, args)


# Updated mode interpretations using more DSL
vj_dsl_halloween_interpretations: Dict[Mode, Dict[str, List]] = {
    Mode.blackout: {
        "layers": lambda w, h: [
            Black(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            HorrorAtmosphere,
        ],
    },
    Mode.gentle: {
        "layers": lambda w, h: [
            DarkRed(w, h),
            HorrorVideo(w, h),
            SpookyLightingLayer(
                "ghost_lights", z_order=3, , num_lights=4
            ),
            ParticleLayer(w, h, max_particles=8),
            HorrorColorGrade("subtle_horror", z_order=5, ),
            LaserHaze("atmosphere", z_order=6, , haze_density=0.2),
            LaserLayer(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            HorrorAtmosphere,
            for_video(
                vj_randomize(RedLightingOnBass, ColorSchemeLighting, WarmCoolLighting)
            ),
            for_laser(
                vj_randomize(
                    vj_with_args("GentleFan", ConcertLasers, num_lasers=4),
                    vj_with_args("SoftSpiral", LaserSpiral, num_spirals=2),
                )
            ),
            for_text(vj_randomize(CreepyCrawl, EerieBreathing, DeadSexyTextHorror)),
        ],
    },
    Mode.rave: {
        "layers": lambda w, h: [
            SolidLayer(
                "abyss", color=(10, 0, 0), alpha=255, z_order=0,             ),
            HorrorVideo(w, h),
            BloodLayer(w, h),
            SpookyLightingLayer(
                "demon_lights", z_order=3, , num_lights=8
            ),
            LightningLayer("lightning", z_order=4, ),
            ParticleLayer(w, h, max_particles=25),
            HorrorColorGrade("blood_tint", z_order=6, ),
            LaserHaze("demon_haze", z_order=7, , haze_density=0.4),
            LaserLayer(w, h),
            DeadSexyText(w, h),
        ],
        "interpreters": [
            IntenseHorror,
            HalloweenBloodCombo,
            HalloweenLightningCombo,
            HalloweenTextCombo,
            HalloweenLaserCombo,
            HalloweenStrobeCombo,
            # Additional chaos effects
            vj_randomize(
                vj_with_args("ChaosGlitch", HalloweenGlitch, glitch_probability=0.05),
                vj_with_args("PumpkinChaos", PumpkinPulse, pulse_speed=0.15),
                vj_with_args("HorrorStrobe", HalloweenStrobeEffect),
            ),
            # Trippy shader effects for rave
            for_layer_type(
                "shader",
                vj_combo(
                    vj_with_args("ShaderMix", ShaderMixer, mix_speed=0.05),
                    vj_with_args("ShaderReact", ShaderReactive, reactivity=2.0),
                    vj_with_args("ShaderBeat", ShaderBeat, beat_threshold=0.6),
                ),
            ),
        ],
    },
}
