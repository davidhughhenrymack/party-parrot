import RemoteControlPage from './RemoteControlPage.jsx';
import VenuesPage from './VenuesPage.jsx';
import DenseVenueEditorPage from './DenseVenueEditorPage.jsx';

export default function App() {
  const path = window.location.pathname;
  const venueMatch = path.match(/^\/venues\/([^/]+)$/);

  if (venueMatch) {
    return <DenseVenueEditorPage venueId={venueMatch[1]} />;
  }

  if (path === '/venues' || path === '/editor') {
    return <VenuesPage />;
  }

  if (path === '/remote') {
    return <RemoteControlPage />;
  }

  return <HomePage />;
}

function HomePage() {
  return (
    <main className="home-shell">
      <section className="home-hero">
        <img
          className="home-parrot-gif"
          src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl1NGRjNzkxeHc1bnpkNjdybXRpOGRlbWk0c2s1aGgyaDZpNHJzaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l3q2zVr6cu95nF6O4/giphy.gif"
          alt="Party Parrot"
        />
        <div className="home-badge">Parrot Cloud</div>
        <h1>Administer Party Parrots from one place.</h1>
        <p className="home-copy">
          Use the remote control for live show changes or enter the venue editor to manage rooms,
          fixtures, and video walls.
        </p>
        <div className="home-actions">
          <button id="enter-remote-button" onClick={() => window.location.assign('/remote')}>
            Enter Remote Control
          </button>
          <button id="enter-editor-button" className="secondary-button" onClick={() => window.location.assign('/venues')}>
            Enter Venue Editor
          </button>
        </div>
      </section>
    </main>
  );
}
