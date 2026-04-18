# Party Parrot — Code Review

Scope: recent refactors and additions across `parrot/director`, `parrot/interpreters`,
`parrot/fixtures`, `parrot/vj`, `parrot_cloud`, and the desktop ↔ cloud bridge
(`parrot/api`, `parrot/runtime_venue_client.py`, `parrot/runtime_fixture_state.py`).

Read as: what's working, what's shaky, and what to change next. File:line
citations below are accurate as of this review; line numbers may drift as code
evolves.

---

## TL;DR

- The recent DSL + mode work is the strongest area: `MODES_BY_HYPE`,
  `CompositeInterpreter`, `print_lighting_tree`, and the pan/tilt range plumbing
  (DB → repo → UI → runtime) are well-factored and tested.
- The weakest area is the fixture layer: inconsistent conventions
  (degrees vs raw DMX, pan/tilt range semantics), a handful of latent DMX width
  bugs, a broken prism channel abstraction, and `cloud_*` attributes leaking
  into `FixtureBase`.
- There are **real latent bugs** to fix: `Director.deploy_hype` crashes when
  called, `motionstrip.py` silently concatenates two DMX slot names,
  `ChauvetSpot160_12Ch` / `ChauvetMove_9Ch` have width-vs-layout mismatches, and
  `Scipy`/`filter_nones`/`RandomPrism`/`RandomFocus` are dead code.
- Client-server architecture is sound but not loud enough about its invariants:
  fixture data is split across typed columns and an untyped `options` JSON
  bag, and the editor frontend both receives WS pushes and polls every 100ms
  "because WS can race HTTP threads."

---

## Good

### Director / interpreter layer
- `parrot/director/mode.py` defines `MODES_BY_HYPE` with runtime assertions
  that the list matches the `Mode` enum exactly. That single source of truth is
  now consumed by the keyboard handler, the overlay menu, the macOS menu
  delegate, and both Flask `/api/mode` endpoints.
- `parrot/director/mode_interpretations.py` is pure data — the "DSL as a dict"
  style is readable, and the separation from `mode_dispatch.py`'s machinery is
  respected.
- `CompositeInterpreter` + the partition loop in `mode_dispatch.py` is compact
  and easy to follow. `_sorted_items` puts `(Group, class)` keys before bare
  `Group` before bare class with a fixture-type tie-break, which is the right
  default for DSL authors.
- `_flatten_interpreter_rows` + the rewritten `print_lighting_tree` in
  `parrot/director/director.py` correctly expand composite interpreters into one
  row per leaf. This addresses the "groups merged on one line" complaint with a
  clean recursive helper.
- `FocusBig`/`FocusSmall`/`RotatePrism`/`PrismOff` form a coherent orthogonal
  set; `Mode.rave` uses group-level `randomize(FocusBig, FocusSmall)` and
  `randomize(RotatePrism, PrismOff)`, and the rewritten
  `test_rave_sheer_lights_randomize_prism_and_focus` proves that both options
  are visited and that movers share one choice per partition.
- `SlowBreath` is a good new primitive: sine dominates, bass is additive and
  clamped, `bass_response` / `bass_smoothing` are explicit.

### Fixtures
- `ChauvetMoverBase` centralises the 0–540°/0–270° → DMX projection and the
  `set(name, value)` pattern keeps the per-personality `dmx_layout` dict as the
  single source of truth.
- `intimidator_hybrid_140sr.py`'s `_Hybrid140SRBase` mixin is the right shape:
  rotating-gobo mapping lives alongside the two personalities that actually
  have it instead of being pushed up into `ChauvetMoverBase`.
- `Mirrorball` is minimal (a `Par` subclass with a single-channel override)
  and has a unit test.

### VJ
- `ConcertStage`'s `LayerCompose` structure (prom `ModeSwitch` + overlays in a
  deterministic order) is easy to reason about.
- `VJMode` + `_LEGACY_VJ_MODE_NAMES` + `parse_vj_mode_string` lets legacy
  persisted `zr_*` values map to prom scenes without exceptions. Good
  backwards-compat hygiene.
- `MovingHeadRenderer` and `DenseSceneController.js` use the **same numeric
  endpoints** (`1.0` wide → `0.22` tight) for focus-driven beam width. Even
  though the representations differ (Python scales cone `end_radius`, Three.js
  scales mesh XZ), the intent is identical.

### Cloud / client-server
- `parrot_cloud/domain.py`'s immutable `VenueSnapshot` / `FixtureSpec` /
  `ControlState` / `RuntimeBootstrap` dataclasses give one shared shape for
  repo, Flask JSON, and `RuntimeVenueClient`.
- Runtime-only state (`fixture_runtime_state`, VJ JPEG preview) lives in
  `VenueRepository` as an in-memory mirror rather than in SQLite — correct
  choice for per-frame data.
- `VenueUpdateHub` takes a per-socket send lock so HTTP worker threads and the
  WS receive loop don't interleave sends on the same client.
- `pickNewerVenueSnapshot` + `summary.revision` in the frontend prevents
  out-of-order WS updates from rewinding the editor after a local PATCH.
- Alembic history is a clean single linear chain (6 revisions) with real
  SQL backfills (`display_mode`, `active_venue_id`, `is_manual`). No orphaned
  revisions.
- State change paths are well-tested: `parrot/test_state.py`,
  `parrot_cloud/test_app.py`, `parrot_cloud/test_repository.py`,
  `parrot_cloud/test_ws_hub.py`, plus the director-level coverage.

---

## Bad

### Latent bugs (fix first)

- **`Director.deploy_hype` will raise `AttributeError` on every call.**
  `parrot/director/director.py:371-372` calls `self.mode_machine.deploy_hype(...)`
  but `mode_machine` is never assigned in `Director.__init__` or anywhere else
  in `parrot/`. `/api/hype` in `parrot/api/web_server.py:101-115` invokes this,
  and `test_web_server.py` only tests it via a Mock director — so the unit
  tests don't catch the bug. Ship-breaking if anything actually hits `/api/hype`.

- **`parrot/fixtures/motionstrip.py:15` silently concatenates two DMX slot names.**
  ```python
  "strobe" "bulb 1: RGBW",   # Python adjacent-string concat → "strobebulb 1: RGBW"
  "bulb 2: RGBW",
  ```
  The missing comma shifts every bulb by one slot and loses the strobe slot
  entirely. This is a real wiring bug masquerading as dead documentation.

- **`ChauvetSpot160_12Ch` width mismatch** (`intimidator160.py:64-66`):
  `dmx_layout` has 12 entries but `super().__init__(..., 11, ...)`. DMX range
  validation will silently clip the `movement_macro_speed` channel and/or
  truncate the address span.

- **`ChauvetMove_9Ch` width mismatch** (`move9.py:56-60`):
  Nine entries in `dmx_layout`, but `width=12`. The class name says 9 channels;
  the runtime reservation says 12. Pick one.

- **Dead imports / dead functions** (cheap wins):
  - `parrot/interpreters/dimmer.py:3` — `import scipy` never used.
  - `parrot/director/director.py:37-38` — `filter_nones` never referenced.
  - `parrot/interpreters/movers.py:176-232` — `RandomPrism` and `RandomFocus`
    classes are defined but have **zero** references after the Rave move to
    group-level `randomize(FocusBig, FocusSmall)` + `randomize(RotatePrism, PrismOff)`.
    These were imported by `mode_interpretations.py` until recently; the
    classes are now leftovers.

### Awkward abstractions / half-finished refactors

- **`set_prism` on `ChauvetMoverBase` is Hybrid-140SR-specific.**
  `mover_base.py:129-153` documents Hybrid's prism1 value ranges and writes to
  the `"prism1"` slot. For movers without `"prism1"` in their layout (e.g.
  Rogue's `"prism"`/`"prism_rotate"`) the state updates but DMX silently does
  nothing. Either move this override into `_Hybrid140SRBase` or make the base
  a no-op with explicit per-subclass overrides.

- **`pan_lower`/`pan_upper` have different semantics in different fixtures.**
  `ChauvetMoverBase` takes them in **degrees** (defaults 270/450) and projects
  to 0–255; `Motionstrip38` takes them as **raw DMX** (defaults 0/255). Same
  field names on the DB side (`_PAN_TILT_RANGE_FIELDS` in `repository.py`),
  two conventions at runtime. A user narrowing a motionstrip's pan range
  through the web editor is editing degrees that get stored as DMX endpoints.

- **`FixtureBase` leaks cloud concerns** (`parrot/fixtures/base.py:25-28`):
  ```python
  self.cloud_spec_id: Optional[str] = None
  self.cloud_fixture_type: Optional[str] = None
  self.cloud_group_name: Optional[str] = None
  self.cloud_is_manual = False
  ```
  `ManualGroup.apply_manual_levels` then does `getattr(fixture, "cloud_spec_id", None)`
  — a base attribute read with `getattr` fallback — violating the project's
  preference for concrete typing.

- **`FixtureInterpreterNode.generate` has `try/except: pass` on interpreter
  teardown** (`parrot/vj/nodes/fixture_interpreter.py:85-90`), directly
  contradicting the `parrot.mdc` rule against `try-except-pass`.

- **`ConcertStage.mode_switch` is actually a `LayerCompose`.** `_create_mode_switch`
  returns a composite (`concert_stage.py:102-106`) and `render`'s docstring says
  "using ModeSwitch" when it's really the full layer stack. Readers will be
  mildly misled.

- **Orphaned `MovingHeadArrayRenderer`** — built in `_create_virtual_moving_heads`
  and assigned to `self.moving_head_renderer`, but nothing composes it into the
  render tree. Either wire it as a `LayerSpec` or delete the factory.

- **`LayerCompose` fragment shader has four blend-mode branches that all do
  the same thing.** Branches 1–3 all compute
  `vec4(tex_color.rgb * opacity, tex_color.a)`. The actual blend difference is
  driven by `blend_func`, so the `blend_mode` uniform + shader branches are
  redundant.

- **`ModeSwitch.generate` uses `hasattr(vibe.mode, "name")`** — a loose duck-type
  check for an enum; `Vibe.mode` should be typed precisely enough to drop the
  fallback.

- **Director signal wiring uses `hasattr` introspection** —
  `ensure_each_signal_is_enabled` (`director.py:259-273`) checks
  `hasattr(interp, "responds_to") and hasattr(interp, "set_enabled")`. A tiny
  Protocol or `isinstance(interp, SignalSwitch)` check would be both stricter
  and cheaper.

- **`combo.py` has two `Combo` classes** — a module-level one and the factory-
  produced inner one — with a misleading return type annotation. Rename or
  collapse.

- **`state.py` lazy-imports `SignalStates` and `FrameSignal`** inside
  `__init__` / `set_effect_thread_safe`. That's a smell for an unresolved
  import cycle rather than genuine runtime need.

- **`state.py` still calls `print` on every mode change** (lines 63–67,
  103–107, and `process_gui_updates`) despite `parrot.mdc` saying "Don't add
  print statements unless asked."

- **`@beartype` removed from `KeyboardHandler` "to allow mocking"**
  (`keyboard_handler.py:15-16`) — weakens the project's typing discipline on
  an input-handling hot path. Prefer a typed Protocol for the mock.

### Cloud / client-server

- **`FixtureModel.options` is an untyped JSON bag** that now holds
  `pan_lower`, `pan_upper`, `tilt_lower`, `tilt_upper`, `dimmer_upper`,
  `invert_pan`, `width`, and more. No schema validation at the DB boundary;
  validators are scattered across `fixture_catalog.py`, `repository.py`
  (`_merge_pan_tilt_range_into_options`, `_hydrate_pan_tilt_range`), and the
  frontend.

- **Fixture identity is split across typed columns and `options` JSON.**
  Transforms (`x`, `y`, `z`, rotations) are typed; everything else is JSON.
  This is the right tradeoff for indexability, but the mental model of "what
  is a fixture" is now distributed across two layers.

- **Dead-ish column: `control_state.manual_dimmer`.** Still declared in
  `models.py:118` and created by the first migration, but `update_control_state`
  and `_control_state_from_model` never read or write it. `manual_fixture_dimmers`
  has superseded it.

- **`display_mode` vs `show_fixture_mode` mirror.** `repository.py:297-298`
  keeps the legacy boolean in sync with the new string. A migration should
  finish this transition.

- **Desktop editor polls `/api/runtime/fixture-state` every 100ms in addition
  to the WS broadcasts** (`DenseVenueEditorPage.jsx:602-625`). The comment says
  "because WS can race HTTP threads," but that's a band-aid: sequence numbers
  or a monotonically increasing `runtime_revision` on the WS payload would let
  us drop the poll entirely.

- **Two Flask apps with overlapping paths.** `parrot/api/web_server.py` and
  `parrot_cloud/app.py` both expose `/api/mode`, `/api/vj_mode`, `/api/effect`.
  Different servers, different responsibilities (desktop mutates `State`
  directly; cloud persists + broadcasts). Not wrong, but easy to confuse when
  debugging. Worth an ADR-style comment.

- **Moving-head type list is hardcoded in two places.**
  `parrot_cloud/frontend/src/fixtureModels.js:15-22` has a JS `MOVING_HEAD_TYPES`
  set; `parrot_cloud/fixture_catalog.py` has the authoritative list. These will
  drift the next time a mover is added.

- **`parrot_cloud/app.py`'s `_log_unhandled` prints and re-raises.** Flask's
  logger will also print → duplicate tracebacks. Either return JSON 500 or
  let Flask log.

- **Desktop `RuntimeVenueClient` swallows errors** with broad `except: pass`
  in the fixture push and WS loops (`runtime_venue_client.py:61-69`). Failures
  are observable only via the `_last_fixture_payload_json = None` reset.

---

## Recommendations (prioritized)

### P0 — Fix latent bugs
1. **Repair or remove `Director.deploy_hype`.** Either wire a real
   `PhraseMachine` (or equivalent) into `Director.__init__`, or delete
   `deploy_hype`, `/api/hype`, and the Mock-only tests. Real behavior first.
2. **Fix `motionstrip.py` layout** — add the missing comma so `strobe` is its
   own slot; verify bulb indices against actual DMX wiring.
3. **Fix `ChauvetSpot160_12Ch` (width 11 → 12) and `ChauvetMove_9Ch`
   (width 12 → 9)** to match their advertised channel counts and `dmx_layout`
   lengths. Add a regression test that asserts
   `fixture.width == len(fixture.dmx_layout)`.
4. **Delete dead code:** `import scipy` in `dimmer.py`, `filter_nones` in
   `director.py`, `RandomPrism`/`RandomFocus` in `movers.py` (plus any stale
   exports).

### P1 — Tighten fixture layer conventions
5. **Move `set_prism`'s Hybrid-specific DMX mapping into `_Hybrid140SRBase`.**
   Leave `ChauvetMoverBase.set_prism` as a no-op default that subclasses
   override when they have a prism channel. Add a test that asserts Rogue's
   prism channel is actually written.
6. **Give pan/tilt range a single convention.** Either: (a) migrate
   `Motionstrip38` to accept degrees and project to DMX internally, matching
   `ChauvetMoverBase`; or (b) rename the motionstrip's fields to
   `pan_dmx_min`/`pan_dmx_max`. Document the chosen convention in the venue
   editor's Pan/Tilt Range panel tooltip.
7. **Get `cloud_*` attributes off `FixtureBase`.** Options:
   - Have `build_runtime_fixture_groups` attach metadata via a side table
     (`dict[id(fixture), CloudMeta]`), or
   - Define a `CloudLabeled` mixin that only the cloud-built fixtures carry.
   - Either way, `ManualGroup.apply_manual_levels` should take a typed
     `Mapping[FixtureBase, str]` rather than reading a dynamic attribute.
8. **Apply `@beartype` uniformly** to `MovingHead`, `Laser`, `ChauvetMoverBase`,
   and `FixtureBase`'s public API (dimmer/color/pan/tilt). The project rule
   is "complete type enforcement"; the fixture layer is the biggest gap.

### P2 — Clean up the VJ and director internals
9. **Rename `ConcertStage.mode_switch` → `stage_composition`** (or
   `root_compose`) and fix the docstring on `render`.
10. **Decide on `MovingHeadArrayRenderer`:** wire it into a `LayerSpec` or
    delete it. It's the clearest "half-finished refactor" artifact in VJ.
11. **Collapse `LayerCompose` shader branches** if GL `blend_func` is doing
    the real work. If not, document why the RGB math differs per branch (right
    now it doesn't).
12. **Replace `hasattr`/`try-except-pass` patterns** in `FixtureInterpreterNode`,
    `FixtureVisualization`, `ModeSwitch`, `position_manager`, and `state.py`'s
    `process_gui_updates` with small `Protocol`s or concrete `isinstance`
    checks. These are the places where the `parrot.mdc` rules are most
    obviously violated.
13. **Resolve `combo.py`'s dual-`Combo` class.** Rename the factory-generated
    class (e.g. `ComboInstance`) and fix `combo(...) -> Combo[T]`.
14. **Drop state import-cycle dance.** Either move `SignalStates` / `FrameSignal`
    to a lower module or document the cycle in a single comment so future
    readers stop tripping on it.
15. **Remove `print` calls from `state.py` and `vj_director.py`** (or gate
    behind a `PARROT_DEBUG` env var). Use `logging` if you want persistent
    traces.

### P3 — Cloud schema and client-server hygiene
16. **Validate `FixtureModel.options` at the repository boundary.** A small
    Pydantic model per fixture type (or a beartyped TypedDict with
    per-type validators) would replace `_merge_pan_tilt_range_into_options`
    and `_hydrate_pan_tilt_range` with a single source of truth.
17. **Replace `_hydrate_pan_tilt_range` with an Alembic backfill.** Read-time
    hydration is a fine stopgap, but a migration makes the DB state actually
    correct and removes an implicit mutation on read.
18. **Drop `control_state.manual_dimmer`.** Write a migration that confirms it
    is zero-valued everywhere and then removes the column.
19. **Finish the `display_mode` transition.** Backfill `show_fixture_mode`
    one last time and drop it, or explicitly document it as the legacy mirror.
20. **Stop polling `/api/runtime/fixture-state` every 100ms.** Add a
    `runtime_revision` counter to the WS payload; the editor can reconcile on
    sequence gaps instead of polling. If WS ordering is genuinely broken, fix
    that first.
21. **Generate `MOVING_HEAD_TYPES` on the frontend** from `/api/config`
    (e.g. expose `has_pan_tilt_range` per fixture type). Avoids silent drift.
22. **Pick one error-handling pattern for the cloud app.** Either JSON 500
    with a structured body from `_log_unhandled`, or let Flask log and remove
    the re-raise + `print_exc`.
23. **Add a README or `ARCHITECTURE.md` snippet** explaining: "Desktop Flask
    (port 5000) mutates `State` directly; Cloud Flask (port 4041) persists to
    SQLite and broadcasts WS. `RuntimeVenueClient` is the bridge." One
    paragraph prevents an entire class of "why are there two `/api/mode`s"
    questions.

### P4 — Docs and polish
24. **Refresh `parrot/vj/overview.md`.** Current text describes an older
    `vj_director` pseudo-code that doesn't match the real
    `ConcertStage` / `LayerCompose` structure.
25. **Fix commented-out dead code** in `parrot/fixtures/led_par.py`
    (`render_color_components` block) and the commented `print` in
    `parrot/fixtures/base.py:render`.
26. **Fix the stale docstring** on `MovingHeadRenderer`
    (`renderers/moving_head.py:42-44`) that still says "beam (TODO)" even
    though beams are implemented.
27. **Add a `len(dmx_layout) == width` assertion** in `ChauvetMoverBase`'s
    constructor. One line, prevents both the 160 and Move9 bugs above from
    recurring.
28. **Add a brief comment at the top of `parrot/director/mode.py`** that lists
    the files to update when adding a new `Mode` (`MODES_BY_HYPE`,
    `mode_interpretations.py`, remote UI). The assertions already prevent
    silent breakage; a checklist prevents churn.

---

## Notes on things that are fine as-is

- The `options` JSON column is the correct tradeoff for type-specific knobs
  that don't need to be indexed. Promoting every key to a column would be
  worse. Validation at the boundary is the real fix (see P3 #16).
- Alembic history is linear and healthy. No reorgs needed.
- `VenueUpdateHub` + per-socket send lock is the correct pattern for
  threaded Flask + flask_sock.
- `pickNewerVenueSnapshot` / `revision` handling in the frontend is the right
  way to reconcile local PATCHes with WS pushes. Keep it.
- The rave sheer-group tests (`test_rave_sheer_lights_randomize_prism_and_focus`)
  are the right model for interpretive-DSL tests — seeded iterations,
  group-wise invariants, coverage of both branches. Replicate this style for
  other `randomize`-heavy modes.
