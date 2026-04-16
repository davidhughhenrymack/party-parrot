import { useEffect, useMemo, useState } from 'react';

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
    manual_dimmer: 0,
  });
  const [manualDimmerSupported, setManualDimmerSupported] = useState(false);

  const manualDimmerPercent = useMemo(
    () => Math.round((controlState.manual_dimmer || 0) * 100),
    [controlState.manual_dimmer],
  );

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
          setControlState((current) => ({
            ...current,
            ...payload.data,
          }));
        } else if (payload.type === 'venues') {
          setVenues(payload.data?.venues || []);
        } else if (payload.type === 'venue_snapshot' && payload.data?.summary?.active) {
          setManualDimmerSupported(
            Boolean(payload.data?.fixtures?.some((fixture) => fixture.is_manual)),
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
        active_venue_id:
          bootstrap.control_state?.active_venue_id ||
          bootstrap.active_venue?.summary?.id ||
          null,
      }));
      setManualDimmerSupported(
        Boolean(bootstrap.active_venue?.fixtures?.some((fixture) => fixture.is_manual)),
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

  return (
    <div className="page-shell">
      <div className="page-header">
        <div>
          <h1>Remote Control</h1>
          <p className="panel-copy">Live controls are now served from Parrot Cloud and synced to the runtime over websocket.</p>
        </div>
        <div className="button-row compact-row">
          <button className="secondary-button" onClick={() => window.location.assign('/')}>Home</button>
          <button className="secondary-button" onClick={() => window.location.assign('/editor')}>Open Venue Editor</button>
        </div>
      </div>

      <div className="remote-grid">
        <section className="panel">
          <h2>Venue</h2>
          <div className="button-grid">
            {venues.map((venue) => (
              <button
                key={venue.id}
                className={controlState.active_venue_id === venue.id ? 'active-choice' : ''}
                onClick={() => patchControlState({ active_venue_id: venue.id })}
              >
                {venue.name}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Lighting Mode</h2>
          <div className="button-grid">
            {config.available_modes.map((mode) => (
              <button
                key={mode}
                className={controlState.mode === mode ? 'active-choice' : ''}
                onClick={() => patchControlState({ mode })}
              >
                {labelize(mode)}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>VJ Mode</h2>
          <div className="button-grid">
            {config.available_vj_modes.map((mode) => (
              <button
                key={mode}
                className={controlState.vj_mode === mode ? 'active-choice' : ''}
                onClick={() => patchControlState({ vj_mode: mode })}
              >
                {formatVjModeLabel(mode)}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Color Scheme</h2>
          <div className="button-grid">
            {config.theme_names.map((themeName) => (
              <button
                key={themeName}
                className={controlState.theme_name === themeName ? 'active-choice' : ''}
                onClick={() => patchControlState({ theme_name: themeName })}
              >
                {themeName}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Display</h2>
          <div className="button-grid">
            {config.available_display_modes.map((displayMode) => (
              <button
                key={displayMode}
                className={controlState.display_mode === displayMode ? 'active-choice' : ''}
                onClick={() => patchControlState({ display_mode: displayMode })}
              >
                {formatDisplayModeLabel(displayMode)}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Effects</h2>
          <div className="button-grid">
            {config.effects.map((effect) => (
              <button key={effect} onClick={() => postJson('/api/effect', { effect })}>
                {labelize(effect)}
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2>Manual Dimmer</h2>
          <p className="panel-copy">
            {manualDimmerSupported ? 'Available for the current active venue.' : 'The current active venue has no manual dimmer fixtures.'}
          </p>
          <input
            type="range"
            min="0"
            max="100"
            value={manualDimmerPercent}
            disabled={!manualDimmerSupported}
            onChange={(event) =>
              setControlState((current) => ({
                ...current,
                manual_dimmer: Number(event.target.value) / 100,
              }))
            }
            onMouseUp={(event) => postJson('/api/manual_dimmer', { value: Number(event.target.value) / 100 })}
            onTouchEnd={(event) => {
              const value = Number(event.target.value) / 100;
              postJson('/api/manual_dimmer', { value });
            }}
          />
          <div className="remote-stat">{manualDimmerPercent}%</div>
        </section>
      </div>
    </div>
  );
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
    return `Zombie Rave · ${rest}`;
  }
  return labelize(mode);
}

function formatDisplayModeLabel(displayMode) {
  if (displayMode === 'dmx_heatmap') {
    return 'DMX heatmap';
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
