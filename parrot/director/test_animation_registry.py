import inspect
from unittest.mock import patch

from parrot.director.animation_registry import (
    REGISTRY,
    animation,
    build_interpreter_factory,
    randomize_spec,
    weighted_randomize_spec,
)
from parrot.director.frame import FrameSignal
from parrot.director.frame import Frame
from parrot.director.mode import Mode
from parrot.director.mode_dispatch import (
    CompositeInterpreter,
    _build_category_combo,
    get_interpreter,
)
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.led_par import ParRGB
from parrot.interpreters.dimmer import SequenceDimmers
from parrot.interpreters.signal import SignalSwitchInterpreter
from parrot.utils.colour import Color
from parrot_cloud.domain import (
    LightingModeSpec,
    VenueAnimationAssignmentSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


def test_builds_randomize_expression():
    factory = build_interpreter_factory(
        randomize_spec(animation("Dimmer0"), animation("Dimmer255"))
    )

    interp = factory([ParRGB(1)], InterpreterArgs(True))

    assert interp is not None


def test_builds_weighted_randomize_expression():
    factory = build_interpreter_factory(
        weighted_randomize_spec(
            (10, animation("Dimmer0")),
            (90, animation("Dimmer255")),
        )
    )

    interp = factory([ParRGB(1)], InterpreterArgs(True))

    assert interp is not None


def test_database_assignments_instantiate_once_for_whole_matching_group():
    pars = [ParRGB(1), ParRGB(8), ParRGB(15)]
    for fixture in pars:
        fixture.cloud_group_name = "track"
        fixture.cloud_fixture_type = "par"
    snapshot = VenueSnapshot(
        summary=VenueSummary(
            id="venue",
            slug="venue",
            name="Venue",
            archived=False,
            active=True,
            revision=1,
        ),
        floor_width=20.0,
        floor_depth=15.0,
        floor_height=10.0,
        video_wall=VideoWallSpec(
            x=0.0,
            y=0.0,
            z=0.0,
            width=10.0,
            height=6.0,
            depth=0.25,
            locked=False,
        ),
        fixtures=(),
        lighting_modes=(
            LightingModeSpec(
                id="mode",
                venue_id="venue",
                key="chill",
                label="Chill",
                order_index=0,
            ),
        ),
        animation_assignments=(
            VenueAnimationAssignmentSpec(
                id="assignment",
                venue_id="venue",
                lighting_mode_id="mode",
                lighting_mode_key="chill",
                fixture_group_name="track",
                fixture_type="par",
                order_index=0,
                animation_spec=animation("SequenceDimmers"),
            ),
        ),
    )

    interp = get_interpreter(Mode.chill, pars, InterpreterArgs(True), snapshot)

    assert isinstance(interp, SignalSwitchInterpreter)
    assert isinstance(interp.interp_std, SequenceDimmers)
    assert interp.group == pars


def test_database_assignments_support_modes_not_in_python_enum():
    pars = [ParRGB(1), ParRGB(8)]
    snapshot = VenueSnapshot(
        summary=VenueSummary(
            id="venue",
            slug="venue",
            name="Venue",
            archived=False,
            active=True,
            revision=1,
        ),
        floor_width=20.0,
        floor_depth=15.0,
        floor_height=10.0,
        video_wall=VideoWallSpec(
            x=0.0,
            y=0.0,
            z=0.0,
            width=10.0,
            height=6.0,
            depth=0.25,
            locked=False,
        ),
        fixtures=(),
        lighting_modes=(
            LightingModeSpec(
                id="mode",
                venue_id="venue",
                key="stage_focus",
                label="Stage Focus",
                order_index=0,
            ),
        ),
        animation_assignments=(
            VenueAnimationAssignmentSpec(
                id="assignment",
                venue_id="venue",
                lighting_mode_id="mode",
                lighting_mode_key="stage_focus",
                fixture_group_name=None,
                fixture_type="par",
                order_index=0,
                animation_spec=animation("SequenceDimmers"),
            ),
        ),
    )

    interp = get_interpreter("stage_focus", pars, InterpreterArgs(True), snapshot)

    assert isinstance(interp, SignalSwitchInterpreter)
    assert isinstance(interp.interp_std, SequenceDimmers)
    assert interp.group == pars


def test_database_assignments_filter_by_fixture_index_in_group():
    pars = [ParRGB(1), ParRGB(8), ParRGB(15), ParRGB(22)]
    for fixture in pars:
        fixture.cloud_group_name = "track"
        fixture.cloud_fixture_type = "par"
    snapshot = VenueSnapshot(
        summary=VenueSummary(
            id="venue",
            slug="venue",
            name="Venue",
            archived=False,
            active=True,
            revision=1,
        ),
        floor_width=20.0,
        floor_depth=15.0,
        floor_height=10.0,
        video_wall=VideoWallSpec(
            x=0.0,
            y=0.0,
            z=0.0,
            width=10.0,
            height=6.0,
            depth=0.25,
            locked=False,
        ),
        fixtures=(),
        lighting_modes=(
            LightingModeSpec(
                id="mode",
                venue_id="venue",
                key="chill",
                label="Chill",
                order_index=0,
            ),
        ),
        animation_assignments=(
            VenueAnimationAssignmentSpec(
                id="assignment",
                venue_id="venue",
                lighting_mode_id="mode",
                lighting_mode_key="chill",
                fixture_group_name="track",
                fixture_type="par",
                order_index=0,
                animation_spec=animation("SequenceDimmers"),
                fixture_index_filter="odds",
            ),
        ),
    )

    interp = get_interpreter(Mode.chill, pars, InterpreterArgs(True), snapshot)

    assert isinstance(interp, CompositeInterpreter)
    odds_child = next(
        child for child in interp.children if isinstance(child, SignalSwitchInterpreter)
    )
    assert odds_child.group == [pars[1], pars[3]]


def test_registry_defaults_are_applied_to_bare_animation_specs():
    factory = build_interpreter_factory(animation("RotatingGobo"))

    fixture = MovingHead(1, "moving", 16, [GoboWheelEntry("open", 0)])
    interp = factory([fixture], InterpreterArgs(True))

    assert interp is not None
    assert fixture.get_rotating_gobo() == (1, 0.3)


def test_strobe_speed_override_is_applied_from_animation_params():
    factory = build_interpreter_factory(animation("StrobeOn", strobe_value=123))
    fixture = ParRGB(1)

    interp = factory([fixture], InterpreterArgs(True))
    interp.step(None, None)

    assert fixture.get_strobe() == 123


def test_sequence_fade_minimum_override_is_applied_from_animation_params():
    factory = build_interpreter_factory(animation("SequenceFadeDimmers", min="80"))
    fixture = ParRGB(1)
    interp = factory([fixture], InterpreterArgs(True))

    assert interp.interpreter.min == 80


def test_numeric_animation_params_accept_string_input_from_web_editor():
    factory = build_interpreter_factory(
        animation("RotatingGobo", slot="2", rotate_speed="0.1")
    )

    fixture = MovingHead(1, "moving", 16, [GoboWheelEntry("open", 0)])
    factory([fixture], InterpreterArgs(True))

    assert fixture.get_rotating_gobo() == (2, 0.1)


def test_float_default_params_stay_float_for_integer_like_input():
    factory = build_interpreter_factory(animation("MoveCircles", multiplier="0"))

    interp = factory([ParRGB(1)], InterpreterArgs(True))

    assert interp.interpreter.multiplier == 0.0


def test_dimmer_animation_auto_wraps_multi_bulb_fixtures():
    factory = build_interpreter_factory(animation("SequenceDimmers"))
    fixture = Motionstrip38(1)
    frame = Frame({})
    frame.time = 0.0

    interp = factory([fixture], InterpreterArgs(True))
    interp.step(frame, ColorScheme(Color("red"), Color("blue"), Color("green")))

    assert fixture.get_dimmer() == 255
    bulb_dimmers = [bulb.get_dimmer() for bulb in fixture.get_bulbs()]
    assert bulb_dimmers == [255, 0, 0, 0, 0, 0, 0, 0]


def test_dimmer_animation_auto_splits_mixed_single_and_multi_bulb_fixtures():
    factory = build_interpreter_factory(animation("SequenceDimmers"))
    par = ParRGB(1)
    strip = Motionstrip38(20)
    frame = Frame({})
    frame.time = 0.0

    interp = factory([par, strip], InterpreterArgs(True))
    interp.step(frame, ColorScheme(Color("red"), Color("blue"), Color("green")))

    assert par.get_dimmer() == 255
    assert strip.get_dimmer() == 255
    bulb_dimmers = [bulb.get_dimmer() for bulb in strip.get_bulbs()]
    assert bulb_dimmers == [255, 0, 0, 0, 0, 0, 0, 0]


def test_color_animation_auto_wraps_multi_bulb_fixtures():
    factory = build_interpreter_factory(animation("ColorAlternateBg"))
    fixture = Motionstrip38(1)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

    interp = factory([fixture], InterpreterArgs(True))
    interp.step(Frame({}), scheme)

    bulb_colors = [bulb.get_color().hex_l for bulb in fixture.get_bulbs()]
    assert bulb_colors[:4] == [
        Color("blue").hex_l,
        Color("green").hex_l,
        Color("blue").hex_l,
        Color("green").hex_l,
    ]


def test_registry_defaults_coerce_signal_fn_to_callable():
    factory = build_interpreter_factory(animation("SlowDecay", signal_fn="identity"))
    fixture = ParRGB(1)
    interp = factory([fixture], InterpreterArgs(True))

    assert callable(interp.interpreter.signal_fn)


def test_signal_param_list_randomly_selects_one_signal():
    with patch(
        "parrot.director.animation_registry.random.choice",
        side_effect=lambda options: options[-1],
    ):
        factory = build_interpreter_factory(
            animation("GentlePulse", signal=["freq_low", "freq_high"])
        )
        interp = factory([ParRGB(1)], InterpreterArgs(True))

    assert interp.interpreter.signal == FrameSignal.freq_high


def test_each_registry_entry_with_parameters_can_be_built_bare():
    for key, entry in REGISTRY.items():
        if not entry.parameters:
            continue
        factory = build_interpreter_factory(animation(key))
        assert factory is not None


def test_registered_interpreters_do_not_require_non_core_constructor_args():
    for key, entry in REGISTRY.items():
        signature = inspect.signature(entry.interpreter.__init__)
        required = [
            name
            for name, parameter in signature.parameters.items()
            if name not in {"self", "group", "args"}
            and parameter.default is inspect.Parameter.empty
            and parameter.kind
            in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
        ]
        assert required == [], f"{key} requires non-default args: {required}"


def test_stab_pulse_registry_does_not_expose_signal_parameter():
    assert [parameter.key for parameter in REGISTRY["StabPulse"].parameters] == [
        "trigger_level"
    ]


def test_beat_motion_animations_are_registered_and_buildable():
    for key in ("BeatNod", "BeatPan"):
        assert REGISTRY[key].category == "Movement"
        factory = build_interpreter_factory(animation(key))
        interp = factory(
            [MovingHead(1, "moving", 16, [GoboWheelEntry("open", 0)])],
            InterpreterArgs(True),
        )
        assert interp is not None


def test_build_category_combo_randomizes_within_each_animation_category():
    assignments = [
        VenueAnimationAssignmentSpec(
            id="1",
            venue_id="venue",
            lighting_mode_id="mode",
            lighting_mode_key="chill",
            fixture_group_name=None,
            fixture_type="par",
            order_index=0,
            animation_spec=animation("Dimmer0"),
        ),
        VenueAnimationAssignmentSpec(
            id="2",
            venue_id="venue",
            lighting_mode_id="mode",
            lighting_mode_key="chill",
            fixture_group_name=None,
            fixture_type="par",
            order_index=1,
            animation_spec=animation("Dimmer255"),
        ),
        VenueAnimationAssignmentSpec(
            id="3",
            venue_id="venue",
            lighting_mode_id="mode",
            lighting_mode_key="chill",
            fixture_group_name=None,
            fixture_type="par",
            order_index=2,
            animation_spec=animation("ColorBg"),
        ),
    ]

    factory = _build_category_combo(assignments)
    interp = factory([ParRGB(1)], InterpreterArgs(True))

    assert len(interp.interpreters) == 2


def test_blank_weight_percents_share_remaining_category_weight():
    assignments = [
        VenueAnimationAssignmentSpec(
            id="1",
            venue_id="venue",
            lighting_mode_id="mode",
            lighting_mode_key="chill",
            fixture_group_name=None,
            fixture_type="par",
            order_index=0,
            animation_spec={**animation("Dimmer0"), "weight_percent": 25},
        ),
        VenueAnimationAssignmentSpec(
            id="2",
            venue_id="venue",
            lighting_mode_id="mode",
            lighting_mode_key="chill",
            fixture_group_name=None,
            fixture_type="par",
            order_index=1,
            animation_spec=animation("Dimmer255"),
        ),
    ]

    factory = _build_category_combo(assignments)
    with patch(
        "parrot.interpreters.randomize.random.choices",
        side_effect=lambda population, weights: [population[0]],
    ) as choices:
        factory([ParRGB(1)], InterpreterArgs(True))

    assert choices.call_args.kwargs["weights"] == [0.25, 0.75]
