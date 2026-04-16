"""Main-window display mode for the desktop GL editor (cycles with backslash)."""

from enum import Enum


class EditorDisplayMode(str, Enum):
    """Order matches `cycle_editor_display_mode` (after current index)."""

    DMX_HEATMAP = "dmx_heatmap"
    VJ = "vj"
    FIXTURE_SCENE = "fixture_scene"


DISPLAY_MODE_CYCLE: tuple[EditorDisplayMode, ...] = (
    EditorDisplayMode.DMX_HEATMAP,
    EditorDisplayMode.VJ,
    EditorDisplayMode.FIXTURE_SCENE,
)
