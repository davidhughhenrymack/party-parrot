import { useEffect, useRef, useState } from 'react';

export default function RemoteControlPage() {
  const [config, setConfig] = useState({
    available_modes: [],
    available_vj_modes: [],
    available_display_modes: [],
    theme_names: [],
    effects: [],
  });
  const [venues, setVenues] = useState([]);
  const [controlState, setControlState] = useState({
    mode: 'chill',
    vj_mode: 'prom_dmack',
    theme_name: 'Rave',
    display_mode: 'dmx_heatmap',
    active_venue_id: null,
    manual_fixture_dimmers: {},
    hype_limiter: false,
    show_waveform: true,
  });
  const [manualFixtures, setManualFixtures] = useState([]);
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
        effects: nextConfig.effects || [],
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
        } else if (payload.type === 'venues') {
          setVenues(payload.data?.venues || []);
        } else if (payload.type === 'venue_snapshot' && payload.data?.summary?.active) {
          const fixtures = payload.data.fixtures || [];
          setManualFixtures(
            fixtures
              .filter((f) => f.is_manual)
              .map((f) => ({
                id: f.id,
                name: f.name || f.fixture_type || 'Manual',
              })),
          );
        }
      };
      ws.onclose = () => {
        reconnectTimer = window.setTimeout(connectWebSocket, 1000);
      };
    }

    function applyBootstrap(bootstrap) {
      setVenues(bootstrap.venues || []);
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
      setManualFixtures(
        fixtures
          .filter((f) => f.is_manual)
          .map((f) => ({
            id: f.id,
            name: f.name || f.fixture_type || 'Manual',
          })),
      );
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

  const mfd = controlState.manual_fixture_dimmers || {};

  return (
    <div className="remote-shell">
      <header className="remote-topbar">
        <h1>Remote</h1>
        <div className="remote-topbar-actions">
          <button className="secondary-button chip" onClick={() => window.location.assign('/')}>Home</button>
          <button className="secondary-button chip" onClick={() => window.location.assign('/editor')}>Editor</button>
        </div>
      </header>

      <section className="remote-hero-panel">
        <h2 className="remote-hero-title">Manual lights</h2>
        {manualDimmerSupported ? (
          manualFixtures.map((fixture) => (
            <div key={fixture.id} className="remote-fader-row">
              <div className="remote-fader-labels">
                <label className="remote-fader-name" htmlFor={`manual-dim-${fixture.id}`}>
                  {fixture.name}
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

      <section className="remote-hero-panel">
        <h2 className="remote-hero-title">Effects</h2>
        {config.effects.length > 0 ? (
          <div className="remote-effects-grid">
            {config.effects.map((effect) => (
              <button
                key={effect}
                className="remote-effect-button"
                onClick={() => postJson('/api/effect', { effect })}
              >
                {labelize(effect)}
              </button>
            ))}
          </div>
        ) : (
          <p className="remote-hero-empty">No effects configured.</p>
        )}
      </section>

      <CompactSelector
        label="Lighting"
        options={config.available_modes}
        value={controlState.mode}
        format={labelize}
        onSelect={(mode) => patchControlState({ mode })}
      />
      <CompactSelector
        label="VJ"
        options={config.available_vj_modes}
        value={controlState.vj_mode}
        format={formatVjModeLabel}
        onSelect={(vj_mode) => patchControlState({ vj_mode })}
      />
      <CompactSelector
        label="Color"
        options={config.theme_names}
        value={controlState.theme_name}
        format={(v) => v}
        onSelect={(theme_name) => patchControlState({ theme_name })}
      />
      <CompactSelector
        label="Display"
        options={config.available_display_modes}
        value={controlState.display_mode}
        format={formatDisplayModeLabel}
        onSelect={(display_mode) => patchControlState({ display_mode })}
      />
      <CompactSelector
        label="Venue"
        options={venues.map((v) => v.id)}
        value={controlState.active_venue_id}
        format={(id) => venues.find((v) => v.id === id)?.name || id}
        onSelect={(active_venue_id) => patchControlState({ active_venue_id })}
      />
    </div>
  );
}

function CompactSelector({ label, options, value, format, onSelect }) {
  if (!options || options.length === 0) {
    return null;
  }
  return (
    <section className="remote-compact-row">
      <div className="remote-compact-label">{label}</div>
      <div className="remote-chip-row">
        {options.map((option) => (
          <button
            key={option}
            className={`chip ${value === option ? 'chip-active' : ''}`}
            onClick={() => onSelect(option)}
          >
            {format(option)}
          </button>
        ))}
      </div>
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

function formatVjModeLabel(mode) {
  if (mode === 'blackout') {
    return 'Blackout';
  }
  if (mode === 'prom_dmack') {
    return 'Prom · dmack';
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

function formatDisplayModeLabel(displayMode) {
  if (displayMode === 'dmx_heatmap') {
    return 'Heatmap';
  }
  return labelize(displayMode);
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
