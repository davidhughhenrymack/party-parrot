from parrot.utils.colour import Color
from parrot.utils.dmx_utils import dmx_clamp
from parrot.utils.string import kebab_case


class FixtureBase:
    def __init__(self, address, name, width):
        self.address = address
        self.name = name
        self.width = width
        self.values = [0 for i in range(width)]
        self.color_value = Color("black")
        self.dimmer_value = 0
        self.strobe_value = 0
        self.speed_value = 0

    def set_color(self, color: Color):
        self.color_value = color

    def get_color(self):
        return self.color_value

    def set_dimmer(self, value):
        self.dimmer_value = value

    def get_dimmer(self):
        return self.dimmer_value

    def set_strobe(self, value):
        self.strobe_value = value

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
        for i in range(len(self.values)):
            dmx.set_channel(self.address + i, dmx_clamp(self.values[i]))

    def __str__(self) -> str:
        return f"{self.name} @ {self.address}"

    @property
    def id(self):
        return f"{kebab_case(self.name)}@{self.address}"


class FixtureWithBulbs(FixtureBase):
    def __init__(self, address, name, width, bulbs):
        super().__init__(address, name, width)
        self.bulbs = bulbs

    def set_dimmer(self, value):
        super().set_dimmer(value)
        for bulb in self.bulbs:
            bulb.set_dimmer(value)

    def set_color(self, color):
        super().set_color(color)
        for bulb in self.bulbs:
            bulb.set_color(color)

    def get_bulbs(self):
        return self.bulbs

    def render(self, dmx):
        for bulb in self.bulbs:
            bulb.render_values(self.values)
        super().render(dmx)


class ColorWheelEntry:
    def __init__(self, color: Color, dmx_value: int):
        self.color = color
        self.dmx_value = dmx_value


class GoboWheelEntry:
    def __init__(self, gobo: str, dmx_value: int):
        self.name = gobo
        self.dmx_value = dmx_value


class FixtureGroup(FixtureBase):
    """A group of fixtures that can be controlled together."""

    def __init__(self, fixtures, name=None):
        """
        Initialize a fixture group with a list of fixtures.

        Args:
            fixtures: List of fixtures to include in the group
            name: Optional name for the group. If not provided, will be generated from fixture types
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

        super().__init__(address, name, width)
        self.fixtures = fixtures

    def set_color(self, color):
        super().set_color(color)
        for fixture in self.fixtures:
            fixture.set_color(color)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        for fixture in self.fixtures:
            fixture.set_dimmer(value)

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
