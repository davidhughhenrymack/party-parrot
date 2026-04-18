import logging
from typing import List, Optional
from beartype import beartype
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import dmx_clamp, Universe
from parrot.utils.string import kebab_case

logger = logging.getLogger(__name__)


@beartype
class FixtureBase:
    def __init__(self, address, name, width, universe=Universe.default):
        self.address = address
        self.name = name
        self.width = width
        self.universe = universe
        self.values = [0 for i in range(width)]
        self.color_value = Color("black")
        self.dimmer_value = 0
        self.strobe_value = 0
        self.speed_value = 0
        self.x: Optional[int] = None
        self.y: Optional[int] = None
        self.cloud_spec_id: Optional[str] = None
        self.cloud_fixture_type: Optional[str] = None
        self.cloud_group_name: Optional[str] = None
        self.cloud_is_manual = False

    def set_position(self, x: int, y: int):
        """Set the position of the fixture in the venue (e.g. it's x,y coordinate from the gui rendering)"""
        self.x = x
        self.y = y

    def get_position(self) -> tuple[int, int]:
        """Get the position of the fixture in the venue (e.g. it's x,y coordinate from the gui rendering)"""
        return self.x, self.y

    def set_color(self, color: Color):
        self.color_value = color

    def get_color(self):
        return self.color_value

    def set_dimmer(self, value):
        self.dimmer_value = value

    def get_dimmer(self):
        return self.dimmer_value

    def begin(self):
        """Reset fixture state before rendering (called before interpreter step() calls)"""
        self.strobe_value = 0

    def set_strobe(self, value):
        """Set strobe value - uses max(existing, new) for highest-takes-precedence behavior"""
        self.strobe_value = max(self.strobe_value, value)

    def get_strobe(self):
        return self.strobe_value

    def set_pan(self, value):
        pass

    def set_tilt(self, value):
        pass

    def set_speed(self, value):
        self.speed_value = value

    def get_speed(self):
        return self.speed_value

    def render(self, dmx):
        # print("-" * 20)
        for i in range(len(self.values)):
            # print(f"{self.address + i:03d} = {int(self.values[i])}")
            if self.address + i > 512:
                logger.warning(
                    f"Fixture {self.name} @ {self.address} has too many channels, skipping {i} channels"
                )
                break
            dmx.set_channel(
                self.address + i, dmx_clamp(self.values[i]), universe=self.universe
            )

    def __str__(self) -> str:
        return f"{self.name} @ {self.address}"

    @property
    def id(self):
        return f"{kebab_case(self.name)}@{self.address}:{self.universe.value}"


@beartype
class FixtureWithBulbs(FixtureBase):
    def __init__(self, address, name, width, bulbs, universe=Universe.default):
        super().__init__(address, name, width, universe)
        self.bulbs = bulbs

    def set_dimmer(self, value):
        super().set_dimmer(value)
        for bulb in self.bulbs:
            bulb.set_dimmer(value)

    def set_color(self, color):
        super().set_color(color)
        for bulb in self.bulbs:
            bulb.set_color(color)

    def begin(self):
        """Reset fixture state before rendering"""
        super().begin()
        for bulb in self.bulbs:
            bulb.begin()

    def get_bulbs(self) -> List[FixtureBase]:
        return self.bulbs

    def render(self, dmx):
        for bulb in self.bulbs:
            bulb.render_values(self.values)
        super().render(dmx)


@beartype
class ColorWheelEntry:
    def __init__(self, color: Color, dmx_value: int):
        self.color = color
        self.dmx_value = dmx_value


@beartype
class GoboWheelEntry:
    def __init__(self, gobo: str, dmx_value: int):
        self.name = gobo
        self.dmx_value = dmx_value


@beartype
class FixtureGroup(FixtureBase):
    """A group of fixtures that can be controlled together."""

    def __init__(self, fixtures, name=None, universe=Universe.default):
        """
        Initialize a fixture group with a list of fixtures.

        Args:
            fixtures: List of fixtures to include in the group
            name: Optional name for the group. If not provided, will be generated from fixture types
            universe: Universe for the group (defaults to Universe.default)
        """
        if not fixtures:
            raise ValueError("FixtureGroup must contain at least one fixture")

        # Use the address of the first fixture as the group address
        address = min(fixture.address for fixture in fixtures)

        # Calculate total width based on the fixtures
        width = sum(fixture.width for fixture in fixtures)

        # Generate a name if not provided
        if name is None:
            fixture_type = type(fixtures[0]).__name__
            if all(isinstance(f, type(fixtures[0])) for f in fixtures):
                name = f"{len(fixtures)} {fixture_type}s"
            else:
                name = "Mixed Fixture Group"

        super().__init__(address, name, width, universe)
        self.fixtures = fixtures

    def set_color(self, color):
        super().set_color(color)
        for fixture in self.fixtures:
            fixture.set_color(color)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        for fixture in self.fixtures:
            fixture.set_dimmer(value)

    def begin(self):
        """Reset fixture state before rendering"""
        super().begin()
        for fixture in self.fixtures:
            fixture.begin()

    def set_strobe(self, value):
        super().set_strobe(value)
        for fixture in self.fixtures:
            fixture.set_strobe(value)

    def set_pan(self, value):
        super().set_pan(value)
        for fixture in self.fixtures:
            fixture.set_pan(value)

    def set_tilt(self, value):
        super().set_tilt(value)
        for fixture in self.fixtures:
            fixture.set_tilt(value)

    def set_speed(self, value):
        super().set_speed(value)
        for fixture in self.fixtures:
            fixture.set_speed(value)

    def render(self, dmx):
        for fixture in self.fixtures:
            fixture.render(dmx)

    def __str__(self) -> str:
        return f"{self.name} @ {self.address} ({len(self.fixtures)} fixtures)"

    def __iter__(self):
        return iter(self.fixtures)

    def __len__(self):
        return len(self.fixtures)

    def __getitem__(self, index):
        return self.fixtures[index]


@beartype
class ManualGroup(FixtureGroup):
    """A group of fixtures driven only by the remote's per-fixture dimmer sliders."""

    def __init__(
        self, fixtures, name="Manual Control Group", universe=Universe.default
    ):
        super().__init__(fixtures, name, universe)
        for fixture in self.fixtures:
            fixture.parent_group = self
            fixture.set_color(Color("white"))

    def apply_manual_levels(self, levels: dict[str, float]) -> None:
        """Set each fixture's dimmer from ``levels[fixture.cloud_spec_id]`` (missing = 0)."""
        for fixture in self.fixtures:
            cid = getattr(fixture, "cloud_spec_id", None)
            raw = levels.get(str(cid)) if cid is not None else None
            v = 0.0 if raw is None else max(0.0, min(1.0, float(raw)))
            dimmer_255 = v * 255.0
            fixture.set_dimmer(dimmer_255)
            fixture.dimmer_value = dimmer_255
            if fixture.width == 1:
                fixture.values[0] = int(dimmer_255)

    def render(self, dmx):
        for fixture in self.fixtures:
            if fixture.width == 1:
                fixture.values[0] = int(fixture.dimmer_value)
        super().render(dmx)
