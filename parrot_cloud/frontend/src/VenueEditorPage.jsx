import { useEffect, useMemo, useRef, useState } from 'react';
import { createSceneController } from './sceneController.js';

const isTestMode = new URLSearchParams(window.location.search).has('test_mode');

export default function VenueEditorPage({ venueId }) {
  const viewportRef = useRef(null);
  const selectedFixtureAddressRef = useRef(null);
  const sceneControllerRef = useRef(null);
  const wsRef = useRef(null);
  const venueRef = useRef(null);
  const videoWallLockedRef = useRef(false);

  const [venueSummaries, setVenueSummaries] = useState([]);
  const [venueSnapshot, setVenueSnapshot] = useState(null);
  const [fixtureTypes, setFixtureTypes] = useState([]);
  const [supportedUniverses, setSupportedUniverses] = useState([]);
  const [currentView, setCurrentView] = useState('top');
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0 });
  const [selectedKind, setSelectedKind] = useState(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState(null);
  const [floorValues, setFloorValues] = useState({
    width: '',
    depth: '',
    height: '',
  });
  const [videoWallLocked, setVideoWallLocked] = useState(false);
  const [newFixtureValues, setNewFixtureValues] = useState({
    fixtureType: '',
    address: '1',
    universe: 'default',
  });
  const [selectedFixtureValues, setSelectedFixtureValues] = useState({
    address: '',
    universe: 'default',
  });

  const selectedFixture = useMemo(() => {
    if (!venueSnapshot || !selectedFixtureId) {
      return null;
    }
    return venueSnapshot.fixtures.find((fixture) => fixture.id === selectedFixtureId) ?? null;
  }, [venueSnapshot, selectedFixtureId]);

  const selectionSummary = useMemo(() => {
    if (selectedKind === 'video_wall') {
      return 'Video Wall';
    }
    if (selectedFixture) {
      return `${selectedFixture.name || selectedFixture.fixture_type} @ ${selectedFixture.universe}:${selectedFixture.address}`;
    }
    return 'Nothing selected';
  }, [selectedFixture, selectedKind]);

  const venueStats = useMemo(() => {
    if (!venueSnapshot) {
      return 'Loading venue';
    }
    const activeLabel = venueSummaries.find((venue) => venue.id === venueSnapshot.summary.id)?.active ? 'yes' : 'no';
    return `Venue: ${venueSnapshot.summary.name} | Fixtures: ${venueSnapshot.fixtures.length} | Active: ${activeLabel} | Video wall locked: ${venueSnapshot.video_wall.locked ? 'yes' : 'no'}`;
  }, [venueSnapshot, venueSummaries]);

  useEffect(() => {
    document.body.dataset.testMode = isTestMode ? 'true' : 'false';

    let disposed = false;

    async function initialize() {
      sceneControllerRef.current = await createSceneController({
        viewportEl: viewportRef.current,
        isTestMode,
        onSelectionChange: handleSelectionChange,
        onFixtureContextMenu: ({ fixture, x, y }) => {
          setSelectedKind('fixture');
          setSelectedFixtureId(fixture.id);
          setContextMenu({ visible: true, x, y });
        },
        onFixtureTransform: async (payload) => {
          if (!venueRef.current) {
            return;
          }
          await apiPatchFixture(venueRef.current.summary.id, payload.fixtureId, {
            x: payload.x,
            y: payload.y,
            z: payload.z,
            rotation_x: payload.rotation_x,
            rotation_y: payload.rotation_y,
            rotation_z: payload.rotation_z,
          });
        },
        onVideoWallTransform: async (payload) => {
          if (!venueRef.current) {
            return;
          }
          await apiPatchVideoWall(venueRef.current.summary.id, {
            x: payload.x,
            y: payload.y,
            z: payload.z,
            width: venueRef.current.video_wall.width,
            height: venueRef.current.video_wall.height,
            depth: venueRef.current.video_wall.depth,
            locked: videoWallLockedRef.current,
          });
        },
      });

      const config = await fetchJson('/api/config');
      if (disposed) {
        return;
      }
      setFixtureTypes(config.fixture_types);
      setSupportedUniverses(config.supported_universes);
      setNewFixtureValues((current) => ({
        ...current,
        fixtureType: config.fixture_types[0]?.key || '',
        universe: config.supported_universes[0]?.value || 'default',
      }));
      setSelectedFixtureValues((current) => ({
        ...current,
        universe: config.supported_universes[0]?.value || 'default',
      }));

      const nextBootstrap = await fetchJson('/api/bootstrap');
      if (disposed) {
        return;
      }
      applyBootstrap(nextBootstrap);
      await loadVenueSnapshot(venueId);
      connectWebSocket();
      document.body.dataset.appReady = 'true';
    }

    initialize().catch((error) => {
      console.error('Failed to initialize venue editor:', error);
      document.body.dataset.appReady = 'false';
    });

    const handleWindowClick = () => setContextMenu((current) => ({ ...current, visible: false }));
    window.addEventListener('click', handleWindowClick);

    return () => {
      disposed = true;
      window.removeEventListener('click', handleWindowClick);
      wsRef.current?.close();
      sceneControllerRef.current?.destroy();
    };
  }, [venueId]);

  useEffect(() => {
    venueRef.current = venueSnapshot;
    if (!venueSnapshot) {
      setFloorValues({ width: '', depth: '', height: '' });
      setVideoWallLocked(false);
      return;
    }
    setFloorValues({
      width: String(venueSnapshot.floor_width),
      depth: String(venueSnapshot.floor_depth),
      height: String(venueSnapshot.floor_height),
    });
    setVideoWallLocked(venueSnapshot.video_wall.locked);
    sceneControllerRef.current?.applyBootstrap(venueSnapshot);
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

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'bootstrap') {
        applyBootstrap(payload.data);
        void loadVenueSnapshot(venueId);
      }
    };
    ws.onclose = () => {
      setTimeout(connectWebSocket, 1000);
    };
    wsRef.current = ws;
  }

  function applyBootstrap(nextBootstrap) {
    setVenueSummaries(nextBootstrap.venues || []);
    if (
      venueSnapshot &&
      selectedFixtureId &&
      !venueSnapshot.fixtures.some((fixture) => fixture.id === selectedFixtureId)
    ) {
      setSelectedFixtureId(null);
      setSelectedKind(null);
    }
  }

  async function loadVenueSnapshot(nextVenueId) {
    try {
      const snapshot = await fetchJson(`/api/venues/${nextVenueId}`);
      setVenueSnapshot(snapshot);
      if (
        selectedFixtureId &&
        !snapshot.fixtures.some((fixture) => fixture.id === selectedFixtureId)
      ) {
        setSelectedFixtureId(null);
        setSelectedKind(null);
      }
    } catch (error) {
      console.error('Failed to load venue snapshot:', error);
      setVenueSnapshot(null);
    }
  }

  function handleSelectionChange(selection) {
    if (!selection) {
      setSelectedKind(null);
      setSelectedFixtureId(null);
      return;
    }
    setSelectedKind(selection.type);
    if (selection.type === 'fixture') {
      setSelectedFixtureId(selection.fixture.id);
    } else {
      setSelectedFixtureId(null);
    }
  }

  async function handleSaveFloor() {
    if (!venueSnapshot) {
      return;
    }
    await apiPatchVenue(venueSnapshot.summary.id, {
      floor_width: Number(floorValues.width || 0),
      floor_depth: Number(floorValues.depth || 0),
      floor_height: Number(floorValues.height || 0),
    });
  }

  async function handleSaveVideoWall() {
    if (!venueSnapshot) {
      return;
    }
    await apiPatchVideoWall(venueSnapshot.summary.id, {
      x: venueSnapshot.video_wall.x,
      y: venueSnapshot.video_wall.y,
      z: venueSnapshot.video_wall.z,
      width: venueSnapshot.video_wall.width,
      height: venueSnapshot.video_wall.height,
      depth: venueSnapshot.video_wall.depth,
      locked: videoWallLocked,
    });
  }

  async function handleAddFixture() {
    if (!venueSnapshot) {
      return;
    }
    await apiAddFixture(venueSnapshot.summary.id, {
      fixture_type: newFixtureValues.fixtureType,
      address: Number(newFixtureValues.address || 1),
      universe: newFixtureValues.universe,
      x: venueSnapshot.floor_width * 10,
      y: venueSnapshot.floor_depth * 10,
      z: 3,
      rotation_x: 0,
      rotation_y: 0,
      rotation_z: 0,
      options: {},
    });
  }

  async function handleSaveSelectedFixtureAddressing() {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    await apiPatchFixture(venueSnapshot.summary.id, selectedFixture.id, {
      address: Number(selectedFixtureValues.address || 1),
      universe: selectedFixtureValues.universe,
    });
  }

  async function handleEditAddressingFromContext() {
    setContextMenu((current) => ({ ...current, visible: false }));
    selectedFixtureAddressRef.current?.focus();
    selectedFixtureAddressRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  async function handleRemoveFixture() {
    setContextMenu((current) => ({ ...current, visible: false }));
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    await apiDeleteFixture(venueSnapshot.summary.id, selectedFixture.id);
  }

  return (
    <>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="panel">
            <h1>{venueSnapshot?.summary.name || 'Venue Editor'}</h1>
            <p className="panel-copy">Edit this venue in the left pane while the right pane stays focused on the live visualization.</p>
            <div className="button-row">
              <button className="secondary-button" onClick={() => window.location.assign(withCurrentSearch('/venues'))}>Back to Venues</button>
              <button className="secondary-button" onClick={() => window.location.assign(withCurrentSearch('/remote'))}>Remote</button>
            </div>
          </div>

          <div className="panel">
            <h2>Venue Settings</h2>
            <div className="selection-summary" id="venue-stats">{venueStats}</div>
            <div className="button-row">
              <button onClick={() => apiActivateVenue(venueId)}>
                {venueSummaries.find((venue) => venue.id === venueId)?.active ? 'Active Venue' : 'Make Active'}
              </button>
              <button
                className="secondary-button"
                onClick={async () => {
                  const nextName = window.prompt('Rename venue', venueSnapshot?.summary.name || '');
                  if (!nextName || !venueSnapshot) {
                    return;
                  }
                  await apiPatchVenue(venueSnapshot.summary.id, { name: nextName });
                }}
              >
                Rename
              </button>
              <button
                className="secondary-button"
                onClick={() => venueSnapshot && apiPatchVenue(venueSnapshot.summary.id, { archived: !venueSnapshot.summary.archived })}
              >
                {venueSnapshot?.summary.archived ? 'Unarchive' : 'Archive'}
              </button>
            </div>
          </div>

          <div className="panel">
            <h2>Views</h2>
            <div className="button-row">
              {['top', 'side', 'perspective'].map((viewName) => (
                <button
                  key={viewName}
                  className={`view-button${currentView === viewName ? ' active' : ''}`}
                  data-view={viewName}
                  onClick={() => setCurrentView(viewName)}
                >
                  {viewName === 'perspective' ? '3D' : viewName[0].toUpperCase() + viewName.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="panel">
            <h2>Floor</h2>
            <label>
              Width
              <input id="floor-width" type="number" step="0.1" value={floorValues.width} onChange={(event) => setFloorValues((current) => ({ ...current, width: event.target.value }))} />
            </label>
            <label>
              Depth
              <input id="floor-depth" type="number" step="0.1" value={floorValues.depth} onChange={(event) => setFloorValues((current) => ({ ...current, depth: event.target.value }))} />
            </label>
            <label>
              Height
              <input id="floor-height" type="number" step="0.1" value={floorValues.height} onChange={(event) => setFloorValues((current) => ({ ...current, height: event.target.value }))} />
            </label>
            <button id="save-floor-button" onClick={handleSaveFloor}>Save Floor</button>
          </div>

          <div className="panel">
            <h2>Video Wall</h2>
            <label className="checkbox-row">
              <input id="video-wall-locked" type="checkbox" checked={videoWallLocked} onChange={(event) => setVideoWallLocked(event.target.checked)} />
              Lock video wall
            </label>
            <button id="save-video-wall-button" onClick={handleSaveVideoWall}>Save Video Wall</button>
          </div>

          <div className="panel">
            <h2>Lights</h2>
            <div id="fixture-list" className="fixture-list">
              {(venueSnapshot?.fixtures || []).length === 0 ? (
                <div className="fixture-empty-state">No lights yet. Add one below.</div>
              ) : (
                (venueSnapshot?.fixtures || []).map((fixture) => (
                  <button
                    key={fixture.id}
                    className={`fixture-row${selectedFixtureId === fixture.id ? ' active-choice' : ''}`}
                    onClick={() => {
                      setSelectedKind('fixture');
                      setSelectedFixtureId(fixture.id);
                    }}
                  >
                    <span>{fixture.name || fixture.fixture_type}</span>
                    <span className="fixture-row-meta">{`${fixture.universe}:${fixture.address}`}</span>
                  </button>
                ))
              )}
            </div>
            <h3 className="section-subtitle">Add New Light</h3>
            <label>
              Fixture Type
              <select
                id="fixture-type-select"
                value={newFixtureValues.fixtureType}
                onChange={(event) => setNewFixtureValues((current) => ({ ...current, fixtureType: event.target.value }))}
              >
                {fixtureTypes.map((fixtureType) => (
                  <option key={fixtureType.key} value={fixtureType.key}>
                    {fixtureType.label}
                  </option>
                ))}
              </select>
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
                onChange={(event) => setNewFixtureValues((current) => ({ ...current, universe: event.target.value }))}
              >
                {supportedUniverses.map((universe) => (
                  <option key={universe.value} value={universe.value}>
                    {`${universe.label} (${universe.value})`}
                  </option>
                ))}
              </select>
            </label>
            <button id="add-fixture-button" onClick={handleAddFixture}>Add Fixture</button>
          </div>

          <div className="panel">
            <h2>Fixture Addressing</h2>
            <div id="selected-fixture-addressing" className="selection-summary">
              {selectedFixture ? `${selectedFixture.name || selectedFixture.fixture_type} currently uses ${selectedFixture.universe}:${selectedFixture.address}` : 'Select a fixture to edit its DMX addressing.'}
            </div>
            <label>
              Address
              <input
                id="selected-fixture-address-input"
                ref={selectedFixtureAddressRef}
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
            <button
              id="save-selected-fixture-addressing-button"
              onClick={handleSaveSelectedFixtureAddressing}
              disabled={!selectedFixture}
            >
              Save Fixture Addressing
            </button>
          </div>

          <div className="panel">
            <h2>Selection</h2>
            <div id="selection-summary" className="selection-summary">{selectionSummary}</div>
          </div>
        </aside>

        <main className="viewport-shell">
          <div id="viewport" ref={viewportRef} />
        </main>
      </div>

      <div
        id="context-menu"
        className={`context-menu${contextMenu.visible ? '' : ' hidden'}`}
        style={{ left: contextMenu.x, top: contextMenu.y }}
      >
        <button id="edit-address-button" onClick={handleEditAddressingFromContext}>Edit DMX Addressing</button>
        <button id="remove-fixture-button" className="danger-button" onClick={handleRemoveFixture}>Remove Fixture</button>
      </div>
    </>
  );

  async function apiActivateVenue(venueId) {
    await fetchJson(`/api/venues/${venueId}/activate`, { method: 'POST' });
  }

  async function apiPatchVenue(venueId, data) {
    await fetchJson(`/api/venues/${venueId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchVideoWall(venueId, data) {
    await fetchJson(`/api/venues/${venueId}/video-wall`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiAddFixture(venueId, data) {
    await fetchJson(`/api/venues/${venueId}/fixtures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchFixture(venueId, fixtureId, data) {
    await fetchJson(`/api/venues/${venueId}/fixtures/${fixtureId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiDeleteFixture(venueId, fixtureId) {
    await fetchJson(`/api/venues/${venueId}/fixtures/${fixtureId}`, {
      method: 'DELETE',
    });
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Request failed');
    }
    return response.json();
  }
}

function withCurrentSearch(pathname) {
  return `${pathname}${window.location.search}`;
}
