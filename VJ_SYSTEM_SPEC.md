# 🎬 Party Parrot VJ System - Complete Overview - Complete Implementation

## 🚀 **COMPLETE VJ SYSTEM OVERVIEW**

**Status: ✅ FULLY OPERATIONAL**

Your Party Parrot VJ system features **70+ interpreters** across **8 categories** with **15+ layer types**, optimized for **Apple M4 Max** performance. The system includes **82 floating metallic pyramids**, **6 Halloween videos**, **professional strobing**, and **concert-style lasers** - all ready for your **Dead Sexy Halloween rave**.

### 🎯 **QUICK START:**
```bash
# VJ-only mode (recommended):
poetry run python -m parrot.main --vj-only

# Full system with GUI:
./main.sh

# Performance-optimized:
poetry run python vj_smooth.py
```

## 🎃 Halloween "Dead Sexy" Theme Integration

The VJ system is specifically designed around a **Halloween party theme** called "Dead Sexy" with the following thematic elements:

### **Color Palette**
- **🔴 Blood Red** (`#FF0000`) - Primary horror color for blood effects and violence
- **🎃 Pumpkin Orange** (`#FFA500`) - Jack-o'-lantern inspired warmth
- **⚫ Deep Black** (`#000000`) - Darkness, mystery, and death
- **👻 Ghost White** (`#FFFFFF`) - Supernatural elements and lightning
- **💜 Dark Purple** (`#800080`) - Witchy, magical, mysterious atmosphere
- **🌑 Dark Red** (`#8B0000`) - Deep blood tones and shadows

### **Thematic Audio Mapping**
- **🔊 Bass = Blood & Violence** - Bass drops trigger blood splatters, red lighting intensifies
- **🎼 Treble = Supernatural** - Treble spikes cause lightning strikes, blue ghostly effects
- **⚡ Energy = Terror Intensity** - Overall horror level, text screaming, chaos effects
- **🥁 Beats = Rhythm of Fear** - Perfect timing for blood splatters, video switches, strobing

### **Text Theme**
- **"DEAD SEXY" text** uses the best available horror font from 914+ system fonts
- **Professional effects**: Black outline + dark red shadow
- **Alpha masking**: Video content shows through the text letters
- **Horror animations**: Breathing, screaming, crawling, shaking effects

## 📋 Complete Effects Inventory (53+ Effects)

### 🎥 **Core VJ System (9 Effects)**
1. **VideoLayer** - Random video playback with Halloween content
2. **TextLayer** - "DEAD SEXY" text with horror font and alpha masking
3. **SolidLayer** - Dark backgrounds (black, dark red) for horror atmosphere
4. **AlphaFade** - Smooth breathing-like alpha transitions
5. **AlphaFlash** - Beat-triggered alpha flashing for jump scares
6. **AlphaPulse** - Heartbeat-like pulsing effects
7. **VideoSelector** - Switches between horror videos on beats
8. **TextAnimator** - Makes text dance with the music
9. **TextColorCycle** - Cycles text through Halloween colors

### 💀 **Halloween Horror Effects (18 Effects)**
10. **LightningFlash** - Dramatic lightning on energy spikes (supernatural)
11. **LightningLayer** - Visual lightning bolts across screen
12. **BloodDrip** - Blood dripping triggered by bass (violence)
13. **BloodSplatter** - Explosive blood on beats (impact)
14. **BloodOverlay** - Blood visual rendering layer
15. **DeadSexyTextHorror** - Text breathing with random SCARE MODE
16. **HorrorTextScream** - Text "screams" with 2.5x scaling explosion
17. **CreepyCrawl** - Text crawls like living creature (circle, zigzag, spiral, shake)
18. **HorrorContrast** - Dynamic contrast (0.3x to 2.0x) for horror movie look
19. **SpookyLighting** - Moving ghost lights (candle, sickly green, purple, blood red)
20. **SpookyLightingLayer** - Renders moving supernatural lights
21. **HalloweenGlitch** - Digital supernatural corruption effects
22. **GhostlyFade** - Ethereal ghost-like materialization
23. **EerieBreathing** - Slow breathing atmosphere (organic, not mechanical)
24. **HalloweenStrobeEffect** - Halloween color strobing
25. **PumpkinPulse** - Jack-o'-lantern orange pulsing
26. **HalloweenParticles** - Floating bats, skulls, spiders, ghosts
27. **HorrorColorGrade** - Red-tinted horror movie color grading

### 🎨 **Color Lighting Effects (9 Effects)**
28. **ColorSchemeLighting** - Halloween color schemes as multiplicative lighting
29. **RedLighting** - Picks out blood/red elements in videos (perfect for horror)
30. **BlueLighting** - Enhances blue/white for ghostly supernatural effects
31. **DynamicColorLighting** - Cycles through Halloween colors with beat boost
32. **SelectiveLighting** - Targets specific colors (blood red) for enhancement
33. **StrobeLighting** - Color strobing through Halloween palette
34. **WarmCoolLighting** - Bass=fire/blood warm, treble=ghost cool
35. **SpotlightEffect** - Moving ghost lights with Halloween colors
36. **ColorChannelSeparation** - Bass→blood red, treble→ghost blue

### 🔴 **Laser Show Effects (6 Effects)**
37. **ConcertLasers** - Fan beams (4-16 lasers) in Halloween colors
38. **LaserMatrix** - Grid patterns (up to 10×6) with Halloween color waves
39. **LaserBurst** - Explosive radial bursts (up to 20 beams) on energy spikes
40. **LaserChase** - Chasing lasers with Halloween color trails
41. **LaserScan** - Sweeping beams in supernatural colors
42. **LaserSpiral** - Hypnotic spirals with alternating directions

### ⚡ **Strobe Effects (11 Effects)**
43. **StrobeFlash** - Basic fixture-style strobing (5-60Hz)
44. **ColorStrobe** - Halloween color cycling while strobing
45. **BeatStrobe** - Perfect beat synchronization with horror music
46. **RandomStrobe** - Unpredictable supernatural strobing
47. **HighSpeedStrobe** - Ultra-fast (60Hz) for peak terror moments
48. **PatternStrobe** - Custom horror strobe sequences
49. **AudioReactiveStrobe** - Bass=red, treble=blue, sustained=green strobing
50. **LayerSelectiveStrobe** - Independent layer strobing with phase offsets
51. **StrobeBlackout** - Dramatic blackouts vs blinding flashes
52. **RGBChannelStrobe** - Independent RGB channel strobing
53. **StrobeZoom** - Text scaling with strobing effects

## 🎭 VJ DSL (Domain Specific Language)

The VJ system uses a DSL similar to `mode_interpretations.py` for clean, readable configuration:

### **DSL Syntax Examples**
```python
# Basic randomization (like lighting fixtures)
vj_randomize(BloodSplatter, BloodDrip, HorrorContrast)

# Weighted selection with probabilities
vj_weighted_randomize(
    (70, BloodSplatter),  # 70% blood splatter
    (30, BloodDrip)       # 30% blood drip
)

# Combine multiple effects (like lighting combo())
vj_combo(
    BloodOnBass,          # Blood triggered by bass
    LightningOnTreble,    # Lightning on treble hits
    StrobeOnManual        # Strobe on button press
)

# Layer type filtering
for_video(RedLightingOnBass)    # Only affects video layers
for_text(TextScreamOnEnergy)    # Only affects text layers
for_laser(LaserShow)            # Only affects laser layers

# Custom parameters (like lighting with_args())
vj_with_args("IntenseRed", RedLighting, red_intensity=3.0)

# Energy-based activation
energy_gate(0.8, LaserBurst)    # Only above 80% energy

# Audio signal switching
signal_switch(StrobeFlash)      # Changes with audio signals
```

### **Halloween Mode Configuration (DSL Style)**
```python
Mode.rave: {
    "layers": [
        Black(w, h),                    # Dark horror background
        HorrorVideo(w, h),             # Spooky video content
        BloodLayer(w, h),              # Blood effects layer
        LaserLayer(w, h),              # Concert laser layer
        DeadSexyText(w, h),            # Horror font text
    ],
    "interpreters": [
        # Video gets randomized horror lighting
        for_video(
            vj_randomize(
                vj_with_args("BloodGlow", RedLighting, red_intensity=3.0),
                vj_with_args("GhostLight", BlueLighting, blue_intensity=2.0),
                vj_with_args("ColorCycle", DynamicColorLighting, beat_boost=True)
            )
        ),
        
        # Text gets random horror effects
        for_text(
            vj_randomize(
                vj_with_args("Screaming", HorrorTextScream, max_scale=2.5),
                vj_with_args("Crawling", CreepyCrawl, crawl_speed=0.04),
                vj_with_args("Breathing", EerieBreathing, breath_speed=0.03)
            )
        ),
        
        # Lasers get weighted random shows
        for_laser(
            vj_weighted_randomize(
                (40, vj_with_args("WideFan", ConcertLasers, num_lasers=12)),
                (30, vj_with_args("Matrix", LaserMatrix, grid_size=(8,6))),
                (20, vj_with_args("Burst", LaserBurst, max_burst_lasers=20)),
                (10, vj_with_args("Spiral", LaserSpiral, num_spirals=3))
            )
        ),
        
        # Blood effects combo
        for_blood(
            vj_combo(
                BloodOnBass,
                vj_with_args("Dripping", BloodDrip, drip_threshold=0.6)
            )
        ),
        
        # Manual strobe control
        StrobeOnManual,
    ]
}
```

## System Architecture

### Core Components

1. **VJ Base Classes** (`parrot/vj/base.py`)
   - `LayerBase`: Abstract base class for all VJ layers
   - `VJInterpreterBase`: Base class for VJ interpreters (similar to lighting interpreters)
   - `VJRenderer`: Main renderer that composites all layers using OpenGL

2. **Layer Types** (`parrot/vj/layers/`)
   - `VideoLayer`: Plays video files with effects
   - `TextLayer`: Renders text with alpha masking
   - `SolidLayer`: Simple solid color layer (for backgrounds)
   - `EffectLayer`: Applies visual effects to other layers

3. **VJ Interpreters** (`parrot/vj/interpreters/`)
   - `AlphaFade`: Controls layer alpha based on audio signals
   - `VideoSelector`: Randomly selects and switches videos
   - `TextAnimator`: Animates text properties
   - `ColorModulator`: Modulates colors based on schemes

4. **VJ Director Integration** (`parrot/director/vj_director.py`)
   - Extends existing Director class to manage VJ renderers
   - Handles VJ mode interpretations
   - Synchronizes with lighting system

5. **Mode Interpretations** (`parrot/vj/vj_interpretations.py`)
   - Defines layer configurations for each mode (gentle, rave, etc.)
   - Similar structure to existing `mode_interpretations.py`

## Technical Requirements

### Dependencies
- **ModernGL**: OpenGL rendering and shader management
- **PyAV**: Video file loading and decoding
- **Pillow**: Text rendering and image manipulation
- **NumPy**: Array operations for video data

### Video System
- Support for common video formats (MP4, AVI, MOV)
- Loop playback with seamless transitions
- Random selection from video directory
- Frame-accurate synchronization with audio

### Text Rendering
- High-quality text rendering with custom fonts
- Alpha masking capabilities
- Support for various text effects

### Layer Composition
- OpenGL-based layer compositing
- Real-time alpha blending
- Efficient GPU memory management
- Support for multiple blend modes

## Detailed Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 VJ Base Classes (`parrot/vj/base.py`)
```python
class LayerBase:
    """Base class for all VJ layers"""
    def __init__(self, name: str, z_order: int = 0)
    def render(self, frame: Frame, scheme: ColorScheme) -> np.ndarray
    def set_alpha(self, alpha: float)
    def get_size(self) -> Tuple[int, int]

class VJInterpreterBase:
    """Base class for VJ interpreters"""
    def __init__(self, layers: List[LayerBase], args: InterpreterArgs)
    def step(self, frame: Frame, scheme: ColorScheme)
    def exit(self, frame: Frame, scheme: ColorScheme)

class VJRenderer:
    """Main VJ renderer using OpenGL"""
    def __init__(self, width: int, height: int)
    def add_layer(self, layer: LayerBase)
    def render_frame(self) -> np.ndarray
    def resize(self, width: int, height: int)
```

#### 1.2 OpenGL Renderer (`parrot/vj/renderer.py`)
- Initialize ModernGL context
- Create shaders for layer compositing
- Implement efficient texture management
- Handle frame buffer operations

### Phase 2: Layer Implementation

#### 2.1 Video Layer (`parrot/vj/layers/video.py`)
```python
class VideoLayer(LayerBase):
    def __init__(self, video_dir: str, loop: bool = True)
    def load_random_video(self)
    def update_frame(self)
    def render(self, frame: Frame, scheme: ColorScheme) -> np.ndarray
```

Features:
- Random video selection from directory
- Seamless looping
- Frame rate synchronization
- Memory-efficient video streaming

#### 2.2 Text Layer (`parrot/vj/layers/text.py`)
```python
class TextLayer(LayerBase):
    def __init__(self, text: str, font_path: str, size: int)
    def set_text(self, text: str)
    def set_font_properties(self, size: int, weight: str)
    def render_with_alpha_mask(self) -> np.ndarray
```

Features:
- High-quality text rendering
- Alpha masking (text as transparency)
- Dynamic text updates
- Font customization

### Phase 3: VJ Interpreters

#### 3.1 Alpha Fade Interpreter (`parrot/vj/interpreters/alpha_fade.py`)
```python
class AlphaFade(VJInterpreterBase):
    def __init__(self, layers, args, signal: FrameSignal)
    def step(self, frame: Frame, scheme: ColorScheme)
```

Maps audio signals to layer alpha values with configurable curves.

#### 3.2 Video Selector Interpreter (`parrot/vj/interpreters/video_selector.py`)
```python
class VideoSelector(VJInterpreterBase):
    def __init__(self, layers, args, switch_probability: float = 0.01)
    def step(self, frame: Frame, scheme: ColorScheme)
```

Randomly switches videos based on probability and audio triggers.

### Phase 4: Director Integration

#### 4.1 VJ Director (`parrot/director/vj_director.py`)
```python
class VJDirector:
    def __init__(self, state: State, video_dir: str)
    def setup_vj_layers(self)
    def generate_vj_interpreters(self)
    def step(self, frame: Frame)
    def render(self) -> np.ndarray
```

Manages VJ system lifecycle and integrates with main Director.

#### 4.2 Director Extension (`parrot/director/director.py`)
- Add VJ director instance
- Coordinate between lighting and VJ systems
- Handle mode changes for both systems

### Phase 5: Mode Interpretations

#### 5.1 VJ Interpretations (`parrot/vj/vj_interpretations.py`)
```python
vj_mode_interpretations = {
    Mode.blackout: {
        "layers": [
            SolidLayer(color="black")
        ]
    },
    Mode.gentle: {
        "layers": [
            SolidLayer(color="black"),
            VideoLayer(alpha_interpreter=AlphaFade(signal=FrameSignal.sustained_low)),
            TextLayer(text="DEAD SEXY", alpha_mask=True)
        ]
    },
    Mode.rave: {
        "layers": [
            SolidLayer(color="black"),
            VideoLayer(alpha_interpreter=AlphaFade(signal=FrameSignal.freq_high)),
            TextLayer(text="DEAD SEXY", alpha_mask=True, animator=TextAnimator())
        ]
    }
}
```

### Phase 6: GUI Integration

#### 6.1 GUI Updates (`parrot/gui/gui.py`)
- Add spacebar key binding for VJ toggle
- Create VJ display window or overlay
- Handle window switching logic
- Maintain state synchronization

```python
def toggle_vj_display(self):
    """Toggle between lighting view and VJ view"""
    self.state.set_vj_mode(not self.state.vj_mode)
    if self.state.vj_mode:
        self.show_vj_window()
    else:
        self.hide_vj_window()
```

## File Structure

```
parrot/
├── vj/
│   ├── __init__.py
│   ├── base.py                 # Base classes
│   ├── renderer.py             # OpenGL renderer
│   ├── vj_interpretations.py   # Mode interpretations
│   ├── layers/
│   │   ├── __init__.py
│   │   ├── video.py            # Video layer
│   │   ├── text.py             # Text layer
│   │   ├── solid.py            # Solid color layer
│   │   └── effect.py           # Effect layers
│   ├── interpreters/
│   │   ├── __init__.py
│   │   ├── alpha_fade.py       # Alpha control
│   │   ├── video_selector.py   # Video switching
│   │   ├── text_animator.py    # Text animation
│   │   └── color_modulator.py  # Color effects
│   └── test/
│       ├── test_base.py
│       ├── test_layers.py
│       ├── test_interpreters.py
│       └── test_renderer.py
├── director/
│   └── vj_director.py          # VJ director integration
└── gui/
    └── vj_window.py            # VJ display window
```

## Testing Strategy

### Unit Tests
1. **Layer Tests**: Test each layer type independently
2. **Interpreter Tests**: Verify signal processing and effects
3. **Renderer Tests**: Test OpenGL compositing
4. **Integration Tests**: Test VJ director coordination

### Performance Tests
1. **Frame Rate**: Ensure consistent 60fps rendering
2. **Memory Usage**: Monitor video memory consumption
3. **CPU Usage**: Profile video decoding performance

### Visual Tests
1. **Layer Composition**: Verify correct alpha blending
2. **Video Playback**: Test seamless looping
3. **Text Rendering**: Verify alpha masking quality

## Configuration

### Settings (`parrot/vj/config.py`)
```python
VJ_CONFIG = {
    'video_directory': 'media/videos/',
    'default_resolution': (1920, 1080),
    'target_fps': 60,
    'max_video_memory_mb': 512,
    'text_font_path': 'assets/fonts/default.ttf',
    'enable_vsync': True
}
```

## Dependencies to Add

Add to `pyproject.toml`:
```toml
moderngl = "^5.8.2"
av = "^10.0.0"
pillow = "^10.0.0"
numpy = "^1.24.0"
```

## Success Criteria

1. **Functional Requirements**
   - VJ system runs parallel to lighting system
   - Video layers play and loop correctly
   - Text layers render with proper alpha masking
   - Audio signals control visual effects
   - GUI toggle works seamlessly

2. **Performance Requirements**
   - Maintains 60fps rendering
   - Memory usage stays under 1GB
   - No audio/video sync drift
   - Responsive to real-time input

3. **Quality Requirements**
   - High-quality video playback
   - Smooth alpha transitions
   - Sharp text rendering
   - Stable OpenGL rendering

## Future Enhancements

1. **Additional Layer Types**
   - Image layers with effects
   - Particle systems
   - Shader-based procedural graphics

2. **Advanced Effects**
   - Blur, distortion, color grading
   - Beat-synchronized effects
   - Cross-layer interactions

3. **Content Management**
   - Dynamic video loading
   - Playlist management
   - Content categorization

This specification provides a comprehensive roadmap for implementing the VJ system while maintaining compatibility with the existing lighting infrastructure.
