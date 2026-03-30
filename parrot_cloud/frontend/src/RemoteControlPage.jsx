import { useEffect, useMemo, useState } from 'react';

export default function RemoteControlPage() {
  const [config, setConfig] = useState({
    available_modes: [],
    available_vj_modes: [],
    effects: [],
  });
  const [controlState, setControlState] = useState({
    mode: 'chill',
    vj_mode: 'full_rave',
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
          <h2>Lighting Mode</h2>
          <div className="button-grid">
            {config.available_modes.map((mode) => (
              <button
                key={mode}
                className={controlState.mode === mode ? 'active-choice' : ''}
                onClick={() => postJson('/api/mode', { mode })}
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
                onClick={() => postJson('/api/vj_mode', { vj_mode: mode })}
              >
                {labelize(mode)}
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

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
