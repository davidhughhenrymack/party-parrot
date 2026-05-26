# Party Parrot

<img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl1NGRjNzkxeHc1bnpkNjdybXRpOGRlbWk0c2s1aGgyaDZpNHJzaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l3q2zVr6cu95nF6O4/giphy.gif" />

Party Parrot is an auto-pilot for party lighting. It listens to the room through a microphone, understands the energy of the music in real time, and drives DMX lights, moving heads, lasers, strobes, blinders, and video visuals so the whole room reacts to drops, builds, breakdowns, and late-night chaos without a lighting operator riding a console.

It is meant to scale with the party: start with a laptop, a USB DMX dongle, and a few cheap fixtures in a living room; grow into multi-universe rigs, mapped venues, moving-head choreography, remote control, and projection visuals for warehouse parties, clubs, and large rave rigs.

https://github.com/user-attachments/assets/72ff89d6-7b12-43f1-8451-35beed2953bf

https://github.com/user-attachments/assets/0b33b6e6-dcdd-497a-94ae-4c70f65ac35f


## What It Does

- **Runs the show automatically.** Audio analysis drives color, dimmer, movement, strobe, chase, and effect choices continuously.
- **Scales from tiny to serious.** Use mock DMX for practice, USB DMX for a simple rig, or Art-Net for networked universes and larger installations.
- **Understands real fixture types.** Party Parrot supports pars, moving heads, derbies, lasers, blinders, motion strips, mirror balls, Chauvet fixtures, generic fixtures, and custom venue patches.
- **Maps your venue.** The browser editor stores venues, floor dimensions, fixture positions, rotations, addresses, scene objects, DJ booths, video walls, and named positions.
- **Gives you operator controls when you want them.** A phone/laptop remote can switch hype levels, blackout, shift scenes, fire momentary effects, and control VJ modes from anywhere on the same Wi-Fi.
- **Shows what the rig is doing.** Live fixture state, patch views, an interpretation tree, a DMX heatmap, and 3D fixture previews make it possible to debug without staring at raw channel values.
- **Adds visuals, not just lights.** The VJ engine can run projector/TV visuals with video layers, shaders, text, virtual fixtures, haze-like beams, and beat-reactive effects.


## The Big Idea

Party Parrot tries to make lighting feel like part of the sound system. Instead of programming a fixed cue list, you define the venue and fixtures, pick a mode, and let the runtime keep making decisions from the live music. The system can sit in the background for a house party, or it can become the backbone of a bigger rig where a human still has quick controls for hype, blackout, effects, and scene changes.

The goal is not to replace every pro lighting desk workflow. It is to make a rig feel alive quickly, especially for dance music, DIY venues, pop-up raves, and parties where nobody wants to spend the night operating lights manually.


## DMX, Art-Net, And Rigs

DMX is the standard way lighting fixtures take instructions. A **universe** is a stream of up to **512 channels**, and each channel is a single value from 0–255: dimmer, red, pan, gobo, and so on. Every fixture is given a **start address** and reads its slice of the stream from there. Party Parrot writes that stream 30+ times a second based on what it hears.

There are two ways Party Parrot can get DMX out of your computer:

- **USB DMX interface:** The usual path. An **Enttec DMX USB Pro** (or any compatible USB-to-DMX adapter) plugs into your laptop, with a standard DMX cable running to your first fixture and daisy-chained to the rest. If nothing is plugged in, Party Parrot falls back to a mock output so you can still run visuals and practice.
- **Art-Net over Ethernet/Wi‑Fi:** Sends DMX over the network to an Art-Net node or console. Enabled per-venue in the app; typically used alongside a USB interface for a second universe.


## App Surfaces

- **Venue editor** (`/venues`, `/venues/<id>`): Build and activate venue layouts, place fixtures in a 3D room, assign addresses and universes, edit scene objects, and preview moving-head orientation.
- **Remote control** (`/remote`): Change lighting mode, VJ mode, blackout, shift scenes, and trigger short effects during a set.
- **Patch list** (`/patch`): See addresses, fixture types, universes, and channel widths for the active venue.
- **Interpretation tree** (`/interpretation`): Inspect the live decision graph and color palette that are feeding the runtime.
- **Desktop/VJ window:** Render the local visual output, DMX heatmap, fixture scene, or full VJ visuals.


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

1. Create or open a **venue**.
2. Set the floor dimensions and add your fixtures with DMX universe and start address.
3. Drag fixtures, DJ booths, video walls, and scene objects into place so the 3D layout matches the real room.
4. Activate the venue, then open **Remote Control** (`/remote`) to run the show.

### 4. Plug in and play

- Point a **microphone** at the speakers, or wire in an audio interface.
- Connect your **USB DMX** interface and DMX cable to your first fixture.
- Press play. Party Parrot takes the wheel.



## Keyboard shortcuts

With the Party Parrot window focused:

| Key | Action |
|-----|--------|
| `↑` / `↓` | Step lighting mode up (towards rave) / down (towards blackout) |
| `←` / `→` | Previous / next VJ mode |
| `Space` | Generate a fresh scene (new lighting + visuals) |
| `B` | Blackout toggle: kills lights and visuals, press again to restore |
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


## Development

Use Poetry and Just:

```bash
poetry install
just test
just launch
```

The main runtime is launched with `just launch`. The browser app is served by the local Party Parrot cloud/editor process, and the desktop renderer runs alongside it.


## License

Open source. Use it, improve it, light up the party.
