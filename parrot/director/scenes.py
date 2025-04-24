from parrot.fixtures.base import FixtureBase, FixtureTag
from parrot.interpreters.base import InterpreterBase, InterpreterArgs, ColorFg
from parrot.interpreters.dimmer import Dimmer255
from parrot.utils.colour import Color
from parrot.director.color_scheme import ColorScheme
from typing import Dict, List, Union, Optional, Callable


class PurpleColorFg(InterpreterBase):
    """A color interpreter that always sets fixtures to purple."""

    def step(self, frame, scheme):
        for i in self.group:
            i.set_color(Color("purple"))


class ComboInterpreter(InterpreterBase):
    """An interpreter that combines multiple interpreters."""

    def __init__(self, group, args, interpreters):
        super().__init__(group, args)
        self.interpreters = [
            interp(group, args) if isinstance(interp, type) else interp(group, args)
            for interp in interpreters
        ]

    def step(self, frame, scheme):
        for interpreter in self.interpreters:
            interpreter.step(frame, scheme)


# Define scenes that can be applied to fixtures
# Each scene maps fixture types to interpreters and optional tags
scenes: Dict[
    str,
    Dict[type[FixtureBase], List[Union[InterpreterBase, Callable, List[FixtureTag]]]],
] = {
    "manual_fixtures": {
        FixtureBase: [Dimmer255, [FixtureTag.MANUAL]],  # All manual fixtures at 100%
    },
    "manual_fixtures_1_9": {
        FixtureBase: [Dimmer255, [FixtureTag.MANUAL]],  # Manual fixtures 1-9 at 100%
    },
    "purple_pars": {
        # This will match any Par fixture type
        FixtureBase: [
            Dimmer255,
            PurpleColorFg,
            [FixtureTag.PAR],
        ],
    },
}


def get_scene_interpreter(
    scene_name: str, fixture_group: List[FixtureBase], args: InterpreterArgs
) -> Optional[InterpreterBase]:
    """Get the interpreter for a scene and fixture group."""
    if scene_name not in scenes:
        raise ValueError(f"Unknown scene: {scene_name}")

    scene = scenes[scene_name]
    for fixture_type, interpreters in scene.items():
        if isinstance(fixture_group, list) and isinstance(
            fixture_group[0], fixture_type
        ):
            # Get the required tags from the last element if it's a list of tags
            required_tags = []
            if isinstance(interpreters[-1], list):
                required_tags = interpreters[-1]
                interpreters = interpreters[
                    :-1
                ]  # Remove the tags from the interpreter list

            # Filter fixtures by tags if required
            if required_tags:
                filtered_fixtures = [
                    f for f in fixture_group if f.has_all_tags(required_tags)
                ]
                if not filtered_fixtures:
                    continue

                # For manual_fixtures_1_9, further filter by address
                if scene_name == "manual_fixtures_1_9":
                    filtered_fixtures = [
                        f for f in filtered_fixtures if 1 <= f.address <= 9
                    ]
                    if not filtered_fixtures:
                        continue

                # Create a combo interpreter with all interpreters
                return ComboInterpreter(filtered_fixtures, args, interpreters)
            else:
                # No tag filtering needed
                return ComboInterpreter(fixture_group, args, interpreters)

    return None  # No matching interpreter found
