import { useEffect, useMemo, useRef, useState } from 'react';
import { createSceneController } from './DenseSceneController.js';

const isTestMode = new URLSearchParams(window.location.search).has('test_mode');

export default function DenseVenueEditorPage({ venueId }) {
  const viewportRef = useRef(null);
  const sceneControllerRef = useRef(null);
  const wsRef = useRef(null);
  const venueRef = useRef(null);
  const videoWallLockedRef = useRef(false);
  const selectedFixtureIdRef = useRef(null);
  const venueNameSaveTimerRef = useRef(null);
  const floorSaveTimerRef = useRef(null);

  const [venueSummaries, setVenueSummaries] = useState([]);
  const [venueSnapshot, setVenueSnapshot] = useState(null);
  const [fixtureTypes, setFixtureTypes] = useState([]);
  const [supportedUniverses, setSupportedUniverses] = useState([]);
  const [currentView, setCurrentView] = useState('perspective');
  const [interactionMode, setInteractionMode] = useState('select');
  const [contextMenu, setContextMenu] = useState({ visible: false, x: 0, y: 0 });
  const [selectedKind, setSelectedKind] = useState(null);
  const [selectedFixtureId, setSelectedFixtureId] = useState(null);
  const [venueNameDraft, setVenueNameDraft] = useState('');
  const [floorValues, setFloorValues] = useState({
    width: '',
    height: '',
  });
  const [videoWallLocked, setVideoWallLocked] = useState(false);
  const [addFixtureModalOpen, setAddFixtureModalOpen] = useState(false);
  const [newFixtureValues, setNewFixtureValues] = useState({
    fixtureType: '',
    address: '1',
    universe: 'default',
  });
  const [addressModalOpen, setAddressModalOpen] = useState(false);
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

  const venueSummary = useMemo(
    () => venueSummaries.find((venue) => venue.id === venueId) ?? null,
    [venueId, venueSummaries],
  );

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
      window.removeEventListener('click', handleWindowClick);
      wsRef.current?.close();
      sceneControllerRef.current?.destroy();
    };
  }, [venueId]);

  useEffect(() => {
    venueRef.current = venueSnapshot;
    if (!venueSnapshot) {
      setVenueNameDraft('');
      setFloorValues({ width: '', height: '' });
      setVideoWallLocked(false);
      return;
    }

    setVenueNameDraft(venueSnapshot.summary.name);
    setFloorValues({
      width: String(venueSnapshot.floor_width),
      height: String(venueSnapshot.floor_depth),
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

  useEffect(() => {
    sceneControllerRef.current?.setInteractionMode(interactionMode);
  }, [interactionMode]);

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
        void apiPatchVenue(venueSnapshot.summary.id, { name: trimmed });
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
    const nextWidth = Number(floorValues.width || 0);
    const nextHeight = Number(floorValues.height || 0);
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
      void apiPatchVenue(venueSnapshot.summary.id, {
        floor_width: nextWidth,
        floor_depth: nextHeight,
      });
    }, 250);
    return () => {
      if (floorSaveTimerRef.current) {
        window.clearTimeout(floorSaveTimerRef.current);
      }
    };
  }, [floorValues, venueSnapshot]);

  useEffect(() => {
    selectedFixtureIdRef.current = selectedFixtureId;
    if (selectedFixtureId) {
      sceneControllerRef.current?.setSelection({ type: 'fixture', fixtureId: selectedFixtureId });
    } else if (selectedKind !== 'video_wall') {
      sceneControllerRef.current?.setSelection(null);
    }
  }, [selectedFixtureId, selectedKind]);

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
  }

  async function loadVenueSnapshot(nextVenueId) {
    try {
      const snapshot = await fetchJson(`/api/venues/${nextVenueId}`);
      setVenueSnapshot(snapshot);
      if (
        selectedFixtureIdRef.current &&
        !snapshot.fixtures.some((fixture) => fixture.id === selectedFixtureIdRef.current)
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

  async function handleAddFixture() {
    if (!venueSnapshot) {
      return;
    }
    await apiAddFixture(venueSnapshot.summary.id, {
      fixture_type: newFixtureValues.fixtureType,
      address: Number(newFixtureValues.address || 1),
      universe: newFixtureValues.universe,
      x: venueSnapshot.floor_width / 2,
      y: venueSnapshot.floor_depth / 2,
      z: Math.max(venueSnapshot.floor_height * 0.5, 4),
      rotation_x: 0,
      rotation_y: 0,
      rotation_z: 0,
      options: {},
    });
    setAddFixtureModalOpen(false);
  }

  async function handleSaveSelectedFixtureAddressing() {
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    await apiPatchFixture(venueSnapshot.summary.id, selectedFixture.id, {
      address: Number(selectedFixtureValues.address || 1),
      universe: selectedFixtureValues.universe,
    });
    setAddressModalOpen(false);
  }

  async function handleRemoveFixture() {
    setContextMenu((current) => ({ ...current, visible: false }));
    if (!venueSnapshot || !selectedFixture) {
      return;
    }
    await apiDeleteFixture(venueSnapshot.summary.id, selectedFixture.id);
    setSelectedFixtureId(null);
    setSelectedKind(null);
  }

  return (
    <>
      <div className="dense-editor-shell">
        <aside className="dense-sidebar">
          <div className="panel dense-header-panel">
            <div className="dense-header-top">
              <button
                className="small-button secondary-button icon-only-button"
                aria-label="Back to venues"
                onClick={() => window.location.assign(withCurrentSearch('/venues'))}
              >
                ←
              </button>
            </div>
            <textarea
              id="venue-name-input"
              className="venue-name-input"
              rows="2"
              value={venueNameDraft}
              onChange={(event) => setVenueNameDraft(event.target.value)}
            />
          </div>

          <div className="panel dense-panel">
            <div className="dense-section-header">
              <h3>Lights</h3>
              <span className="dense-section-count">
                {venueSnapshot ? venueSnapshot.fixtures.length : '...'}
              </span>
            </div>
            <div id="fixture-list" className="fixture-list dense-fixture-list">
              {(venueSnapshot?.fixtures || []).length === 0 ? (
                <div className="fixture-empty-state">No lights yet. Use the Add Light bar.</div>
              ) : (
                (venueSnapshot?.fixtures || []).map((fixture) => (
                  <button
                    key={fixture.id}
                    className={`fixture-row dense-fixture-row${selectedFixtureId === fixture.id ? ' active-choice' : ''}`}
                    onClick={() => {
                      setSelectedKind('fixture');
                      setSelectedFixtureId(fixture.id);
                    }}
                  >
                    <span className="dense-fixture-main">
                      <strong>{fixture.name || fixture.fixture_type}</strong>
                      <span className="fixture-row-meta">{fixture.fixture_type}</span>
                    </span>
                    <span className="dense-fixture-actions">
                      {selectedFixtureId === fixture.id ? (
                        <>
                          <button
                            className="icon-button link-button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setAddressModalOpen(true);
                            }}
                          >
                            {`${fixture.universe}:${fixture.address}`}
                          </button>
                          <button
                            className="icon-button danger-button"
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
                ))
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
                  step="0.1"
                  value={floorValues.width}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setFloorValues((current) => ({ ...current, width: nextValue }));
                    setVenueSnapshot((current) => (
                      current
                        ? {
                            ...current,
                            floor_width: Number(nextValue || current.floor_width),
                          }
                        : current
                    ));
                  }}
                />
              </label>
              <label className="compact-label">
                <span>H</span>
                <input
                  id="floor-height"
                  type="number"
                  step="0.1"
                  value={floorValues.height}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setFloorValues((current) => ({ ...current, height: nextValue }));
                    setVenueSnapshot((current) => (
                      current
                        ? {
                            ...current,
                            floor_depth: Number(nextValue || current.floor_depth),
                          }
                        : current
                    ));
                  }}
                />
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

          <div className="floating-bottom-bar">
            <div className="tool-radio-group" role="radiogroup" aria-label="Viewport tool">
              <button
                className={`tool-chip${interactionMode === 'select' ? ' active' : ''}`}
                aria-checked={interactionMode === 'select'}
                onClick={() => setInteractionMode('select')}
              >
                Cursor
              </button>
              <button
                className={`tool-chip${interactionMode === 'pan' ? ' active' : ''}`}
                aria-checked={interactionMode === 'pan'}
                onClick={() => setInteractionMode('pan')}
              >
                Pan
              </button>
              <button
                className={`tool-chip${interactionMode === 'rotate' ? ' active' : ''}`}
                aria-checked={interactionMode === 'rotate'}
                onClick={() => setInteractionMode('rotate')}
              >
                Rotate
              </button>
            </div>
            <button id="open-add-light-modal-button" onClick={() => setAddFixtureModalOpen(true)}>
              Add Light
            </button>
          </div>
        </main>
      </div>

      <div
        id="context-menu"
        className={`context-menu${contextMenu.visible ? '' : ' hidden'}`}
        style={{ left: contextMenu.x, top: contextMenu.y }}
      >
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
        onClose={() => setAddFixtureModalOpen(false)}
      >
        <div className="modal-form">
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
          <div className="modal-actions">
            <button className="secondary-button" onClick={() => setAddFixtureModalOpen(false)}>Cancel</button>
            <button id="add-fixture-button" onClick={handleAddFixture}>Add Fixture</button>
          </div>
        </div>
      </Modal>
    </>
  );

  async function apiActivateVenue(targetVenueId) {
    await fetchJson(`/api/venues/${targetVenueId}/activate`, { method: 'POST' });
  }

  async function apiPatchVenue(targetVenueId, data) {
    await fetchJson(`/api/venues/${targetVenueId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchVideoWall(targetVenueId, data) {
    await fetchJson(`/api/venues/${targetVenueId}/video-wall`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiAddFixture(targetVenueId, data) {
    await fetchJson(`/api/venues/${targetVenueId}/fixtures`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiPatchFixture(targetVenueId, fixtureId, data) {
    await fetchJson(`/api/venues/${targetVenueId}/fixtures/${fixtureId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  }

  async function apiDeleteFixture(targetVenueId, fixtureId) {
    await fetchJson(`/api/venues/${targetVenueId}/fixtures/${fixtureId}`, {
      method: 'DELETE',
    });
  }
}

function Modal({ open, title, onClose, children }) {
  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="small-button secondary-button" onClick={onClose}>Close</button>
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
