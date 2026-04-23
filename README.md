# Party Parrot

<img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl1NGRjNzkxeHc1bnpkNjdybXRpOGRlbWk0c2s1aGgyaDZpNHJzaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l3q2zVr6cu95nF6O4/giphy.gif" />

Party Parrot runs the lights at your party. It listens to the music through a microphone and drives your DMX rig in real time, so the room reacts to drops, builds, and breakdowns without anyone touching a board.

Built for house parties and small venues. No cue programming, no lighting-desk experience required.

https://github.com/user-attachments/assets/72ff89d6-7b12-43f1-8451-35beed2953bf

https://github.com/user-attachments/assets/0b33b6e6-dcdd-497a-94ae-4c70f65ac35f


## Features

- Reacts to the music in real time — beats, energy, and dynamics drive color, movement, and intensity.
- Works with common rigs: LED pars, moving heads, derbies, lasers, blinders, motion strips, and more.
- Switchable modes for different vibes — party, rave, mellow/twinkle, blackout.
- Browser-based venue editor to lay out your fixtures in a 3D room.
- Phone/laptop remote so you can change mode and intensity from anywhere on the Wi‑Fi.
- Optional VJ window for a projector or TV with video and beat-synced effects.



## Talks to lights over DMX

DMX is the standard way lighting fixtures take instructions. A **universe** is a stream of up to **512 channels**, and each channel is a single value from 0–255 — dimmer, red, pan, gobo, and so on. Every fixture is given a **start address** and reads its slice of the stream from there. Party Parrot writes that stream 30+ times a second based on what it hears.

There are two ways Party Parrot can get DMX out of your computer:

- **USB DMX interface** — The usual path. An **Enttec DMX USB Pro** (or any compatible USB-to-DMX adapter) plugs into your laptop, with a standard DMX cable running to your first fixture and daisy-chained to the rest. If nothing is plugged in, Party Parrot falls back to a mock output so you can still run visuals and practice.
- **Art-Net over Ethernet/Wi‑Fi** — Sends DMX over the network to an Art-Net node or console. Enabled per-venue in the app; typically used alongside a USB interface for a second universe.

---

## Getting started

### 1. Install

Requires macOS (or Linux), [Homebrew](https://brew.sh/), [Poetry](https://python-poetry.org/), and Python 3.12.

```bash
brew install portaudio python-tk@3.12
poetry install
```

### 2. Launch

```bash
just launch
```

This starts the venue editor (port `4041`), opens it in your browser, and runs the lighting engine. The local database is created and seeded on first launch.

To control it from your phone, open `http://<your-mac-ip>:4041/` on the same Wi‑Fi.

### 3. Lay out your room

In the venue editor:

1. Open your **venue** and add the fixtures you have, with their DMX start addresses.
2. Drag them into position so the layout matches your real space.
3. Hit **Remote Control** (`/remote`) to switch modes and adjust the show during a set.

### 4. Plug in and play

- Point a **microphone** at the speakers, or wire in an audio interface.
- Connect your **USB DMX** interface and DMX cable to your first fixture.
- Press play. Lights go.



## Keyboard shortcuts

With the Party Parrot window focused:

| Key | Action |
|-----|--------|
| `↑` / `↓` | Step lighting mode up (towards rave) / down (towards blackout) |
| `←` / `→` | Previous / next VJ mode |
| `Space` | Generate a fresh scene (new lighting + visuals) |
| `B` | Blackout toggle — kills lights and visuals, press again to restore |
| `N` | Shift the lighting scene only |
| `O` | Shift the VJ scene only |
| `S` | Shift the color scheme |
| `\` | Toggle fixture/debug view |

Hold-to-trigger moments (release to stop):

| Key | Effect |
|-----|--------|
| `1` / `I` | Rainbow |
| `2` / `G` | Big blinder |
| `3` / `H` | Strobe |
| `4` / `J` | Chase |



## License

Open source. Use it, improve it, light up the party.
