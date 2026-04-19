import { useEffect, useMemo, useRef, useState } from 'react';
import { createSceneController } from './DenseSceneController.js';
import { isMovingHeadFixtureType } from './fixtureModels.js';
import { isViewportWebGlDisabledForTests } from './viewportTestMode.js';

const isTestMode = isViewportWebGlDisabledForTests();
const FEET_PER_METER = 3.280839895;
const ROTATION_STEP_DEGREES = 45;

// Moving-head pan/tilt geometry. Pan spans 540° physical (0–540 in stored
// degrees); the UI treats 270° as "forward" and lets the user set left/right
// deviations around that center. Tilt spans 270° physical (0–270).
const PAN_MIN_DEG = 0;
const PAN_MAX_DEG = 540;
/** Full mechanical pan sweep in stored degrees (same convention as fixture runtime / `fixture_catalog`). */
const PAN_RANGE_FULL_DEG = Object.freeze({
  pan_lower: PAN_MIN_DEG,
  pan_upper: PAN_MAX_DEG,
});
const PAN_CENTER_DEG = 270;
const PAN_HALF_MAX_DEG = 270;
const TILT_MAX_DEG = 270;

const PAN_TILT_RANGE_KEYS = ['pan_lower', 'pan_upper', 'tilt_lower', 'tilt_upper'];

const PAN_TILT_QUICK_PRESETS = {
  // Narrow: 120° pan arc centered forward, tilt 0–70° (stays near the floor).
  narrow: {
    label: 'Narrow',
    title: '120° pan arc centered forward · tilt 0–70°',
    values: {
      pan_lower: PAN_CENTER_DEG - 60,
      pan_upper: PAN_CENTER_DEG + 60,
      tilt_lower: 0,
      tilt_upper: 70,
    },
  },
  // Sky: full mechanical pan (0°–540° stored), tilt 45–135° (beams up / away from floor).
  sky: {
    label: 'Sky',
    title: `Pan ${PAN_MIN_DEG}°–${PAN_MAX_DEG}° (full sweep) · tilt 45°–135°`,
    values: {
      ...PAN_RANGE_FULL_DEG,
      tilt_lower: 45,
      tilt_upper: 135,
    },
  },
  // Full: unrestricted mechanical range — pan 0°–540° and tilt 0°–270°. Use
  // when the operator wants the fixture to roam anywhere its yoke can reach.
  full: {
    label: 'Full',
    title: `Pan ${PAN_MIN_DEG}°–${PAN_MAX_DEG}° · tilt 0°–${TILT_MAX_DEG}° (full mechanical range)`,
    values: {
      ...PAN_RANGE_FULL_DEG,
      tilt_lower: 0,
      tilt_upper: TILT_MAX_DEG,
    },
  },
};

function labelizeRemoteMode(value) {
  return String(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

async function patchControlState(body) {
  const response = await fetch('/api/control-state', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

/** Default RGB triples (fg / bg / contrast) when no live desktop palette is available. */
const DEFAULT_EDITOR_COLOR_PALETTE = [
  [0.18, 0.22, 0.3],
  [0.32, 0.38, 0.46],
  [0.48, 0.52, 0.58],
];

function readColorPaletteFromFixturePayload(data) {
  const p = data?.color_palette;
  if (!Array.isArray(p) || p.length !== 3) {
    return null;
  }
  const out = [];
  for (const slot of p) {
    if (!Array.isArray(slot) || slot.length < 3) {
      return null;
    }
    out.push([
      Math.max(0, Math.min(1, Number(slot[0]))),
      Math.max(0, Math.min(1, Number(slot[1]))),
      Math.max(0, Math.min(1, Number(slot[2]))),
    ]);
  }
  return out;
}

function rgbTripleToCss(rgb) {
  if (!Array.isArray(rgb) || rgb.length < 3) {
    return 'rgb(100, 116, 139)';
  }
  const r = Math.round(Math.max(0, Math.min(1, rgb[0])) * 255);
  const g = Math.round(Math.max(0, Math.min(1, rgb[1])) * 255);
  const b = Math.round(Math.max(0, Math.min(1, rgb[2])) * 255);
  return `rgb(${r},${g},${b})`;
}

async function postShiftTarget(target) {
  const response = await fetch('/api/shift', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function ViewportToolIcon({ mode }) {
  if (mode === 'select') {
    return (
      <svg fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="tool-chip-svg" viewBox="0 0 24 24" aria-hidden>
        <path d="M4.037 4.688a.5.5 0 0 1 .651-.651l16 6.5a.5.5 0 0 1-.063.947l-6.124 1.582a2 2 0 0 0-1.438 1.435l-1.579 6.126a.5.5 0 0 1-.947.063z" />
      </svg>
    );
  }
  if (mode === 'pan') {
    return (
      <svg fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="tool-chip-svg" viewBox="0 0 24 24" aria-hidden>
        <path d="M5 9l-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3M2 12h20M12 2v20" />
      </svg>
    );
  }
  return (
    <svg fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="tool-chip-svg" viewBox="0 0 24 24" aria-hidden>
      <path d="M21 12a9 9 0 1 1-3-7.5L21 8" />
      <path d="M21 3v5h-5" />
    </svg>
  );
}

function mergePendingFloorIntoSnapshot(snapshot, floorValues) {
  if (!snapshot) {
    return snapshot;
  }
  const w = feetToMeters(Number(floorValues.width || 0));
  const d = feetToMeters(Number(floorValues.height || 0));
  if (!Number.isFinite(w) || !Number.isFinite(d) || w <= 0 || d <= 0) {
    return snapshot;
  }
  if (
    Math.abs(w - snapshot.floor_width) < 0.02 &&
    Math.abs(d - snapshot.floor_depth) < 0.02
  ) {
    return snapshot;
  }
  const scene_objects = snapshot.scene_objects.map((obj) =>
    obj.kind === 'floor' ? { ...obj, width: w, height: d } : obj,
  );
  return {
    ...snapshot,
    floor_width: w,
    floor_depth: d,
    scene_objects,
  };
}

function mergePendingVideoWallSizeIntoSnapshot(snapshot, videoWallSizeValues) {
  if (!snapshot) {
    return snapshot;
  }
  const w = feetToMeters(Number(videoWallSizeValues.width || 0));
  const h = feetToMeters(Number(videoWallSizeValues.height || 0));
  if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
    return snapshot;
  }
  if (
    Math.abs(w - snapshot.video_wall.width) < 0.02 &&
    Math.abs(h - snapshot.video_wall.height) < 0.02
  ) {
    return snapshot;
  }
  const scene_objects = snapshot.scene_objects.map((obj) =>
    obj.kind === 'video_wall' ? { ...obj, width: w, height: h } : obj,
  );
  return {
    ...snapshot,
    video_wall: { ...snapshot.video_wall, width: w, height: h },
    scene_objects,
  };
}

/**
 * Venue editor: React `venueSnapshot` is the canonical model for the 3D scene (fixtures,
 * floor, video wall, DJ booth scene objects). The server increments `summary.revision` on
 * each change; we prefer the newer snapshot so WS / buffered updates cannot rewind state.
 */
function pickNewerVenueSnapshot(current, incoming) {
  if (!incoming || typeof incoming !== 'object') {
    return current;
  }
  if (!current?.summary) {
    return incoming;
  }
  const nr = Number(incoming.summary?.revision ?? 0);
  const cr = Number(current.summary?.revision ?? 0);
  return nr >= cr ? incoming : current;
}

/** Meters: audience-left (−) to audience-right (+) per venue conventions. */
const CLONE_LIGHT_OFFSET_X_M = 1.0;

function dmxAddressWidthForFixture(fixture, fixtureTypes) {
  if (fixture.fixture_type === 'manual_dimmer_channel') {
    const w = fixture.options?.width;
    return Math.max(1, Math.floor(Number(w) || 1));
  }
  const def = fixtureTypes.find((t) => t.key === fixture.fixture_type);
  return Math.max(1, Math.floor(Number(def?.dmx_address_width) || 1));
}

function cloneAddressAndUniverse(fixture, channelWidth, supportedUniverses) {
  const w = channelWidth;
  const nextStart = fixture.address + w;
  if (nextStart >= 1 && nextStart + w - 1 <= 512) {
    return { address: nextStart, universe: fixture.universe };
  }
  const order = supportedUniverses.map((u) => u.value);
  const idx = order.indexOf(fixture.universe);
  if (idx >= 0 && idx < order.length - 1) {
    return { address: 1, universe: order[idx + 1] };
  }
  const maxStart = 512 - w + 1;
  return { address: Math.min(Math.max(1, nextStart), maxStart), universe: fixture.universe };
}

function dmxAddressWidthForFixtureType(fixtureTypeKey, fixtureTypes) {
  if (fixtureTypeKey === 'manual_dimmer_channel') {
    return 1;
  }
  const def = fixtureTypes.find((t) => t.key === fixtureTypeKey);
  return Math.max(1, Math.floor(Number(def?.dmx_address_width) || 1));
}

/** First DMX address after the last occupied channel in this universe (max of address + width). */
function computeNextSafeStartAddress(venueSnapshot, universe, fixtureTypeKey, fixtureTypes) {
  if (!venueSnapshot) {
    return 1;
  }
  const newFixtureWidth = dmxAddressWidthForFixtureType(fixtureTypeKey, fixtureTypes);
  let maxEndExclusive = 0;
  for (const f of venueSnapshot.fixtures || []) {
    if (f.universe !== universe) {
      continue;
    }
    const w = dmxAddressWidthForFixture(f, fixtureTypes);
    const endExclusive = f.address + w;
    if (endExclusive > maxEndExclusive) {
      maxEndExclusive = endExclusive;
    }
  }
  const next = maxEndExclusive >= 1 ? maxEndExclusive : 1;
  const maxStart = Math.max(1, 512 - newFixtureWidth + 1);
  return Math.min(Math.max(1, next), maxStart);
}

/**
 * Single-axis slider with a clickable value readout that shows "Mixed" when
 * values differ across a multi-selection. Clicking "Mixed" (or the plain
 * value) swaps the readout for a number input so the user can type an exact
 * override that commits to every selected fixture at once.
 *
 * Slider drags only commit on pointer-up / key-up so one drag is a single
 * PATCH per fixture rather than one-per-tick — multi-select edits would
 * otherwise storm the backend.
 */
function PanTiltMixedSlider({
  compactLabel,
  value,
  isMixed,
  min,
  max,
  warn,
  title,
  onCommit,
  reversed = false,
}) {
  const [editing, setEditing] = useState(false);
  const [textDraft, setTextDraft] = useState('');
  const [sliderDraft, setSliderDraft] = useState(Number.isFinite(value) ? value : min);
  const draggingRef = useRef(false);

  // Keep the slider in sync with the prop unless the user is in the middle of
  // a drag or typing into the Mixed-click number field. A WebSocket snapshot
  // arriving mid-drag (e.g. a peer edit on the same venue) would otherwise
  // snap the thumb back to the server value and eat the in-flight gesture.
  useEffect(() => {
    if (!editing && !draggingRef.current) {
      setSliderDraft(Number.isFinite(value) ? value : min);
    }
  }, [value, editing, min]);

  const clamp = (v) => Math.max(min, Math.min(max, v));
  const display = isMixed ? 'Mixed' : `${Math.round(sliderDraft)}°`;

  // In `reversed` mode we mirror the entire control with `transform: scaleX(-1)`
  // in CSS. That flips the thumb position, the accent-color fill region, and
  // the drag coordinate mapping in one go, so stored `sliderDraft` still runs
  // natively low→high and onChange keeps its usual semantics.
  const labelNode = compactLabel
    ? <span className="pan-tilt-slider-compact-label">{compactLabel}</span>
    : null;

  if (editing) {
    const commitTextAndExit = () => {
      setEditing(false);
      const n = Number(textDraft);
      if (Number.isFinite(n)) {
        void onCommit(clamp(n));
      }
    };
    const textCluster = (
      <>
        <input
          type="number"
          className="compact-input pan-tilt-slider-text-input"
          autoFocus
          value={textDraft}
          min={min}
          max={max}
          step="5"
          size={4}
          onChange={(event) => setTextDraft(event.target.value)}
          onBlur={commitTextAndExit}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.currentTarget.blur();
            } else if (event.key === 'Escape') {
              setEditing(false);
            }
          }}
        />
        <span className="compact-suffix">°</span>
      </>
    );
    return (
      <div className={`pan-tilt-slider${warn ? ' warn' : ''}${reversed ? ' reversed' : ''}`} title={title}>
        {reversed ? textCluster : labelNode}
        {reversed ? labelNode : textCluster}
      </div>
    );
  }

  const valueButton = (
    <button
      type="button"
      className="pan-tilt-slider-value"
      onClick={() => {
        setTextDraft(isMixed ? '' : String(Math.round(sliderDraft)));
        setEditing(true);
      }}
      title={
        isMixed
          ? 'Values differ across selection — click to type one value for all'
          : 'Click to type an exact value'
      }
    >
      {display}
    </button>
  );

  const rangeInput = (
    <input
      type="range"
      className="pan-tilt-slider-input"
      min={min}
      max={max}
      step="1"
      value={clamp(sliderDraft)}
      onChange={(event) => setSliderDraft(Number(event.target.value))}
      onPointerDown={() => {
        draggingRef.current = true;
      }}
      onPointerUp={() => {
        draggingRef.current = false;
        void onCommit(clamp(sliderDraft));
      }}
      onPointerCancel={() => {
        draggingRef.current = false;
      }}
      onKeyUp={(event) => {
        if (
          event.key === 'ArrowLeft'
          || event.key === 'ArrowRight'
          || event.key === 'ArrowUp'
          || event.key === 'ArrowDown'
          || event.key === 'Home'
          || event.key === 'End'
          || event.key === 'PageUp'
          || event.key === 'PageDown'
        ) {
          void onCommit(clamp(sliderDraft));
        }
      }}
    />
  );

  return (
    <div className={`pan-tilt-slider${warn ? ' warn' : ''}${isMixed ? ' mixed' : ''}${reversed ? ' reversed' : ''}`} title={title}>
      {reversed ? valueButton : labelNode}
      {rangeInput}
      {reversed ? labelNode : valueButton}
    </div>
  );
}

/**
 * Summarize one of the four pan/tilt range keys across a selection: returns
 * the common value (or ``null`` if none of the fixtures carries it), plus a
 * ``isMixed`` flag when values disagree by more than half a degree. The
 * half-degree tolerance absorbs harmless float round-trips through the API.
 */
function summarizePanTiltKey(fixtures, key) {
  const values = [];
  for (const f of fixtures) {
    const raw = f?.options?.[key];
    const numeric = Number(raw);
    if (Number.isFinite(numeric)) {
      values.push(numeric);
    }
  }
  if (values.length === 0) {
    return { value: null, isMixed: false };
  }
  const first = values[0];
  const isMixed = values.some((v) => Math.abs(v - first) > 0.5);
  return { value: first, isMixed };
}

/**
 * Pan / tilt range editor for one or more moving-head fixtures. Pan is
 * presented as two deviation sliders around a fixed 270° forward center so
 * the user can sweep beams symmetrically without doing arithmetic; tilt gets
 * one slider per bound so a skylight-style ``tilt_lower > floor`` is obvious.
 * The panel flags inverted bounds (upper < lower) in red rather than silently
 * "fixing" them — the fixture will still behave weirdly live until the user
 * resolves the inversion themselves.
 */
function PanTiltRangePanel({ fixtures, onPatch }) {
  const panLower = summarizePanTiltKey(fixtures, 'pan_lower');
  const panUpper = summarizePanTiltKey(fixtures, 'pan_upper');
  const tiltLower = summarizePanTiltKey(fixtures, 'tilt_lower');
  const tiltUpper = summarizePanTiltKey(fixtures, 'tilt_upper');

  const panInverted =
    !panLower.isMixed
    && !panUpper.isMixed
    && panLower.value !== null
    && panUpper.value !== null
    && panUpper.value < panLower.value;
  const tiltInverted =
    !tiltLower.isMixed
    && !tiltUpper.isMixed
    && tiltLower.value !== null
    && tiltUpper.value !== null
    && tiltUpper.value < tiltLower.value;

  // Pan is edited as deviations from the 270° forward center. Negative
  // deviations (e.g. pan_lower = 360 on some fixture defaults) clamp to 0 for
  // the slider; if the user touches the slider the stored value becomes
  // symmetric around 270°, which is the intent of this UI.
  const leftDevValue =
    panLower.value === null ? 0 : Math.max(0, PAN_CENTER_DEG - panLower.value);
  const rightDevValue =
    panUpper.value === null ? 0 : Math.max(0, panUpper.value - PAN_CENTER_DEG);

  return (
    <div className="floating-transform-panel pan-tilt-range-panel">
      <div className="dense-section-header">
        <h3>Pan / Tilt Range</h3>
        {fixtures.length > 1 ? (
          <span className="pan-tilt-selection-count">{fixtures.length} fixtures</span>
        ) : null}
      </div>

      <div className="pan-tilt-row">
        <span className="pan-tilt-row-label">Pan</span>
        <div className="pan-tilt-pan-sliders">
          <PanTiltMixedSlider
            compactLabel="←"
            title="Left deviation from forward (270°) — slider is reversed so dragging left grows the leftward arc"
            value={leftDevValue}
            isMixed={panLower.isMixed}
            min={0}
            max={PAN_HALF_MAX_DEG}
            warn={panInverted}
            reversed
            onCommit={(dev) => onPatch({ pan_lower: PAN_CENTER_DEG - dev })}
          />
          <PanTiltMixedSlider
            compactLabel="→"
            title="Right deviation from forward (270°)"
            value={rightDevValue}
            isMixed={panUpper.isMixed}
            min={0}
            max={PAN_HALF_MAX_DEG}
            warn={panInverted}
            onCommit={(dev) => onPatch({ pan_upper: PAN_CENTER_DEG + dev })}
          />
        </div>
      </div>
      {panInverted ? (
        <div className="pan-tilt-warning">
          Pan lower {Math.round(panLower.value)}° is above upper {Math.round(panUpper.value)}°
        </div>
      ) : null}

      <div className="pan-tilt-row">
        <span className="pan-tilt-row-label">Tilt min</span>
        <PanTiltMixedSlider
          title="Tilt lower bound (0 = straight down in fixture frame)"
          value={tiltLower.value === null ? 0 : tiltLower.value}
          isMixed={tiltLower.isMixed}
          min={0}
          max={TILT_MAX_DEG}
          warn={tiltInverted}
          onCommit={(v) => onPatch({ tilt_lower: v })}
        />
      </div>
      <div className="pan-tilt-row">
        <span className="pan-tilt-row-label">Tilt max</span>
        <PanTiltMixedSlider
          title="Tilt upper bound"
          value={tiltUpper.value === null ? 0 : tiltUpper.value}
          isMixed={tiltUpper.isMixed}
          min={0}
          max={TILT_MAX_DEG}
          warn={tiltInverted}
          onCommit={(v) => onPatch({ tilt_upper: v })}
        />
      </div>
      {tiltInverted ? (
        <div className="pan-tilt-warning">
          Tilt max {Math.round(tiltUpper.value)}° is below min {Math.round(tiltLower.value)}°
        </div>
      ) : null}

      <div className="pan-tilt-quick-presets">
        {Object.entries(PAN_TILT_QUICK_PRESETS).map(([key, preset]) => (
          <button
            key={key}
            type="button"
            className="small-button secondary-button pan-tilt-quick-preset-button"
            title={preset.title}
            onClick={() => void onPatch(preset.values)}
          >
            {preset.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function DenseVenueEditorPage({ venueId }) {
  const viewportRef = useRef(null);
  const sceneControllerRef = useRef(null);
  const wsRef = useRef(null);
  const venueRef = useRef(null);
  const videoWallLockedRef = useRef(false);
  const selectedFixtureIdsRef = useRef([]);
  const transformDraggingRef = useRef(false);
  const pendingVenueSnapshotRef = useRef(null);
  const venueNameSaveTimerRef = useRef(null);
  const floorSaveTimerRef = useRef(null);
  const videoWallSaveTimerRef = useRef(null);
  const fixtureRuntimeStateRef = useRef(null);
  const lastRuntimeFixtureJsonRef = useRef('');
  const livePulseHideTimerRef = useRef(null);
  const activeVenueIdRef = useRef(null);
  const editorMenuRef = useRef(null);
  /** Index in `fixturesInPanelOrder` for Shift+click range selection (last plain click in the list). */
  const fixtureListRangeAnchorIndexRef = useRef(-1);

  const [venueSummaries, setVenueSummaries] = useState([]);
  const [venueSnapshot, setVenueSnapshot] = useState(null);
  const [fixtureTypes, setFixtureTypes] = useState([]);
  const [supportedUniverses, setSupportedUniverses] = useState([]);
  const [currentView, setCurrentView] = useState('perspective');
  const [interactionMode, setInteractionMode] = useState('rotate');
  /** Latest mode for async scene-controller init (ref can be null when interaction `useEffect` runs). */
  const interactionModeRef = useRef(interactionMode);
  interactionModeRef.current = interactionMode;
  const [contextMenu, setContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    kind: 'fixture',
    groupName: null,
  });
  const [selectedKind, setSelectedKind] = useState(null);
  const [selectedFixtureIds, setSelectedFixtureIds] = useState([]);
  const [venueNameDraft, setVenueNameDraft] = useState('');
  const [floorValues, setFloorValues] = useState({
    width: '',
    height: '',
  });
  const [videoWallSizeValues, setVideoWallSizeValues] = useState({
    width: '',
    height: '',
  });
  const floorValuesRef = useRef(floorValues);
  const videoWallSizeValuesRef = useRef(videoWallSizeValues);
  floorValuesRef.current = floorValues;
  videoWallSizeValuesRef.current = videoWallSizeValues;
  const [videoWallLocked, setVideoWallLocked] = useState(false);
  const [addFixtureModalOpen, setAddFixtureModalOpen] = useState(false);
  const [newFixtureValues, setNewFixtureValues] = useState({
    fixtureType: '',
    address: '1',
    universe: 'default',
    quantity: '1',
  });
  const [addFixtureError, setAddFixtureError] = useState('');
  const [addressModalOpen, setAddressModalOpen] = useState(false);
  const [selectedFixtureValues, setSelectedFixtureValues] = useState({
    address: '',
    universe: 'default',
  });
  const [remoteConfig, setRemoteConfig] = useState({
    available_modes: [],
    theme_names: [],
    shift_targets: [],
  });
  /** Live fg/bg/bg_contrast from desktop fixture-state push; null until first valid `color_palette`. */
  const [liveColorPalette, setLiveColorPalette] = useState(null);
  const [controlState, setControlState] = useState({
    mode: 'chill',
    theme_name: 'Rave',
    active_venue_id: null,
  });
  const [liveLightingPulse, setLiveLightingPulse] = useState(false);
  const [vjPreviewUpdatedAt, setVjPreviewUpdatedAt] = useState(null);
  /** Bumps when a new WebGL scene controller is mounted so VJ preview reloads onto the live controller. */
  const [sceneControllerEpoch, setSceneControllerEpoch] = useState(0);
  const [editorMenuOpen, setEditorMenuOpen] = useState(false);
  const [editorMenuSection, setEditorMenuSection] = useState(null);

  /** Primary fixture for detail actions (last clicked in multi-select). */
  const selectedFixtureId =
    selectedFixtureIds.length > 0 ? selectedFixtureIds[selectedFixtureIds.length - 1] : null;

  const selectedFixture = useMemo(() => {
    if (!venueSnapshot || !selectedFixtureId) {
      return null;
    }
    return venueSnapshot.fixtures.find((fixture) => fixture.id === selectedFixtureId) ?? null;
  }, [venueSnapshot, selectedFixtureId]);

  /**
   * Subset of the current selection that is editable by the Pan/Tilt panel.
   * Computing this once avoids re-filtering inside the render block and lets
   * the panel's "Mixed" detection operate on exactly the fixtures that will
   * receive the patch — non-moving-heads never contribute values and are
   * never targeted by commits.
   */
  const selectedMovingHeadFixtures = useMemo(() => {
    if (!venueSnapshot || selectedFixtureIds.length === 0) {
      return [];
    }
    const idSet = new Set(selectedFixtureIds);
    return venueSnapshot.fixtures.filter(
      (f) => idSet.has(f.id) && isMovingHeadFixtureType(f.fixture_type),
    );
  }, [venueSnapshot, selectedFixtureIds]);

  const selectedSceneObject = useMemo(() => {
    if (!venueSnapshot || !selectedKind) {
      return null;
    }
    if (selectedKind === 'video_wall') {
      return venueSnapshot.scene_objects.find((sceneObject) => sceneObject.kind === 'video_wall') ?? null;
    }
    if (selectedKind === 'dj_booth') {
      return venueSnapshot.scene_objects.find((sceneObject) => sceneObject.kind === 'dj_table') ?? null;
    }
    return null;
  }, [selectedKind, venueSnapshot]);

  const venueSummary = useMemo(
    () => venueSummaries.find((venue) => venue.id === venueId) ?? null,
    [venueId, venueSummaries],
  );

  const fixtureListGroups = useMemo(() => {
    const fixtures = venueSnapshot?.fixtures || [];
    const byName = new Map();
    const ungrouped = [];
    for (const f of fixtures) {
      const gn = f.group_name?.trim();
      if (!gn) {
        ungrouped.push(f);
      } else {
        if (!byName.has(gn)) {
          byName.set(gn, []);
        }
        byName.get(gn).push(f);
      }
    }
    const groups = [...byName.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([name, items]) => ({
        name,
        fixtures: items.sort((x, y) => (x.name || x.fixture_type).localeCompare(y.name || y.fixture_type)),
      }));
    return { groups, ungrouped };
  }, [venueSnapshot]);

  const fixturesInPanelOrder = useMemo(() => {
    const { ungrouped, groups } = fixtureListGroups;
    const out = [...ungrouped];
    for (const g of groups) {
      out.push(...g.fixtures);
    }
    return out;
  }, [fixtureListGroups]);

  useEffect(() => {
    fixtureListRangeAnchorIndexRef.current = -1;
  }, [venueId]);

  useEffect(() => {
    document.body.dataset.testMode = isTestMode ? 'true' : 'false';
    let disposed = false;

    async function initialize() {
      const controller = await createSceneController({
        viewportEl: viewportRef.current,
        isTestMode,
        onSelectionChange: handleSelectionChange,
        onFixtureContextMenu: ({ fixture, x, y }) => {
          setSelectedKind('fixture');
          setSelectedFixtureIds([fixture.id]);
          setContextMenu({
            visible: true,
            x,
            y,
            kind: 'fixture',
            groupName: null,
          });
        },
        onFixtureTransform: async (payload) => {
          if (!venueRef.current) {
            return;
          }
          const snapshot = await apiPatchFixture(venueRef.current.summary.id, payload.fixtureId, {
            x: payload.x,
            y: payload.y,
            z: payload.z,
            rotation_x: payload.rotation_x,
            rotation_y: payload.rotation_y,
            rotation_z: payload.rotation_z,
          });
          if (!transformDraggingRef.current) {
            setVenueSnapshot(snapshot);
          } else {
            pendingVenueSnapshotRef.current = pickNewerVenueSnapshot(
              pendingVenueSnapshotRef.current,
              snapshot,
            );
          }
        },
        onFixtureTransformsBatch: async (payloads) => {
          if (!venueRef.current || payloads.length === 0) {
            return;
          }
          let snapshot = venueRef.current;
          for (const payload of payloads) {
            snapshot = await apiPatchFixture(venueRef.current.summary.id, payload.fixtureId, {
              x: payload.x,
              y: payload.y,
              z: payload.z,
              rotation_x: payload.rotation_x,
              rotation_y: payload.rotation_y,
              rotation_z: payload.rotation_z,
            });
          }
          if (!transformDraggingRef.current) {
            setVenueSnapshot(snapshot);
          } else {
            pendingVenueSnapshotRef.current = pickNewerVenueSnapshot(
              pendingVenueSnapshotRef.current,
              snapshot,
            );
          }
        },
        onVideoWallTransform: async (payload) => {
          if (!venueRef.current) {
            return;
          }
          const snapshot = await apiPatchVideoWall(venueRef.current.summary.id, {
            x: payload.x,
            y: payload.y,
            z: payload.z,
            width: venueRef.current.video_wall.width,
            height: venueRef.current.video_wall.height,
            depth: venueRef.current.video_wall.depth,
            locked: videoWallLockedRef.current,
          });
          setVenueSnapshot(snapshot);
        },
        onSceneObjectTransform: async (payload) => {
          if (!venueRef.current || payload.type !== 'dj_booth') {
            return;
          }
          let lastSnapshot = null;
          for (const sceneObject of payload.objects) {
            lastSnapshot = await apiPatchSceneObject(venueRef.current.summary.id, sceneObject.kind, {
              x: sceneObject.x,
              y: sceneObject.y,
              z: sceneObject.z,
              rotation_x: sceneObject.rotation_x,
              rotation_y: sceneObject.rotation_y,
              rotation_z: sceneObject.rotation_z,
            });
          }
          if (lastSnapshot) {
            setVenueSnapshot(lastSnapshot);
          }
        },
        onTransformDragStateChange: (isDragging) => {
          transformDraggingRef.current = isDragging;
          if (!isDragging) {
            const pending = pendingVenueSnapshotRef.current;
            pendingVenueSnapshotRef.current = null;
            if (pending != null) {
              setVenueSnapshot((current) => pickNewerVenueSnapshot(current, pending));
            }
          }
        },
      });
      if (disposed) {
        controller.destroy();
        return;
      }
      sceneControllerRef.current = controller;
      controller.setInteractionMode(interactionModeRef.current);
      setSceneControllerEpoch((n) => n + 1);

      const config = await fetchJson('/api/config');
      if (disposed) {
        return;
      }
      setFixtureTypes(config.fixture_types);
      setSupportedUniverses(config.supported_universes);
      setRemoteConfig({
        available_modes: config.available_modes || [],
        theme_names: config.theme_names || [],
        shift_targets: config.shift_targets || [],
      });
      setNewFixtureValues((current) => ({
        ...current,
        fixtureType: config.fixture_types[0]?.key || '',
        universe: config.supported_universes[0]?.value || 'default',
        quantity: '1',
      }));
      setSelectedFixtureValues((current) => ({
        ...current,
        universe: config.supported_universes[0]?.value || 'default',
      }));

      const nextBootstrap = await fetchJson('/api/bootstrap');
      if (disposed) {
        return;
      }
      fixtureRuntimeStateRef.current = nextBootstrap.fixture_runtime_state ?? {
        version: 1,
        fixtures: [],
      };
      applyBootstrap(nextBootstrap);
      await loadVenueSnapshot(venueId);
      sceneControllerRef.current?.applyFixtureRuntimeState(fixtureRuntimeStateRef.current);
      connectWebSocket();
      document.body.dataset.appReady = 'true';
    }

    initialize().catch((error) => {
      console.error('Failed to initialize dense venue editor:', error);
      document.body.dataset.appReady = 'false';
    });

    const handleWindowClick = () => setContextMenu((current) => ({ ...current, visible: false }));
    window.addEventListener('click', handleWindowClick);

    return () => {
      disposed = true;
      if (venueNameSaveTimerRef.current) {
        window.clearTimeout(venueNameSaveTimerRef.current);
      }
      if (floorSaveTimerRef.current) {
        window.clearTimeout(floorSaveTimerRef.current);
      }
      if (videoWallSaveTimerRef.current) {
        window.clearTimeout(videoWallSaveTimerRef.current);
      }
      if (livePulseHideTimerRef.current) {
        window.clearTimeout(livePulseHideTimerRef.current);
      }
      window.removeEventListener('click', handleWindowClick);
      wsRef.current?.close();
      sceneControllerRef.current?.destroy();
      sceneControllerRef.current = null;
    };
  }, [venueId]);

  useEffect(() => {
    if (!venueSnapshot) {
      venueRef.current = null;
      setVenueNameDraft('');
      setFloorValues({ width: '', height: '' });
      setVideoWallSizeValues({ width: '', height: '' });
      setVideoWallLocked(false);
      return;
    }

    setVenueNameDraft(venueSnapshot.summary.name);

    const fv = floorValuesRef.current;
    const parsedFloorW = feetToMeters(Number(fv.width || 0));
    const parsedFloorD = feetToMeters(Number(fv.height || 0));
    const floorInputsEmpty = fv.width === '' && fv.height === '';
    const floorMatchesServer =
      Number.isFinite(parsedFloorW) &&
      Number.isFinite(parsedFloorD) &&
      parsedFloorW > 0 &&
      parsedFloorD > 0 &&
      Math.abs(parsedFloorW - venueSnapshot.floor_width) < 0.02 &&
      Math.abs(parsedFloorD - venueSnapshot.floor_depth) < 0.02;

    if (floorInputsEmpty || floorMatchesServer) {
      setFloorValues({
        width: String(Math.round(metersToFeet(venueSnapshot.floor_width))),
        height: String(Math.round(metersToFeet(venueSnapshot.floor_depth))),
      });
    }

    const vs = videoWallSizeValuesRef.current;
    const parsedVw = feetToMeters(Number(vs.width || 0));
    const parsedVh = feetToMeters(Number(vs.height || 0));
    const videoWallInputsEmpty = vs.width === '' && vs.height === '';
    const videoWallMatchesServer =
      Number.isFinite(parsedVw) &&
      Number.isFinite(parsedVh) &&
      parsedVw > 0 &&
      parsedVh > 0 &&
      Math.abs(parsedVw - venueSnapshot.video_wall.width) < 0.02 &&
      Math.abs(parsedVh - venueSnapshot.video_wall.height) < 0.02;

    if (videoWallInputsEmpty || videoWallMatchesServer) {
      setVideoWallSizeValues({
        width: String(Math.round(metersToFeet(venueSnapshot.video_wall.width))),
        height: String(Math.round(metersToFeet(venueSnapshot.video_wall.height))),
      });
    }

    setVideoWallLocked(venueSnapshot.video_wall.locked);

    const merged = mergePendingVideoWallSizeIntoSnapshot(
      mergePendingFloorIntoSnapshot(venueSnapshot, floorValuesRef.current),
      videoWallSizeValuesRef.current,
    );
    venueRef.current = merged;
    sceneControllerRef.current?.applyBootstrap(merged);
    if (fixtureRuntimeStateRef.current) {
      sceneControllerRef.current?.applyFixtureRuntimeState(fixtureRuntimeStateRef.current);
    }
  }, [venueSnapshot]);

  useEffect(() => {
    videoWallLockedRef.current = videoWallLocked;
  }, [videoWallLocked]);

  useEffect(() => {
    if (!selectedFixture) {
      setSelectedFixtureValues((current) => ({
        address: '',
        universe: supportedUniverses[0]?.value || current.universe || 'default',
      }));
      return;
    }
    setSelectedFixtureValues({
      address: String(selectedFixture.address),
      universe: selectedFixture.universe,
    });
  }, [selectedFixture, supportedUniverses]);

  useEffect(() => {
    sceneControllerRef.current?.setView(currentView);
  }, [currentView]);

  // Orthographic views (top/front/side) orbit awkwardly; if the user was orbiting
  // in perspective, switch to pan when entering those views.
  useEffect(() => {
    if (currentView === 'perspective') {
      return;
    }
    setInteractionMode((mode) => (mode === 'rotate' ? 'pan' : mode));
  }, [currentView]);

  useEffect(() => {
    activeVenueIdRef.current = controlState.active_venue_id;
  }, [controlState.active_venue_id]);

  useEffect(() => {
    if (vjPreviewUpdatedAt == null) {
      sceneControllerRef.current?.resetVideoWallToPlaceholder?.();
      return;
    }
    const url = `/api/runtime/vj-preview?t=${encodeURIComponent(String(vjPreviewUpdatedAt))}`;
    sceneControllerRef.current?.applyVjPreviewUrl?.(url);
  }, [vjPreviewUpdatedAt, venueSnapshot?.summary?.id, sceneControllerEpoch]);

  useEffect(() => {
    if (!editorMenuOpen) {
      return undefined;
    }
    function handlePointerDown(event) {
      if (editorMenuRef.current && !editorMenuRef.current.contains(event.target)) {
        setEditorMenuOpen(false);
        setEditorMenuSection(null);
      }
    }
    window.addEventListener('pointerdown', handlePointerDown);
    return () => window.removeEventListener('pointerdown', handlePointerDown);
  }, [editorMenuOpen]);

  /** Poll live DMX/visual state: WS broadcasts can race HTTP threads; polling keeps the editor in sync. */
  useEffect(() => {
    if (isTestMode) {
      return undefined;
    }
    lastRuntimeFixtureJsonRef.current = '';
    const fixtureStatePollMs = Math.round(1000 / 30);
    const intervalId = window.setInterval(() => {
      const controller = sceneControllerRef.current;
      if (!controller || document.hidden) {
        return;
      }
      void fetchJson('/api/runtime/fixture-state')
        .then((data) => {
          const enc = JSON.stringify(data);
          if (enc === lastRuntimeFixtureJsonRef.current) {
            return;
          }
          lastRuntimeFixtureJsonRef.current = enc;
          fixtureRuntimeStateRef.current = data;
          {
            const pal = readColorPaletteFromFixturePayload(data);
            setLiveColorPalette(pal);
          }
          controller.applyFixtureRuntimeState(data);
          bumpLiveLightingPulse();
        })
        .catch(() => {});
    }, fixtureStatePollMs);
    return () => window.clearInterval(intervalId);
  }, [venueId]);

  useEffect(() => {
    sceneControllerRef.current?.setInteractionMode(interactionMode);
  }, [interactionMode]);

  useEffect(() => {
    if (interactionMode !== 'pan' && interactionMode !== 'rotate') {
      return;
    }
    setSelectedFixtureIds((ids) => (ids.length > 0 ? [] : ids));
    setSelectedKind((currentKind) => (currentKind === 'fixture' ? null : currentKind));
    setContextMenu((current) => ({ ...current, visible: false }));
  }, [interactionMode]);

  useEffect(() => {
    function onViewportToolKey(event) {
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      const el = event.target;
      if (
        el instanceof HTMLInputElement ||
        el instanceof HTMLTextAreaElement ||
        el instanceof HTMLSelectElement ||
        (el instanceof HTMLElement && el.isContentEditable)
      ) {
        return;
      }
      const k = event.key.toLowerCase();
      if (k === 'v') {
        event.preventDefault();
        setInteractionMode('select');
      } else if (k === 'h') {
        event.preventDefault();
        setInteractionMode('pan');
      } else if (k === 'r') {
        event.preventDefault();
        setInteractionMode('rotate');
      }
    }
    window.addEventListener('keydown', onViewportToolKey);
    return () => window.removeEventListener('keydown', onViewportToolKey);
  }, []);

  useEffect(() => {
    if (!venueSnapshot) {
      return;
    }
    if (venueNameDraft === venueSnapshot.summary.name) {
      return;
    }
    if (venueNameSaveTimerRef.current) {
      window.clearTimeout(venueNameSaveTimerRef.current);
    }
    venueNameSaveTimerRef.current = window.setTimeout(() => {
      const trimmed = venueNameDraft.trim();
      if (trimmed && trimmed !== venueRef.current?.summary.name) {
        void apiPatchVenue(venueSnapshot.summary.id, { name: trimmed }).then((snap) => {
          setVenueSnapshot(snap);
        });
      }
    }, 350);
    return () => {
      if (venueNameSaveTimerRef.current) {
        window.clearTimeout(venueNameSaveTimerRef.current);
      }
    };
  }, [venueNameDraft, venueSnapshot]);

  useEffect(() => {
    if (!venueSnapshot) {
      return;
    }
    const nextWidth = feetToMeters(Number(floorValues.width || 0));
    const nextHeight = feetToMeters(Number(floorValues.height || 0));
    if (
      Number.isNaN(nextWidth) ||
      Number.isNaN(nextHeight) ||
      (nextWidth === venueSnapshot.floor_width && nextHeight === venueSnapshot.floor_depth)
    ) {
      return;
    }
    if (floorSaveTimerRef.current) {
      window.clearTimeout(floorSaveTimerRef.current);
    }
    floorSaveTimerRef.current = window.setTimeout(() => {
      const venue = venueRef.current;
      if (!venue) {
        return;
      }
      void apiPatchVenue(venue.summary.id, {
        floor_width: nextWidth,
        floor_depth: nextHeight,
      }).then((snap) => {
        setVenueSnapshot(snap);
      });
    }, 250);
    return () => {
      if (floorSaveTimerRef.current) {
        window.clearTimeout(floorSaveTimerRef.current);
      }
    };
  }, [floorValues, venueSnapshot]);

  useEffect(() => {
    if (!venueSnapshot) {
      return;
    }
    const nextW = feetToMeters(Number(videoWallSizeValues.width || 0));
    const nextH = feetToMeters(Number(videoWallSizeValues.height || 0));
    if (
      Number.isNaN(nextW) ||
      Number.isNaN(nextH) ||
      (nextW === venueSnapshot.video_wall.width && nextH === venueSnapshot.video_wall.height)
    ) {
      return;
    }
    if (videoWallSaveTimerRef.current) {
      window.clearTimeout(videoWallSaveTimerRef.current);
    }
    videoWallSaveTimerRef.current = window.setTimeout(() => {
      const venue = venueRef.current;
      if (!venue) {
        return;
      }
      const w = feetToMeters(Number(videoWallSizeValuesRef.current.width || 0));
      const h = feetToMeters(Number(videoWallSizeValuesRef.current.height || 0));
      if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) {
        return;
      }
      void apiPatchVideoWall(venue.summary.id, {
        x: venue.video_wall.x,
        y: venue.video_wall.y,
        z: venue.video_wall.z,
        width: w,
        height: h,
        depth: venue.video_wall.depth,
        locked: videoWallLockedRef.current,
      }).then((snap) => {
        setVenueSnapshot(snap);
      });
    }, 250);
    return () => {
      if (videoWallSaveTimerRef.current) {
        window.clearTimeout(videoWallSaveTimerRef.current);
      }
    };
  }, [videoWallSizeValues, venueSnapshot]);

  useEffect(() => {
    selectedFixtureIdsRef.current = selectedFixtureIds;
    if (selectedKind === 'fixture' && selectedFixtureIds.length > 0) {
      sceneControllerRef.current?.setSelection(
        { type: 'fixture', fixtureIds: selectedFixtureIds },
        { notifyParent: false },
      );
    } else if (selectedKind !== 'video_wall' && selectedKind !== 'dj_booth') {
      sceneControllerRef.current?.setSelection(null, { notifyParent: false });
    }
  }, [selectedFixtureIds, selectedKind]);

  function bumpLiveLightingPulse() {
    if (activeVenueIdRef.current !== venueId) {
      return;
    }
    setLiveLightingPulse(true);
    if (livePulseHideTimerRef.current) {
      window.clearTimeout(livePulseHideTimerRef.current);
    }
    livePulseHideTimerRef.current = window.setTimeout(() => {
      setLiveLightingPulse(false);
      livePulseHideTimerRef.current = null;
    }, 2800);
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'bootstrap') {
        fixtureRuntimeStateRef.current = payload.data?.fixture_runtime_state ?? {
          version: 1,
          fixtures: [],
        };
        applyBootstrap(payload.data);
        void loadVenueSnapshot(venueId);
      } else if (payload.type === 'control_state') {
        setControlState((current) => ({
          ...current,
          ...payload.data,
        }));
      } else if (payload.type === 'vj_preview') {
        const u = payload.data?.updated_at;
        setVjPreviewUpdatedAt(u != null ? u : null);
      } else if (payload.type === 'fixture_runtime_state') {
        fixtureRuntimeStateRef.current = payload.data;
        {
          const pal = readColorPaletteFromFixturePayload(payload.data);
          setLiveColorPalette(pal);
        }
        sceneControllerRef.current?.applyFixtureRuntimeState(payload.data);
        bumpLiveLightingPulse();
      } else if (payload.type === 'venues') {
        setVenueSummaries(payload.data?.venues || []);
      } else if (payload.type === 'venue_snapshot') {
        if (payload.data?.summary?.id === venueId) {
          if (transformDraggingRef.current) {
            pendingVenueSnapshotRef.current = pickNewerVenueSnapshot(
              pendingVenueSnapshotRef.current,
              payload.data,
            );
          } else {
            setVenueSnapshot((current) => pickNewerVenueSnapshot(current, payload.data));
          }
        }
      }
    };
    ws.onclose = () => {
      setTimeout(connectWebSocket, 1000);
    };
    wsRef.current = ws;
  }

  function applyBootstrap(nextBootstrap) {
    setVenueSummaries(nextBootstrap.venues || []);
    fixtureRuntimeStateRef.current = nextBootstrap.fixture_runtime_state ?? {
      version: 1,
      fixtures: [],
    };
    {
      const pal = readColorPaletteFromFixturePayload(fixtureRuntimeStateRef.current);
      setLiveColorPalette(pal);
    }
    setControlState((current) => ({
      ...current,
      ...(nextBootstrap.control_state || {}),
      active_venue_id:
        nextBootstrap.control_state?.active_venue_id ??
        nextBootstrap.active_venue?.summary?.id ??
        null,
    }));
    if (nextBootstrap.active_venue?.summary?.id === venueId) {
      setVenueSnapshot(nextBootstrap.active_venue);
    }
    const vjU = nextBootstrap.vj_preview?.updated_at;
    setVjPreviewUpdatedAt(vjU != null ? vjU : null);
  }

  async function loadVenueSnapshot(nextVenueId) {
    try {
      const snapshot = await fetchJson(`/api/venues/${nextVenueId}`);
      setVenueSnapshot(snapshot);
      if (selectedFixtureIdsRef.current.length > 0) {
        const missing = selectedFixtureIdsRef.current.some(
          (id) => !snapshot.fixtures.some((fixture) => fixture.id === id),
        );
        if (missing) {
          setSelectedFixtureIds([]);
          setSelectedKind(null);
        }
      }
    } catch (error) {
      console.error('Failed to load venue snapshot:', error);
      setVenueSnapshot(null);
    }
  }

  function handleSelectionChange(selection) {
    if (!selection) {
      setSelectedKind(null);
      setSelectedFixtureIds([]);
      return;
    }
    if (selection.type === 'fixture') {
      setSelectedKind('fixture');
      const ids =
        Array.isArray(selection.fixtureIds) && selection.fixtureIds.length > 0
          ? selection.fixtureIds
          : selection.fixtures?.map((f) => f.id) ??
            (selection.fixture
              ? [selection.fixture.id]
              : []);
      setSelectedFixtureIds(ids);
      return;
    }
    setSelectedFixtureIds([]);
    setSelectedKind(selection.type);
  }

  function handleFixtureListRowClick(fixture, event) {
    setSelectedKind('fixture');
    const flat = fixturesInPanelOrder;
    const clickedIndex = flat.findIndex((f) => f.id === fixture.id);
    if (clickedIndex < 0) {
      return;
    }

    const shiftRange =
      event.shiftKey || (event.nativeEvent && typeof event.nativeEvent.getModifierState === 'function'
        ? event.nativeEvent.getModifierState('Shift')
        : false);

    if (shiftRange) {
      event.preventDefault();
      let anchor = fixtureListRangeAnchorIndexRef.current;
      if (anchor < 0 || anchor >= flat.length) {
        anchor = selectedFixtureId
          ? flat.findIndex((f) => f.id === selectedFixtureId)
          : 0;
        if (anchor < 0) {
          anchor = 0;
        }
      }
      const rangeStart = Math.min(anchor, clickedIndex);
      const rangeEnd = Math.max(anchor, clickedIndex);
      setSelectedFixtureIds(flat.slice(rangeStart, rangeEnd + 1).map((f) => f.id));
      return;
    }

    if (event.metaKey || event.ctrlKey) {
      event.preventDefault();
      setSelectedFixtureIds((prev) => {
        const next = new Set(prev);
        if (next.has(fixture.id)) {
          next.delete(fixture.id);
        } else {
          next.add(fixture.id);
        }
        return [...next];
      });
      return;
    }

    fixtureListRangeAnchorIndexRef.current = clickedIndex;
    setSelectedFixtureIds([fixture.id]);
  }

  function handleOpenAddFixtureModal() {
    if (!venueSnapshot) {
      return;
    }
    setAddFixtureError('');
    setNewFixtureValues((current) => ({
      ...current,
      quantity: '1',
      address: String(
        computeNextSafeStartAddress(venueSnapshot, current.universe, current.fixtureType, fixtureTypes),
      ),
    }));
    setAddFixtureModalOpen(true);
  }

  async function handleAddFixture() {
    if (!venueSnapshot) {
      return;
    }
    setAddFixtureError('');
    const dims = venueRef.current ?? venueSnapshot;
    const width = dmxAddressWidthForFixtureType(newFixtureValues.fixtureType, fixtureTypes);
    const startAddress = Math.max(1, Math.floor(Number(newFixtureValues.address) || 1));
    const requestedQty = Math.max(1, Math.min(64, Math.floor(Number(newFixtureValues.quantity) || 1)));
    let qty = requestedQty;
    const lastChannel = startAddress + qty * width - 1;
    if (lastChannel > 512) {
      const maxQty = Math.max(0, Math.floor((512 - startAddress + 1) / width));
      if (maxQty < 1) {
        setAddFixtureError('Starting address is too high for this fixture type in a single universe.');
        return;
      }
      qty = Math.min(requestedQty, maxQty);
      if (qty < requestedQty) {
        setAddFixtureError(`Only ${qty} fixture(s) fit before channel 512.`);
      }
    }
    const baseY = dims.floor_depth / 2;
    const z = Math.max(dims.floor_height * 0.5, 4);
    const centerX = dims.floor_width / 2;
    const rowStartX = centerX - ((qty - 1) * CLONE_LIGHT_OFFSET_X_M) / 2;

    const isManualType = newFixtureValues.fixtureType === 'manual_dimmer_channel';
    let snap = venueSnapshot;
    for (let i = 0; i < qty; i += 1) {
      snap = await apiAddFixture(snap.summary.id, {
        fixture_type: newFixtureValues.fixtureType,
        address: startAddress + i * width,
        universe: newFixtureValues.universe,
        x: rowStartX + i * CLONE_LIGHT_OFFSET_X_M,
        y: baseY,
        z,
        rotation_x: 0,
        rotation_y: 0,
        rotation_z: 0,
        is_manual: isManualType,
        options: {},
      });
    }
    setVenueSnapshot(snap);
    setAddFixtureModalOpen(false);
    setAddFixtureError('');
  }

  async function handleMagicRepatch() {
    if (!venueSnapshot) {
      return;
    }
    const fixtures = venueSnapshot.fixtures || [];
    if (fixtures.length === 0) {
      return;
    }
    const ok = window.confirm(
      'Repack all DMX addresses in each universe to start at channel 1 with no gaps between fixtures? Current addresses will be replaced.',
    );
    if (!ok) {
      return;
    }
    try {
      const snap = await apiMagicRepatchFixtures(venueSnapshot.summary.id);
      setVenueSnapshot(snap);
    } catch (err) {
      let message = err instanceof Error ? err.message : String(err);
      try {
        const parsed = JSON.parse(message);
        if (parsed && typeof parsed.error === 'string') {
          message = parsed.error;
        }
      } catch {
        /* keep message */
      }
      window.alert(message);
    }
  }

  async function handleGroupSelectedFixtures() {
    if (!venueSnapshot || selectedFixtureIds.length < 2) {
      return;
    }
    const base =
      window.prompt('Group name', `Group ${fixtureListGroups.groups.length + 1}`)?.trim() ?? '';
    if (!base) {
      return;
    }
    let snapshot = venueSnapshot;
    for (const id of selectedFixtureIds) {
      snapshot = await apiPatchFixture(venueSnapshot.summary.id, id, { group_name: base });
    }
    setVenueSnapshot(snapshot);
  }

  async function handleRenameFixtureGroup(oldName, newName) {
    if (!venueSnapshot || !oldName?.trim()) {
      return;
    }
    const next = newName?.trim() ?? '';
    if (!next || next === oldName) {
      return;
    }
    const fixtures = venueSnapshot.fixtures.filter((f) => f.group_name === oldName);
    if (fixtures.length === 0) {
      return;
    }
    let snapshot = venueSnapshot;
    for (const f of fixtures) {
      snapshot = await apiPatchFixture(venueSnapshot.summary.id, f.id, { group_name: next });
    }
    setVenueSnapshot(snapshot);
  }

  async function handleRenameFixtureGroupPrompt(oldName) {
    if (!venueSnapshot || !oldName?.trim()) {
      return;
    }
    const raw = window.prompt('Rename group', oldName);
    if (raw == null) {
      return;
    }
    await handleRenameFixtureGroup(oldName, raw);
  }

  async function handleUngroupFixtureGroup(name) {
    if (!venueSnapshot || !name?.trim()) {
      return;
    }
    const fixtures = venueSnapshot.fixtures.filter((f) => f.group_name === name);
    if (fixtures.length === 0) {
      return;
    }
    let snapshot = venueSnapshot;
    for (const f of fixtures) {
      snapshot = await apiPatchFixture(venueSnapshot.summary.id, f.id, { group_name: null });
    }
    setVenueSnapshot(snapshot);
  }

  function handleFixtureGroupHeaderClick(groupedFixtures) {
    setSelectedKind('fixture');
    const idSet = new Set(groupedFixtures.map((f) => f.id));
    const ordered = fixturesInPanelOrder.filter((f) => idSet.has(f.id));
    if (ordered.length === 0) {
      return;
    }
    setSelectedFixtureIds(ordered.map((f) => f.id));
    const flat = fixturesInPanelOrder;
    const firstIdx = flat.findIndex((f) => idSet.has(f.id));
    if (firstIdx >= 0) {
      fixtureListRangeAnchorIndexRef.current = firstIdx;
    }
  }

  async function handleSaveSelectedFixtureAddressing() {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    const snap = await apiPatchFixture(venueSnapshot.summary.id, selectedFixture.id, {
      address: Number(selectedFixtureValues.address || 1),
      universe: selectedFixtureValues.universe,
    });
    setVenueSnapshot(snap);
    setAddressModalOpen(false);
  }

  async function handleRemoveFixture() {
    setContextMenu((current) => ({ ...current, visible: false }));
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    const snap = await apiDeleteFixture(venueSnapshot.summary.id, selectedFixture.id);
    setVenueSnapshot(snap);
    const nextIds = selectedFixtureIds.filter((id) => id !== selectedFixture.id);
    setSelectedFixtureIds(nextIds);
    if (nextIds.length === 0) {
      setSelectedKind(null);
    }
  }

  async function handleCloneFixture(fixture) {
    if (!venueSnapshot || !fixture) {
      return;
    }
    const w = dmxAddressWidthForFixture(fixture, fixtureTypes);
    const { address, universe } = cloneAddressAndUniverse(fixture, w, supportedUniverses);
    const baseName = fixture.name?.trim();
    const snap = await apiAddFixture(venueSnapshot.summary.id, {
      fixture_type: fixture.fixture_type,
      address,
      universe,
      x: fixture.x + CLONE_LIGHT_OFFSET_X_M,
      y: fixture.y,
      z: fixture.z,
      rotation_x: fixture.rotation_x ?? 0,
      rotation_y: fixture.rotation_y ?? 0,
      rotation_z: fixture.rotation_z ?? 0,
      name: baseName ? `${baseName} copy` : null,
      group_name: fixture.group_name ?? null,
      is_manual: fixture.is_manual ?? fixture.fixture_type === 'manual_dimmer_channel',
      options: { ...(fixture.options || {}) },
    });
    setVenueSnapshot(snap);
  }

  function handleMakeVenueActive() {
    if (!venueSnapshot) {
      return;
    }
    void patchControlState({ active_venue_id: venueSnapshot.summary.id }).then((next) => {
      setControlState((current) => ({ ...current, ...next }));
    });
  }

  async function handleRotateSelection(axis, direction) {
    if (!venueSnapshot || !selectedKind) {
      return;
    }
    const deltaRadians = degreesToRadians(ROTATION_STEP_DEGREES * direction);

    if (selectedKind === 'fixture') {
      if (selectedFixtureIds.length === 0) {
        return;
      }
      let snapshot = venueSnapshot;
      for (const id of selectedFixtureIds) {
        const fixture = snapshot.fixtures.find((f) => f.id === id);
        if (!fixture) {
          continue;
        }
        const nextRotation = normalizeRightAngleRadians(
          (fixture[`rotation_${axis}`] || 0) + deltaRadians,
        );
        snapshot = await apiPatchFixture(venueSnapshot.summary.id, id, {
          [`rotation_${axis}`]: nextRotation,
        });
      }
      setVenueSnapshot(snapshot);
      return;
    }

    if (selectedKind === 'video_wall') {
      const videoWallSceneObject = venueSnapshot.scene_objects.find((sceneObject) => sceneObject.kind === 'video_wall');
      if (!videoWallSceneObject) {
        return;
      }
      const nextRotation = normalizeRightAngleRadians((videoWallSceneObject[`rotation_${axis}`] || 0) + deltaRadians);
      const snap = await apiPatchSceneObject(venueSnapshot.summary.id, 'video_wall', {
        [`rotation_${axis}`]: nextRotation,
      });
      setVenueSnapshot(snap);
      return;
    }

    if (selectedKind === 'dj_booth') {
      const djTableSceneObject = venueSnapshot.scene_objects.find((sceneObject) => sceneObject.kind === 'dj_table');
      if (!djTableSceneObject) {
        return;
      }
      const nextRotation = normalizeRightAngleRadians((djTableSceneObject[`rotation_${axis}`] || 0) + deltaRadians);
      await apiPatchSceneObject(venueSnapshot.summary.id, 'dj_table', { [`rotation_${axis}`]: nextRotation });
      const snap = await apiPatchSceneObject(venueSnapshot.summary.id, 'dj_cutout', {
        [`rotation_${axis}`]: nextRotation,
      });
      setVenueSnapshot(snap);
    }
  }

  /**
   * Apply a partial pan/tilt range patch (any subset of the four keys) to every
   * selected moving-head fixture. Non-moving-head fixtures in the selection are
   * skipped silently so mixed selections don't poison the batch. The caller is
   * expected to coalesce drags into a single commit (e.g. on pointer-up) rather
   * than firing one request per slider tick.
   */
  async function handleUpdateFixturePanTiltRange(patch) {
    if (!venueSnapshot || selectedFixtureIds.length === 0) {
      return;
    }
    const cleaned = {};
    for (const key of PAN_TILT_RANGE_KEYS) {
      if (patch && key in patch) {
        const numeric = Number(patch[key]);
        if (Number.isFinite(numeric)) {
          cleaned[key] = numeric;
        }
      }
    }
    if (Object.keys(cleaned).length === 0) {
      return;
    }
    const targetIds = selectedFixtureIds.filter((id) => {
      const f = venueSnapshot.fixtures.find((x) => x.id === id);
      return f && isMovingHeadFixtureType(f.fixture_type);
    });
    if (targetIds.length === 0) {
      return;
    }
    let snapshot = venueSnapshot;
    for (const id of targetIds) {
      snapshot = await apiPatchFixture(venueSnapshot.summary.id, id, cleaned);
    }
    setVenueSnapshot(snapshot);
  }

  return (
    <>
      <div className="dense-editor-shell">
        <aside className="dense-sidebar">
          <div className="panel dense-header-panel">
            <div className="dense-header-top" ref={editorMenuRef}>
              <div className="dense-header-leading">
                <button
                  className="small-button secondary-button icon-only-button"
                  aria-label="Back to venues"
                  onClick={() => window.location.assign(withCurrentSearch('/venues'))}
                >
                  ←
                </button>
                {venueSnapshot && controlState.active_venue_id === venueSnapshot.summary.id ? (
                  <span
                    className="dense-venue-active-badge"
                    title={
                      liveLightingPulse
                        ? 'Active venue — receiving live lighting updates'
                        : 'This venue is the active runtime venue'
                    }
                  >
                    {liveLightingPulse ? (
                      <span className="dense-live-pulse-dot" aria-hidden />
                    ) : null}
                    <span className="dense-venue-active-label">ACTIVE</span>
                  </span>
                ) : null}
              </div>
              <div className="dense-editor-menu-wrap">
                <button
                  type="button"
                  className="small-button secondary-button icon-only-button"
                  aria-label="Settings"
                  aria-expanded={editorMenuOpen}
                  aria-haspopup="true"
                  onClick={() => {
                    setEditorMenuOpen((open) => !open);
                    setEditorMenuSection(null);
                  }}
                >
                  ☰
                </button>
                {editorMenuOpen ? (
                  <div className="dense-editor-menu-dropdown" role="menu">
                    <div className="dense-editor-menu-section">
                      <a
                        className="dense-editor-menu-heading dense-editor-menu-external-link"
                        href={withCurrentSearch('/remote')}
                        target="_blank"
                        rel="noopener noreferrer"
                        role="menuitem"
                        onClick={() => setEditorMenuOpen(false)}
                      >
                        Open remote control
                      </a>
                    </div>
                    <div className="dense-editor-menu-section">
                      <button
                        type="button"
                        id="magic-repatch-fixtures-button"
                        className="dense-editor-menu-heading"
                        role="menuitem"
                        disabled={!venueSnapshot || (venueSnapshot.fixtures || []).length === 0}
                        title="Repack DMX addresses from 1 with no gaps (per universe)"
                        onClick={() => {
                          void handleMagicRepatch();
                          setEditorMenuOpen(false);
                          setEditorMenuSection(null);
                        }}
                      >
                        Magic repatch
                      </button>
                    </div>
                    {venueSnapshot && controlState.active_venue_id !== venueSnapshot.summary.id ? (
                      <div className="dense-editor-menu-section">
                        <button
                          type="button"
                          className="dense-editor-menu-heading dense-editor-menu-make-active"
                          role="menuitem"
                          onClick={() => {
                            handleMakeVenueActive();
                            setEditorMenuOpen(false);
                            setEditorMenuSection(null);
                          }}
                        >
                          Make venue active
                        </button>
                      </div>
                    ) : null}
                    <div className="dense-editor-menu-section">
                      <button
                        type="button"
                        className="dense-editor-menu-heading"
                        aria-expanded={editorMenuSection === 'color_scheme'}
                        onClick={() =>
                          setEditorMenuSection((s) => (s === 'color_scheme' ? null : 'color_scheme'))
                        }
                      >
                        Color scheme
                        <span className="dense-editor-menu-chevron" aria-hidden>
                          ▸
                        </span>
                      </button>
                      {editorMenuSection === 'color_scheme' ? (
                        <div className="dense-editor-menu-sub" role="group" aria-label="Color scheme">
                          {remoteConfig.theme_names.map((themeName) => (
                            <label key={themeName} className="dense-editor-menu-option">
                              <input
                                type="radio"
                                name="remote-color-scheme"
                                checked={controlState.theme_name === themeName}
                                onChange={() => {
                                  void patchControlState({ theme_name: themeName }).then((next) => {
                                    setControlState((current) => ({ ...current, ...next }));
                                  });
                                  setEditorMenuOpen(false);
                                  setEditorMenuSection(null);
                                }}
                              />
                              <span>{themeName}</span>
                            </label>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
            <div className="dense-venue-name-row">
              <textarea
                id="venue-name-input"
                className="venue-name-input"
                rows="1"
                value={venueNameDraft}
                onChange={(event) => setVenueNameDraft(event.target.value)}
              />
            </div>
          </div>

          <div className="panel dense-panel">
            <div className="dense-section-header dense-lights-header">
              <h3>Lights</h3>
              <div className="dense-lights-header-actions">
                <button
                  id="open-add-light-modal-button"
                  type="button"
                  className="dense-lights-add-icon"
                  aria-label="Add light"
                  disabled={!venueSnapshot}
                  onClick={() => handleOpenAddFixtureModal()}
                >
                  +
                </button>
              </div>
            </div>
            <div id="fixture-list" className="fixture-list dense-fixture-list">
              {(venueSnapshot?.fixtures || []).length === 0 ? (
                <div className="fixture-empty-state">No lights yet. Tap + next to Lights.</div>
              ) : (
                <>
                  {fixtureListGroups.ungrouped.map((fixture) => (
                    <button
                      key={fixture.id}
                      type="button"
                      className={`fixture-row dense-fixture-row${selectedFixtureIds.includes(fixture.id) ? ' active-choice' : ''}`}
                      onMouseDown={(event) => {
                        if (event.shiftKey || event.metaKey || event.ctrlKey) {
                          event.preventDefault();
                        }
                      }}
                      onClick={(event) => handleFixtureListRowClick(fixture, event)}
                    >
                      <span className="dense-fixture-main">
                        <span className="dense-fixture-name">{fixture.name || fixture.fixture_type}</span>
                        {fixture.name ? (
                          <span className="fixture-row-meta dense-fixture-meta">{fixture.fixture_type}</span>
                        ) : null}
                      </span>
                      <span className="dense-fixture-actions">
                        {selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id ? (
                          <>
                            <button
                              className="icon-button small-button link-button"
                              onClick={(event) => {
                                event.stopPropagation();
                                setAddressModalOpen(true);
                              }}
                            >
                              {`${fixture.universe}:${fixture.address}`}
                            </button>
                            <button
                              type="button"
                              className="icon-button small-button secondary-button"
                              aria-label="Clone light"
                              onClick={(event) => {
                                event.stopPropagation();
                                void handleCloneFixture(fixture);
                              }}
                            >
                              Clone
                            </button>
                            <button
                              className="icon-button small-button danger-button"
                              aria-label="Delete light"
                              onClick={(event) => {
                                event.stopPropagation();
                                void handleRemoveFixture();
                              }}
                            >
                              🗑
                            </button>
                          </>
                        ) : (
                          <span className="fixture-row-meta">{`${fixture.universe}:${fixture.address}`}</span>
                        )}
                      </span>
                    </button>
                  ))}
                  {fixtureListGroups.groups.map(({ name, fixtures: groupedFixtures }) => (
                    <div key={name} className="dense-fixture-group-block">
                      <div
                        className="dense-fixture-group-header"
                        onContextMenu={(event) => {
                          event.preventDefault();
                          setContextMenu({
                            visible: true,
                            x: event.clientX,
                            y: event.clientY,
                            kind: 'group',
                            groupName: name,
                          });
                        }}
                      >
                        <div className="dense-fixture-group-header-row">
                          <button
                            type="button"
                            className="dense-fixture-group-title-button"
                            onClick={() => handleFixtureGroupHeaderClick(groupedFixtures)}
                          >
                            {name}
                          </button>
                        </div>
                      </div>
                      <div className="dense-fixture-group-nested">
                        {groupedFixtures.map((fixture) => (
                          <button
                            key={fixture.id}
                            type="button"
                            className={`fixture-row dense-fixture-row dense-fixture-row-nested${selectedFixtureIds.includes(fixture.id) ? ' active-choice' : ''}`}
                            onMouseDown={(event) => {
                              if (event.shiftKey || event.metaKey || event.ctrlKey) {
                                event.preventDefault();
                              }
                            }}
                            onClick={(event) => handleFixtureListRowClick(fixture, event)}
                          >
                            <span className="dense-fixture-main">
                              <span className="dense-fixture-name">{fixture.name || fixture.fixture_type}</span>
                              {fixture.name ? (
                                <span className="fixture-row-meta dense-fixture-meta">{fixture.fixture_type}</span>
                              ) : null}
                            </span>
                            <span className="dense-fixture-actions">
                              {selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id ? (
                                <>
                                  <button
                                    className="icon-button small-button link-button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setAddressModalOpen(true);
                                    }}
                                  >
                                    {`${fixture.universe}:${fixture.address}`}
                                  </button>
                                  <button
                                    type="button"
                                    className="icon-button small-button secondary-button"
                                    aria-label="Clone light"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      void handleCloneFixture(fixture);
                                    }}
                                  >
                                    Clone
                                  </button>
                                  <button
                                    className="icon-button small-button danger-button"
                                    aria-label="Delete light"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      void handleRemoveFixture();
                                    }}
                                  >
                                    🗑
                                  </button>
                                </>
                              ) : (
                                <span className="fixture-row-meta">{`${fixture.universe}:${fixture.address}`}</span>
                              )}
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>

          <div className="panel dense-panel">
            <div className="dense-section-header">
              <h3>Floor</h3>
            </div>
            <div className="floor-inline-row">
              <label className="compact-label">
                <span>W</span>
                <input
                  id="floor-width"
                  type="number"
                  step="10"
                  value={floorValues.width}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setFloorValues((current) => ({ ...current, width: nextValue }));
                    const parsedWidth = feetToMeters(Number(nextValue));
                    if (Number.isFinite(parsedWidth) && parsedWidth > 0) {
                      sceneControllerRef.current?.updateFloorPreview({
                        width: parsedWidth,
                        depth: feetToMeters(Number(floorValues.height || metersToFeet(venueRef.current?.floor_depth || 0))),
                      });
                    }
                  }}
                />
                <span className="compact-suffix">ft</span>
              </label>
              <label className="compact-label">
                <span>H</span>
                <input
                  id="floor-height"
                  type="number"
                  step="10"
                  value={floorValues.height}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setFloorValues((current) => ({ ...current, height: nextValue }));
                    const parsedDepth = feetToMeters(Number(nextValue));
                    if (Number.isFinite(parsedDepth) && parsedDepth > 0) {
                      sceneControllerRef.current?.updateFloorPreview({
                        width: feetToMeters(Number(floorValues.width || metersToFeet(venueRef.current?.floor_width || 0))),
                        depth: parsedDepth,
                      });
                    }
                  }}
                />
                <span className="compact-suffix">ft</span>
              </label>
            </div>
          </div>

          <div className="panel dense-panel">
            <div className="dense-section-header">
              <h3>Video screen</h3>
            </div>
            <div className="floor-inline-row">
              <label className="compact-label">
                <span>W</span>
                <input
                  id="video-wall-width"
                  type="number"
                  step="1"
                  value={videoWallSizeValues.width}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    const nextState = { ...videoWallSizeValues, width: nextValue };
                    setVideoWallSizeValues(nextState);
                    const parsedW = feetToMeters(Number(nextValue));
                    const parsedH = feetToMeters(Number(nextState.height || 0));
                    const fallback = venueRef.current?.video_wall;
                    const w = Number.isFinite(parsedW) && parsedW > 0 ? parsedW : fallback?.width;
                    const h = Number.isFinite(parsedH) && parsedH > 0 ? parsedH : fallback?.height;
                    if (Number.isFinite(w) && w > 0 && Number.isFinite(h) && h > 0) {
                      sceneControllerRef.current?.updateVideoWallPreview({ width: w, height: h });
                    }
                  }}
                />
                <span className="compact-suffix">ft</span>
              </label>
              <label className="compact-label">
                <span>H</span>
                <input
                  id="video-wall-height"
                  type="number"
                  step="1"
                  value={videoWallSizeValues.height}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    const nextState = { ...videoWallSizeValues, height: nextValue };
                    setVideoWallSizeValues(nextState);
                    const parsedH = feetToMeters(Number(nextValue));
                    const parsedW = feetToMeters(Number(nextState.width || 0));
                    const fallback = venueRef.current?.video_wall;
                    const h = Number.isFinite(parsedH) && parsedH > 0 ? parsedH : fallback?.height;
                    const w = Number.isFinite(parsedW) && parsedW > 0 ? parsedW : fallback?.width;
                    if (Number.isFinite(w) && w > 0 && Number.isFinite(h) && h > 0) {
                      sceneControllerRef.current?.updateVideoWallPreview({ width: w, height: h });
                    }
                  }}
                />
                <span className="compact-suffix">ft</span>
              </label>
            </div>
          </div>
        </aside>

        <main className="dense-viewport-shell">
          <div className="floating-view-switcher" role="radiogroup" aria-label="Editor view">
            {['top', 'front', 'side', 'perspective'].map((viewName) => (
              <button
                key={viewName}
                className={`view-chip${currentView === viewName ? ' active' : ''}`}
                aria-checked={currentView === viewName}
                onClick={() => setCurrentView(viewName)}
              >
                {viewName === 'perspective' ? '3D' : viewName[0].toUpperCase() + viewName.slice(1)}
              </button>
            ))}
          </div>

          <div id="viewport" ref={viewportRef} />

          {selectedKind && !(selectedKind === 'fixture' && selectedFixtureIds.length === 0) ? (
            <div className="floating-transform-stack">
              <div className="floating-transform-panel">
                <div className="dense-section-header floating-transform-panel-header">
                  <h3>{selectedKind === 'fixture' ? 'Fixture Rotation' : selectedKind === 'video_wall' ? 'Video Wall Rotation' : 'DJ Booth Rotation'}</h3>
                  <div className="floating-transform-panel-actions">
                    {selectedKind === 'fixture' ? (
                      <button
                        type="button"
                        id="group-selected-fixtures-button"
                        className="small-button secondary-button"
                        disabled={!venueSnapshot || selectedFixtureIds.length < 2}
                        title="Cmd+click to toggle. Shift+click a second row for a range. Group sets FixtureGroup (group_name)."
                        onClick={() => void handleGroupSelectedFixtures()}
                      >
                        Group
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="small-button secondary-button"
                      title="Clear current selection"
                      onClick={() => handleSelectionChange(null)}
                    >
                      Deselect
                    </button>
                  </div>
                </div>
                {['x', 'y', 'z'].map((axis) => {
                  const radians = selectedKind === 'fixture'
                    ? (selectedFixture?.[`rotation_${axis}`] || 0)
                    : (selectedSceneObject?.[`rotation_${axis}`] || 0);
                  return (
                    <div key={axis} className="rotation-row">
                      <span className={`rotation-axis rotation-axis-${axis}`}>{axis.toUpperCase()}</span>
                      <button type="button" className="small-button secondary-button" onClick={() => void handleRotateSelection(axis, -1)}>
                        -45°
                      </button>
                      <span className="rotation-value">{Math.round(radiansToDegrees(radians))}°</span>
                      <button type="button" className="small-button secondary-button" onClick={() => void handleRotateSelection(axis, 1)}>
                        +45°
                      </button>
                    </div>
                  );
                })}
              </div>

              {selectedKind === 'fixture' && selectedMovingHeadFixtures.length > 0 ? (
                <PanTiltRangePanel
                  fixtures={selectedMovingHeadFixtures}
                  onPatch={handleUpdateFixturePanTiltRange}
                />
              ) : null}
            </div>
          ) : null}

          <div className="floating-bottom-bar">
            <div className="tool-radio-group" role="radiogroup" aria-label="Viewport tool">
              <button
                type="button"
                className={`tool-chip${interactionMode === 'rotate' ? ' active' : ''}`}
                aria-checked={interactionMode === 'rotate'}
                aria-keyshortcuts="r"
                title="Orbit the view (R)"
                onClick={() => setInteractionMode('rotate')}
              >
                <ViewportToolIcon mode="rotate" />
                <span className="tool-chip-label">Rotate</span>
                <kbd className="tool-chip-kbd">R</kbd>
              </button>
              <button
                type="button"
                className={`tool-chip${interactionMode === 'pan' ? ' active' : ''}`}
                aria-checked={interactionMode === 'pan'}
                aria-keyshortcuts="h"
                title="Pan the view (H)"
                onClick={() => setInteractionMode('pan')}
              >
                <ViewportToolIcon mode="pan" />
                <span className="tool-chip-label">Pan</span>
                <kbd className="tool-chip-kbd">H</kbd>
              </button>
              <button
                type="button"
                className={`tool-chip${interactionMode === 'select' ? ' active' : ''}`}
                aria-checked={interactionMode === 'select'}
                aria-keyshortcuts="v"
                title="Select and drag fixtures (V)"
                onClick={() => setInteractionMode('select')}
              >
                <ViewportToolIcon mode="select" />
                <span className="tool-chip-label">Cursor</span>
                <kbd className="tool-chip-kbd">V</kbd>
              </button>
            </div>
            <label className="floating-bottom-bar-mode">
              <span className="floating-bottom-bar-mode-label">Mode</span>
              <select
                className="floating-bottom-bar-mode-select"
                aria-label="Lighting mode"
                value={controlState.mode}
                disabled={remoteConfig.available_modes.length === 0}
                onChange={(event) => {
                  const nextMode = event.target.value;
                  void patchControlState({ mode: nextMode }).then((next) => {
                    setControlState((current) => ({ ...current, ...next }));
                  });
                }}
              >
                {remoteConfig.available_modes.map((mode) => (
                  <option key={mode} value={mode}>
                    {labelizeRemoteMode(mode)}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="floating-bottom-bar-palette"
              title="Shift colors"
              aria-label="Shift colors"
              disabled={!remoteConfig.shift_targets?.includes('color_scheme')}
              onClick={() => {
                void postShiftTarget('color_scheme').catch(() => {});
              }}
            >
              <span className="floating-bottom-bar-palette-swatches" aria-hidden="true">
                {(liveColorPalette ?? DEFAULT_EDITOR_COLOR_PALETTE).map((rgb, i) => (
                  <span
                    key={i}
                    className="floating-bottom-bar-palette-swatch"
                    style={{ background: rgbTripleToCss(rgb) }}
                  />
                ))}
              </span>
            </button>
          </div>
        </main>
      </div>

      <div
        id="context-menu"
        className={`context-menu${contextMenu.visible ? '' : ' hidden'}`}
        style={{ left: contextMenu.x, top: contextMenu.y }}
      >
        {contextMenu.kind === 'group' && contextMenu.groupName ? (
          <>
            <button
              type="button"
              id="context-menu-rename-group"
              onClick={() => {
                const gn = contextMenu.groupName;
                setContextMenu((current) => ({ ...current, visible: false }));
                void handleRenameFixtureGroupPrompt(gn);
              }}
            >
              Rename group
            </button>
            <button
              type="button"
              id="context-menu-ungroup"
              onClick={() => {
                const gn = contextMenu.groupName;
                setContextMenu((current) => ({ ...current, visible: false }));
                void handleUngroupFixtureGroup(gn);
              }}
            >
              Ungroup
            </button>
          </>
        ) : (
          <>
            <button
              id="edit-address-button"
              onClick={() => {
                setContextMenu((current) => ({ ...current, visible: false }));
                setAddressModalOpen(true);
              }}
            >
              Edit DMX Addressing
            </button>
            <button id="remove-fixture-button" className="danger-button" onClick={handleRemoveFixture}>
              Remove Fixture
            </button>
          </>
        )}
      </div>

      <Modal
        open={addressModalOpen}
        title={selectedFixture ? `Address ${selectedFixture.name || selectedFixture.fixture_type}` : 'Address Light'}
        onClose={() => setAddressModalOpen(false)}
      >
        <div className="modal-form">
          <label>
            Address
            <input
              id="selected-fixture-address-input"
              type="number"
              step="1"
              min="1"
              value={selectedFixtureValues.address}
              onChange={(event) => setSelectedFixtureValues((current) => ({ ...current, address: event.target.value }))}
            />
          </label>
          <label>
            Universe
            <select
              id="selected-fixture-universe-input"
              value={selectedFixtureValues.universe}
              onChange={(event) => setSelectedFixtureValues((current) => ({ ...current, universe: event.target.value }))}
            >
              {supportedUniverses.map((universe) => (
                <option key={universe.value} value={universe.value}>
                  {`${universe.label} (${universe.value})`}
                </option>
              ))}
            </select>
          </label>
          <div className="modal-actions">
            <button className="secondary-button" onClick={() => setAddressModalOpen(false)}>Cancel</button>
            <button id="save-selected-fixture-addressing-button" onClick={handleSaveSelectedFixtureAddressing} disabled={!selectedFixture}>
              Save Addressing
            </button>
          </div>
        </div>
      </Modal>

      <Modal
        open={addFixtureModalOpen}
        title="Add Light"
        onClose={() => {
          setAddFixtureModalOpen(false);
          setAddFixtureError('');
        }}
        showHeaderCloseButton={false}
      >
        <form
          className="modal-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleAddFixture();
          }}
        >
          <label>
            Fixture Type
            <select
              id="fixture-type-select"
              value={newFixtureValues.fixtureType}
              onChange={(event) => {
                const fixtureType = event.target.value;
                setNewFixtureValues((current) => ({
                  ...current,
                  fixtureType,
                  address: venueSnapshot
                    ? String(
                        computeNextSafeStartAddress(
                          venueSnapshot,
                          current.universe,
                          fixtureType,
                          fixtureTypes,
                        ),
                      )
                    : current.address,
                }));
              }}
            >
              {fixtureTypes.map((fixtureType) => (
                <option key={fixtureType.key} value={fixtureType.key}>
                  {fixtureType.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Quantity
            <input
              id="fixture-quantity-input"
              type="number"
              step="1"
              min="1"
              max="64"
              value={newFixtureValues.quantity}
              onChange={(event) =>
                setNewFixtureValues((current) => ({ ...current, quantity: event.target.value }))
              }
            />
          </label>
          <label>
            Address
            <input
              id="fixture-address-input"
              type="number"
              step="1"
              min="1"
              value={newFixtureValues.address}
              onChange={(event) => setNewFixtureValues((current) => ({ ...current, address: event.target.value }))}
            />
          </label>
          <label>
            Universe
            <select
              id="fixture-universe-input"
              value={newFixtureValues.universe}
              onChange={(event) =>
                setNewFixtureValues((current) => ({ ...current, universe: event.target.value }))
              }
            >
              {supportedUniverses.map((universe) => (
                <option key={universe.value} value={universe.value}>
                  {`${universe.label} (${universe.value})`}
                </option>
              ))}
            </select>
          </label>
          {addFixtureError ? (
            <p className="modal-form-error" role="alert">
              {addFixtureError}
            </p>
          ) : null}
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={() => setAddFixtureModalOpen(false)}>
              Cancel
            </button>
            <button id="add-fixture-button" type="submit">
              Add fixture{Number(newFixtureValues.quantity) > 1 ? 's' : ''}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );

  async function apiActivateVenue(targetVenueId) {
    await fetchJson(`/api/venues/${targetVenueId}/activate`, { method: 'POST' });
  }

  async function apiPatchVenue(targetVenueId, data) {
    return fetchJson(`/api/venues/${targetVenueId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchVideoWall(targetVenueId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/video-wall`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchSceneObject(targetVenueId, kind, data) {
    return fetchJson(`/api/venues/${targetVenueId}/scene-objects/${kind}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiAddFixture(targetVenueId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/fixtures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchFixture(targetVenueId, fixtureId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/fixtures/${fixtureId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiDeleteFixture(targetVenueId, fixtureId) {
    return fetchJson(`/api/venues/${targetVenueId}/fixtures/${fixtureId}`, {
      method: 'DELETE',
    });
  }

  async function apiMagicRepatchFixtures(targetVenueId) {
    return fetchJson(`/api/venues/${targetVenueId}/fixtures/magic-repatch`, {
      method: 'POST',
    });
  }
}

function Modal({ open, title, onClose, children, showHeaderCloseButton = true }) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          {showHeaderCloseButton ? (
            <button type="button" className="small-button secondary-button" onClick={onClose}>Close</button>
          ) : null}
        </div>
        {children}
      </div>
    </div>
  );
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Request failed');
  }
  return response.json();
}

function withCurrentSearch(pathname) {
  return `${pathname}${window.location.search}`;
}

function metersToFeet(value) {
  return value * FEET_PER_METER;
}

function feetToMeters(value) {
  return value / FEET_PER_METER;
}

function degreesToRadians(value) {
  return (value * Math.PI) / 180;
}

function radiansToDegrees(value) {
  return (value * 180) / Math.PI;
}

function normalizeRightAngleRadians(value) {
  const step = degreesToRadians(ROTATION_STEP_DEGREES);
  return Math.round(value / step) * step;
}
