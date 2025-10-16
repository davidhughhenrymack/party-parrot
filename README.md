# 🦜 Party Parrot
### Your AI Lighting Designer & VJ System

<img src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNXl1NGRjNzkxeHc1bnpkNjdybXRpOGRlbWk0c2s1aGgyaDZpNHJzaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/l3q2zVr6cu95nF6O4/giphy.gif" />

**Party Parrot is the ultimate robot companion for DJs and live performers.** It listens to your music in real-time, analyzes every beat and frequency, then orchestrates a complete audio-visual experience combining intelligent DMX lighting control with GPU-accelerated visual effects.

Think of it as your tireless lighting designer and VJ rolled into one, constantly adapting to the energy of your music, never repeating itself, always surprising you.

https://github.com/user-attachments/assets/72ff89d6-7b12-43f1-8451-35beed2953bf

https://github.com/user-attachments/assets/0b33b6e6-dcdd-497a-94ae-4c70f65ac35f

https://github.com/user-attachments/assets/80028f98-0602-4d91-86d1-8140eff4e39a

https://github.com/user-attachments/assets/abe38098-7e1c-4c25-be31-e967eed0709c

https://github.com/user-attachments/assets/3359f668-8472-4afb-a809-ddf2639c94cb

---

## 🚀 Quick Start

Get up and running in under 2 minutes:

```bash
# Install dependencies
brew install portaudio python-tk@3.12
poetry install

# Launch Party Parrot
just launch

# Or launch fullscreen for performances
just launch-fullscreen
```

That's it! Party Parrot will start listening to your microphone, analyzing the music, and controlling your DMX fixtures and visuals.

---

## ✨ What Makes Party Parrot Special

### 🎛️ **Intelligent DMX Lighting Control**
Party Parrot doesn't just flash lights to the beat—it **understands** your music:
- **Real-time audio analysis** with advanced beat detection, frequency separation, and energy tracking
- **Automatic scene generation** that creates unique lighting combinations for every song
- **Smart transitions** that shift between looks based on musical dynamics
- **Energy-aware programming** that intensifies during drops and pulls back during breakdowns
- **Never repeats** the same combination—always fresh, always evolving

### 🎨 **Professional VJ Visuals**
A complete GPU-accelerated visual system running at **870+ FPS**:
- **Dynamic video playback** from themed video collections (warehouse raves, neon streets, church raves, vintage horror, and more)
- **30+ real-time effects**: Bloom, camera zoom/shake, datamosh, RGB shift, pixelation, scanlines, hot sparks, CRT mask, vintage film, color strobes, and more
- **3D virtual lighting fixtures** with volumetric beam rendering and haze effects
- **Beat-synchronized effects** that pulse, strobe, and evolve with the music
- **Text overlays** with animated color effects
- **Layer compositing** for complex multi-effect combinations
- **Oscilloscope visualization** for that analog synth aesthetic

### 🎪 **Extensive Fixture Support**
Works with a massive range of professional DMX fixtures:
- **Moving Heads**: Chauvet Intimidator series (Spot 110, 120, 160), Rogue Beam R2, MoveWhite 9
- **LED Pars**: RGB and RGBA color mixing, strobe effects
- **Lasers**: Chauvet, Oultia, and UKing laser systems
- **Effect Lights**: Rotospheres, Derby effects, Color Band Pix
- **Atmospheric Effects**: Motion strips, stage blinders
- **Complete rigs**: Chauvet GigBar support

### 🌈 **Adaptive Color Schemes**
Intelligent color management that creates cohesive looks:
- **Theme-based palettes**: Automatically generates complementary color schemes
- **Smooth transitions** between color schemes
- **Rainbow mode support** for high-energy moments
- **Color coordination** across all fixtures and visuals

### 🎭 **Multiple Performance Modes**
Switch between modes for different vibes:
- **Party Mode**: High-energy lighting with aggressive beat detection
- **Rave Mode**: Maximum intensity with all effects engaged
- **Twinkle Mode**: Gentle, ambient lighting for mellow moments
- **Blackout**: Instant lights-out

### 📱 **Mobile Web Interface**
Control everything from your phone or tablet:
- **Remote mode switching** from any device on your network
- **Real-time updates** with thread-safe state management
- **Clean, mobile-optimized UI**
- **Custom port configuration**

### 🎯 **Smart Behavior**
Party Parrot watches your music and adapts:
- **Automatic scene shifts** every 60 seconds during quiet moments (never mid-drop!)
- **Hype detection** that escalates intensity during peak energy
- **Signal routing** that ensures every frequency range is always represented
- **Warmup period** for smooth startup transitions
- **Position management** for spatial effects across multiple fixtures

---

## 🎪 Performance Features

### Real-Time Audio Analysis
- Multi-band frequency analysis (bass, mid, treble, presence)
- Beat detection with tempo tracking
- Energy level monitoring
- Sustained signal detection
- Dynamic range adaptation

### Lighting Effects Arsenal
- **Chase patterns** across fixture groups
- **Strobe effects** synchronized to beats
- **Color washes** that sweep the room
- **Movement patterns**: Fans, circles, random walks, bounces
- **Dimmer animations**: Pulses, chases, breathing effects
- **Position effects**: Tilts, pans, coordinated movements
- **Gobo rotations** and pattern effects (for supported fixtures)

### Visual Effects Library
- **Camera effects**: Zoom, shake, dolly
- **Color grading**: Hue shifts, saturation pulses, sepia tones
- **Distortion**: Datamosh, pixelation, RGB shift, noise
- **Retro effects**: CRT mask, scanlines, vintage film grain
- **Glow effects**: Bloom, bright glow, hot sparks
- **Masking**: Circular vignettes, sprocket holes
- **Compositing**: Layer blending, multiply modes, opacity control

---

## 🏗️ Architecture

Party Parrot is built on a sophisticated, modular architecture:

### Director System
The **Director** is the brain that coordinates everything:
- Manages fixture groups and interpreters
- Generates color schemes and transitions
- Coordinates timing and scene shifts
- Bridges DMX lighting and VJ visuals
- Handles mode switching and state management

### Interpreter Pipeline
Each fixture group gets its own **Interpreter** that translates music into light:
- Base interpreters for different fixture types
- Composite interpreters that chain effects
- Signal-driven interpreters that respond to specific frequencies
- Latched interpreters that hold states
- Randomization for organic variation

### VJ Graph System
A node-based rendering pipeline for visuals:
- **BaseInterpretationNode**: Composable effects that transform video frames
- **Fixture renderers**: 3D volumetric lighting simulation
- **Layer composition**: Stack effects like Photoshop layers
- **Mode switching**: Different visual styles for different modes
- **Recursive generation**: Partial or complete scene regeneration

### State Management
Thread-safe state with event-driven updates:
- Mode, theme, and venue selection
- Hype levels and limiters
- Manual dimmer control
- Web interface integration
- Keyboard shortcuts

---

## 🎛️ Hardware Setup

### Required
- **Mac or Linux** (tested on macOS)
- **USB Audio Interface** for microphone input
- **Entec DMX USB Pro** (or compatible) for DMX output
- **DMX fixtures** connected via standard DMX cables

### Optional
- **Projector or external display** for VJ output
- **MIDI controller** for live parameter control (future feature)
- **Network connection** for web interface

---

## 💻 Usage

### Command-Line Options
```bash
# Standard launch
poetry run python -m parrot.main

# Fullscreen VJ window
poetry run python -m parrot.main --vj-fullscreen

# Start in rave mode
poetry run python -m parrot.main --rave

# Custom web port
poetry run python -m parrot.main --web-port 8080

# Disable web interface
poetry run python -m parrot.main --no-web

# Fixture visualization mode
poetry run python -m parrot.main --fixture-mode

# Enable profiling
poetry run python -m parrot.main --profile --profile-interval 30

# Legacy tkinter GUI (deprecated)
poetry run python -m parrot.main --legacy-gui
```

### Justfile Commands
```bash
just launch              # Standard launch
just launch-fullscreen   # Fullscreen mode
just launch-rave        # Start in rave mode
just launch-fixture     # Fixture renderer mode
just launch-profile     # With performance profiling
just test              # Run test suite
```

### Keyboard Shortcuts
- **Mode switching**: Change performance modes on the fly
- **Manual dimmer control**: Adjust overall brightness
- **Overlay toggle**: Show/hide debug information
- **Scene shifts**: Force immediate scene changes

---

## 🎨 Customization

### Adding Video Content
Place video files in organized folders:
```
media/videos/
  bg/              # High-energy backgrounds
  bg_chill/        # Mellow backgrounds
  bg_hiphop/       # Hip-hop specific visuals
  bg_music_vid/    # Music video footage
```

Party Parrot will intelligently select and transition between videos based on the current mode and energy level.

### Creating Venue Patches
Define your fixture setup in `patch_bay.py`:
```python
venue_patches = {
    "my_venue": [
        MovingHead(address=1, name="Stage Left"),
        MovingHead(address=20, name="Stage Right"),
        Par(address=40, name="Front Wash"),
        Laser(address=100, name="Crowd Laser"),
    ]
}
```

### Custom Color Themes
Add new themes in `director/themes.py` with:
- Custom color scheme palettes
- Rainbow enable/disable
- Fixture-specific behaviors

---

## 🧪 Testing

Party Parrot includes comprehensive test coverage:

```bash
# Run all tests
just test

# Run specific test files
poetry run pytest parrot/fixtures/test_moving_head.py
poetry run pytest parrot/vj/nodes/test_video_player.py

# Run with coverage report
poetry run coverage run -m pytest
poetry run coverage report
```

Tests cover:
- Fixture control and DMX rendering
- Audio analysis algorithms
- VJ effect rendering (including headless GPU tests)
- Director logic and scene generation
- State management and threading
- Keyboard input handling
- Web interface endpoints

---

## 🏆 Technical Highlights

- **Modern OpenGL**: Hardware-accelerated rendering with ModernGL
- **Type Safety**: Runtime type checking with beartype
- **Dependency Management**: Poetry for reproducible builds
- **Testing**: Pytest with headless rendering support
- **Audio Processing**: PortAudio for low-latency audio capture
- **Color Science**: Proper color space handling and mixing
- **DMX Protocol**: Robust DMX control via PyEnttec
- **Concurrent Execution**: Thread-safe state with event system
- **Modular Design**: Easy to extend with new fixtures and effects

---

## 🎯 Future Roadmap

- MIDI controller support for live parameter tweaking
- Machine learning for genre detection and automatic mode selection
- Networked multi-instance support for large venues
- ArtNet/sACN support for larger DMX universes
- Preset save/load system
- Timeline recording and playback
- SMPTE timecode sync for A/V production
- Plugin system for custom effects

---

## 🛠️ Development

### Project Structure
```
parrot/
  ├── main.py              # Application entry point
  ├── director/            # Scene coordination and color management
  ├── fixtures/            # DMX fixture definitions
  ├── interpreters/        # Music-to-light translation
  ├── vj/                  # Visual system
  │   ├── nodes/          # Effect nodes (30+ effects)
  │   ├── renderers/      # 3D fixture renderers
  │   └── vj_director.py  # VJ coordination
  ├── audio/              # Audio analysis
  ├── api/                # Web interface
  └── utils/              # Shared utilities
```

### Contributing
Party Parrot follows strict development practices:
- **Type enforcement** with beartype decorators
- **No silent failures**: Code should fail loudly and clearly
- **Comprehensive tests**: Test complex logic, not trivial code
- **Clean code**: Avoid hasattr/try-except fallbacks, use precise typing
- **Run before commit**: Always test with `just launch` and `just test`

---

## 📚 Credits

Built with:
- [ModernGL](https://github.com/moderngl/moderngl) - GPU rendering
- [PortAudio](http://www.portaudio.com/) - Audio capture
- [PyEnttec](https://github.com/generalelectrix/PyEnttec) - DMX control
- [NumPy](https://numpy.org/) - Audio processing
- [Flask](https://flask.palletsprojects.com/) - Web interface
- [beartype](https://github.com/beartype/beartype) - Runtime type checking

---

## 📄 License

Party Parrot is open source. Use it, remix it, take it to your shows, and make some noise! 🎉

---

**Ready to rock?** `just launch` and let Party Parrot transform your performance! 🦜🎉💡
