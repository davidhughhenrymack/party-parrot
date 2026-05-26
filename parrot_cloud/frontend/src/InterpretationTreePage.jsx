import { useEffect, useState } from 'react';

const DEFAULT_INTERPRETATION_COLOR_PALETTE = [
  [0.18, 0.22, 0.3],
  [0.32, 0.38, 0.46],
  [0.48, 0.52, 0.58],
];

export default function InterpretationTreePage() {
  const [payload, setPayload] = useState(null);
  const [liveColorPalette, setLiveColorPalette] = useState(null);
  const [config, setConfig] = useState({ theme_color_examples: [] });
  const [controlState, setControlState] = useState({ theme_name: '' });
  const [error, setError] = useState('');

  useEffect(() => {
    let disposed = false;
    let reconnectTimer = null;
    let ws = null;

    async function initialize() {
      const [next, bootstrap, nextConfig] = await Promise.all([
        fetchJson('/api/runtime/interpretation-tree'),
        fetchJson('/api/runtime/bootstrap'),
        fetchJson('/api/config'),
      ]);
      if (disposed) {
        return;
      }
      setPayload(next);
      setConfig({ theme_color_examples: nextConfig.theme_color_examples || [] });
      setControlState(bootstrap.control_state || { theme_name: '' });
      setLiveColorPalette(readColorPaletteFromFixturePayload(bootstrap.fixture_runtime_state));
      connectWebSocket();
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'interpretation_tree') {
          setPayload(message.data);
        } else if (message.type === 'fixture_runtime_state') {
          setLiveColorPalette(readColorPaletteFromFixturePayload(message.data));
        } else if (message.type === 'bootstrap') {
          setControlState(message.data?.control_state || { theme_name: '' });
          setLiveColorPalette(readColorPaletteFromFixturePayload(message.data?.fixture_runtime_state));
        } else if (message.type === 'control_state') {
          setControlState(message.data || { theme_name: '' });
        }
      };
      ws.onclose = () => {
        reconnectTimer = window.setTimeout(connectWebSocket, 1000);
      };
    }

    initialize().catch((err) => {
      console.error('Failed to load interpretation tree:', err);
      if (!disposed) {
        setError(err.message || String(err));
      }
    });

    return () => {
      disposed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, []);

  const colorPalette = liveColorPalette ?? DEFAULT_INTERPRETATION_COLOR_PALETTE;
  const themeExampleByName = new Map(
    (config.theme_color_examples || []).map((example) => [example.name, example]),
  );
  const selectedThemeExample = themeExampleByName.get(controlState.theme_name);
  const selectedThemeAlwaysRainbow = selectedThemeExample?.always_rainbow === true;

  return (
    <main className="interpretation-page-shell">
      <header className="interpretation-page-header">
        <h1>Lighting Interpretation</h1>
      </header>
      <section className="interpretation-panel">
        <div
          className={`interpretation-color-scheme${selectedThemeAlwaysRainbow ? ' rainbow-gradient-bg' : ''}`}
          style={{ '--interpretation-color-scheme-gradient': paletteToGradient(colorPalette) }}
        >
          <span className="interpretation-color-scheme-label">Current color scheme</span>
          <span className="interpretation-color-scheme-swatches" aria-hidden="true">
            {colorPalette.map((rgb, index) => (
              <span
                key={index}
                className={`interpretation-color-scheme-swatch${index === 0 && selectedThemeAlwaysRainbow ? ' rainbow-hue-tile' : ''}`}
                style={index === 0 && selectedThemeAlwaysRainbow ? undefined : { background: rgbTripleToCss(rgb) }}
              />
            ))}
          </span>
        </div>
        {error ? <p className="interpretation-error">{error}</p> : null}
        {payload?.tree ? (
          <ul className="interpretation-tree">
            <InterpretationNode node={payload.tree} />
          </ul>
        ) : (
          <p className="interpretation-empty">No interpretation has been published yet.</p>
        )}
      </section>
    </main>
  );
}

function InterpretationNode({ node }) {
  const children = Array.isArray(node.children) ? node.children : [];
  return (
    <li className={`interpretation-node interpretation-node-${node.kind || 'unknown'}`}>
      <div className="interpretation-node-card">
        <span className="interpretation-node-kind">{node.kind || 'node'}</span>
        <span className="interpretation-node-label">{node.label || '(unnamed)'}</span>
        {node.fixture_label ? (
          <span className="interpretation-node-fixtures">{node.fixture_label}</span>
        ) : null}
      </div>
      {children.length > 0 ? (
        <ul>
          {children.map((child, index) => (
            <InterpretationNode key={`${child.kind || 'node'}-${child.label || index}-${index}`} node={child} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function readColorPaletteFromFixturePayload(data) {
  const palette = data?.color_palette;
  if (!Array.isArray(palette) || palette.length !== 3) {
    return null;
  }
  const out = [];
  for (const slot of palette) {
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
  const colors = (palette || DEFAULT_INTERPRETATION_COLOR_PALETTE).map(rgbTripleToCss);
  return `linear-gradient(135deg, ${colors.join(', ')})`;
}
