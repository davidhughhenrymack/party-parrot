import { useEffect, useRef, useState } from 'react';

const LIGHTING_EFFECT_HOTKEYS = Object.freeze({
  g: 'strobe',
  j: 'big_blinder',
});

export default function RemoteControlPage() {
  const [config, setConfig] = useState({
    available_modes: [],
    available_vj_modes: [],
    available_display_modes: [],
    theme_names: [],
    theme_color_examples: [],
    effects: [],
    shift_targets: [],
    lighting_modes: [],
  });
  const [controlState, setControlState] = useState({
    mode: 'chill',
    vj_mode: 'prom_dmack',
    theme_name: 'Rave',
    display_mode: 'dmx_heatmap',
    active_venue_id: null,
    manual_fixture_dimmers: {},
    show_waveform: true,
  });
  const [manualFixtures, setManualFixtures] = useState([]);
  /** Live fg/bg/bg_contrast from desktop `fixture_runtime_state.color_palette`. */
  const [liveColorPalette, setLiveColorPalette] = useState(null);
  const draggingFixtureIdRef = useRef(null);

  const manualDimmerSupported = manualFixtures.length > 0;

  useEffect(() => {
    let disposed = false;
    let reconnectTimer = null;
    let ws = null;

    async function initialize() {
      const [nextConfig, bootstrap] = await Promise.all([
        fetchJson('/api/config'),
        fetchJson('/api/bootstrap'),
      ]);
      if (disposed) {
        return;
      }
      setConfig({
        available_modes: nextConfig.available_modes || [],
        available_vj_modes: nextConfig.available_vj_modes || [],
        available_display_modes: nextConfig.available_display_modes || [],
        theme_names: nextConfig.theme_names || [],
        theme_color_examples: nextConfig.theme_color_examples || [],
        effects: nextConfig.effects || [],
        shift_targets: nextConfig.shift_targets || [],
        lighting_modes: [],
      });
      applyBootstrap(bootstrap);
      connectWebSocket();
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === 'bootstrap') {
          applyBootstrap(payload.data);
        } else if (payload.type === 'control_state') {
          setControlState((current) => {
            const incoming = payload.data || {};
            if (draggingFixtureIdRef.current) {
              return {
                ...current,
                ...incoming,
                manual_fixture_dimmers: current.manual_fixture_dimmers,
              };
            }
            return {
              ...current,
              ...incoming,
              manual_fixture_dimmers:
                incoming.manual_fixture_dimmers !== undefined
                  ? { ...incoming.manual_fixture_dimmers }
                  : current.manual_fixture_dimmers,
            };
          });
        } else if (payload.type === 'fixture_runtime_state') {
          const pal = readColorPaletteFromFixturePayload(payload.data);
          setLiveColorPalette(pal);
        } else if (payload.type === 'venue_snapshot' && payload.data?.summary?.active) {
          const fixtures = payload.data.fixtures || [];
          setConfig((current) => ({
            ...current,
            available_modes: [
              ...current.available_modes.filter((mode) => mode === 'blackout'),
              ...(payload.data.lighting_modes || []).map((mode) => mode.key),
            ],
            lighting_modes: payload.data.lighting_modes || [],
          }));
          setManualFixtures(
            fixtures
              .filter((f) => f.is_manual)
              .map((f) => ({
                id: f.id,
                displayLabel:
                  typeof f.name === 'string' && f.name.trim() !== ''
                    ? f.name.trim()
                    : (f.fixture_type || 'Manual'),
              })),
          );
        }
      };
      ws.onclose = () => {
        reconnectTimer = window.setTimeout(connectWebSocket, 1000);
      };
    }

    function applyBootstrap(bootstrap) {
      setControlState((current) => ({
        ...current,
        ...bootstrap.control_state,
        manual_fixture_dimmers: bootstrap.control_state?.manual_fixture_dimmers || {},
        active_venue_id:
          bootstrap.control_state?.active_venue_id ||
          bootstrap.active_venue?.summary?.id ||
          null,
      }));
      const fixtures = bootstrap.active_venue?.fixtures || [];
      setConfig((current) => ({
        ...current,
        available_modes: [
          ...current.available_modes.filter((mode) => mode === 'blackout'),
          ...(bootstrap.active_venue?.lighting_modes || []).map((mode) => mode.key),
        ],
        lighting_modes: bootstrap.active_venue?.lighting_modes || [],
      }));
      setManualFixtures(
        fixtures
          .filter((f) => f.is_manual)
          .map((f) => ({
            id: f.id,
            displayLabel:
              typeof f.name === 'string' && f.name.trim() !== ''
                ? f.name.trim()
                : (f.fixture_type || 'Manual'),
          })),
      );
      {
        const pal = readColorPaletteFromFixturePayload(bootstrap.fixture_runtime_state);
        setLiveColorPalette(pal);
      }
    }

    initialize().catch((error) => {
      console.error('Failed to initialize remote control:', error);
    });

    return () => {
      disposed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, []);

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
        void postJson('/api/effect', { effect });
        return;
      }
      const mode = (config.lighting_modes || []).find((candidate) => candidate.hotkey === key);
      if (!mode || mode.key === controlState.mode) {
        return;
      }
      event.preventDefault();
      void patchControlState({ mode: mode.key });
    }
    window.addEventListener('keydown', onLightingModeHotkey);
    return () => window.removeEventListener('keydown', onLightingModeHotkey);
  }, [config.lighting_modes, controlState.mode]);

  const mfd = controlState.manual_fixture_dimmers || {};
  const visibleEffects = config.effects.filter((effect) => !REMOTE_HIDDEN_EFFECTS.has(effect));
  const secondaryShiftTargets = config.shift_targets.filter(
    (target) => !['lighting_only', 'color_scheme', 'vj_only'].includes(target),
  );
  const canShiftLighting = config.shift_targets.includes('lighting_only');
  const canShiftColors = config.shift_targets.includes('color_scheme');
  const canShiftVj = config.shift_targets.includes('vj_only');
  const themeExampleByName = new Map(
    (config.theme_color_examples || []).map((example) => [example.name, example]),
  );
  const selectedThemeExample = themeExampleByName.get(controlState.theme_name);
  const selectedThemeAlwaysRainbow = selectedThemeExample?.always_rainbow === true;

  return (
    <div className="remote-shell">
      <CompactSelector
        options={orderRemoteLightingModes(config.available_modes)}
        value={controlState.mode}
        format={labelize}
        onSelect={(mode) => patchControlState({ mode })}
        variant="primary-mode"
      >
        {canShiftLighting ? (
          <button
            type="button"
            className="remote-lighting-shift-button"
            onClick={() => postJson('/api/shift', { target: 'lighting_only' })}
          >
            {formatShiftLabel('lighting_only')}
          </button>
        ) : null}
      </CompactSelector>

      <section className="remote-hero-panel">
        <h2 className="remote-hero-title">Effects</h2>
        {visibleEffects.length > 0 ? (
          <div className="remote-effects-grid">
            {visibleEffects.map((effect) => (
              <RemoteEffectButton key={effect} effect={effect} label={labelize(effect)} />
            ))}
          </div>
        ) : (
          <p className="remote-hero-empty">No effects configured.</p>
        )}
      </section>

      <section className="remote-hero-panel">
        {manualDimmerSupported ? (
          manualFixtures.map((fixture) => (
            <div key={fixture.id} className="remote-fader-row">
              <div className="remote-fader-labels">
                <label className="remote-fader-name" htmlFor={`manual-dim-${fixture.id}`}>
                  {fixture.displayLabel}
                </label>
                <div className="remote-fader-value">
                  {manualDimmerPercentFor(mfd, fixture.id)}%
                </div>
              </div>
              <input
                id={`manual-dim-${fixture.id}`}
                className="remote-fader"
                type="range"
                min="0"
                max="100"
                value={manualDimmerPercentFor(mfd, fixture.id)}
                onPointerDown={() => {
                  draggingFixtureIdRef.current = fixture.id;
                }}
                onPointerUp={() => {
                  draggingFixtureIdRef.current = null;
                }}
                onPointerCancel={() => {
                  draggingFixtureIdRef.current = null;
                }}
                onInput={(event) => {
                  const value01 = Number(event.target.value) / 100;
                  setControlState((current) => ({
                    ...current,
                    manual_fixture_dimmers: {
                      ...(current.manual_fixture_dimmers || {}),
                      [fixture.id]: value01,
                    },
                  }));
                  void patchControlState({
                    manual_fixture_dimmers: { [fixture.id]: value01 },
                  }).then((next) => {
                    setControlState((current) => ({
                      ...current,
                      ...next,
                      manual_fixture_dimmers:
                        next.manual_fixture_dimmers || current.manual_fixture_dimmers,
                    }));
                  });
                }}
              />
            </div>
          ))
        ) : (
          <p className="remote-hero-empty">The active venue has no manual fixtures.</p>
        )}
      </section>

      {secondaryShiftTargets.length > 0 && (
        <section className="remote-hero-panel remote-shift-panel">
          <h2 className="remote-hero-title">Shift</h2>
          <div className="remote-effects-grid remote-shift-grid">
            {secondaryShiftTargets.map((target) => (
              <button
                key={target}
                type="button"
                className={`remote-effect-button remote-shift-button${
                  target === 'color_scheme' ? ' remote-shift-colors' : ''
                }`}
                aria-label={formatShiftLabel(target)}
                onClick={() => postJson('/api/shift', { target })}
              >
                {target === 'color_scheme' ? (
                  <span className="remote-shift-colors-inner">
                    <span className="remote-shift-swatches" aria-hidden="true">
                      {(liveColorPalette ?? DEFAULT_REMOTE_COLOR_PALETTE).map((rgb, i) => (
                        <span
                          key={i}
                          className="remote-shift-swatch"
                          style={{ background: rgbTripleToCss(rgb) }}
                        />
                      ))}
                    </span>
                    <span className="remote-shift-label">{formatShiftLabel(target)}</span>
                  </span>
                ) : (
                  formatShiftLabel(target)
                )}
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="remote-hero-panel remote-color-panel">
        {canShiftColors ? (
          <button
            type="button"
            className={`remote-color-shift-button${selectedThemeAlwaysRainbow ? ' rainbow-gradient-bg' : ''}`}
            style={{
              '--remote-shift-gradient': paletteToGradient(liveColorPalette ?? DEFAULT_REMOTE_COLOR_PALETTE),
            }}
            onClick={() => postJson('/api/shift', { target: 'color_scheme' })}
          >
            <span className="remote-shift-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M17.7 6.3A7.95 7.95 0 0 0 12 4a8 8 0 0 0-7.75 6h2.1A6 6 0 0 1 16.3 7.7L14 10h6V4l-2.3 2.3Z" />
                <path d="M6.3 17.7A7.95 7.95 0 0 0 12 20a8 8 0 0 0 7.75-6h-2.1A6 6 0 0 1 7.7 16.3L10 14H4v6l2.3-2.3Z" />
              </svg>
            </span>
            <span className="remote-shift-swatches remote-color-shift-swatches" aria-hidden="true">
              {(liveColorPalette ?? DEFAULT_REMOTE_COLOR_PALETTE).map((rgb, i) => (
                <span
                  key={i}
                  className={`remote-shift-swatch${i === 0 && selectedThemeAlwaysRainbow ? ' rainbow-hue-tile' : ''}`}
                  style={i === 0 && selectedThemeAlwaysRainbow ? undefined : { background: rgbTripleToCss(rgb) }}
                />
              ))}
            </span>
            <span>{formatShiftLabel('color_scheme')}</span>
          </button>
        ) : null}
        <div className="remote-color-grid">
          {config.theme_names.map((themeName) => {
            const example = themeExampleByName.get(themeName);
            const palette = example?.palette ?? DEFAULT_REMOTE_COLOR_PALETTE;
            const alwaysRainbow = example?.always_rainbow === true;
            return (
              <button
                key={themeName}
                type="button"
                className={`remote-color-button${controlState.theme_name === themeName ? ' remote-color-button-active' : ''}${alwaysRainbow ? ' rainbow-gradient-bg' : ''}`}
                style={{ '--remote-theme-gradient': paletteToGradient(palette) }}
                onClick={() => patchControlState({ theme_name: themeName })}
              >
                <span className="remote-color-button-label">{themeName}</span>
              </button>
            );
          })}
        </div>
      </section>

      <CompactSelector
        label="VJ"
        options={config.available_vj_modes}
        value={controlState.vj_mode}
        format={formatVjModeLabel}
        onSelect={(vj_mode) => patchControlState({ vj_mode })}
      >
        {canShiftVj ? (
          <button
            type="button"
            className="remote-inline-shift-button"
            onClick={() => postJson('/api/shift', { target: 'vj_only' })}
          >
            {formatShiftLabel('vj_only')}
          </button>
        ) : null}
      </CompactSelector>
    </div>
  );
}

/** Short tap = one-shot effect (~0.35s server-side); hold = signal stays at 1 until release. */
const REMOTE_EFFECT_TAP_MS = 280;
const REMOTE_HIDDEN_EFFECTS = new Set(['rainbow', 'chase']);
const REMOTE_UTILITY_MODES = new Set();
const REMOTE_UTILITY_MODE_ORDER = [];

function orderRemoteLightingModes(modes) {
  const normal = [];
  const utility = [];
  for (const mode of modes || []) {
    if (REMOTE_UTILITY_MODES.has(mode)) {
      utility.push(mode);
    } else {
      normal.push(mode);
    }
  }
  utility.sort(
    (a, b) => REMOTE_UTILITY_MODE_ORDER.indexOf(a) - REMOTE_UTILITY_MODE_ORDER.indexOf(b),
  );
  return [...normal, ...utility];
}

function RemoteEffectButton({ effect, label }) {
  const downAtRef = useRef(0);
  const pressedRef = useRef(false);

  function releaseEffect(event) {
    event.preventDefault();
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    if (!pressedRef.current) {
      return;
    }
    pressedRef.current = false;
    const dt = performance.now() - downAtRef.current;
    if (effect !== 'strobe' && dt < REMOTE_EFFECT_TAP_MS) {
      void postJson('/api/effect', { effect });
      return;
    }
    void postJson('/api/effect', { effect, value: 0 });
  }

  return (
    <button
      type="button"
      className="remote-effect-button"
      onContextMenu={(e) => e.preventDefault()}
      onSelectStart={(e) => e.preventDefault()}
      onPointerDown={(e) => {
        e.preventDefault();
        pressedRef.current = true;
        try {
          e.currentTarget.setPointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
        downAtRef.current = performance.now();
        void postJson('/api/effect', { effect, value: 1 });
      }}
      onPointerUp={releaseEffect}
      onPointerCancel={(e) => {
        e.preventDefault();
        if (e.currentTarget.hasPointerCapture?.(e.pointerId)) {
          e.currentTarget.releasePointerCapture(e.pointerId);
        }
        pressedRef.current = false;
        void postJson('/api/effect', { effect, value: 0 });
      }}
      onBlur={() => {
        if (pressedRef.current) {
          pressedRef.current = false;
          void postJson('/api/effect', { effect, value: 0 });
        }
      }}
    >
      {label}
    </button>
  );
}

function CompactSelector({ label, options, value, format, onSelect, variant = 'compact', children }) {
  if (!options || options.length === 0) {
    return null;
  }
  const primary = variant === 'primary-mode';
  const primaryNormalOptions = primary
    ? options.filter((option) => !REMOTE_UTILITY_MODES.has(option))
    : options;
  const primaryUtilityOptions = primary
    ? options.filter((option) => REMOTE_UTILITY_MODES.has(option))
    : [];
  return (
    <section className={`remote-compact-row${primary ? ' remote-primary-mode-row' : ''}`}>
      {label ? <div className="remote-compact-label">{label}</div> : null}
      <div className={`remote-chip-row${primary ? ' remote-primary-mode-grid' : ''}`}>
        {primaryNormalOptions.map((option) => (
          <button
            key={option}
            className={`${primary ? `remote-mode-button${REMOTE_UTILITY_MODES.has(option) ? ' remote-mode-button-utility' : ''}` : 'chip'} ${value === option ? (primary ? 'remote-mode-button-active' : 'chip-active') : ''}`}
            onClick={() => onSelect(option)}
          >
            {format(option)}
          </button>
        ))}
      </div>
      {primaryUtilityOptions.length > 0 ? (
        <div className="remote-utility-mode-row">
          {primaryUtilityOptions.map((option) => (
            <button
              key={option}
              className={`remote-mode-button remote-mode-button-utility${value === option ? ' remote-mode-button-active' : ''}`}
              onClick={() => onSelect(option)}
            >
              {format(option)}
            </button>
          ))}
        </div>
      ) : null}
      {children}
    </section>
  );
}

function manualDimmerPercentFor(manualFixtureDimmers, fixtureId) {
  const raw = manualFixtureDimmers[fixtureId];
  const v = raw !== undefined && raw !== null ? raw : 0;
  return Math.round(Math.max(0, Math.min(1, v)) * 100);
}

function labelize(value) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (match) => match.toUpperCase());
}

function isEditableKeyboardTarget(target) {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  );
}

function formatVjModeLabel(mode) {
  if (mode === 'blackout') {
    return 'Blackout';
  }
  if (mode.startsWith('prom_')) {
    return `Prom · ${mode.slice('prom_'.length)}`;
  }
  if (mode.startsWith('zr_')) {
    const rest = mode
      .slice(3)
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
    return `ZR · ${rest}`;
  }
  return labelize(mode);
}

const SHIFT_LABELS = {
  lighting_only: 'Shift Lighting',
  color_scheme: 'Shift Colors',
  vj_only: 'Shift VJ',
};

/** Fallback when desktop has not yet pushed `color_palette` on fixture runtime state. */
const DEFAULT_REMOTE_COLOR_PALETTE = [
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

function paletteToGradient(palette) {
  const colors = Array.isArray(palette) && palette.length > 0
    ? palette.map(rgbTripleToCss)
    : DEFAULT_REMOTE_COLOR_PALETTE.map(rgbTripleToCss);
  if (colors.length === 1) {
    return colors[0];
  }
  return `linear-gradient(135deg, ${colors.join(',')})`;
}

function formatShiftLabel(target) {
  return SHIFT_LABELS[target] || `Shift ${labelize(target)}`;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
