import unittest
from unittest.mock import MagicMock, patch
import time
import tempfile
import shutil
import os
from parrot.director.director import Director
from parrot.state import State
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.fixtures.base import FixtureGroup
from parrot.fixtures.led_par import ParRGB
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.chauvet import ChauvetSpot160_12Ch


class TestDirector(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test isolation
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        self.state = State()
        self.director = Director(self.state)

    def tearDown(self):
        """Clean up after each test method."""
        # Change back to original directory first
        os.chdir(self.original_cwd)
        # Clean up entire temp directory and all its contents
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_isolation_from_real_state_file(self):
        """Test that tests run in isolated temp directory, not touching real state.json"""
        # Verify we're in a temp directory (use realpath to resolve symlinks on macOS)
        current_dir = os.path.realpath(os.getcwd())
        temp_dir = os.path.realpath(self.temp_dir)
        self.assertEqual(current_dir, temp_dir)
        self.assertTrue("/tmp" in current_dir or "/var/folders" in current_dir)

        # Verify we're NOT in the project directory
        self.assertNotEqual(current_dir, os.path.realpath(self.original_cwd))

    def test_initialization(self):
        """Test that the director initializes correctly"""
        self.assertIsNotNone(self.director.scheme)
        self.assertEqual(self.director.state, self.state)
        self.assertFalse(self.director.warmup_complete)

    def test_setup_patch(self):
        """Test that setup_patch creates fixture groups and interpreters"""
        self.director.setup_patch()
        self.assertIsNotNone(self.director.fixture_groups)
        self.assertIsNotNone(self.director.interpreters)

    def test_mode_change(self):
        """Test that mode changes trigger interpreter regeneration"""
        with patch.object(self.director, "generate_interpreters") as mock_gen:
            self.director.on_mode_change(Mode.rave)
            mock_gen.assert_called_once()

    def test_shift_color_scheme(self):
        """Test that color scheme shifting works"""
        original_scheme = self.director.scheme.render()
        self.director.shift_color_scheme()
        new_scheme = self.director.scheme.render()
        self.assertNotEqual(original_scheme, new_scheme)

    def test_manual_fixtures_rendered_to_dmx(self):
        """Test that manual fixtures are rendered to DMX output when present"""
        from parrot.patch_bay import venues, get_manual_group

        self.state.set_venue(venues.mtn_lotus)

        mock_dmx = MagicMock()

        manual_group = get_manual_group(self.state.venue)
        self.assertIsNotNone(manual_group, "mtn_lotus should have manual fixtures")

        with patch.object(manual_group, 'render', wraps=manual_group.render) as mock_render:
            self.director.render(mock_dmx)
            mock_render.assert_called_once_with(mock_dmx)

        mock_dmx.submit.assert_called_once()


class TestDirectorTestModeDispatch(unittest.TestCase):
    """Regression guard for the per-cloud-group dispatch invariant.

    The director partitions the runtime patch by ``cloud_group_name`` and
    runs the mode DSL once per bucket, so:

    1. A cloud group that mixes a mirrorball with moving heads dispatches
       via :class:`CompositeInterpreter` so each class gets its own
       interpreter pack (the original bug: moving heads silently inherited
       the mirrorball's ``Dimmer255 + RigColorCycle`` and never received
       ``PanTiltAxisCheck``, so the physical heads did not move).

    2. Two separately-named cloud groups of the same fixture class get
       independent random picks rather than collapsing onto one row
       (the follow-up user report: "TRACK" and "TRUSS MOVERS" were being
       lumped together under one ``MovingHead`` interpreter).
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self.state = State()

    def tearDown(self):
        os.chdir(self.original_cwd)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @staticmethod
    def _collect_leaves(interpreter):
        """Flatten a (possibly nested) interpreter tree into concrete leaves.

        ``combo(...)`` wraps children in ``self.interpreters``; ``randomize``
        picks one option and stores it on ``self.interpreter`` (singular).
        We recurse through both.
        """
        leaves = []
        stack = [interpreter]
        while stack:
            node = stack.pop()
            picked = getattr(node, "interpreter", None)
            children = getattr(node, "interpreters", None)
            if children is not None:
                stack.extend(children)
            elif picked is not None:
                stack.append(picked)
            else:
                leaves.append(node)
        return leaves

    def _build_heterogeneous_cloud_group(self, group_name: str = "sheer lights"):
        """Mimics a venue where the editor bundled a mirrorball + moving
        heads under a single ``group_name`` (e.g. "sheer lights").

        The mirrorball is listed first so it becomes ``fixture_group[0]`` —
        which is exactly the ordering that triggered the original bug.
        Every member has ``cloud_group_name`` set to mirror what the cloud
        ``_apply_transform`` does for spec-built fixtures.
        """
        mirrorball = Mirrorball(237)
        movers = [ChauvetSpot160_12Ch(patch=1 + idx * 12) for idx in range(3)]
        members = [mirrorball, *movers]
        for m in members:
            m.cloud_group_name = group_name
        return mirrorball, movers, FixtureGroup(members, name=group_name)

    @staticmethod
    def _composite_children(interpreter):
        from parrot.director.mode_dispatch import CompositeInterpreter

        if isinstance(interpreter, CompositeInterpreter):
            return list(interpreter.children)
        return [interpreter]

    def _leaves_for_group(self, director, fixtures):
        """Return the interpreter leaves dispatched to exactly ``fixtures``.

        Walks every bucket in ``director.interpreters`` and expands any
        :class:`CompositeInterpreter` into its per-class children so the
        caller can match the specific partition they care about.
        """
        target = set(id(f) for f in fixtures)
        for interp in director.interpreters:
            for child in self._composite_children(interp):
                if set(id(f) for f in child.group) == target:
                    return self._collect_leaves(child)
        return None

    def _install_runtime_patch(self, fixtures):
        """Inject a runtime patch without needing a real venue DB."""
        self.state._runtime_patch = list(fixtures)
        self.state._runtime_manual_group = None

    def _director_for_mode(self, mode, fixtures):
        self._install_runtime_patch(fixtures)
        self.state.set_mode(mode)
        director = Director(self.state)
        return director

    def test_heterogeneous_cloud_group_is_one_bucket_with_composite(self):
        """A mixed cloud group stays in one top-level bucket (preserving its
        group identity in the printed tree and snapshot), but the dispatcher
        returns a :class:`CompositeInterpreter` so each class still gets its
        own interpreter row."""
        from parrot.director.mode_dispatch import CompositeInterpreter

        mirrorball, movers, group = self._build_heterogeneous_cloud_group()
        director = self._director_for_mode(Mode.test, [group])

        self.assertEqual(len(director.fixture_groups), 1)
        self.assertEqual(director.fixture_group_names, ["sheer lights"])
        self.assertEqual(
            set(id(f) for f in director.fixture_groups[0]),
            set(id(f) for f in [mirrorball, *movers]),
        )

        self.assertEqual(len(director.interpreters), 1)
        composite = director.interpreters[0]
        self.assertIsInstance(composite, CompositeInterpreter)
        child_groups = [set(id(f) for f in c.group) for c in composite.children]
        self.assertIn({id(mirrorball)}, child_groups)
        self.assertIn(set(id(m) for m in movers), child_groups)

    def test_test_mode_applies_pan_tilt_axis_check_to_moving_heads(self):
        """In ``Mode.test`` the moving heads must receive
        ``PanTiltAxisCheck`` even when bundled in a mixed cloud group with a
        mirrorball (the original failure mode left them only with
        ``Dimmer255 + RigColorCycle``)."""
        _, movers, group = self._build_heterogeneous_cloud_group()
        director = self._director_for_mode(Mode.test, [group])

        leaves = self._leaves_for_group(director, movers)
        self.assertIsNotNone(leaves, "movers partition missing from composite")
        leaf_names = {type(leaf).__name__ for leaf in leaves}
        self.assertIn("PanTiltAxisCheck", leaf_names)
        self.assertIn("Dimmer255", leaf_names)
        self.assertIn("RigColorCycle", leaf_names)

    def test_test_mode_does_not_apply_pan_tilt_to_mirrorball(self):
        """The mirrorball has no pan/tilt motors, so its row must stay on
        the ``Dimmer255 + RigColorCycle`` combo and never pick up
        ``PanTiltAxisCheck`` (doing so would try to call ``set_pan`` on it)."""
        mirrorball, _, group = self._build_heterogeneous_cloud_group()
        director = self._director_for_mode(Mode.test, [group])

        leaves = self._leaves_for_group(director, [mirrorball])
        self.assertIsNotNone(leaves, "mirrorball partition missing from composite")
        leaf_names = {type(leaf).__name__ for leaf in leaves}
        self.assertIn("Dimmer255", leaf_names)
        self.assertIn("RigColorCycle", leaf_names)
        self.assertNotIn("PanTiltAxisCheck", leaf_names)

    def test_test_mode_interpreter_drives_all_pan_tilt_extremes(self):
        """Drive the mover interpreter directly across the full
        ``PanTiltAxisCheck.SEQUENCE`` and verify every moving head receives
        each extreme pose. This is the property the user actually observed
        was missing on the rig (no movement at all).

        We bypass ``Director.step`` here because ``Frame.__mul__`` rebuilds
        the frame with ``time.perf_counter()``, overwriting any time we try
        to pin in the test. Interpreters receive the scaled frame, so driving
        them directly is both simpler and more deterministic.
        """
        from parrot.interpreters.mode_test_interpreters import PanTiltAxisCheck
        from parrot.director.color_scheme import ColorScheme
        from parrot.utils.colour import Color

        _, movers, group = self._build_heterogeneous_cloud_group()
        director = self._director_for_mode(Mode.test, [group])

        pan_seen = {id(m): set() for m in movers}
        tilt_seen = {id(m): set() for m in movers}
        for m in movers:
            m.set_pan = lambda v, _m=m: pan_seen[id(_m)].add(v)
            m.set_tilt = lambda v, _m=m: tilt_seen[id(_m)].add(v)

        # The heterogeneous cloud group dispatches to a CompositeInterpreter;
        # the mover-class child is the one we want to drive directly.
        composite = director.interpreters[0]
        mover_interp = next(
            c for c in self._composite_children(composite)
            if set(id(f) for f in c.group) == set(id(m) for m in movers)
        )
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Step the interpreter across one full sequence period so every pose
        # (center + four extremes) is visited regardless of perf_counter drift.
        base_time = 0.0
        for step_idx in range(len(PanTiltAxisCheck.SEQUENCE)):
            frame = Frame(
                {signal: 0.1 for signal in FrameSignal},
                {signal.name: [0.1] * 4 for signal in FrameSignal},
            )
            frame.time = base_time + step_idx * PanTiltAxisCheck.SECONDS_PER_STEP + 0.1
            mover_interp.step(frame, scheme)

        expected_pans = {pan for pan, _ in PanTiltAxisCheck.SEQUENCE}
        expected_tilts = {tilt for _, tilt in PanTiltAxisCheck.SEQUENCE}
        for m in movers:
            self.assertEqual(
                pan_seen[id(m)], expected_pans,
                f"{m} missing pan extremes; saw {pan_seen[id(m)]}",
            )
            self.assertEqual(
                tilt_seen[id(m)], expected_tilts,
                f"{m} missing tilt extremes; saw {tilt_seen[id(m)]}",
            )

    def test_ungrouped_mirrorball_gets_its_own_interpreter_partition(self):
        """Sanity: even though both the mirrorball and the par land in the
        single "ungrouped" bucket, the dispatcher must still partition by
        class so the mirrorball does not fall into the ``Par`` bucket (it
        is a ``Par`` subclass) and end up with the par interpreter.
        """
        mirrorball = Mirrorball(237)
        par = ParRGB(100)
        director = self._director_for_mode(Mode.test, [mirrorball, par])

        # One bucket (both fixtures are ungrouped) with the ungrouped label.
        self.assertEqual(len(director.fixture_groups), 1)
        self.assertEqual(director.fixture_group_names, [None])

        mb_leaves = self._leaves_for_group(director, [mirrorball])
        par_leaves = self._leaves_for_group(director, [par])
        self.assertIsNotNone(mb_leaves)
        self.assertIsNotNone(par_leaves)
        # The two partitions must be different interpreter leaves — if the
        # dispatcher collapsed them onto one row they would share identity.
        self.assertNotEqual(
            {type(leaf).__name__ for leaf in mb_leaves},
            {type(leaf).__name__ for leaf in par_leaves}.union({"PanTiltAxisCheck"}),
        )

    def test_same_class_in_two_cloud_groups_gets_independent_buckets(self):
        """Two separately-named cloud groups of the same fixture class must
        produce two distinct buckets (and therefore two independent random
        picks from the mode DSL). This is the TRACK / TRUSS MOVERS case."""
        import random as _random

        _random.seed(0)
        track_movers = [ChauvetSpot160_12Ch(patch=1 + i * 12) for i in range(3)]
        for m in track_movers:
            m.cloud_group_name = "track"
        truss_movers = [ChauvetSpot160_12Ch(patch=40 + i * 12) for i in range(3)]
        for m in truss_movers:
            m.cloud_group_name = "truss movers"

        track_group = FixtureGroup(list(track_movers), name="track")
        truss_group = FixtureGroup(list(truss_movers), name="truss movers")
        director = self._director_for_mode(Mode.rave, [track_group, truss_group])

        # Each cloud group becomes its own bucket; names appear in the
        # printed tree so the two partitions are visually distinguishable.
        self.assertEqual(len(director.fixture_groups), 2)
        self.assertEqual(set(director.fixture_group_names), {"track", "truss movers"})

        # Each bucket's interpreter binds to exactly the members of that
        # cloud group; they are distinct objects, i.e. picked independently.
        bucket_by_name = dict(
            zip(director.fixture_group_names, director.interpreters)
        )
        self.assertEqual(
            set(id(f) for f in bucket_by_name["track"].group),
            set(id(m) for m in track_movers),
        )
        self.assertEqual(
            set(id(f) for f in bucket_by_name["truss movers"].group),
            set(id(m) for m in truss_movers),
        )
        self.assertIsNot(bucket_by_name["track"], bucket_by_name["truss movers"])

    def test_print_lighting_tree_shows_cloud_group_names(self):
        """The printed lighting tree must label each bucket with its cloud
        group name so it is obvious which group a row belongs to."""
        track_movers = [ChauvetSpot160_12Ch(patch=1 + i * 12) for i in range(2)]
        for m in track_movers:
            m.cloud_group_name = "track"
        truss_movers = [ChauvetSpot160_12Ch(patch=40 + i * 12) for i in range(2)]
        for m in truss_movers:
            m.cloud_group_name = "truss movers"
        loose = Mirrorball(237)

        director = self._director_for_mode(
            Mode.rave,
            [
                FixtureGroup(list(track_movers), name="track"),
                FixtureGroup(list(truss_movers), name="truss movers"),
                loose,
            ],
        )
        tree = director.print_lighting_tree()
        self.assertIn("[track]", tree)
        self.assertIn("[truss movers]", tree)
        self.assertIn("[(ungrouped)]", tree)


if __name__ == "__main__":
    unittest.main()
