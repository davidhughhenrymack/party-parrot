import random
import re
import time
import os
from collections import defaultdict
from colorama import Fore, Style
from parrot.director.frame import Frame, FrameSignal

from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from .mode_dispatch import CompositeInterpreter, get_interpreter

from parrot.utils.lerp import LerpAnimator
from parrot.state import State
from parrot.utils.color_utils import format_color_scheme
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.venue_runtime import (
    get_runtime_fixtures,
    get_runtime_manual_group,
    replace_fixture_leaf_in_runtime_patch,
)
from parrot.director.interpretation_blend import InterpretationBlend

SHIFT_AFTER = 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "1")), 1)
INTERPRETATION_BLEND_SECONDS = max(
    float(os.environ.get("INTERPRETATION_BLEND_SECONDS", "2.0")), 0.05
)

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
        self._interpretation_blend: InterpretationBlend | None = None
        self._pending_regenerate_interpreters = False
        self._force_fresh_interpreters = False

        # Register event handlers
        self.state.events.on_mode_change += self.on_mode_change
        self.state.events.on_theme_change += lambda s: self.generate_color_scheme()
        self.state.events.on_venue_change += lambda s: self.setup_patch(reset_vj=False)

    def setup_patch(self, reset_vj: bool = False):
        self._interpretation_blend = None
        self._pending_regenerate_interpreters = False
        self._force_fresh_interpreters = True
        self.group_fixtures()
        self.generate_interpreters()
        self._force_fresh_interpreters = False
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

    def _default_interpreter_args_for_bucket_index(self, idx: int) -> InterpreterArgs:
        return InterpreterArgs(self.state.theme.allow_rainbows)

    def _interpreter_args_for_auto_shift_eviction(self) -> InterpreterArgs:
        return InterpreterArgs(self.state.theme.allow_rainbows)

    def _start_interpretation_blend(
        self,
        bucket_indices: list[int],
        args_by_bucket: dict[int, InterpreterArgs],
    ) -> None:
        incoming_interpreters: dict[int, InterpreterBase] = {}
        incoming_fixtures: dict[int, list[FixtureBase]] = {}
        lerp_fixtures: dict[int, list[FixtureBase]] = {}
        for i in bucket_indices:
            group = self.fixture_groups[i]
            incoming_fixtures[i] = [f.transition_clone() for f in group]
            lerp_fixtures[i] = [f.transition_clone() for f in group]
            incoming_interpreters[i] = get_interpreter(
                self.state.mode,
                incoming_fixtures[i],
                args_by_bucket[i],
            )
        self._interpretation_blend = InterpretationBlend(
            start_time=time.time(),
            bucket_indices=frozenset(bucket_indices),
            incoming_interpreters=incoming_interpreters,
            incoming_fixtures=incoming_fixtures,
            lerp_fixtures=lerp_fixtures,
        )

    def _finish_interpretation_blend(self, frame: Frame, scheme: ColorScheme) -> None:
        b = self._interpretation_blend
        if b is None:
            return
        for i in b.bucket_indices:
            self.interpreters[i].exit(frame, scheme)
        patch = get_runtime_fixtures(self.state)
        for i in b.bucket_indices:
            olds = list(self.fixture_groups[i])
            news = b.incoming_fixtures[i]
            for old_f, new_f in zip(olds, news):
                replaced = replace_fixture_leaf_in_runtime_patch(patch, old_f, new_f)
                if not replaced:
                    raise RuntimeError(
                        "Failed to promote incoming fixture into runtime patch"
                    )
            self.fixture_groups[i] = list(news)
            self.interpreters[i] = b.incoming_interpreters[i]
        self._interpretation_blend = None
        self.last_shift_time = time.time()
        if self._pending_regenerate_interpreters:
            self._pending_regenerate_interpreters = False
            self.generate_interpreters()

    def resolve_output_fixture(self, primary: FixtureBase) -> FixtureBase:
        b = self._interpretation_blend
        if b is None:
            return primary
        for i in b.bucket_indices:
            group = self.fixture_groups[i]
            for k, f in enumerate(group):
                if f is primary:
                    return b.lerp_fixtures[i][k]
        return primary

    def output_fixture_overrides_by_spec_id(self) -> dict[str, FixtureBase]:
        b = self._interpretation_blend
        if b is None:
            return {}
        out: dict[str, FixtureBase] = {}
        for i in b.bucket_indices:
            for k, primary in enumerate(self.fixture_groups[i]):
                cid = getattr(primary, "cloud_spec_id", None)
                if cid is not None:
                    out[str(cid)] = b.lerp_fixtures[i][k]
        return out

    def _effective_interpreters_for_signals(self) -> list[InterpreterBase]:
        if self._interpretation_blend is None:
            return self.interpreters
        b = self._interpretation_blend
        return [
            (
                b.incoming_interpreters[idx]
                if idx in b.bucket_indices
                else self.interpreters[idx]
            )
            for idx in range(len(self.interpreters))
        ]

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
            result += (
                f"{section_connector}{Fore.MAGENTA}{header_label}{Style.RESET_ALL}\n"
            )

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
        if self._interpretation_blend is not None:
            self._pending_regenerate_interpreters = True
            return
        n = len(self.fixture_groups)
        if n == 0:
            self.interpreters = []
            print(self.print_lighting_tree(self.state.mode.name))
            return
        is_regen = (
            not self._force_fresh_interpreters
            and hasattr(self, "interpreters")
            and len(self.interpreters) == n
        )
        if is_regen:
            args_by_bucket = {
                idx: self._default_interpreter_args_for_bucket_index(idx)
                for idx in range(n)
            }
            self._start_interpretation_blend(list(range(n)), args_by_bucket)
        else:
            self.interpreters = [
                get_interpreter(
                    self.state.mode,
                    group,
                    self._default_interpreter_args_for_bucket_index(idx),
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

    def ensure_each_signal_is_enabled(self):
        """Makes a list of every interpreter that is a SignalSwitch. Then for each signal they handle, ensures
        at least one interpreter handles it. If not, a randomly selected SignalSwitch has the un-handled signal enabled.
        """
        signal_switches = [
            i
            for i in self._effective_interpreters_for_signals()
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
        self.generate_interpreters()
        self.ensure_each_signal_is_enabled()
        self.shift_count += 1
        print(self.print_lighting_tree(self.state.mode.name))

    def shift_vj_only(self):
        """Full shift of VJ visuals only (no lighting changes) - complete regeneration"""
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

    def step(self, frame: Frame):
        self.last_frame = frame
        scheme = self.scheme.render()
        run_time = time.time() - self.start_time
        warmup_phase = min(1, run_time / WARMUP_SECONDS)

        if warmup_phase == 1 and not self.warmup_complete:
            self.warmup_complete = True

        frame = frame * warmup_phase

        if self._interpretation_blend is not None:
            b = self._interpretation_blend
            t_done = (time.time() - b.start_time) / INTERPRETATION_BLEND_SECONDS
            if t_done >= 1.0:
                self._finish_interpretation_blend(frame, scheme)
                scheme = self.scheme.render()

        # Reset fixture state before interpreter step() calls
        # This ensures strobe values accumulate using max(existing, new)
        for fixture in get_runtime_fixtures(self.state):
            fixture.begin()

        if self._interpretation_blend is not None:
            b = self._interpretation_blend
            for i in b.bucket_indices:
                for f in b.incoming_fixtures[i]:
                    f.begin()

        for idx, interp in enumerate(self.interpreters):
            interp.step(frame, scheme)

        if self._interpretation_blend is not None:
            b = self._interpretation_blend
            for i in b.bucket_indices:
                b.incoming_interpreters[i].step(frame, scheme)
            t = min(
                1.0,
                (time.time() - b.start_time) / INTERPRETATION_BLEND_SECONDS,
            )
            for i in b.bucket_indices:
                for k in range(len(self.fixture_groups[i])):
                    b.lerp_fixtures[i][k].lerp_into(
                        self.fixture_groups[i][k],
                        b.incoming_fixtures[i][k],
                        t,
                    )

        # Pass frame and scheme to VJ system for rendering
        if self.vj_director:
            self.vj_director.step(frame, scheme)

        if (
            self._interpretation_blend is None
            and len(self.interpreters) > 0
            and time.time() - self.last_shift_time > SHIFT_AFTER
            and frame[FrameSignal.sustained_low] < 0.2
        ):
            eviction_index = random.randint(0, len(self.interpreters) - 1)
            for idx, interp in enumerate(self.interpreters):
                if idx != eviction_index:
                    interp.exit(frame, scheme)
            self._start_interpretation_blend(
                [eviction_index],
                {eviction_index: self._interpreter_args_for_auto_shift_eviction()},
            )
            self.shift_color_scheme()
            self.ensure_each_signal_is_enabled()
            if self.vj_director:
                self.vj_director.shift(self.state.vj_mode, threshold=0.3)
            self.shift_count += 1
            print(self.print_lighting_tree(self.state.mode.name))

    def render(self, dmx):
        # Get manual group and set its dimmer value
        manual_group = get_runtime_manual_group(self.state)
        if manual_group:
            manual_group.apply_manual_levels(self.state.manual_fixture_dimmers)
            manual_group.render(dmx)

        for item in get_runtime_fixtures(self.state):
            if isinstance(item, FixtureGroup):
                for leaf in item.fixtures:
                    self.resolve_output_fixture(leaf).render(dmx)
            else:
                self.resolve_output_fixture(item).render(dmx)

        dmx.submit()

    def on_mode_change(self, mode):
        """Handle mode changes, including those from the web interface."""
        print(f"mode changed to: {mode.name}")
        # Regenerate lighting interpreters only (VJ is independent)
        self.generate_interpreters()
        print(self.print_lighting_tree(mode.name))
