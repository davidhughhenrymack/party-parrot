import random
import re
import time
import os
from collections import defaultdict
from typing import List
from colorama import Fore, Style, init
from parrot.director.frame import Frame, FrameSignal

from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.director.mode import Mode
from .mode_dispatch import CompositeInterpreter, get_interpreter

from parrot.utils.lerp import LerpAnimator
from parrot.state import State
from parrot.utils.color_utils import format_color_scheme
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.venue_runtime import get_runtime_fixtures, get_runtime_manual_group

SHIFT_AFTER = 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "1")), 1)

HYPE_BUCKETS = [10, 40, 70]


def _flatten_runtime_fixtures(top_level) -> list[FixtureBase]:
    """Walk runtime patch entries into a flat list of individual fixtures.

    ``ManualGroup`` is skipped entirely — those fixtures are driven by manual
    UI sliders rather than interpreters. Nested ``FixtureGroup`` wrappers
    (cloud-defined groups) are flattened; their membership is recovered later
    via each fixture's ``cloud_group_name``, which the cloud already stamps
    on every spec-built instance.
    """
    out: list[FixtureBase] = []
    for entry in top_level:
        if isinstance(entry, ManualGroup):
            continue
        if isinstance(entry, FixtureGroup):
            out.extend(_flatten_runtime_fixtures(entry.fixtures))
            continue
        out.append(entry)
    return out


def _flatten_interpreter_rows(
    interpreter: InterpreterBase,
) -> list[tuple[list[FixtureBase], str]]:
    """Return one ``(group, str(interpreter))`` row per leaf interpreter.

    A :class:`CompositeInterpreter` partitions its ``group`` across children —
    printing it as a single row against its flat group would imply every child
    applies to every fixture, which is wrong. Expand to one row per child so
    the tree reflects the real dispatch.
    """
    if isinstance(interpreter, CompositeInterpreter):
        rows: list[tuple[list[FixtureBase], str]] = []
        for child in interpreter.children:
            rows.extend(_flatten_interpreter_rows(child))
        return rows
    return [(list(interpreter.group), str(interpreter))]


class Director:
    def __init__(self, state: State, vj_director=None):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()
        self.shift_count = 0
        self.start_time = time.time()
        self.state = state
        self.vj_director = vj_director

        # Initialize position manager first (so fixtures have positions before interpreters are created)
        self.position_manager = FixturePositionManager(state)

        self.setup_patch(reset_vj=True)
        self.generate_color_scheme()

        self.warmup_complete = False

        # Register event handlers
        self.state.events.on_mode_change += self.on_mode_change
        self.state.events.on_theme_change += lambda s: self.generate_color_scheme()
        self.state.events.on_venue_change += lambda s: self.setup_patch(reset_vj=False)

    def setup_patch(self, reset_vj: bool = False):
        self.group_fixtures()
        self.generate_interpreters()
        if reset_vj and self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

    def group_fixtures(self):
        """Partition the runtime patch into one bucket per cloud group.

        Every fixture in the venue editor can be tagged with a cloud group
        name (the "SHEER LIGHTS" / "TRACK" / "TRUSS MOVERS" pills in the
        editor sidebar). Each distinct name becomes its own top-level
        bucket here, so the mode DSL runs independently per group — two
        separately-named groups of the same fixture class will therefore
        get independent random picks, rather than collapsing onto a single
        ``MovingHead`` row. Fixtures without a cloud group share a trailing
        "ungrouped" bucket.

        ``ManualGroup`` members are skipped entirely (they are driven by
        manual UI sliders, not interpreters). Within each bucket
        :func:`get_interpreter` handles any class-level partitioning via
        :class:`CompositeInterpreter`, so a cloud group that mixes e.g. a
        mirrorball with moving heads still dispatches each class to its own
        interpreter pack.
        """
        self.fixture_groups: list[list[FixtureBase]] = []
        self.fixture_group_names: list[str | None] = []

        bucket_index: dict[str, int] = {}
        ungrouped: list[FixtureBase] = []

        for fixture in _flatten_runtime_fixtures(get_runtime_fixtures(self.state)):
            raw = getattr(fixture, "cloud_group_name", None)
            name = raw.strip() if isinstance(raw, str) and raw.strip() else None
            if name is None:
                ungrouped.append(fixture)
                continue
            key = name.casefold()
            if key not in bucket_index:
                bucket_index[key] = len(self.fixture_groups)
                self.fixture_groups.append([])
                self.fixture_group_names.append(name)
            self.fixture_groups[bucket_index[key]].append(fixture)

        if ungrouped:
            self.fixture_groups.append(ungrouped)
            self.fixture_group_names.append(None)

    def format_fixture_names(self, fixtures):
        # Format fixtures
        fixtures = [str(j) for j in fixtures]
        if len(fixtures) == 1:
            return fixtures[0]
        
        # Group fixtures by type (base name)
        grouped = defaultdict(list)
        for f in fixtures:
            parts = f.split(" @ ")
            base_name = parts[0]
            address = int(parts[1])
            grouped[base_name].append(address)
        
        # Format each group: "type @ addr1, addr2, addr3"
        parts = []
        for base_name in sorted(grouped.keys()):
            addresses = sorted(grouped[base_name])
            addr_str = ", ".join(str(addr) for addr in addresses)
            parts.append(f"{base_name} @ {addr_str}")
        
        return "; ".join(parts)

    def print_lighting_tree(self, mode_name: str | None = None):
        """Print a tree representation of the lighting interpreters.

        The outer iteration is one entry per cloud group (plus an optional
        "ungrouped" trailing bucket). Each bucket's interpreter may be a
        :class:`CompositeInterpreter` whose children each apply to a different
        class-partitioned sub-group; those are flattened into one row per
        child so each sub-group displays its own fixtures and interpreter.

        Group names are rendered as plain headers (``└── GROUP NAME``) so it
        is obvious from the log which partition a given row belongs to and
        why two otherwise-identical fixture classes may receive different
        randomized picks.
        """
        name_for_header = (mode_name or self.state.mode.name).capitalize()
        result = f"{name_for_header} interpretation:\n"

        if not self.interpreters:
            result += "└── (no interpreters)\n"
            return result

        sections: list[tuple[str | None, list[tuple[list[FixtureBase], str]]]] = []
        for name, interpreter in zip(self.fixture_group_names, self.interpreters):
            rows = _flatten_interpreter_rows(interpreter)
            if rows:
                sections.append((name, rows))

        for s_idx, (name, rows) in enumerate(sections):
            is_last_section = s_idx == len(sections) - 1
            section_connector = "└── " if is_last_section else "├── "
            header_label = name if name is not None else "ungrouped"
            result += f"{section_connector}{Fore.MAGENTA}{header_label}{Style.RESET_ALL}\n"

            section_pipe = "    " if is_last_section else "│   "
            for r_idx, (group, interpreter_str_raw) in enumerate(rows):
                is_last_row = r_idx == len(rows) - 1
                row_connector = "└── " if is_last_row else "├── "
                fixture_str = self.format_fixture_names(group)
                interpreter_str = re.sub(r"\x1b\[[0-9;]*m", "", interpreter_str_raw)
                result += (
                    f"{section_pipe}{row_connector}"
                    f"{Fore.BLUE}{fixture_str}{Style.RESET_ALL} {interpreter_str}\n"
                )

        return result

    def generate_interpreters(self):
        """Generate interpreters for lighting only (does not affect VJ)"""
        self.interpreters: List[InterpreterBase] = [
            get_interpreter(
                self.state.mode,
                group,
                InterpreterArgs(
                    HYPE_BUCKETS[idx % len(HYPE_BUCKETS)],
                    self.state.theme.allow_rainbows,
                    0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
                    (
                        100
                        if not self.state.hype_limiter
                        else min(100, self.state.hype + 30)
                    ),
                ),
            )
            for idx, group in enumerate(self.fixture_groups)
        ]

        print(self.print_lighting_tree(self.state.mode.name))

    def generate_all(self):
        """Generate both lighting interpreters and VJ visuals"""
        self.generate_interpreters()

        # Also shift VJ director with high threshold for "shift all" (complete regeneration)
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

    def generate_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        self.scheme.push(s)
        print(f"Shifting to {format_color_scheme(s)}")

    def shift_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        st = s.to_list()
        current = self.scheme.render()
        ct = current.to_list()
        idx = random.randint(0, 2)
        ct[idx] = st[idx]
        new_scheme = ColorScheme.from_list(
            ct, allows_rainbow=current.allows_rainbow or s.allows_rainbow
        )
        self.scheme.push(new_scheme)
        print(f"Shifting to {format_color_scheme(new_scheme)}")

    def shift_interpreter(self):
        eviction_index = random.randint(0, len(self.interpreters) - 1)
        eviction_group = self.fixture_groups[eviction_index]

        hype_bracket = (
            0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
            100 if not self.state.hype_limiter else min(100, self.state.hype + 30),
        )

        self.interpreters[eviction_index] = get_interpreter(
            self.state.mode,
            eviction_group,
            InterpreterArgs(
                self.state.hype,
                self.state.theme.allow_rainbows,
                hype_bracket[0],
                hype_bracket[1],
            ),
        )

    def ensure_each_signal_is_enabled(self):
        """Makes a list of every interpreter that is a SignalSwitch. Then for each signal they handle, ensures
        at least one interpreter handles it. If not, a randomly selected SignalSwitch has the un-handled signal enabled.
        """
        signal_switches = [
            i
            for i in self.interpreters
            if hasattr(i, "responds_to") and hasattr(i, "set_enabled")
        ]
        if not signal_switches:
            return

        for signal in FrameSignal:
            if not any(i.responds_to.get(signal, False) for i in signal_switches):
                random.choice(signal_switches).set_enabled(signal, True)

    def shift_lighting_only(self):
        """Full shift of DMX lighting only (no VJ changes) - regenerates all interpreters"""
        self.generate_color_scheme()

        # Regenerate all interpreters (similar to generate_interpreters but without VJ shift)
        self.interpreters: List[InterpreterBase] = [
            get_interpreter(
                self.state.mode,
                group,
                InterpreterArgs(
                    HYPE_BUCKETS[idx % len(HYPE_BUCKETS)],
                    self.state.theme.allow_rainbows,
                    0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
                    (
                        100
                        if not self.state.hype_limiter
                        else min(100, self.state.hype + 30)
                    ),
                ),
            )
            for idx, group in enumerate(self.fixture_groups)
        ]

        self.ensure_each_signal_is_enabled()

        self.last_shift_time = time.time()
        self.shift_count += 1

        # Print the tree structure after shift
        print(self.print_lighting_tree(self.state.mode.name))

    def shift_vj_only(self):
        """Full shift of VJ visuals only (no lighting changes) - complete regeneration"""
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

    def shift(self):
        """Shift DMX lighting and VJ together"""
        self.shift_color_scheme()
        self.shift_interpreter()
        self.ensure_each_signal_is_enabled()

        # Shift VJ director if available (with moderate threshold for subtle changes)
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=0.3)

        self.last_shift_time = time.time()
        self.shift_count += 1

        # Print the tree structure after shift
        print(self.print_lighting_tree(self.state.mode.name))

    def step(self, frame: Frame):
        self.last_frame = frame
        scheme = self.scheme.render()
        run_time = time.time() - self.start_time
        warmup_phase = min(1, run_time / WARMUP_SECONDS)

        if warmup_phase == 1 and not self.warmup_complete:
            self.warmup_complete = True

        frame = frame * warmup_phase

        # Reset fixture state before interpreter step() calls
        # This ensures strobe values accumulate using max(existing, new)
        for fixture in get_runtime_fixtures(self.state):
            fixture.begin()

        for i in self.interpreters:
            i.step(frame, scheme)

        # Pass frame and scheme to VJ system for rendering
        if self.vj_director:
            self.vj_director.step(frame, scheme)

        if (
            time.time() - self.last_shift_time > SHIFT_AFTER
            and frame[FrameSignal.sustained_low] < 0.2
        ):
            for i in self.interpreters:
                i.exit(frame, scheme)
            self.shift()

    def render(self, dmx):
        # Get manual group and set its dimmer value
        manual_group = get_runtime_manual_group(self.state)
        if manual_group:
            manual_group.apply_manual_levels(self.state.manual_fixture_dimmers)
            manual_group.render(dmx)

        # Render all fixtures
        for i in get_runtime_fixtures(self.state):
            i.render(dmx)

        dmx.submit()

    def on_mode_change(self, mode):
        """Handle mode changes, including those from the web interface."""
        print(f"mode changed to: {mode.name}")
        # Regenerate lighting interpreters only (VJ is independent)
        self.generate_interpreters()
        print(self.print_lighting_tree(mode.name))
