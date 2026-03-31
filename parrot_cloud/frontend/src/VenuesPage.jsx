import { useEffect, useState } from 'react';

export default function VenuesPage() {
  const [venues, setVenues] = useState([]);

  useEffect(() => {
    let reconnectTimer = null;
    let ws = null;

    async function initialize() {
      const bootstrap = await fetchJson('/api/bootstrap');
      setVenues(bootstrap.venues || []);
      connectWebSocket();
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      ws = new WebSocket(`${protocol}://${window.location.host}/ws/venue-updates`);
      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === 'bootstrap') {
          setVenues(payload.data.venues || []);
        } else if (payload.type === 'venues') {
          setVenues(payload.data?.venues || []);
        }
      };
      ws.onclose = () => {
        reconnectTimer = window.setTimeout(connectWebSocket, 1000);
      };
    }

    initialize().catch((error) => {
      console.error('Failed to initialize venues page:', error);
    });

    return () => {
      if (reconnectTimer !== null) {
        window.clearTimeout(reconnectTimer);
      }
      ws?.close();
    };
  }, []);

  async function handleAddVenue() {
    const name = window.prompt('New venue name');
    if (!name) {
      return;
    }
    const created = await fetchJson('/api/venues', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    window.location.assign(withCurrentSearch(`/venues/${created.summary.id}`));
  }

  return (
    <main className="page-shell">
      <div className="page-header">
        <div>
          <h1>Venues</h1>
          <p className="panel-copy">Choose a venue to edit its layout, lights, and video wall.</p>
        </div>
        <div className="button-row compact-row">
          <button className="secondary-button" onClick={() => window.location.assign('/')}>Home</button>
          <button className="secondary-button" onClick={() => window.location.assign(withCurrentSearch('/remote'))}>Remote Control</button>
        </div>
      </div>

      <section id="venue-grid" className="venue-grid">
        {venues.map((venue) => (
          <button
            key={venue.id}
            className={`venue-tile${venue.active ? ' active-choice' : ''}`}
            onClick={() => window.location.assign(withCurrentSearch(`/venues/${venue.id}`))}
          >
            <div className="venue-tile-title">{venue.name}</div>
            <div className="venue-tile-meta">{venue.slug}</div>
            <div className="venue-tile-meta">{`Revision ${venue.revision}`}</div>
            <div className="venue-tile-meta">{venue.archived ? 'Archived' : venue.active ? 'Active venue' : 'Draft'}</div>
          </button>
        ))}

        <button id="add-venue-tile" className="venue-tile add-venue-tile" onClick={handleAddVenue}>
          <div className="venue-tile-title">Add New Venue</div>
          <div className="venue-tile-meta">Create another room profile.</div>
        </button>
      </section>
    </main>
  );
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
