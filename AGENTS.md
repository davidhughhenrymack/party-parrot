# AGENTS.md

## Cursor Cloud specific instructions

### Services overview

Party Parrot is a Python 3.12 real-time DMX lighting + VJ system. It uses Poetry for dependencies and Just as a task runner. See the `README.md` for full command reference.

### Environment prerequisites (already installed in snapshot)

Xvfb (`:99`), PulseAudio with a null-sink dummy audio device, and Mesa software OpenGL libraries are required for headless operation. These are pre-installed in the VM snapshot.

### Key environment variables

The following must be set before running the app or tests:

| Variable | Value | Notes |
|---|---|---|
| `DISPLAY` | `:99` | Xvfb virtual display |
| `PYOPENGL_PLATFORM` | `x11` | **Must be `x11`, not `egl`** — `egl` causes "no valid context" errors with imgui/pyglet |
| `MESA_GL_VERSION_OVERRIDE` | `3.3` | Force Mesa to report GL 3.3 |
| `LIBGL_ALWAYS_SOFTWARE` | `1` | Force software rendering |
| `MPLBACKEND` | `Agg` | Non-interactive matplotlib |
| `SDL_VIDEODRIVER` | `dummy` | SDL dummy video |
| `QT_QPA_PLATFORM` | `offscreen` | Qt offscreen |

### Starting services before running

Before running `just launch` or `just test`, ensure:

1. **Xvfb** is running: `Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &`
2. **PulseAudio** is running with a null sink: `pulseaudio --start --exit-idle-time=-1 --system=false --daemonize=true && pactl load-module module-null-sink sink_name=dummy`

### Running tests

`just test` runs the full pytest suite. One test file (`parrot/vj/nodes/test_layer_compose.py`) has a pre-existing broken import (`volumetric_beam` module doesn't exist) and will error at collection time. To skip it: `poetry run python -m pytest --ignore=parrot/vj/nodes/test_layer_compose.py`.

The `test_output/` directory must exist for some tests (e.g. `test_simple_dmx_render.py`). Create it with `mkdir -p test_output`.

### Running the app

`just launch` (i.e. `poetry run python -m parrot.main`). Useful flags for headless verification:
- `--screenshot` — captures a frame and exits
- `--debug-frame` — runs 20 frames, saves debug PNGs, and exits
- `--no-web` — disables the Flask web server

DMX hardware is not required; the app falls back to a mock DMX controller when no Enttec USB device is found.

### Gotchas

- **`PYOPENGL_PLATFORM` must be `x11`**: The committed `.cursor/environment.json` specified `egl`, but that causes `OpenGL.error.Error: Attempt to retrieve context when no valid context` during imgui overlay initialization. Use `x11` instead.
- **ALSA/JACK warnings**: Numerous ALSA and JACK warnings appear on stderr when the app starts. These are harmless — the app successfully opens the PulseAudio null-sink for audio input.
- Some test failures are pre-existing in the repo (fixture render tests, performance benchmarks, missing modules) and are not caused by the dev environment.
