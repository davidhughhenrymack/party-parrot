import { useEffect, useMemo, useState } from 'react';

export default function PatchListPage() {
  const [fixtureTypes, setFixtureTypes] = useState([]);
  const [venueSnapshot, setVenueSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const venueId = new URLSearchParams(window.location.search).get('venue_id');

  useEffect(() => {
    let disposed = false;
    let reconnectTimer = null;
    let ws = null;

    async function initialize() {
      setLoading(true);
      setError('');
      const [config, bootstrap] = await Promise.all([
        fetchJson('/api/config'),
        fetchJson('/api/bootstrap'),
      ]);
      if (disposed) {
        return;
      }
      setFixtureTypes(config.fixture_types || []);
      await loadInitialVenue(bootstrap);
      connectWebSocket();
      if (!disposed) {
        setLoading(false);
      }
    }

    async function loadInitialVenue(bootstrap) {
      if (venueId) {
        setVenueSnapshot(await fetchJson(`/api/venues/${encodeURIComponent(venueId)}`));
        return;
      }
      setVenueSnapshot(bootstrap.active_venue || null);
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type !== 'venue_snapshot') {
          return;
        }
        const snapshot = payload.data;
        if (!snapshot?.summary?.id) {
          return;
        }
        setVenueSnapshot((current) => {
          const targetId = venueId || current?.summary?.id;
          return snapshot.summary.id === targetId ? snapshot : current;
        });
      };
      ws.onclose = () => {
        reconnectTimer = window.setTimeout(connectWebSocket, 1000);
      };
    }

    initialize().catch((err) => {
      console.error('Failed to initialize patch list:', err);
      if (!disposed) {
        setError(err.message || String(err));
        setLoading(false);
      }
    });

    return () => {
      disposed = true;
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, [venueId]);

  const rows = useMemo(() => {
    const fixtures = venueSnapshot?.fixtures || [];
    return [...fixtures].sort(compareFixturesForPatchList).map((fixture) => ({
      fixture,
      width: dmxAddressWidthForFixture(fixture, fixtureTypes),
      fixtureType: fixtureTypeLabel(fixture.fixture_type, fixtureTypes),
      panMode: angleModeLabel(fixture.fixture_type, fixtureTypes, 'pan'),
      tiltMode: angleModeLabel(fixture.fixture_type, fixtureTypes, 'tilt'),
    }));
  }, [fixtureTypes, venueSnapshot]);

  const editorHref = venueSnapshot
    ? withCurrentSearch(`/venues/${venueSnapshot.summary.id}`)
    : withCurrentSearch('/venues');

  return (
    <main className="page-shell patch-page-shell">
      <div className="page-header">
        <div>
          <h1>Patch List</h1>
          <p className="panel-copy">
            {venueSnapshot ? venueSnapshot.summary.name : 'Active venue fixture addressing'}
          </p>
        </div>
        <div className="button-row compact-row">
          <button className="secondary-button" onClick={() => window.location.assign(editorHref)}>
            Venue Editor
          </button>
          <button className="secondary-button" onClick={() => window.location.assign(withCurrentSearch('/remote'))}>
            Remote Control
          </button>
        </div>
      </div>

      <section className="panel patch-list-panel">
        {loading ? <p className="panel-copy">Loading patch list...</p> : null}
        {error ? <p className="patch-list-error">{error}</p> : null}
        {!loading && !error && !venueSnapshot ? (
          <p className="panel-copy">No active venue is available.</p>
        ) : null}
        {!loading && !error && venueSnapshot && rows.length === 0 ? (
          <p className="panel-copy">No fixtures are patched in this venue.</p>
        ) : null}
        {!loading && !error && rows.length > 0 ? (
          <div className="patch-list-table-wrap">
            <table className="patch-list-table">
              <thead>
                <tr>
                  <th>Universe</th>
                  <th>Address</th>
                  <th>Width</th>
                  <th>Fixture Type</th>
                  <th>Fixture Name</th>
                  <th>Group</th>
                  <th>Pan Angle Mode</th>
                  <th>Tilt Angle Mode</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ fixture, width, fixtureType, panMode, tiltMode }) => (
                  <tr key={fixture.id}>
                    <td>{fixture.universe || 'default'}</td>
                    <td>{fixture.address}</td>
                    <td>{width}</td>
                    <td>{fixtureType}</td>
                    <td>{fixture.name || '-'}</td>
                    <td>{fixture.group_name || '-'}</td>
                    <td>{panMode}</td>
                    <td>{tiltMode}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}

function compareFixturesForPatchList(a, b) {
  const universe = String(a.universe || '').localeCompare(String(b.universe || ''));
  if (universe !== 0) {
    return universe;
  }
  return Number(a.address || 0) - Number(b.address || 0);
}

function dmxAddressWidthForFixture(fixture, fixtureTypes) {
  if (fixture.fixture_type === 'manual_dimmer_channel') {
    const w = fixture.options?.width;
    return Math.max(1, Math.floor(Number(w) || 1));
  }
  const def = fixtureTypes.find((t) => t.key === fixture.fixture_type);
  return Math.max(1, Math.floor(Number(def?.dmx_address_width) || 1));
}

function fixtureTypeLabel(fixtureType, fixtureTypes) {
  return fixtureTypes.find((t) => t.key === fixtureType)?.label || fixtureType || '-';
}

function angleModeLabel(fixtureType, fixtureTypes, axis) {
  const def = fixtureTypes.find((t) => t.key === fixtureType);
  const degrees = def?.[`${axis}_angle_mode_degrees`];
  if (degrees === undefined || degrees === null) {
    return '-';
  }
  return `${degrees}deg`;
}

function withCurrentSearch(pathname) {
  return `${pathname}${window.location.search}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
