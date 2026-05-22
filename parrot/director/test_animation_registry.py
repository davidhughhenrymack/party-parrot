import inspect
from unittest.mock import patch

from parrot.director.animation_registry import (
    REGISTRY,
    animation,
    build_interpreter_factory,
    randomize_spec,
    weighted_randomize_spec,
)
from parrot.director.mode_dispatch import _build_category_combo
from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.led_par import ParRGB
from parrot_cloud.domain import VenueAnimationAssignmentSpec


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


def test_registry_defaults_are_applied_to_bare_animation_specs():
    factory = build_interpreter_factory(animation("RotatingGobo"))

    fixture = MovingHead(1, "moving", 16, [GoboWheelEntry("open", 0)])
    interp = factory([fixture], InterpreterArgs(True))

    assert interp is not None
    assert fixture.get_rotating_gobo() == (1, 0.3)


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
