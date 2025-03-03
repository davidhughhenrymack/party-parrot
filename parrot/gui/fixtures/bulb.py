from parrot.director.frame import Frame
from .base import FixtureGuiRenderer, render_strobe_dim_color
from parrot.fixtures import FixtureBase
from parrot.fixtures.base import ManualGroup
from tkinter import Canvas
from parrot.utils.color_extra import dim_color
from parrot.utils.colour import Color

CIRCLE_SIZE = 30


class BulbRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return 30

    @property
    def height(self) -> int:
        return 30

    def setup(self, canvas: Canvas):
        self.oval = canvas.create_oval(
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
            fill="black",
            outline="black",
        )

    def set_position(self, canvas: Canvas, x: int, y: int):
        super().set_position(canvas, x, y)
        canvas.coords(
            self.oval, self.x, self.y, self.x + self.width, self.y + self.height
        )

    def render(self, canvas: Canvas, frame: Frame):
        # Check if this fixture is part of a manual group
        is_manual = False
        if hasattr(self.fixture, "parent_group") and isinstance(
            self.fixture.parent_group, ManualGroup
        ):
            is_manual = True

        # Get the fill color based on whether it's a manual fixture or not
        if is_manual:
            # For manual fixtures, use a white color dimmed by the manual dimmer value
            dimmer = self.fixture.get_dimmer()
            fill = dim_color(Color("white"), dimmer)
        else:
            # For regular fixtures, use the normal rendering
            fill = render_strobe_dim_color(self.fixture, frame)

        canvas.itemconfig(self.oval, fill=fill)


class RectBulbRenderer(BulbRenderer):
    """A rectangular bulb renderer"""

    def setup(self, canvas: Canvas):
        self.oval = canvas.create_rectangle(
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
            fill="black",
            outline="black",
        )


class RoundedRectBulbRenderer(BulbRenderer):
    """A rounded rectangle bulb renderer"""

    def setup(self, canvas: Canvas):
        # Create a rounded rectangle by using a rectangle with small corner radius
        corner_radius = 8

        # Create the main rectangle
        self.oval = canvas.create_rectangle(
            self.x + corner_radius,
            self.y,
            self.x + self.width - corner_radius,
            self.y + self.height,
            fill="black",
            outline="black",
        )

        # Create the vertical rectangle for rounded corners
        self.rect_v = canvas.create_rectangle(
            self.x,
            self.y + corner_radius,
            self.x + self.width,
            self.y + self.height - corner_radius,
            fill="black",
            outline="black",
        )

        # Create the four corner arcs
        self.corners = []
        # Top-left corner
        self.corners.append(
            canvas.create_arc(
                self.x,
                self.y,
                self.x + corner_radius * 2,
                self.y + corner_radius * 2,
                start=90,
                extent=90,
                style="pieslice",
                fill="black",
                outline="black",
            )
        )

        # Top-right corner
        self.corners.append(
            canvas.create_arc(
                self.x + self.width - corner_radius * 2,
                self.y,
                self.x + self.width,
                self.y + corner_radius * 2,
                start=0,
                extent=90,
                style="pieslice",
                fill="black",
                outline="black",
            )
        )

        # Bottom-left corner
        self.corners.append(
            canvas.create_arc(
                self.x,
                self.y + self.height - corner_radius * 2,
                self.x + corner_radius * 2,
                self.y + self.height,
                start=180,
                extent=90,
                style="pieslice",
                fill="black",
                outline="black",
            )
        )

        # Bottom-right corner
        self.corners.append(
            canvas.create_arc(
                self.x + self.width - corner_radius * 2,
                self.y + self.height - corner_radius * 2,
                self.x + self.width,
                self.y + self.height,
                start=270,
                extent=90,
                style="pieslice",
                fill="black",
                outline="black",
            )
        )

    def set_position(self, canvas: Canvas, x: int, y: int):
        super().set_position(canvas, x, y)

        corner_radius = 8

        # Update main rectangle
        canvas.coords(
            self.oval,
            self.x + corner_radius,
            self.y,
            self.x + self.width - corner_radius,
            self.y + self.height,
        )

        # Update vertical rectangle
        canvas.coords(
            self.rect_v,
            self.x,
            self.y + corner_radius,
            self.x + self.width,
            self.y + self.height - corner_radius,
        )

        # Update corners
        # Top-left
        canvas.coords(
            self.corners[0],
            self.x,
            self.y,
            self.x + corner_radius * 2,
            self.y + corner_radius * 2,
        )

        # Top-right
        canvas.coords(
            self.corners[1],
            self.x + self.width - corner_radius * 2,
            self.y,
            self.x + self.width,
            self.y + corner_radius * 2,
        )

        # Bottom-left
        canvas.coords(
            self.corners[2],
            self.x,
            self.y + self.height - corner_radius * 2,
            self.x + corner_radius * 2,
            self.y + self.height,
        )

        # Bottom-right
        canvas.coords(
            self.corners[3],
            self.x + self.width - corner_radius * 2,
            self.y + self.height - corner_radius * 2,
            self.x + self.width,
            self.y + self.height,
        )

    def render(self, canvas: Canvas, frame: Frame):
        fill = render_strobe_dim_color(self.fixture, frame)
        canvas.itemconfig(self.oval, fill=fill)
        canvas.itemconfig(self.rect_v, fill=fill)
        for corner in self.corners:
            canvas.itemconfig(corner, fill=fill)
