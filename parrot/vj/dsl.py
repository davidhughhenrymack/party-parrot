"""
VJ DSL (Domain Specific Language) for interpreter configuration
Similar to the lighting system's mode_interpretations.py DSL
"""

import random
from typing import List, Type, Union, Callable, Any, Dict
from parrot.vj.base import LayerBase, VJInterpreterBase
from parrot.interpreters.base import InterpreterArgs


def vj_randomize(*interpreters) -> Callable:
    """Randomly select one interpreter from the given options"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        selected_interpreter = random.choice(interpreters)
        return selected_interpreter(layers, args, **kwargs)

    # Store the options for debugging/inspection
    create_interpreter._vj_randomize_options = interpreters
    create_interpreter.__name__ = (
        f"randomize({', '.join(i.__name__ for i in interpreters)})"
    )

    return create_interpreter


def vj_weighted_randomize(*weighted_interpreters) -> Callable:
    """Randomly select interpreter with weights: (weight, interpreter)"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        weights = []
        interpreters = []

        for weight, interpreter in weighted_interpreters:
            weights.append(weight)
            interpreters.append(interpreter)

        # Weighted random selection
        total_weight = sum(weights)
        r = random.uniform(0, total_weight)

        cumulative_weight = 0
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return interpreters[i](layers, args, **kwargs)

        # Fallback to last interpreter
        return interpreters[-1](layers, args, **kwargs)

    create_interpreter._vj_weighted_options = weighted_interpreters
    create_interpreter.__name__ = (
        f"weighted_randomize({len(weighted_interpreters)} options)"
    )

    return create_interpreter


def vj_combo(*interpreters) -> Callable:
    """Combine multiple interpreters to work together"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        return VJComboInterpreter(layers, args, interpreters, **kwargs)

    create_interpreter._vj_combo_interpreters = interpreters
    create_interpreter.__name__ = (
        f"combo({', '.join(i.__name__ for i in interpreters)})"
    )

    return create_interpreter


def vj_with_args(
    name: str, interpreter: Type[VJInterpreterBase], **interpreter_kwargs
) -> Callable:
    """Create interpreter with specific arguments"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        # Merge interpreter_kwargs with any additional kwargs
        final_kwargs = {**interpreter_kwargs, **kwargs}
        return interpreter(layers, args, **final_kwargs)

    create_interpreter._vj_with_args_name = name
    create_interpreter._vj_with_args_interpreter = interpreter
    create_interpreter._vj_with_args_kwargs = interpreter_kwargs
    create_interpreter.__name__ = name

    return create_interpreter


def for_layer_type(
    layer_type: Union[Type[LayerBase], str], interpreter_factory: Callable
) -> Callable:
    """Apply interpreter only to layers of specific type"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        # Filter layers by type
        if isinstance(layer_type, str):
            # Filter by name substring
            filtered_layers = [
                l
                for l in layers
                if hasattr(l, "name") and layer_type.lower() in l.name.lower()
            ]
        else:
            # Filter by class type
            filtered_layers = [l for l in layers if isinstance(l, layer_type)]

        if filtered_layers:
            return interpreter_factory(filtered_layers, args, **kwargs)
        else:
            # Return no-op interpreter if no matching layers
            return VJNoopInterpreter(layers, args)

    create_interpreter._vj_layer_filter = layer_type
    create_interpreter._vj_filtered_interpreter = interpreter_factory
    create_interpreter.__name__ = (
        f"for_{layer_type}({getattr(interpreter_factory, '__name__', 'interpreter')})"
    )

    return create_interpreter


def signal_switch(interpreter_factory: Callable, signal_map: Dict = None) -> Callable:
    """Switch interpreter behavior based on audio signals (like signal_switch in lighting)"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        return VJSignalSwitchInterpreter(
            layers, args, interpreter_factory, signal_map, **kwargs
        )

    create_interpreter._vj_signal_switch_base = interpreter_factory
    create_interpreter._vj_signal_map = signal_map
    create_interpreter.__name__ = (
        f"signal_switch({getattr(interpreter_factory, '__name__', 'interpreter')})"
    )

    return create_interpreter


class VJComboInterpreter(VJInterpreterBase):
    """Combines multiple VJ interpreters to work together"""

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        interpreters: List[Callable],
        **kwargs,
    ):
        super().__init__(layers, args)

        # Create all sub-interpreters
        self.sub_interpreters = []
        for interpreter_factory in interpreters:
            try:
                sub_interp = interpreter_factory(layers, args, **kwargs)
                self.sub_interpreters.append(sub_interp)
            except Exception as e:
                print(f"Failed to create sub-interpreter {interpreter_factory}: {e}")

    def step(self, frame, scheme):
        """Update all sub-interpreters"""
        for interp in self.sub_interpreters:
            try:
                interp.step(frame, scheme)
            except Exception as e:
                print(f"Error in sub-interpreter {interp}: {e}")

    def exit(self, frame, scheme):
        """Exit all sub-interpreters"""
        for interp in self.sub_interpreters:
            try:
                interp.exit(frame, scheme)
            except:
                pass

    def __str__(self):
        sub_names = [str(interp) for interp in self.sub_interpreters]
        return f"Combo({' + '.join(sub_names)})"


class VJSignalSwitchInterpreter(VJInterpreterBase):
    """Switches interpreter behavior based on audio signals"""

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        base_interpreter_factory: Callable,
        signal_map: Dict = None,
        **kwargs,
    ):
        super().__init__(layers, args)

        # Create base interpreter
        self.base_interpreter = base_interpreter_factory(layers, args, **kwargs)

        # Default signal map
        self.signal_map = signal_map or {
            "low_energy": 0.3,
            "medium_energy": 0.6,
            "high_energy": 0.8,
        }

        self.current_mode = "low_energy"

    def step(self, frame, scheme):
        """Update based on current signal state"""
        from parrot.director.frame import FrameSignal

        # Determine current mode based on energy
        energy = frame[FrameSignal.freq_all]

        if energy > self.signal_map.get("high_energy", 0.8):
            self.current_mode = "high_energy"
        elif energy > self.signal_map.get("medium_energy", 0.6):
            self.current_mode = "medium_energy"
        else:
            self.current_mode = "low_energy"

        # Update base interpreter
        self.base_interpreter.step(frame, scheme)

    def __str__(self):
        return f"SignalSwitch({self.base_interpreter}, {self.current_mode})"


class VJNoopInterpreter(VJInterpreterBase):
    """No-operation interpreter for when no layers match filters"""

    def step(self, frame, scheme):
        pass

    def __str__(self):
        return "VJNoop"


# Layer type shortcuts for common filtering
def for_video(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to video layers"""
    return for_layer_type("video", interpreter_factory)


def for_text(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to text layers"""
    return for_layer_type("text", interpreter_factory)


def for_laser(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to laser layers"""
    return for_layer_type("laser", interpreter_factory)


def for_blood(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to blood layers"""
    return for_layer_type("blood", interpreter_factory)


def for_lighting(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to lighting layers"""
    return for_layer_type("light", interpreter_factory)


def for_particles(interpreter_factory: Callable) -> Callable:
    """Apply interpreter only to particle layers"""
    return for_layer_type("particle", interpreter_factory)


# Audio signal shortcuts
def on_bass(interpreter_factory: Callable, threshold: float = 0.6) -> Callable:
    """Activate interpreter on bass hits"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        from parrot.vj.interpreters.alpha_fade import AlphaFade
        from parrot.director.frame import FrameSignal

        # Create a bass-triggered version
        return vj_with_args(
            f"OnBass({getattr(interpreter_factory, '__name__', 'interpreter')})",
            AlphaFade,  # Use alpha fade as base, but could be enhanced
            signal=FrameSignal.freq_low,
            min_alpha=0.0,
            max_alpha=1.0,
        )(layers, args, **kwargs)

    return create_interpreter


def on_treble(interpreter_factory: Callable, threshold: float = 0.7) -> Callable:
    """Activate interpreter on treble hits"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        from parrot.vj.interpreters.alpha_fade import AlphaFlash
        from parrot.director.frame import FrameSignal

        return vj_with_args(
            f"OnTreble({getattr(interpreter_factory, '__name__', 'interpreter')})",
            AlphaFlash,
            signal=FrameSignal.freq_high,
            threshold=threshold,
        )(layers, args, **kwargs)

    return create_interpreter


def on_beat(interpreter_factory: Callable) -> Callable:
    """Activate interpreter on beat detection"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        from parrot.vj.interpreters.strobe_effects import BeatStrobe

        return BeatStrobe(layers, args, **kwargs)

    return create_interpreter


# Pre-configured effect combinations
def HorrorAtmosphere(
    layers: List[LayerBase], args: InterpreterArgs
) -> VJInterpreterBase:
    """Pre-configured horror atmosphere combination"""
    from parrot.vj.interpreters.halloween_effects import EerieBreathing, BloodDrip
    from parrot.vj.interpreters.alpha_fade import AlphaFade
    from parrot.director.frame import FrameSignal

    return vj_combo(
        vj_with_args("EerieBreathing", EerieBreathing, breath_speed=0.02),
        vj_with_args("SubtleBlood", BloodDrip, drip_threshold=0.8),
        vj_with_args("GentleFade", AlphaFade, signal=FrameSignal.sustained_low),
    )(layers, args)


def IntenseHorror(layers: List[LayerBase], args: InterpreterArgs) -> VJInterpreterBase:
    """Pre-configured intense horror combination"""
    from parrot.vj.interpreters.halloween_effects import (
        HorrorTextScream,
        BloodSplatter,
        LightningFlash,
    )

    return vj_combo(
        vj_with_args("ScreamingText", HorrorTextScream, scream_threshold=0.75),
        vj_with_args("BloodExplosion", BloodSplatter, splatter_threshold=0.6),
        vj_with_args("LightningStorm", LightningFlash, energy_threshold=0.7),
    )(layers, args)


def LaserShow(layers: List[LayerBase], args: InterpreterArgs) -> VJInterpreterBase:
    """Pre-configured laser show combination"""
    from parrot.vj.interpreters.laser_effects import (
        ConcertLasers,
        LaserMatrix,
        LaserBurst,
    )

    return vj_randomize(
        vj_with_args("ConcertFan", ConcertLasers, num_lasers=8, fan_angle=120.0),
        vj_with_args("LaserGrid", LaserMatrix, grid_size=(6, 4)),
        vj_with_args("LaserExplosion", LaserBurst, max_burst_lasers=16),
    )(layers, args)


def StrobeShow(layers: List[LayerBase], args: InterpreterArgs) -> VJInterpreterBase:
    """Pre-configured strobe show combination"""
    from parrot.vj.interpreters.strobe_effects import (
        StrobeFlash,
        BeatStrobe,
        ColorStrobe,
    )

    return vj_randomize(
        vj_with_args("BasicStrobe", StrobeFlash, strobe_frequency=12.0),
        vj_with_args("BeatSync", BeatStrobe, beat_threshold=0.7),
        vj_with_args("ColorCycle", ColorStrobe, strobe_speed=0.5),
    )(layers, args)


# Utility functions for layer creation in DSL style
def Black(width: int, height: int) -> "SolidLayer":
    """Create black background layer"""
    from parrot.vj.base import SolidLayer

    return SolidLayer(
        "black_bg", color=(0, 0, 0), alpha=255, z_order=0, width=width, height=height
    )


def DarkRed(width: int, height: int) -> "SolidLayer":
    """Create dark red background layer"""
    from parrot.vj.base import SolidLayer

    return SolidLayer(
        "dark_red_bg",
        color=(10, 0, 0),
        alpha=255,
        z_order=0,
        width=width,
        height=height,
    )


def HorrorVideo(width: int, height: int) -> "VideoLayer":
    """Create horror video layer"""
    from parrot.vj.layers.video import VideoLayer
    from parrot.vj.config import CONFIG

    return VideoLayer(
        "horror_video",
        CONFIG["video_directory"],
        loop=True,
        z_order=1,
        width=width,
        height=height,
    )


def DeadSexyText(width: int, height: int) -> "TextLayer":
    """Create 'DEAD SEXY' text layer with horror font"""
    from parrot.vj.halloween_interpretations import _create_horror_text_layer

    return _create_horror_text_layer(
        "DEAD SEXY", "dead_sexy_text", z_order=10, width=width, height=height
    )


def BloodLayer(width: int, height: int) -> "BloodOverlay":
    """Create blood effects layer"""
    from parrot.vj.layers.halloween import BloodOverlay

    return BloodOverlay("blood_effects", z_order=5, width=width, height=height)


def LaserLayer(width: int, height: int) -> "LaserLayer":
    """Create laser effects layer"""
    from parrot.vj.layers.laser import LaserLayer

    return LaserLayer("lasers", z_order=12, width=width, height=height)


def ParticleLayer(
    width: int, height: int, max_particles: int = 15
) -> "HalloweenParticles":
    """Create Halloween particle layer"""
    from parrot.vj.layers.halloween import HalloweenParticles

    return HalloweenParticles(
        "particles", z_order=6, width=width, height=height, max_particles=max_particles
    )


# Pre-configured interpreter shortcuts
def BloodOnBass(layers: List[LayerBase], args: InterpreterArgs) -> VJInterpreterBase:
    """Blood effects triggered by bass"""
    from parrot.vj.interpreters.halloween_effects import BloodSplatter

    return BloodSplatter(layers, args, splatter_threshold=0.6)


def LightningOnTreble(
    layers: List[LayerBase], args: InterpreterArgs
) -> VJInterpreterBase:
    """Lightning effects triggered by treble"""
    from parrot.vj.interpreters.halloween_effects import LightningFlash

    return LightningFlash(layers, args, energy_threshold=0.7)


def StrobeOnManual(layers: List[LayerBase], args: InterpreterArgs) -> VJInterpreterBase:
    """Strobing triggered by manual strobe button"""
    from parrot.vj.interpreters.strobe_effects import StrobeFlash
    from parrot.director.frame import FrameSignal

    return StrobeFlash(
        layers, args, trigger_signal=FrameSignal.strobe, strobe_frequency=15.0
    )


def RedLightingOnBass(
    layers: List[LayerBase], args: InterpreterArgs
) -> VJInterpreterBase:
    """Red lighting that intensifies with bass"""
    from parrot.vj.interpreters.color_lighting import RedLighting
    from parrot.director.frame import FrameSignal

    return RedLighting(
        layers, args, red_intensity=2.0, response_signal=FrameSignal.freq_low
    )


def TextScreamOnEnergy(
    layers: List[LayerBase], args: InterpreterArgs
) -> VJInterpreterBase:
    """Text screaming triggered by high energy"""
    from parrot.vj.interpreters.halloween_effects import HorrorTextScream

    return HorrorTextScream(layers, args, scream_threshold=0.8, max_scale=2.5)


# Advanced DSL functions
def energy_gate(threshold: float, interpreter_factory: Callable) -> Callable:
    """Only activate interpreter above energy threshold"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        return VJEnergyGateInterpreter(
            layers, args, interpreter_factory, threshold, **kwargs
        )

    create_interpreter.__name__ = f"energy_gate({threshold}, {getattr(interpreter_factory, '__name__', 'interpreter')})"
    return create_interpreter


def time_limit(duration_frames: int, interpreter_factory: Callable) -> Callable:
    """Limit interpreter to specific duration"""

    def create_interpreter(layers: List[LayerBase], args: InterpreterArgs, **kwargs):
        return VJTimeLimitInterpreter(
            layers, args, interpreter_factory, duration_frames, **kwargs
        )

    create_interpreter.__name__ = f"time_limit({duration_frames}, {getattr(interpreter_factory, '__name__', 'interpreter')})"
    return create_interpreter


class VJEnergyGateInterpreter(VJInterpreterBase):
    """Only activates when energy is above threshold"""

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        interpreter_factory: Callable,
        threshold: float,
        **kwargs,
    ):
        super().__init__(layers, args)
        self.interpreter = interpreter_factory(layers, args, **kwargs)
        self.threshold = threshold
        self.active = False

    def step(self, frame, scheme):
        from parrot.director.frame import FrameSignal

        energy = frame[FrameSignal.freq_all]
        self.active = energy > self.threshold

        if self.active:
            self.interpreter.step(frame, scheme)

    def __str__(self):
        status = "ACTIVE" if self.active else f"waiting>{self.threshold:.1f}"
        return f"EnergyGate({self.interpreter}, {status})"


class VJTimeLimitInterpreter(VJInterpreterBase):
    """Limits interpreter to specific duration"""

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        interpreter_factory: Callable,
        duration_frames: int,
        **kwargs,
    ):
        super().__init__(layers, args)
        self.interpreter = interpreter_factory(layers, args, **kwargs)
        self.duration_frames = duration_frames
        self.frames_remaining = duration_frames
        self.active = True

    def step(self, frame, scheme):
        if self.active and self.frames_remaining > 0:
            self.interpreter.step(frame, scheme)
            self.frames_remaining -= 1

            if self.frames_remaining <= 0:
                self.active = False

    def __str__(self):
        if self.active:
            return f"TimeLimit({self.interpreter}, {self.frames_remaining}f)"
        else:
            return f"TimeLimit({self.interpreter}, EXPIRED)"
