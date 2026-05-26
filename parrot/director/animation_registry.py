from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Type

from beartype import beartype

from parrot.director.frame import FrameSignal
from parrot.director.mode import Mode
from parrot.fixtures.base import FixtureWithBulbs
from parrot.interpreters.base import (
    AnyColor,
    ColorAlternateBg,
    ColorBg,
    ColorFg,
    ColorRainbow,
    FlashBeat,
    InterpreterBase,
    Noop,
    with_args,
)
from parrot.interpreters.bulbs import AllBulbs255, for_bulbs
from parrot.interpreters.combo import combo
from parrot.interpreters.dimmer import (
    Dimmer0,
    Dimmer30,
    Dimmer255,
    DimmerFadeIn,
    DimmersBeatChase,
    GentlePulse,
    LightningStab,
    SequenceDimmers,
    SequenceFadeDimmers,
    StabPulse,
    Twinkle,
)
from parrot.interpreters.laser import LaserLatch
from parrot.interpreters.latched import DimmerFadeLatched, DimmerFadeLatched4s
from parrot.interpreters.mode_test_interpreters import (
    HomePanTilt,
    PanTiltAxisCheck,
    RigColorCycle,
)
from parrot.interpreters.move import (
    MoveCircles,
    MoveFan,
    MoveFigureEight,
    MoveNamedPosition,
    MoveNod,
    MoveSmoothWalk,
)
from parrot.interpreters.movers import (
    FocusBig,
    FocusSinePhased,
    FocusSmall,
    MoverGobo,
    MoverNoGobo,
    MoverRandomGobo,
    PrismOff,
    RotatePrism,
    RotatingGobo,
)
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.interpreters.rotosphere import RotosphereSpinColor, Spin
from parrot.interpreters.signal import signal_switch
from parrot.interpreters.slow import SlowDecay, SlowSustained, VerySlowDecay
from parrot.interpreters.strobe import (
    StrobeChannelSustained,
    StrobeHighSustained,
    StrobeOff,
    StrobeOn,
)

JsonDict = dict[str, Any]

_AUTO_FOR_BULBS_CATEGORIES = {"Color", "Dimmer"}


@beartype
@dataclass(frozen=True)
class AnimationParameter:
    key: str
    label: str
    value_type: str
    default: object
    min_value: int | float | None = None
    max_value: int | float | None = None
    step: int | float | None = None

    def to_dict(self) -> JsonDict:
        out: JsonDict = {
            "key": self.key,
            "label": self.label,
            "type": self.value_type,
            "default": self.default,
        }
        if self.min_value is not None:
            out["min"] = self.min_value
        if self.max_value is not None:
            out["max"] = self.max_value
        if self.step is not None:
            out["step"] = self.step
        if self.value_type == "signal":
            out["options"] = [
                {"value": signal.name, "label": signal.name.replace("_", " ").title()}
                for signal in FrameSignal
            ]
        return out

    def coerce(self, value: object) -> object:
        if self.value_type != "number":
            return _coerce_param(self.key, value)
        coerced = float(value)
        if isinstance(self.default, float):
            return coerced
        if isinstance(self.default, int) and not isinstance(self.default, bool):
            return int(coerced)
        return coerced


@beartype
@dataclass(frozen=True)
class AnimationRegistryEntry:
    key: str
    label: str
    category: str
    interpreter: type[InterpreterBase]
    parameters: tuple[AnimationParameter, ...] = field(default_factory=tuple)

    def to_dict(self) -> JsonDict:
        return {
            "key": self.key,
            "label": self.label,
            "category": self.category,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }

    def params_with_defaults(self, raw: object = None) -> dict[str, object]:
        parameters_by_key = {parameter.key: parameter for parameter in self.parameters}
        params = {
            parameter.key: parameter.coerce(parameter.default)
            for parameter in self.parameters
        }
        if not isinstance(raw, dict):
            return params
        for key, value in raw.items():
            normalized_key = str(key)
            parameter = parameters_by_key.get(normalized_key)
            if parameter is None:
                params[normalized_key] = _coerce_param(normalized_key, value)
            else:
                params[normalized_key] = parameter.coerce(value)
        return params


def _param(
    key: str,
    label: str,
    value_type: str,
    default: object,
    *,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    step: int | float | None = None,
) -> AnimationParameter:
    return AnimationParameter(key, label, value_type, default, min_value, max_value, step)


def _identity(value: float) -> float:
    return value


def _inverse(value: float) -> float:
    return 1.0 - value


def _sheer_ethereal_low_freq_dimmer(signal_value: float) -> float:
    x = max(0.0, min(1.0, float(signal_value)))
    return 0.7 + 0.3 * x


_SIGNAL_FNS = {
    "identity": _identity,
    "inverse": _inverse,
    "sheer_ethereal_low_freq_dimmer": _sheer_ethereal_low_freq_dimmer,
}


REGISTRY: dict[str, AnimationRegistryEntry] = {
    "AnyColor": AnimationRegistryEntry("AnyColor", "Any Color", "Color", AnyColor),
    "ColorAlternateBg": AnimationRegistryEntry(
        "ColorAlternateBg", "Alternate Background", "Color", ColorAlternateBg
    ),
    "ColorBg": AnimationRegistryEntry("ColorBg", "Background Color", "Color", ColorBg),
    "ColorFg": AnimationRegistryEntry("ColorFg", "Foreground Color", "Color", ColorFg),
    "ColorRainbow": AnimationRegistryEntry(
        "ColorRainbow", "Rainbow Color", "Color", ColorRainbow
    ),
    "Dimmer0": AnimationRegistryEntry("Dimmer0", "Dimmer Off", "Dimmer", Dimmer0),
    "Dimmer30": AnimationRegistryEntry("Dimmer30", "Dimmer 30", "Dimmer", Dimmer30),
    "Dimmer255": AnimationRegistryEntry("Dimmer255", "Dimmer Full", "Dimmer", Dimmer255),
    "DimmerFadeIn": AnimationRegistryEntry(
        "DimmerFadeIn",
        "Fade In",
        "Dimmer",
        DimmerFadeIn,
        (_param("fade_time", "Fade Time", "number", 3, min_value=0.1, step=0.1),),
    ),
    "DimmersBeatChase": AnimationRegistryEntry(
        "DimmersBeatChase", "Beat Chase", "Dimmer", DimmersBeatChase
    ),
    "GentlePulse": AnimationRegistryEntry(
        "GentlePulse",
        "Gentle Pulse",
        "Dimmer",
        GentlePulse,
        (
            _param("signal", "Signal", "signal", FrameSignal.freq_all.name),
            _param("trigger_level", "Trigger", "number", 0.2),
        ),
    ),
    "LightningStab": AnimationRegistryEntry(
        "LightningStab", "Lightning Stab", "Dimmer", LightningStab
    ),
    "SequenceDimmers": AnimationRegistryEntry(
        "SequenceDimmers", "Sequence", "Dimmer", SequenceDimmers
    ),
    "SequenceFadeDimmers": AnimationRegistryEntry(
        "SequenceFadeDimmers",
        "Sequence Fade",
        "Dimmer",
        SequenceFadeDimmers,
        (_param("min", "Minimum Dimmer", "number", 0, min_value=0, max_value=255, step=1),),
    ),
    "StabPulse": AnimationRegistryEntry(
        "StabPulse",
        "Stab Pulse",
        "Dimmer",
        StabPulse,
        (_param("trigger_level", "Trigger", "number", 0.2),),
    ),
    "Twinkle": AnimationRegistryEntry("Twinkle", "Twinkle", "Dimmer", Twinkle),
    "SlowDecay": AnimationRegistryEntry(
        "SlowDecay",
        "Slow Decay",
        "Dimmer",
        SlowDecay,
        (
            _param("decay_rate", "Decay", "number", 0.1),
            _param("signal", "Signal", "signal", FrameSignal.freq_all.name),
        ),
    ),
    "SlowSustained": AnimationRegistryEntry(
        "SlowSustained", "Slow Sustained", "Dimmer", SlowSustained
    ),
    "VerySlowDecay": AnimationRegistryEntry(
        "VerySlowDecay", "Very Slow Decay", "Dimmer", VerySlowDecay
    ),
    "DimmerFadeLatched": AnimationRegistryEntry(
        "DimmerFadeLatched", "Latched Fade", "Dimmer", DimmerFadeLatched
    ),
    "DimmerFadeLatched4s": AnimationRegistryEntry(
        "DimmerFadeLatched4s", "Latched Fade 4s", "Dimmer", DimmerFadeLatched4s
    ),
    "LaserLatch": AnimationRegistryEntry("LaserLatch", "Laser Latch", "Dimmer", LaserLatch),
    "AllBulbs255": AnimationRegistryEntry(
        "AllBulbs255", "All Bulbs Full", "Dimmer", AllBulbs255
    ),
    "FlashBeat": AnimationRegistryEntry("FlashBeat", "Flash Beat", "Dimmer", FlashBeat),
    "MoveCircles": AnimationRegistryEntry(
        "MoveCircles",
        "Circles",
        "Movement",
        MoveCircles,
        (_param("multiplier", "Speed", "number", 1.0, min_value=0, step=0.05),),
    ),
    "MoveFan": AnimationRegistryEntry(
        "MoveFan",
        "Fan",
        "Movement",
        MoveFan,
        (
            _param("multiplier", "Speed", "number", 1.0, min_value=0, step=0.05),
            _param("spread", "Spread", "number", 1.0, min_value=0, step=0.05),
        ),
    ),
    "MoveFigureEight": AnimationRegistryEntry(
        "MoveFigureEight",
        "Figure Eight",
        "Movement",
        MoveFigureEight,
        (_param("multiplier", "Speed", "number", 1.0, min_value=0, step=0.05),),
    ),
    "MoveNamedPosition": AnimationRegistryEntry(
        "MoveNamedPosition",
        "Named Position",
        "Movement",
        MoveNamedPosition,
        (_param("position_name", "Position", "named_position", ""),),
    ),
    "MoveNod": AnimationRegistryEntry(
        "MoveNod", "Nod", "Movement", MoveNod, (_param("multiplier", "Speed", "number", 1.0, min_value=0, step=0.05),)
    ),
    "MoveSmoothWalk": AnimationRegistryEntry(
        "MoveSmoothWalk",
        "Smooth Walk",
        "Movement",
        MoveSmoothWalk,
        (_param("multiplier", "Speed", "number", 0.2, min_value=0, step=0.05),),
    ),
    "FocusBig": AnimationRegistryEntry("FocusBig", "Wide Focus", "Focus", FocusBig),
    "FocusSinePhased": AnimationRegistryEntry(
        "FocusSinePhased",
        "Focus Sine",
        "Focus",
        FocusSinePhased,
        (_param("period_seconds", "Period", "number", 14.0, min_value=0.1, step=0.1),),
    ),
    "FocusSmall": AnimationRegistryEntry("FocusSmall", "Tight Focus", "Focus", FocusSmall),
    "MoverGobo": AnimationRegistryEntry(
        "MoverGobo", "Set Gobo", "Gobo", MoverGobo, (_param("gobo", "Gobo", "string", "open"),)
    ),
    "MoverNoGobo": AnimationRegistryEntry("MoverNoGobo", "No Gobo", "Gobo", MoverNoGobo),
    "MoverRandomGobo": AnimationRegistryEntry(
        "MoverRandomGobo", "Random Gobo", "Gobo", MoverRandomGobo
    ),
    "RotatingGobo": AnimationRegistryEntry(
        "RotatingGobo",
        "Rotating Gobo",
        "Gobo",
        RotatingGobo,
        (
            _param("slot", "Gobo Wheel Slot", "number", 1, min_value=0, step=1),
            _param("rotate_speed", "Speed", "number", 0.3, min_value=-1, max_value=1, step=0.05),
        ),
    ),
    "PrismOff": AnimationRegistryEntry("PrismOff", "Prism Off", "Prism", PrismOff),
    "RotatePrism": AnimationRegistryEntry(
        "RotatePrism",
        "Rotate Prism",
        "Prism",
        RotatePrism,
        (_param("rotate_speed", "Speed", "number", 0.25, min_value=-1, max_value=1, step=0.05),),
    ),
    "StrobeChannelSustained": AnimationRegistryEntry(
        "StrobeChannelSustained",
        "Strobe Channel",
        "Strobe",
        StrobeChannelSustained,
        (_param("strobe_value", "Speed", "number", 220, min_value=0, max_value=255, step=1),),
    ),
    "StrobeHighSustained": AnimationRegistryEntry(
        "StrobeHighSustained",
        "High Strobe",
        "Strobe",
        StrobeHighSustained,
        (_param("strobe_value", "Speed", "number", 220, min_value=0, max_value=255, step=1),),
    ),
    "StrobeOff": AnimationRegistryEntry("StrobeOff", "Strobe Off", "Strobe", StrobeOff),
    "StrobeOn": AnimationRegistryEntry(
        "StrobeOn",
        "Strobe On",
        "Strobe",
        StrobeOn,
        (_param("strobe_value", "Speed", "number", 220, min_value=0, max_value=255, step=1),),
    ),
    "Spin": AnimationRegistryEntry(
        "Spin", "Spin", "Movement", Spin, (_param("speed", "Speed", "number", 50, min_value=0, max_value=255, step=1),)
    ),
    "RotosphereSpinColor": AnimationRegistryEntry(
        "RotosphereSpinColor", "Rotosphere Spin Color", "Movement", RotosphereSpinColor
    ),
    "Noop": AnimationRegistryEntry("Noop", "Noop", "Utility", Noop),
    "RigColorCycle": AnimationRegistryEntry(
        "RigColorCycle", "Rig Color Cycle", "Utility", RigColorCycle
    ),
    "HomePanTilt": AnimationRegistryEntry(
        "HomePanTilt", "Home Pan/Tilt", "Utility", HomePanTilt
    ),
    "PanTiltAxisCheck": AnimationRegistryEntry(
        "PanTiltAxisCheck", "Pan/Tilt Axis Check", "Utility", PanTiltAxisCheck
    ),
}


def animation_registry_payload() -> JsonDict:
    return {
        "animations": [entry.to_dict() for entry in sorted(REGISTRY.values(), key=lambda e: (e.category, e.label))],
        "combinators": [
            {"type": "combo", "label": "Stack"},
            {"type": "randomize", "label": "Randomize"},
            {"type": "weighted_randomize", "label": "Weighted Randomize"},
            {"type": "signal_switch", "label": "Signal Switch"},
            {"type": "for_bulbs", "label": "For Bulbs"},
        ],
    }


def animation(key: str, **params: object) -> JsonDict:
    out: JsonDict = {"type": "animation", "key": key}
    if params:
        out["params"] = dict(params)
    return out


def combo_spec(*children: JsonDict) -> JsonDict:
    return {"type": "combo", "children": list(children)}


def randomize_spec(*options: JsonDict) -> JsonDict:
    return {"type": "randomize", "options": list(options)}


def weighted_randomize_spec(*options: tuple[int, JsonDict]) -> JsonDict:
    return {
        "type": "weighted_randomize",
        "options": [
            {"weight": int(weight), "animation": spec}
            for weight, spec in options
        ],
    }


def signal_switch_spec(child: JsonDict) -> JsonDict:
    return {"type": "signal_switch", "animation": child}


def for_bulbs_spec(*children: JsonDict) -> JsonDict:
    return {"type": "for_bulbs", "children": list(children)}


def with_args_spec(name: str, key: str, **params: object) -> JsonDict:
    return {"type": "with_args", "name": name, "key": key, "params": dict(params)}


def legacy_mode_spec(mode_key: str) -> JsonDict:
    return {"type": "legacy_mode", "mode": mode_key}


def _coerce_param(key: str, value: object) -> object:
    if key == "signal":
        if isinstance(value, FrameSignal):
            return value
        if isinstance(value, (list, tuple)):
            options = [FrameSignal[str(item)] for item in value]
            if not options:
                return FrameSignal.freq_all
            return random.choice(options)
        return FrameSignal[str(value)]
    if key == "signal_fn":
        if callable(value):
            return value
        return _SIGNAL_FNS[str(value)]
    return value


def _params(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    return {str(k): _coerce_param(str(k), v) for k, v in raw.items()}


def _auto_for_bulbs(interpreter: type[InterpreterBase]) -> type[InterpreterBase]:
    bulb_interpreter = for_bulbs(interpreter)

    def is_multi_bulb_fixture(fixture: object) -> bool:
        return isinstance(fixture, FixtureWithBulbs) and len(fixture.get_bulbs()) > 1

    class AutoForBulbs(InterpreterBase):
        def __new__(cls, group, args):
            fixture_group = [fixture for fixture in group if not is_multi_bulb_fixture(fixture)]
            bulb_group = [fixture for fixture in group if is_multi_bulb_fixture(fixture)]
            if not bulb_group:
                return interpreter(group, args)
            if not fixture_group:
                return bulb_interpreter(group, args)
            return super().__new__(cls)

        def __init__(self, group, args):
            super().__init__(group, args)
            self._fixture_group = [
                fixture
                for fixture in group
                if not is_multi_bulb_fixture(fixture)
            ]
            self._bulb_group = [
                fixture
                for fixture in group
                if is_multi_bulb_fixture(fixture)
            ]
            self._fixture_interpreter = (
                interpreter(self._fixture_group, args)
                if self._fixture_group
                else None
            )
            self._bulb_interpreter = (
                bulb_interpreter(self._bulb_group, args)
                if self._bulb_group
                else None
            )

        @classmethod
        def acceptable(cls, args):
            return interpreter.acceptable(args)

        def step(self, frame, scheme):
            if self._fixture_interpreter is not None:
                self._fixture_interpreter.step(frame, scheme)
            if self._bulb_interpreter is not None:
                self._bulb_interpreter.step(frame, scheme)

        def exit(self, frame, scheme):
            if self._fixture_interpreter is not None:
                self._fixture_interpreter.exit(frame, scheme)
            if self._bulb_interpreter is not None:
                self._bulb_interpreter.exit(frame, scheme)

        def __str__(self) -> str:
            children = [
                child
                for child in (self._fixture_interpreter, self._bulb_interpreter)
                if child is not None
            ]
            return " + ".join(str(child) for child in children)

    AutoForBulbs.__name__ = f"AutoForBulbs{interpreter.__name__}"
    return AutoForBulbs


def _maybe_auto_for_bulbs(
    entry: AnimationRegistryEntry,
    interpreter: type[InterpreterBase],
) -> type[InterpreterBase]:
    if entry.category not in _AUTO_FOR_BULBS_CATEGORIES:
        return interpreter
    if entry.key == "AllBulbs255":
        return interpreter
    return _auto_for_bulbs(interpreter)


@beartype
def build_interpreter_factory(spec: JsonDict) -> type[InterpreterBase]:
    expression_type = str(spec.get("type", "animation"))
    if expression_type == "animation":
        key = str(spec["key"])
        entry = REGISTRY[key]
        params = entry.params_with_defaults(spec.get("params", {}))
        if params:
            return _maybe_auto_for_bulbs(
                entry,
                with_args(str(spec.get("name", key)), entry.interpreter, **params),
            )
        return _maybe_auto_for_bulbs(entry, entry.interpreter)
    if expression_type == "with_args":
        key = str(spec["key"])
        entry = REGISTRY[key]
        return _maybe_auto_for_bulbs(
            entry,
            with_args(str(spec.get("name", key)), entry.interpreter, **entry.params_with_defaults(spec.get("params", {}))),
        )
    if expression_type == "combo":
        return combo(*(build_interpreter_factory(dict(child)) for child in spec.get("children", [])))
    if expression_type == "randomize":
        return randomize(*(build_interpreter_factory(dict(child)) for child in spec.get("options", [])))
    if expression_type == "weighted_randomize":
        weighted = []
        for item in spec.get("options", []):
            row = dict(item)
            weighted.append((int(row["weight"]), build_interpreter_factory(dict(row["animation"]))))
        return weighted_randomize(*weighted)
    if expression_type == "signal_switch":
        return signal_switch(build_interpreter_factory(dict(spec["animation"])))
    if expression_type == "for_bulbs":
        return for_bulbs(*(build_interpreter_factory(dict(child)) for child in spec.get("children", [])))
    if expression_type == "legacy_mode":
        from parrot.director.mode_interpretations import mode_interpretations
        from parrot.interpreters.randomize import randomize as legacy_randomize

        mode = Mode[str(spec["mode"])]
        legacy_options: list[Type[InterpreterBase]] = []
        for options in mode_interpretations.get(mode, {}).values():
            legacy_options.extend(options)
        if not legacy_options:
            return Dimmer0
        return legacy_randomize(*legacy_options)
    raise ValueError(f"Unknown animation expression type: {expression_type}")


DEFAULT_PAR_ANIMATION = combo_spec(
    animation("ColorBg"),
    signal_switch_spec(randomize_spec(animation("SequenceFadeDimmers"), animation("GentlePulse"), animation("Twinkle"))),
)

DEFAULT_MOVING_LIGHT_ANIMATION = combo_spec(
    animation("ColorBg"),
    signal_switch_spec(randomize_spec(animation("SequenceFadeDimmers"), animation("GentlePulse"), animation("StabPulse"))),
    randomize_spec(animation("MoveCircles"), animation("MoveNod"), animation("MoveFan")),
    randomize_spec(animation("MoverRandomGobo"), animation("MoverNoGobo")),
    randomize_spec(animation("RotatePrism"), animation("PrismOff")),
)

DEFAULT_STROBY_PAR_ANIMATION = combo_spec(
    randomize_spec(animation("StrobeChannelSustained"), animation("Noop")),
    animation("AnyColor"),
    signal_switch_spec(randomize_spec(animation("StabPulse"), animation("LightningStab"))),
)

DEFAULT_STROBY_MOVING_LIGHT_ANIMATION = combo_spec(
    randomize_spec(animation("StrobeChannelSustained"), animation("Noop")),
    animation("AnyColor"),
    signal_switch_spec(randomize_spec(animation("StabPulse"), animation("LightningStab"))),
    randomize_spec(animation("MoveCircles"), animation("MoveNod"), animation("MoveFan")),
    weighted_randomize_spec((10, animation("RotatePrism")), (90, animation("PrismOff"))),
)

