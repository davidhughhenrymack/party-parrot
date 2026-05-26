import { useEffect, useMemo, useRef, useState } from 'react';
import { createSceneController } from './DenseSceneController.js';
import { isMovingHeadFixtureType } from './fixtureModels.js';
import { isViewportWebGlDisabledForTests } from './viewportTestMode.js';

const isTestMode = isViewportWebGlDisabledForTests();
const FEET_PER_METER = 3.280839895;
const ROTATION_STEP_DEGREES = 45;
const BUILT_IN_FIXTURE_TYPE_TARGETS = new Set(['moving_head', 'par']);

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
const DIRECT_DMX_MAX = 255;

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

function isEditableKeyboardTarget(target) {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  );
}

function normalizeHotkeyInput(value) {
  return String(value || '').trim().slice(0, 1).toLowerCase();
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
const EXPENSIVE_EFFECTS_STORAGE_KEY = 'party-parrot-editor-expensive-effects';
const DEFAULT_EXPENSIVE_EFFECTS_ENABLED = true;
const LIGHTING_EFFECT_HOTKEYS = Object.freeze({
  g: 'strobe',
  j: 'big_blinder',
});

function readStoredExpensiveEffects() {
  if (typeof window === 'undefined') {
    return DEFAULT_EXPENSIVE_EFFECTS_ENABLED;
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(EXPENSIVE_EFFECTS_STORAGE_KEY) || 'true');
    if (typeof parsed === 'boolean') {
      return parsed;
    }
    return parsed.bloom !== false && parsed.dynamicLighting !== false;
  } catch {
    return DEFAULT_EXPENSIVE_EFFECTS_ENABLED;
  }
}

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

function paletteToGradient(palette) {
  const colors = Array.isArray(palette) && palette.length > 0
    ? palette.map(rgbTripleToCss)
    : DEFAULT_EDITOR_COLOR_PALETTE.map(rgbTripleToCss);
  if (colors.length === 1) {
    return colors[0];
  }
  return `linear-gradient(135deg, ${colors.join(',')})`;
}

function animationSpecForKey(key) {
  return { type: 'animation', key };
}

function summarizeAnimationSpec(spec) {
  if (!spec || typeof spec !== 'object') {
    return 'Animation';
  }
  if (spec.type === 'animation') {
    if (spec.key === 'MoveNamedPosition' && spec.params?.position_name) {
      return `Named Position: ${spec.params.position_name}`;
    }
    return spec.key || 'Animation';
  }
  if (spec.type === 'with_args') {
    if (spec.key === 'MoveNamedPosition' && spec.params?.position_name) {
      return `Named Position: ${spec.params.position_name}`;
    }
    return spec.name || spec.key || 'Animation';
  }
  if (spec.type === 'combo') {
    return `Stack (${(spec.children || []).length})`;
  }
  if (spec.type === 'randomize') {
    return `Randomize (${(spec.options || []).length})`;
  }
  if (spec.type === 'weighted_randomize') {
    return `Weighted Randomize (${(spec.options || []).length})`;
  }
  if (spec.type === 'signal_switch') {
    return `Signal Switch: ${summarizeAnimationSpec(spec.animation)}`;
  }
  if (spec.type === 'for_bulbs') {
    return `For Bulbs (${(spec.children || []).length})`;
  }
  if (spec.type === 'legacy_mode') {
    return `Legacy ${spec.mode}`;
  }
  return spec.type || 'Animation';
}

function animationDisplayNameForSpec(spec, registryEntryByKey) {
  if (!spec || typeof spec !== 'object') {
    return 'Animation';
  }
  if (spec.type === 'animation' || spec.type === 'with_args') {
    const label = registryEntryByKey.get(spec.key)?.label || spec.name || spec.key || 'Animation';
    if (spec.key === 'MoveNamedPosition' && spec.params?.position_name) {
      return `${label}: ${spec.params.position_name}`;
    }
    return label;
  }
  return summarizeAnimationSpec(spec);
}

function animationCategoryForSpec(spec, registryEntryByKey) {
  if (!spec || typeof spec !== 'object') {
    return 'Animation';
  }
  if (spec.type === 'animation' || spec.type === 'with_args') {
    return registryEntryByKey.get(spec.key)?.category || 'Animation';
  }
  if (spec.type === 'signal_switch') {
    return animationCategoryForSpec(spec.animation, registryEntryByKey);
  }
  if (spec.type === 'randomize') {
    const categories = new Set((spec.options || []).map((option) => animationCategoryForSpec(option, registryEntryByKey)));
    return categories.size === 1 ? [...categories][0] : 'Stack';
  }
  if (spec.type === 'weighted_randomize') {
    const categories = new Set((spec.options || []).map((option) => animationCategoryForSpec(option.animation, registryEntryByKey)));
    return categories.size === 1 ? [...categories][0] : 'Stack';
  }
  if (spec.type === 'combo') {
    return 'Stack';
  }
  return 'Animation';
}

const ANIMATION_CATEGORY_COLORS = {
  Color: { fg: '#f0abfc', bg: 'rgba(192, 38, 211, 0.16)', border: 'rgba(240, 171, 252, 0.36)' },
  Dimmer: { fg: '#fde68a', bg: 'rgba(202, 138, 4, 0.18)', border: 'rgba(253, 230, 138, 0.34)' },
  Movement: { fg: '#93c5fd', bg: 'rgba(37, 99, 235, 0.18)', border: 'rgba(147, 197, 253, 0.36)' },
  Strobe: { fg: '#fca5a5', bg: 'rgba(220, 38, 38, 0.17)', border: 'rgba(252, 165, 165, 0.34)' },
  Gobo: { fg: '#c4b5fd', bg: 'rgba(124, 58, 237, 0.17)', border: 'rgba(196, 181, 253, 0.36)' },
  Focus: { fg: '#99f6e4', bg: 'rgba(13, 148, 136, 0.17)', border: 'rgba(153, 246, 228, 0.34)' },
  Prism: { fg: '#86efac', bg: 'rgba(22, 163, 74, 0.17)', border: 'rgba(134, 239, 172, 0.34)' },
  Stack: { fg: '#cbd5e1', bg: 'rgba(100, 116, 139, 0.17)', border: 'rgba(203, 213, 225, 0.3)' },
  Animation: { fg: '#8ec5ff', bg: 'rgba(88, 166, 255, 0.16)', border: 'rgba(142, 197, 255, 0.34)' },
};

function animationCategoryStyle(category) {
  const color = ANIMATION_CATEGORY_COLORS[category] || ANIMATION_CATEGORY_COLORS.Animation;
  return {
    '--animation-category-fg': color.fg,
    '--animation-category-bg': color.bg,
    '--animation-category-border': color.border,
  };
}

function formatWeightPlaceholder(value) {
  if (!Number.isFinite(value)) {
    return '';
  }
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

function isNamedPositionAnimationSpec(spec) {
  return (
    spec &&
    typeof spec === 'object' &&
    (spec.type === 'animation' || spec.type === 'with_args') &&
    spec.key === 'MoveNamedPosition'
  );
}

function registryEntryForAnimationSpec(spec, registryEntryByKey) {
  if (!spec || typeof spec !== 'object') {
    return null;
  }
  if (spec.type !== 'animation' && spec.type !== 'with_args') {
    return null;
  }
  return registryEntryByKey.get(spec.key) || null;
}

function signalParameterSelection(rawValue, parameter) {
  if (Array.isArray(rawValue)) {
    return rawValue;
  }
  if (typeof rawValue === 'string' && rawValue) {
    return [rawValue];
  }
  return parameter.default ? [parameter.default] : [];
}

function clampDirectDmx(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  return Math.max(0, Math.min(DIRECT_DMX_MAX, numeric));
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

async function postLightingEffect(effect) {
  const response = await fetch('/api/effect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ effect }),
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
    <div className="panel dense-panel pan-tilt-range-panel">
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

function DenseFixtureNameInput({ fixture, onCommit }) {
  const [draft, setDraft] = useState(fixture.name ?? '');

  useEffect(() => {
    setDraft(fixture.name ?? '');
  }, [fixture.id, fixture.name]);

  async function commitIfChanged() {
    const trimmed = draft.trim();
    const nextName = trimmed === '' ? null : trimmed;
    const prevName = fixture.name ?? null;
    if (nextName === prevName) {
      return;
    }
    try {
      await onCommit(nextName);
    } catch (error) {
      console.error('Failed to save fixture name:', error);
      setDraft(fixture.name ?? '');
    }
  }

  return (
    <input
      type="text"
      className="dense-fixture-name-input"
      placeholder={fixture.fixture_type}
      autoComplete="off"
      aria-label={`Optional name (${fixture.fixture_type})`}
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => void commitIfChanged()}
      onKeyDown={(event) => {
        if (event.key === 'Enter') {
          event.currentTarget.blur();
        }
      }}
      onMouseDown={(event) => event.stopPropagation()}
      onClick={(event) => event.stopPropagation()}
    />
  );
}

function NamedPositionsPanel({
  fixture,
  namedPositions,
  assignments,
  activeEdit,
  onStartEdit,
  onStopEdit,
  onAddAssignment,
  onCreateAndAddAssignment,
  onUpdateAssignment,
  onDeleteAssignment,
}) {
  const assignedNameIds = new Set(assignments.map((position) => position.named_position_id));
  const availableNames = namedPositions.filter((position) => !assignedNameIds.has(position.id));
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addPositionId, setAddPositionId] = useState('');
  const [newName, setNewName] = useState('');
  const [editStepMode, setEditStepMode] = useState('coarse');
  const createNewValue = '__create_new_named_position__';
  const addId = addPositionId || availableNames[0]?.id || createNewValue;
  const isCreatingNew = addId === createNewValue;
  const editStep = editStepMode === 'fine' ? 0.01 : 1;

  useEffect(() => {
    if (
      addPositionId &&
      addPositionId !== createNewValue &&
      !availableNames.some((position) => position.id === addPositionId)
    ) {
      setAddPositionId('');
    }
  }, [addPositionId, availableNames, createNewValue]);

  return (
    <div className="panel dense-panel named-positions-panel">
      <div className="dense-section-header named-positions-header">
        <h3>Named positions</h3>
        <button
          type="button"
          className="small-button secondary-button named-position-add-button"
          aria-label="Add named position"
          onClick={() => setAddModalOpen(true)}
        >
          +
        </button>
      </div>

      <div className="named-position-list">
        {assignments.length === 0 ? (
          <p className="named-position-empty">No named positions programmed for this light.</p>
        ) : (
          assignments.map((position) => {
            const isActive =
              activeEdit?.fixtureId === fixture.id &&
              activeEdit?.namedPositionId === position.named_position_id;
            return (
              <div key={position.id} className={`named-position-card${isActive ? ' active' : ''}`}>
                <div className="named-position-card-header">
                  <strong>{position.position_name}</strong>
                  <div className="named-position-header-actions">
                    <button
                      type="button"
                      className={`small-button secondary-button named-position-icon-button${isActive ? ' active' : ''}`}
                      aria-label={isActive ? 'Stop editing named position' : 'Edit named position live'}
                      title={isActive ? 'Stop editing' : 'Edit live'}
                      onClick={() => (isActive ? onStopEdit() : onStartEdit(position))}
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      className="small-button danger-button named-position-icon-button"
                      aria-label="Delete named position from fixture"
                      title="Delete position"
                      onClick={() => onDeleteAssignment(position.named_position_id)}
                    >
                      🗑
                    </button>
                  </div>
                </div>
                {isActive ? (
                  <div className="named-position-card-actions">
                    <div className="named-position-step-toggle" role="radiogroup" aria-label="Edit step size">
                      <button
                        type="button"
                        className={`small-button secondary-button${editStepMode === 'coarse' ? ' active' : ''}`}
                        aria-checked={editStepMode === 'coarse'}
                        role="radio"
                        onClick={() => setEditStepMode('coarse')}
                      >
                        Coarse
                      </button>
                      <button
                        type="button"
                        className={`small-button secondary-button${editStepMode === 'fine' ? ' active' : ''}`}
                        aria-checked={editStepMode === 'fine'}
                        role="radio"
                        onClick={() => setEditStepMode('fine')}
                      >
                        Fine
                      </button>
                    </div>
                  </div>
                ) : null}
                <div className="named-position-values">
                  <label>
                    Pan
                    <input
                      type="number"
                      min="0"
                      max="255"
                      step={isActive ? editStep : 1}
                      value={position.pan}
                      onChange={(event) =>
                        onUpdateAssignment(position.named_position_id, {
                          pan: clampDirectDmx(event.target.value),
                          tilt: position.tilt,
                        })
                      }
                    />
                  </label>
                  <label>
                    Tilt
                    <input
                      type="number"
                      min="0"
                      max="255"
                      step={isActive ? editStep : 1}
                      value={position.tilt}
                      onChange={(event) =>
                        onUpdateAssignment(position.named_position_id, {
                          pan: position.pan,
                          tilt: clampDirectDmx(event.target.value),
                        })
                      }
                    />
                  </label>
                </div>
              </div>
            );
          })
        )}
      </div>

      <Modal
        open={addModalOpen}
        title={`Add position for ${fixture.name || fixture.fixture_type}`}
        onClose={() => setAddModalOpen(false)}
      >
        <form
          className="modal-form"
          onSubmit={async (event) => {
            event.preventDefault();
            if (isCreatingNew) {
              await onCreateAndAddAssignment(newName);
              setNewName('');
            } else {
              await onAddAssignment(addId);
            }
            setAddPositionId('');
            setAddModalOpen(false);
          }}
        >
          <label>
            Named position
            <select value={addId} onChange={(event) => setAddPositionId(event.target.value)}>
              {availableNames.map((position) => (
                <option key={position.id} value={position.id}>
                  {position.name}
                </option>
              ))}
              <option value={createNewValue}>Create new named position...</option>
            </select>
          </label>
          {isCreatingNew ? (
            <label>
              New name
              <input
                type="text"
                placeholder="Mirrorball"
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
              />
            </label>
          ) : null}
          <div className="modal-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => setAddModalOpen(false)}
            >
              Cancel
            </button>
            <button type="submit" disabled={isCreatingNew ? !newName.trim() : !addId}>
              Add position
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

function AnimationEditorPanel({
  venueSnapshot,
  fixtureTypes,
  animationRegistry,
  selectedModeKey,
  onSelectedModeKeyChange,
  onCreateLightingMode,
  onPatchLightingMode,
  onAddAssignment,
  onPatchAssignment,
  onDeleteAssignment,
}) {
  const modes = venueSnapshot?.lighting_modes || [];
  const assignments = venueSnapshot?.animation_assignments || [];
  const namedPositions = venueSnapshot?.named_positions || [];
  const [customTargetDraft, setCustomTargetDraft] = useState({ groupName: '', fixtureType: '' });
  const [customTargets, setCustomTargets] = useState([]);
  const [addTargetModalOpen, setAddTargetModalOpen] = useState(false);
  const [addModeModalOpen, setAddModeModalOpen] = useState(false);
  const [newModeLabel, setNewModeLabel] = useState('');
  const [expandedAssignmentIds, setExpandedAssignmentIds] = useState(() => new Set());
  const selectedMode = modes.find((mode) => mode.key === selectedModeKey) || modes[0] || null;
  const [entrySecondsDraft, setEntrySecondsDraft] = useState('');
  const [hotkeyDraft, setHotkeyDraft] = useState('');
  useEffect(() => {
    setEntrySecondsDraft(selectedMode ? String(selectedMode.entry_seconds ?? 2) : '');
    setHotkeyDraft(selectedMode?.hotkey || '');
  }, [selectedMode?.id, selectedMode?.entry_seconds, selectedMode?.hotkey]);
  const registryByCategory = useMemo(() => {
    const groups = new Map();
    for (const entry of animationRegistry?.animations || []) {
      if (!groups.has(entry.category)) {
        groups.set(entry.category, []);
      }
      groups.get(entry.category).push(entry);
    }
    return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [animationRegistry]);
  const registryEntryByKey = useMemo(
    () => new Map((animationRegistry?.animations || []).map((entry) => [entry.key, entry])),
    [animationRegistry],
  );
  const fixtureTypeLabelByKey = useMemo(
    () => new Map(fixtureTypes.map((fixtureType) => [fixtureType.key, fixtureType.label])),
    [fixtureTypes],
  );
  const groupNames = useMemo(
    () => [...new Set((venueSnapshot?.fixtures || []).map((f) => f.group_name).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [venueSnapshot],
  );
  const venueFixtureTypes = useMemo(
    () => [...new Set((venueSnapshot?.fixtures || []).map((f) => f.fixture_type).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    [venueSnapshot],
  );
  const destinationGroups = useMemo(() => {
    const fixtureTypeTargets = [
      { key: 'all', label: 'All', fixture_group_name: null, fixture_type: null },
      { key: 'moving_head', label: 'Movers', fixture_group_name: null, fixture_type: 'moving_head' },
      { key: 'par', label: 'Pars', fixture_group_name: null, fixture_type: 'par' },
    ];
    const groupTargets = groupNames.map((groupName) => ({
      key: `group:${groupName}`,
      label: groupName,
      fixture_group_name: groupName,
      fixture_type: null,
    }));
    const definedTargetPairs = new Map();
    for (const target of customTargets) {
      if (!target.groupName && BUILT_IN_FIXTURE_TYPE_TARGETS.has(target.fixtureType)) {
        continue;
      }
      definedTargetPairs.set(`${target.groupName || ''}:${target.fixtureType}`, target);
    }
    for (const assignment of assignments) {
      if (
        assignment.lighting_mode_key === selectedModeKey &&
        assignment.fixture_type &&
        (assignment.fixture_group_name || !BUILT_IN_FIXTURE_TYPE_TARGETS.has(assignment.fixture_type))
      ) {
        definedTargetPairs.set(`${assignment.fixture_group_name || ''}:${assignment.fixture_type}`, {
          groupName: assignment.fixture_group_name || '',
          fixtureType: assignment.fixture_type,
        });
      }
    }
    const definedTargets = [...definedTargetPairs.values()]
      .filter((target) => (!target.groupName || groupNames.includes(target.groupName)) && venueFixtureTypes.includes(target.fixtureType))
      .map((target) => ({
        key: target.groupName
          ? `custom:${target.groupName}:type:${target.fixtureType}`
          : `custom:type:${target.fixtureType}`,
        label: target.groupName
          ? `${target.groupName} · ${fixtureTypeLabelByKey.get(target.fixtureType) || target.fixtureType}`
          : fixtureTypeLabelByKey.get(target.fixtureType) || target.fixtureType,
        fixture_group_name: target.groupName || null,
        fixture_type: target.fixtureType,
      }));
    return [
      { key: 'fixture-type', title: 'Fixture Type', targets: fixtureTypeTargets },
      { key: 'group', title: 'Group', targets: groupTargets },
      { key: 'defined', title: 'Defined Targets', targets: definedTargets },
    ];
  }, [assignments, customTargets, fixtureTypeLabelByKey, groupNames, selectedModeKey, venueFixtureTypes]);
  const modeAssignments = assignments.filter((a) => a.lighting_mode_key === selectedModeKey);
  const assignmentsForDestination = (destination) =>
    modeAssignments.filter(
      (a) =>
        (a.fixture_group_name || null) === destination.fixture_group_name &&
        (a.fixture_type || null) === destination.fixture_type,
    );

  function handleDragStart(event, entry) {
    event.dataTransfer.setData(
      'application/x-parrot-animation',
      JSON.stringify(animationSpecForKey(entry.key)),
    );
    event.dataTransfer.effectAllowed = 'copy';
  }

  function handleDrop(event, destination) {
    event.preventDefault();
    const raw = event.dataTransfer.getData('application/x-parrot-animation');
    if (!raw) {
      return;
    }
    const spec = JSON.parse(raw);
    const entry = registryEntryForAnimationSpec(spec, registryEntryByKey);
    const namedPositionParameter = (entry?.parameters || []).find(
      (parameter) => parameter.type === 'named_position',
    );
    if (namedPositionParameter && namedPositions[0]?.name) {
      spec.params = {
        ...(spec.params || {}),
        [namedPositionParameter.key]: namedPositions[0].name,
      };
    }
    void onAddAssignment({
      lighting_mode_key: selectedModeKey,
      fixture_group_name: destination.fixture_group_name,
      fixture_type: destination.fixture_type,
      animation_spec: spec,
    });
  }

  function handleWeightedOptionWeight(assignment, index, value) {
    const numeric = Math.max(1, Math.floor(Number(value) || 1));
    const nextOptions = (assignment.animation_spec.options || []).map((option, i) =>
      i === index ? { ...option, weight: numeric } : option,
    );
    void onPatchAssignment(assignment.id, {
      animation_spec: { ...assignment.animation_spec, options: nextOptions },
    });
  }

  function toggleAssignmentExpanded(assignmentId) {
    setExpandedAssignmentIds((current) => {
      const next = new Set(current);
      if (next.has(assignmentId)) {
        next.delete(assignmentId);
      } else {
        next.add(assignmentId);
      }
      return next;
    });
  }

  function handleAssignmentWeightPercent(assignment, value) {
    const nextSpec = { ...assignment.animation_spec };
    if (value === '') {
      delete nextSpec.weight_percent;
    } else {
      nextSpec.weight_percent = Math.max(0, Math.min(100, Math.floor(Number(value) || 0)));
    }
    void onPatchAssignment(assignment.id, { animation_spec: nextSpec });
  }

  function handleNamedPositionAnimationPosition(assignment, positionName) {
    handleAnimationParameterOverride(assignment, 'position_name', positionName);
  }

  function handleAnimationParameterOverride(assignment, parameterKey, value) {
    const nextParams = { ...(assignment.animation_spec.params || {}) };
    if (value === '') {
      delete nextParams[parameterKey];
    } else {
      nextParams[parameterKey] = value;
    }
    const nextSpec = { ...assignment.animation_spec };
    if (Object.keys(nextParams).length > 0) {
      nextSpec.params = nextParams;
    } else {
      delete nextSpec.params;
    }
    void onPatchAssignment(assignment.id, {
      animation_spec: nextSpec,
    });
  }

  function renderAnimationParameterControl(assignment, parameter) {
    const value = assignment.animation_spec?.params?.[parameter.key] ?? '';
    if (parameter.type === 'number') {
      return (
        <label key={parameter.key} className="animation-parameter-row">
          <span>{parameter.label}</span>
          <input
            type="number"
            min={parameter.min ?? undefined}
            max={parameter.max ?? undefined}
            step={parameter.step ?? 'any'}
            value={value}
            placeholder={String(parameter.default)}
            onChange={(event) =>
              handleAnimationParameterOverride(
                assignment,
                parameter.key,
                event.target.value,
              )
            }
          />
        </label>
      );
    }
    if (parameter.type === 'named_position') {
      return (
        <label key={parameter.key} className="animation-parameter-row">
          <span>{parameter.label}</span>
          <select
            value={value}
            disabled={namedPositions.length === 0}
            onChange={(event) =>
              handleAnimationParameterOverride(assignment, parameter.key, event.target.value)
            }
          >
            <option value="">
              {namedPositions.length === 0 ? 'No named positions' : `Default (${parameter.default || 'none'})`}
            </option>
            {namedPositions.map((position) => (
              <option key={position.id} value={position.name}>
                {position.name}
              </option>
            ))}
          </select>
        </label>
      );
    }
    if (parameter.type === 'signal') {
      const selectedSignals = signalParameterSelection(value, parameter);
      const selectedSet = new Set(selectedSignals);
      return (
        <div key={parameter.key} className="animation-parameter-row animation-signal-parameter-row">
          <span>{parameter.label}</span>
          <div className="animation-signal-checkboxes">
            {(parameter.options || []).map((option) => (
              <label key={option.value} className="animation-signal-checkbox">
                <input
                  type="checkbox"
                  checked={selectedSet.has(option.value)}
                  onChange={(event) => {
                    const next = new Set(selectedSignals);
                    if (event.target.checked) {
                      next.add(option.value);
                    } else {
                      next.delete(option.value);
                    }
                    handleAnimationParameterOverride(
                      assignment,
                      parameter.key,
                      next.size === 0 ? '' : [...next],
                    );
                  }}
                />
                <span>{option.label || option.value}</span>
              </label>
            ))}
          </div>
        </div>
      );
    }
    return (
      <label key={parameter.key} className="animation-parameter-row">
        <span>{parameter.label}</span>
        <input
          value={value}
          placeholder={String(parameter.default)}
          onChange={(event) =>
            handleAnimationParameterOverride(assignment, parameter.key, event.target.value)
          }
        />
      </label>
    );
  }

  function handleAddCustomTarget() {
    const groupName = customTargetDraft.groupName;
    const fixtureType = customTargetDraft.fixtureType;
    if (!fixtureType) {
      return;
    }
    if (!groupName && BUILT_IN_FIXTURE_TYPE_TARGETS.has(fixtureType)) {
      setCustomTargetDraft({ groupName: '', fixtureType: '' });
      setAddTargetModalOpen(false);
      return;
    }
    const key = `${groupName || ''}:${fixtureType}`;
    if (customTargets.some((target) => `${target.groupName || ''}:${target.fixtureType}` === key)) {
      return;
    }
    setCustomTargets((targets) => [...targets, { groupName, fixtureType }]);
    setCustomTargetDraft({ groupName: '', fixtureType: '' });
    setAddTargetModalOpen(false);
  }

  async function handleAddLightingMode() {
    const label = newModeLabel.trim();
    if (!label) {
      return;
    }
    const snapshot = await onCreateLightingMode({ label });
    const createdMode = (snapshot?.lighting_modes || []).find((mode) => mode.label === label);
    if (createdMode) {
      onSelectedModeKeyChange(createdMode.key);
    }
    setNewModeLabel('');
    setAddModeModalOpen(false);
  }

  function commitEntrySecondsDraft() {
    if (!selectedMode || entrySecondsDraft === '') {
      return;
    }
    const numeric = Number(entrySecondsDraft);
    if (!Number.isFinite(numeric)) {
      setEntrySecondsDraft(String(selectedMode.entry_seconds ?? 2));
      return;
    }
    const next = Math.max(0.05, numeric);
    if (next === Number(selectedMode.entry_seconds ?? 2)) {
      setEntrySecondsDraft(String(next));
      return;
    }
    void onPatchLightingMode(selectedMode.id, { entry_seconds: next });
  }

  function commitHotkeyDraft() {
    if (!selectedMode) {
      return;
    }
    const next = normalizeHotkeyInput(hotkeyDraft);
    if (next === (selectedMode.hotkey || '')) {
      setHotkeyDraft(next);
      return;
    }
    void onPatchLightingMode(selectedMode.id, { hotkey: next });
  }

  function renderDestination(destination) {
    const rows = assignmentsForDestination(destination);
    const isEmpty = rows.length === 0;
    const rowsByCategory = new Map();
    for (const assignment of rows) {
      const category = animationCategoryForSpec(assignment.animation_spec, registryEntryByKey);
      if (!rowsByCategory.has(category)) {
        rowsByCategory.set(category, []);
      }
      rowsByCategory.get(category).push(assignment);
    }
    const categoryRows = [...rowsByCategory.entries()].sort((a, b) => a[0].localeCompare(b[0]));
    return (
      <div
        key={destination.key}
        className={`animation-destination${isEmpty ? ' animation-destination-empty' : ''}`}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => handleDrop(event, destination)}
      >
        <div className="animation-destination-header">
          <strong>{destination.label}</strong>
        </div>
        {isEmpty ? (
          <p className="animation-empty-drop">Drop here</p>
        ) : (
          categoryRows.map(([category, assignmentsInCategory]) => {
            const explicitTotal = assignmentsInCategory.reduce(
              (total, assignment) =>
                assignment.animation_spec?.weight_percent == null
                  ? total
                  : total + Number(assignment.animation_spec.weight_percent),
              0,
            );
            const blankCount = assignmentsInCategory.filter(
              (assignment) => assignment.animation_spec?.weight_percent == null,
            ).length;
            const blankPlaceholder =
              blankCount > 0 ? formatWeightPlaceholder(Math.max(0, 100 - explicitTotal) / blankCount) : '';
            return (
              <div
                key={category}
                className="animation-assignment-category-group"
                style={animationCategoryStyle(category)}
              >
                {assignmentsInCategory.map((assignment) => {
                  const registryEntry = registryEntryForAnimationSpec(assignment.animation_spec, registryEntryByKey);
                  const parameters = registryEntry?.parameters || [];
                  const hasWeightedOptions = assignment.animation_spec?.type === 'weighted_randomize';
                  const hasExpandedControls = parameters.length > 0 || hasWeightedOptions;
                  const isExpanded = expandedAssignmentIds.has(assignment.id);
                  return (
                    <div key={assignment.id} className="animation-assignment-row">
                      <span className="animation-assignment-main">
                        <span className="animation-assignment-name">
                          {animationDisplayNameForSpec(assignment.animation_spec, registryEntryByKey)}
                        </span>
                        {hasExpandedControls ? (
                          <button
                            type="button"
                            className="animation-assignment-expand"
                            aria-label={isExpanded ? 'Collapse animation parameters' : 'Expand animation parameters'}
                            aria-expanded={isExpanded}
                            onClick={() => toggleAssignmentExpanded(assignment.id)}
                          >
                            <span className="animation-assignment-expand-triangle" aria-hidden="true" />
                          </button>
                        ) : (
                          <span className="animation-assignment-expand-spacer" aria-hidden="true" />
                        )}
                      </span>
                      <span className="animation-assignment-actions">
                        <label className="animation-weight-percent">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            value={assignment.animation_spec?.weight_percent ?? ''}
                            placeholder={assignment.animation_spec?.weight_percent == null ? blankPlaceholder : ''}
                            onChange={(event) => handleAssignmentWeightPercent(assignment, event.target.value)}
                          />
                          <span>%</span>
                        </label>
                        <button
                          type="button"
                          className="animation-assignment-delete"
                          aria-label="Delete animation"
                          onClick={() => onDeleteAssignment(assignment.id)}
                        >
                          <svg
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <path d="M3 6h18" />
                            <path d="M8 6V4h8v2" />
                            <path d="M19 6l-1 14H6L5 6" />
                            <path d="M10 11v5" />
                            <path d="M14 11v5" />
                          </svg>
                        </button>
                      </span>
                      {isExpanded && parameters.length > 0 ? (
                        <div className="animation-parameter-list">
                          {parameters.map((parameter) =>
                            renderAnimationParameterControl(assignment, parameter),
                          )}
                        </div>
                      ) : null}
                      {isExpanded && hasWeightedOptions ? (
                        <div className="animation-weight-list">
                          {(assignment.animation_spec.options || []).map((option, index) => (
                            <label key={index} className="animation-weight-row">
                              <span>{animationDisplayNameForSpec(option.animation, registryEntryByKey)}</span>
                              <input
                                type="number"
                                min="1"
                                step="1"
                                value={option.weight}
                                onChange={(event) =>
                                  handleWeightedOptionWeight(assignment, index, event.target.value)
                                }
                              />
                            </label>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            );
          })
        )}
      </div>
    );
  }

  return (
    <>
      <div className="panel dense-panel animation-mode-panel">
        <div className="dense-section-header">
          <h3>Animation mode</h3>
          <button
            type="button"
            className="small-button secondary-button dense-lights-add-icon"
            aria-label="Add animation mode"
            onClick={() => setAddModeModalOpen(true)}
          >
            +
          </button>
        </div>
        <select
          className="animation-mode-select"
          value={selectedModeKey || modes[0]?.key || ''}
          onChange={(event) => onSelectedModeKeyChange(event.target.value)}
        >
          {modes.map((mode) => (
            <option key={mode.id} value={mode.key}>
              {mode.label}
            </option>
          ))}
        </select>
        <div className="animation-mode-meta-row">
          <label className="animation-mode-entry-seconds">
            <span>Entry fade</span>
            <input
              type="number"
              min="0.05"
              step="0.05"
              value={entrySecondsDraft}
              disabled={!selectedMode}
              onChange={(event) => setEntrySecondsDraft(event.target.value)}
              onBlur={commitEntrySecondsDraft}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.currentTarget.blur();
                }
              }}
            />
            <span>sec</span>
          </label>
          <label className="animation-mode-hotkey">
            <span>Hot key</span>
            <input
              type="text"
              maxLength={1}
              value={hotkeyDraft}
              disabled={!selectedMode}
              onChange={(event) => setHotkeyDraft(normalizeHotkeyInput(event.target.value))}
              onBlur={commitHotkeyDraft}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.currentTarget.blur();
                }
              }}
            />
          </label>
        </div>
      </div>

      <div className="animation-editor-workspace">
        <div className="panel dense-panel animation-destinations-panel">
          <div className="dense-section-header">
            <h3>Destinations</h3>
          </div>
          {destinationGroups.map((group) => (
            <div key={group.key} className="animation-target-group">
              {group.key === 'fixture-type' ? null : (
                <div className="animation-target-group-header">
                  <div className="section-subtitle">{group.title}</div>
                  {group.key === 'defined' ? (
                    <button
                      type="button"
                      className="small-button secondary-button animation-add-target-button"
                      aria-label="Add selection target"
                      onClick={() => setAddTargetModalOpen(true)}
                    >
                      +
                    </button>
                  ) : null}
                </div>
              )}
              {group.targets.length > 0 ? (
                group.targets.map((destination) => renderDestination(destination))
              ) : (
                <p className="animation-empty-group">No targets yet.</p>
              )}
            </div>
          ))}
        </div>

        <div className="panel dense-panel animation-palette-panel">
          <div className="dense-section-header">
            <h3>Animations</h3>
          </div>
          {registryByCategory.map(([category, entries]) => (
            <div key={category} className="animation-palette-category">
              <div className="section-subtitle">{category}</div>
              <div className="animation-palette-grid">
                {entries.map((entry) => (
                  <button
                    key={entry.key}
                    type="button"
                    className="animation-palette-chip"
                    style={animationCategoryStyle(entry.category)}
                    draggable
                    onDragStart={(event) => handleDragStart(event, entry)}
                    title="Drag onto a destination"
                  >
                    {entry.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <Modal
        open={addModeModalOpen}
        title="Add Animation Mode"
        onClose={() => setAddModeModalOpen(false)}
      >
        <form
          className="modal-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleAddLightingMode();
          }}
        >
          <label>
            Mode name
            <input
              value={newModeLabel}
              onChange={(event) => setNewModeLabel(event.target.value)}
              placeholder="Afterparty"
              autoFocus
            />
          </label>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={() => setAddModeModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" disabled={!newModeLabel.trim()}>
              Add Mode
            </button>
          </div>
        </form>
      </Modal>
      <Modal
        open={addTargetModalOpen}
        title="Add Selection Target"
        onClose={() => setAddTargetModalOpen(false)}
      >
        <form
          className="modal-form animation-target-modal-form"
          onSubmit={(event) => {
            event.preventDefault();
            handleAddCustomTarget();
          }}
        >
          <label>
            Group (optional)
            <select
              value={customTargetDraft.groupName}
              onChange={(event) =>
                setCustomTargetDraft((draft) => ({ ...draft, groupName: event.target.value }))
              }
            >
              <option value="">No group</option>
              {groupNames.map((groupName) => (
                <option key={groupName} value={groupName}>
                  {groupName}
                </option>
              ))}
            </select>
          </label>
          <label>
            Fixture type
            <select
              value={customTargetDraft.fixtureType}
              onChange={(event) =>
                setCustomTargetDraft((draft) => ({ ...draft, fixtureType: event.target.value }))
              }
            >
              <option value="">Choose a fixture type</option>
              {venueFixtureTypes.map((fixtureType) => (
                <option key={fixtureType} value={fixtureType}>
                  {fixtureTypeLabelByKey.get(fixtureType) || fixtureType}
                </option>
              ))}
            </select>
          </label>
          <div className="modal-actions">
            <button type="button" className="secondary-button" onClick={() => setAddTargetModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" disabled={!customTargetDraft.fixtureType}>
              Add Target
            </button>
          </div>
        </form>
      </Modal>
    </>
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
  const [animationRegistry, setAnimationRegistry] = useState({ animations: [], combinators: [] });
  const [editorMode, setEditorMode] = useState('fixture');
  const [selectedAnimationModeKey, setSelectedAnimationModeKey] = useState('chill');
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
    theme_color_examples: [],
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
  const [expensiveEffectsEnabled, setExpensiveEffectsEnabled] = useState(readStoredExpensiveEffects);
  const [activeNamedPositionEdit, setActiveNamedPositionEdit] = useState(null);

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

  const selectedFixtureNamedPositions = useMemo(() => {
    if (!venueSnapshot || !selectedFixture) {
      return [];
    }
    return (venueSnapshot.fixture_named_positions || [])
      .filter((position) => position.fixture_id === selectedFixture.id)
      .sort((a, b) => a.position_name.localeCompare(b.position_name));
  }, [venueSnapshot, selectedFixture]);

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

  useEffect(() => {
    const modes = venueSnapshot?.lighting_modes || [];
    if (modes.length === 0) {
      return;
    }
    if (!modes.some((mode) => mode.key === selectedAnimationModeKey)) {
      setSelectedAnimationModeKey(modes[0].key);
    }
  }, [selectedAnimationModeKey, venueSnapshot]);

  const selectionInspectorVisible =
    editorMode === 'fixture' &&
    Boolean(selectedKind) &&
    !(selectedKind === 'fixture' && selectedFixtureIds.length === 0);

  const selectionSidebarTitle = useMemo(() => {
    if (!selectedKind) {
      return '';
    }
    if (selectedKind === 'fixture') {
      if (selectedFixtureIds.length === 0) {
        return '';
      }
      if (selectedFixtureIds.length > 1) {
        return `${selectedFixtureIds.length} fixtures`;
      }
      return selectedFixture ? selectedFixture.fixture_type : 'Fixture';
    }
    if (selectedKind === 'video_wall') {
      return 'Video screen';
    }
    if (selectedKind === 'dj_booth') {
      return 'DJ booth';
    }
    return '';
  }, [selectedKind, selectedFixtureIds, selectedFixture]);

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
      controller.setExpensiveEffects({
        bloom: expensiveEffectsEnabled,
        dynamicLighting: expensiveEffectsEnabled,
      });
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
        theme_color_examples: config.theme_color_examples || [],
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

      const nextAnimationRegistry = await fetchJson('/api/animation-registry');
      if (disposed) {
        return;
      }
      setAnimationRegistry(nextAnimationRegistry);

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

  /** Opening/closing the inspector changes the viewport column width without a window `resize` event — resize the WebGL canvas. */
  useEffect(() => {
    sceneControllerRef.current?.resize?.();
  }, [selectionInspectorVisible, sceneControllerEpoch]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) {
      return undefined;
    }
    const ro = new ResizeObserver(() => {
      sceneControllerRef.current?.resize?.();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [sceneControllerEpoch]);

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

  useEffect(() => {
    if (!activeNamedPositionEdit || !venueSnapshot) {
      return;
    }
    const assignment = (venueSnapshot.fixture_named_positions || []).find(
      (position) =>
        position.fixture_id === activeNamedPositionEdit.fixtureId &&
        position.named_position_id === activeNamedPositionEdit.namedPositionId,
    );
    if (!assignment) {
      sceneControllerRef.current?.setNamedPositionPreviewOverride(
        activeNamedPositionEdit.fixtureId,
        null,
      );
      void apiPostNamedPositionOverride({
        active: false,
        fixture_id: activeNamedPositionEdit.fixtureId,
      });
      setActiveNamedPositionEdit(null);
      return;
    }
    sceneControllerRef.current?.setNamedPositionPreviewOverride(assignment.fixture_id, {
      pan: assignment.pan,
      tilt: assignment.tilt,
    });
    void apiPostNamedPositionOverride({
      active: true,
      fixture_id: assignment.fixture_id,
      position_name: assignment.position_name,
      pan: assignment.pan,
      tilt: assignment.tilt,
    }).catch(() => {});
  }, [activeNamedPositionEdit, venueSnapshot]);

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
    try {
      window.localStorage.setItem(
        EXPENSIVE_EFFECTS_STORAGE_KEY,
        JSON.stringify(expensiveEffectsEnabled),
      );
    } catch {
      // Ignore storage failures; toggles still work for this session.
    }
    sceneControllerRef.current?.setExpensiveEffects({
      bloom: expensiveEffectsEnabled,
      dynamicLighting: expensiveEffectsEnabled,
    });
  }, [expensiveEffectsEnabled]);

  useEffect(() => {
    if (interactionMode !== 'pan' && interactionMode !== 'rotate') {
      return;
    }
    setSelectedFixtureIds((ids) => (ids.length > 0 ? [] : ids));
    setSelectedKind((currentKind) => (currentKind === 'fixture' ? null : currentKind));
    setContextMenu((current) => ({ ...current, visible: false }));
  }, [interactionMode]);

  useEffect(() => {
    function onLightingModeHotkey(event) {
      if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) {
        return;
      }
      if (event.key.length !== 1 || isEditableKeyboardTarget(event.target)) {
        return;
      }
      const key = event.key.toLowerCase();
      const effect = LIGHTING_EFFECT_HOTKEYS[key];
      if (effect) {
        event.preventDefault();
        void postLightingEffect(effect).catch(() => {});
        return;
      }
      const mode = (venueSnapshot?.lighting_modes || []).find(
        (candidate) => candidate.hotkey === key,
      );
      if (!mode || mode.key === controlState.mode) {
        return;
      }
      event.preventDefault();
      void patchControlState({ mode: mode.key }).then((next) => {
        setControlState((current) => ({ ...current, ...next }));
      });
    }
    window.addEventListener('keydown', onLightingModeHotkey);
    return () => window.removeEventListener('keydown', onLightingModeHotkey);
  }, [controlState.mode, venueSnapshot]);

  useEffect(() => {
    function onViewportToolKey(event) {
      if (event.defaultPrevented) {
        return;
      }
      if (event.metaKey || event.ctrlKey || event.altKey) {
        return;
      }
      if (isEditableKeyboardTarget(event.target)) {
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

  useEffect(() => {
    if (
      activeNamedPositionEdit &&
      (selectedKind !== 'fixture' ||
        selectedFixtureIds.length !== 1 ||
        selectedFixtureIds[0] !== activeNamedPositionEdit.fixtureId)
    ) {
      sceneControllerRef.current?.setNamedPositionPreviewOverride(
        activeNamedPositionEdit.fixtureId,
        null,
      );
      void apiPostNamedPositionOverride({
        active: false,
        fixture_id: activeNamedPositionEdit.fixtureId,
      });
      setActiveNamedPositionEdit(null);
    }
  }, [activeNamedPositionEdit, selectedFixtureIds, selectedKind]);

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

  function handleStartNamedPositionEdit(position) {
    setActiveNamedPositionEdit({
      fixtureId: position.fixture_id,
      namedPositionId: position.named_position_id,
    });
    sceneControllerRef.current?.setNamedPositionPreviewOverride(position.fixture_id, {
      pan: position.pan,
      tilt: position.tilt,
    });
    void apiPostNamedPositionOverride({
      active: true,
      fixture_id: position.fixture_id,
      position_name: position.position_name,
      pan: position.pan,
      tilt: position.tilt,
    }).catch(() => {});
  }

  function handleStopNamedPositionEdit() {
    if (!activeNamedPositionEdit) {
      return;
    }
    sceneControllerRef.current?.setNamedPositionPreviewOverride(
      activeNamedPositionEdit.fixtureId,
      null,
    );
    void apiPostNamedPositionOverride({
      active: false,
      fixture_id: activeNamedPositionEdit.fixtureId,
    }).catch(() => {});
    setActiveNamedPositionEdit(null);
  }

  async function handleAddFixtureNamedPosition(positionId) {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    const snap = await apiPutFixtureNamedPosition(
      venueSnapshot.summary.id,
      selectedFixture.id,
      positionId,
      { pan: 128, tilt: 128 },
    );
    setVenueSnapshot(snap);
  }

  async function handleUpdateFixtureNamedPosition(positionId, values) {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    const pan = clampDirectDmx(values.pan);
    const tilt = clampDirectDmx(values.tilt);
    const snap = await apiPutFixtureNamedPosition(
      venueSnapshot.summary.id,
      selectedFixture.id,
      positionId,
      { pan, tilt },
    );
    setVenueSnapshot(snap);
    if (
      activeNamedPositionEdit?.fixtureId === selectedFixture.id &&
      activeNamedPositionEdit?.namedPositionId === positionId
    ) {
      const positionName =
        (venueSnapshot.named_positions || []).find((position) => position.id === positionId)?.name ??
        '';
      sceneControllerRef.current?.setNamedPositionPreviewOverride(selectedFixture.id, {
        pan,
        tilt,
      });
      void apiPostNamedPositionOverride({
        active: true,
        fixture_id: selectedFixture.id,
        position_name: positionName,
        pan,
        tilt,
      }).catch(() => {});
    }
  }

  async function handleDeleteFixtureNamedPosition(positionId) {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    if (activeNamedPositionEdit?.namedPositionId === positionId) {
      handleStopNamedPositionEdit();
    }
    const snap = await apiDeleteFixtureNamedPosition(
      venueSnapshot.summary.id,
      selectedFixture.id,
      positionId,
    );
    setVenueSnapshot(snap);
  }

  async function handleCreateAndAddFixtureNamedPosition(name) {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    const position = await apiCreateNamedPosition(name);
    const snap = await apiPutFixtureNamedPosition(
      venueSnapshot.summary.id,
      selectedFixture.id,
      position.id,
      { pan: 128, tilt: 128 },
    );
    setVenueSnapshot(snap);
  }

  async function handleAddAnimationAssignment(data) {
    if (!venueSnapshot) {
      return;
    }
    const snap = await apiCreateAnimationAssignment(venueSnapshot.summary.id, data);
    setVenueSnapshot(snap);
  }

  async function handleCreateLightingMode(data) {
    if (!venueSnapshot) {
      return null;
    }
    const snap = await apiCreateLightingMode(venueSnapshot.summary.id, data);
    setVenueSnapshot(snap);
    const nextModes = (snap.lighting_modes || []).map((mode) => mode.key);
    setRemoteConfig((current) => ({
      ...current,
      available_modes: [
        ...current.available_modes.filter((mode) => ['test', 'blackout', 'home'].includes(mode)),
        ...nextModes,
      ],
    }));
    return snap;
  }

  async function handlePatchLightingMode(lightingModeId, data) {
    if (!venueSnapshot) {
      return;
    }
    const snap = await apiPatchLightingMode(venueSnapshot.summary.id, lightingModeId, data);
    setVenueSnapshot(snap);
  }

  async function handlePatchAnimationAssignment(assignmentId, data) {
    if (!venueSnapshot) {
      return;
    }
    const snap = await apiPatchAnimationAssignment(venueSnapshot.summary.id, assignmentId, data);
    setVenueSnapshot(snap);
  }

  async function handleDeleteAnimationAssignment(assignmentId) {
    if (!venueSnapshot) {
      return;
    }
    const snap = await apiDeleteAnimationAssignment(venueSnapshot.summary.id, assignmentId);
    setVenueSnapshot(snap);
  }

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

  async function apiCreateNamedPosition(name) {
    return fetchJson('/api/named-positions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
  }

  async function apiPutFixtureNamedPosition(targetVenueId, fixtureId, positionId, data) {
    return fetchJson(
      `/api/venues/${targetVenueId}/fixtures/${fixtureId}/named-positions/${positionId}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      },
    );
  }

  async function apiDeleteFixtureNamedPosition(targetVenueId, fixtureId, positionId) {
    return fetchJson(
      `/api/venues/${targetVenueId}/fixtures/${fixtureId}/named-positions/${positionId}`,
      {
        method: 'DELETE',
      },
    );
  }

  async function apiPostNamedPositionOverride(data) {
    return fetchJson('/api/runtime/named-position-override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiCreateAnimationAssignment(targetVenueId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/animations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiCreateLightingMode(targetVenueId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/lighting-modes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchLightingMode(targetVenueId, lightingModeId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/lighting-modes/${lightingModeId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchAnimationAssignment(targetVenueId, assignmentId, data) {
    return fetchJson(`/api/venues/${targetVenueId}/animations/${assignmentId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiDeleteAnimationAssignment(targetVenueId, assignmentId) {
    return fetchJson(`/api/venues/${targetVenueId}/animations/${assignmentId}`, {
      method: 'DELETE',
    });
  }

  function handleOpenAnimationEditor() {
    const editableModes = venueSnapshot?.lighting_modes || [];
    const liveEditableMode = editableModes.find((mode) => mode.key === controlState.mode);
    setSelectedAnimationModeKey(liveEditableMode?.key || editableModes[0]?.key || selectedAnimationModeKey);
    setEditorMode('animation');
  }

  const themeExampleByName = new Map(
    (remoteConfig.theme_color_examples || []).map((example) => [example.name, example]),
  );
  const selectedThemeExample = themeExampleByName.get(controlState.theme_name);
  const selectedThemeAlwaysRainbow = selectedThemeExample?.always_rainbow === true;

  return (
    <>
      <div
        className={`dense-editor-shell${selectionInspectorVisible ? ' dense-editor-shell-inspector-open' : ''}${editorMode === 'animation' ? ' dense-editor-shell-animation' : ''}`}
      >
        <aside className={`dense-sidebar${editorMode === 'animation' ? ' dense-sidebar-animation' : ''}`}>
          <div className="panel dense-header-panel">
            <div className="dense-header-top" ref={editorMenuRef}>
              <div className="dense-header-leading">
                {venueSnapshot && controlState.active_venue_id === venueSnapshot.summary.id ? (
                  <span
                    className="dense-venue-active-badge"
                    title={
                      liveLightingPulse
                        ? 'Active venue — receiving live lighting updates'
                        : 'This venue is the active runtime venue'
                    }
                  >
                    <span className={`dense-live-pulse-dot${liveLightingPulse ? ' is-pulsing' : ''}`} aria-hidden />
                  </span>
                ) : null}
              </div>
              <textarea
                id="venue-name-input"
                className="venue-name-input"
                rows="1"
                value={venueNameDraft}
                onChange={(event) => setVenueNameDraft(event.target.value)}
              />
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
                        href={withCurrentSearch('/venues')}
                        role="menuitem"
                        onClick={() => setEditorMenuOpen(false)}
                      >
                        Back to venues
                      </a>
                    </div>
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
                      <a
                        className="dense-editor-menu-heading dense-editor-menu-external-link"
                        href={patchListHref(venueSnapshot?.summary?.id)}
                        role="menuitem"
                        onClick={() => setEditorMenuOpen(false)}
                      >
                        Patch list
                      </a>
                    </div>
                    <div className="dense-editor-menu-section">
                      <a
                        className="dense-editor-menu-heading dense-editor-menu-external-link"
                        href={withCurrentSearch('/interpretation')}
                        target="_blank"
                        rel="noopener noreferrer"
                        role="menuitem"
                        onClick={() => setEditorMenuOpen(false)}
                      >
                        Interpretation tree
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
                      <label className="dense-editor-menu-option dense-editor-menu-checkbox">
                        <input
                          type="checkbox"
                          checked={expensiveEffectsEnabled}
                          onChange={(event) => {
                            setExpensiveEffectsEnabled(event.target.checked);
                          }}
                        />
                        <span>Expensive effects</span>
                      </label>
                    </div>
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
                          {remoteConfig.theme_names.map((themeName) => {
                            const example = themeExampleByName.get(themeName);
                            const palette = example?.palette ?? DEFAULT_EDITOR_COLOR_PALETTE;
                            const alwaysRainbow = example?.always_rainbow === true;
                            return (
                              <label
                                key={themeName}
                                className={`dense-editor-menu-option dense-editor-color-option${alwaysRainbow ? ' rainbow-gradient-bg' : ''}`}
                                style={{ '--dense-color-option-gradient': paletteToGradient(palette) }}
                              >
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
                                <span className="dense-editor-color-option-swatches" aria-hidden="true">
                                  {palette.map((rgb, i) => (
                                    <span
                                      key={i}
                                      className={`dense-editor-color-option-swatch${i === 0 && alwaysRainbow ? ' rainbow-hue-tile' : ''}`}
                                      style={i === 0 && alwaysRainbow ? undefined : { background: rgbTripleToCss(rgb) }}
                                    />
                                  ))}
                                </span>
                                <span>{themeName}</span>
                              </label>
                            );
                          })}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
            <div className="editor-mode-toggle" role="radiogroup" aria-label="Editor mode">
              <button
                type="button"
                className={`view-chip${editorMode === 'fixture' ? ' active' : ''}`}
                role="radio"
                aria-checked={editorMode === 'fixture'}
                onClick={() => setEditorMode('fixture')}
              >
                Fixtures
              </button>
              <button
                type="button"
                className={`view-chip${editorMode === 'animation' ? ' active' : ''}`}
                role="radio"
                aria-checked={editorMode === 'animation'}
                onClick={handleOpenAnimationEditor}
              >
                Animations
              </button>
            </div>
          </div>

          {editorMode === 'animation' ? (
            <AnimationEditorPanel
              venueSnapshot={venueSnapshot}
              fixtureTypes={fixtureTypes}
              animationRegistry={animationRegistry}
              selectedModeKey={selectedAnimationModeKey}
              onSelectedModeKeyChange={setSelectedAnimationModeKey}
              onCreateLightingMode={handleCreateLightingMode}
              onPatchLightingMode={handlePatchLightingMode}
              onAddAssignment={handleAddAnimationAssignment}
              onPatchAssignment={handlePatchAnimationAssignment}
              onDeleteAssignment={handleDeleteAnimationAssignment}
            />
          ) : (
            <>
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
                      aria-label={selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id ? `${fixture.universe}:${fixture.address}` : undefined}
                      onMouseDown={(event) => {
                        if (event.shiftKey || event.metaKey || event.ctrlKey) {
                          event.preventDefault();
                        }
                      }}
                      onClick={(event) => {
                        if (selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id) {
                          setAddressModalOpen(true);
                          return;
                        }
                        handleFixtureListRowClick(fixture, event);
                      }}
                    >
                      <span className="dense-fixture-main">
                        <span className="dense-fixture-name">{fixture.name || fixture.fixture_type}</span>
                        {fixture.name ? (
                          <span className="fixture-row-meta dense-fixture-meta">{fixture.fixture_type}</span>
                        ) : null}
                      </span>
                      {!fixture.name ? (
                        <span className="dense-fixture-actions">
                          <span className="fixture-row-meta">{`${fixture.universe}:${fixture.address}`}</span>
                        </span>
                      ) : null}
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
                            aria-label={selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id ? `${fixture.universe}:${fixture.address}` : undefined}
                            onMouseDown={(event) => {
                              if (event.shiftKey || event.metaKey || event.ctrlKey) {
                                event.preventDefault();
                              }
                            }}
                            onClick={(event) => {
                              if (selectedFixtureIds.length === 1 && selectedFixtureId === fixture.id) {
                                setAddressModalOpen(true);
                                return;
                              }
                              handleFixtureListRowClick(fixture, event);
                            }}
                          >
                            <span className="dense-fixture-main">
                              <span className="dense-fixture-name">{fixture.name || fixture.fixture_type}</span>
                              {fixture.name ? (
                                <span className="fixture-row-meta dense-fixture-meta">{fixture.fixture_type}</span>
                              ) : null}
                            </span>
                            {!fixture.name ? (
                              <span className="dense-fixture-actions">
                                <span className="fixture-row-meta">{`${fixture.universe}:${fixture.address}`}</span>
                              </span>
                            ) : null}
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
            </>
          )}
        </aside>

        <main className={`dense-viewport-shell${currentView === 'perspective' ? ' dense-viewport-shell-3d' : ''}`}>
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
                    className={`floating-bottom-bar-palette-swatch${i === 0 && selectedThemeAlwaysRainbow ? ' rainbow-hue-tile' : ''}`}
                    style={i === 0 && selectedThemeAlwaysRainbow ? undefined : { background: rgbTripleToCss(rgb) }}
                  />
                ))}
              </span>
            </button>
          </div>
        </main>

        {selectionInspectorVisible ? (
          <aside className="dense-sidebar dense-sidebar-right" aria-label="Selection properties">
            <div className="panel dense-header-panel dense-selection-header-panel">
              <div className="dense-selection-title-row">
                <h2 className="dense-selection-title">{selectionSidebarTitle}</h2>
                <div className="dense-selection-header-actions">
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
                  {selectedKind === 'fixture' && selectedFixtureIds.length === 1 && selectedFixture ? (
                    <>
                      <button
                        type="button"
                        className="small-button secondary-button"
                        onClick={() => void handleCloneFixture(selectedFixture)}
                      >
                        Clone
                      </button>
                      <button
                        type="button"
                        className="small-button danger-button"
                        onClick={() => void handleRemoveFixture()}
                      >
                        Delete
                      </button>
                    </>
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
              {selectedKind === 'fixture' && selectedFixtureIds.length === 1 && selectedFixture ? (
                <label className="dense-selection-name-field">
                  <span className="dense-selection-field-label">Name</span>
                  <DenseFixtureNameInput
                    fixture={selectedFixture}
                    onCommit={async (nextName) => {
                      const snap = await apiPatchFixture(venueSnapshot.summary.id, selectedFixture.id, {
                        name: nextName,
                      });
                      setVenueSnapshot(snap);
                    }}
                  />
                </label>
              ) : null}
            </div>

            {selectedKind === 'fixture' && selectedFixtureIds.length === 1 && selectedFixture ? (
              <div className="panel dense-panel dense-selection-dmx-panel">
                <div className="dense-section-header">
                  <h3>DMX patch</h3>
                </div>
                <p className="dense-selection-dmx-line">
                  {selectedFixture.fixture_type}
                  {' · '}
                  {`${selectedFixture.universe}:${selectedFixture.address}`}
                  {' · '}
                  {`${dmxAddressWidthForFixture(selectedFixture, fixtureTypes)} ch`}
                </p>
                <div className="dense-selection-fixture-actions">
                  <button
                    type="button"
                    className="small-button link-button"
                    onClick={() => setAddressModalOpen(true)}
                  >
                    Edit patch
                  </button>
                </div>
              </div>
            ) : null}

            <div className="panel dense-panel">
              <div className="dense-section-header">
                <h3>Rotation</h3>
              </div>
              {['x', 'y', 'z'].map((axis) => {
                const radians =
                  selectedKind === 'fixture'
                    ? selectedFixture?.[`rotation_${axis}`] || 0
                    : selectedSceneObject?.[`rotation_${axis}`] || 0;
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

            {selectedKind === 'fixture' &&
            selectedFixtureIds.length === 1 &&
            selectedFixture &&
            isMovingHeadFixtureType(selectedFixture.fixture_type) ? (
              <NamedPositionsPanel
                fixture={selectedFixture}
                namedPositions={venueSnapshot?.named_positions || []}
                assignments={selectedFixtureNamedPositions}
                activeEdit={activeNamedPositionEdit}
                onStartEdit={handleStartNamedPositionEdit}
                onStopEdit={handleStopNamedPositionEdit}
                onAddAssignment={handleAddFixtureNamedPosition}
                onCreateAndAddAssignment={handleCreateAndAddFixtureNamedPosition}
                onUpdateAssignment={handleUpdateFixtureNamedPosition}
                onDeleteAssignment={handleDeleteFixtureNamedPosition}
              />
            ) : null}
          </aside>
        ) : null}
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

function patchListHref(venueId) {
  const params = new URLSearchParams(window.location.search);
  if (venueId) {
    params.set('venue_id', venueId);
  }
  const query = params.toString();
  return query ? `/patch?${query}` : '/patch';
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
