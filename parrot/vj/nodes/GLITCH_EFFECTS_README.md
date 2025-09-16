# Glitch Effects for Party Parrot VJ System

This collection of glitch effects provides retro distortions and digital corruption aesthetics for your VJ performances.

## Available Effects

### 1. DatamoshEffect (`datamosh_effect.py`)
**Digital compression artifacts and pixel displacement**
- Simulates video compression corruption
- Horizontal and vertical pixel displacement
- Color corruption and quantization
- Digital noise patterns
- Perfect for: Glitch hop, breakcore, digital hardcore

**Parameters:**
- `displacement_strength` (0.0-1.0): How much pixels get displaced
- `corruption_intensity` (0.0-1.0): Color corruption intensity  
- `glitch_frequency` (0.0-1.0): How often glitches occur
- `signal`: Audio signal that triggers stronger glitches

### 2. RGBShiftEffect (`rgb_shift_effect.py`)
**Chromatic aberration and RGB channel separation**
- Separates and shifts RGB channels independently
- Animated shifting patterns
- Optional vertical shifting
- Perfect for: Synthwave, vaporwave, retro aesthetics

**Parameters:**
- `shift_strength` (0.0-0.1): Maximum shift distance
- `shift_speed` (0.1-10.0): Animation speed
- `vertical_shift` (bool): Enable vertical channel shifting
- `signal`: Audio signal controlling shift intensity

### 3. ScanlinesEffect (`scanlines_effect.py`)
**Retro CRT monitor simulation**
- Authentic scanlines with rolling animation
- Screen curvature (barrel distortion)
- Phosphor glow effects
- Edge vignetting
- Perfect for: Retro gaming, 80s aesthetics, cyberpunk

**Parameters:**
- `scanline_intensity` (0.0-1.0): Darkness of scanlines
- `scanline_count` (100-500): Number of scanlines
- `roll_speed` (0.1-2.0): Rolling animation speed
- `curvature` (0.0-0.5): Screen curvature amount
- `signal`: Audio signal affecting interference

### 4. PixelateEffect (`pixelate_effect.py`)
**8-bit/16-bit retro pixelation**
- Dynamic pixel size based on audio
- Color quantization (2-256 colors per channel)
- Optional dithering for smooth gradients
- Retro color shifting
- Perfect for: Chiptune, 8-bit music, retro gaming

**Parameters:**
- `pixel_size` (2.0-50.0): Size of pixel blocks
- `color_depth` (2-256): Colors per channel (lower = more retro)
- `dither` (bool): Apply dithering for gradients
- `signal`: Audio signal controlling pixelation intensity

### 5. NoiseEffect (`noise_effect.py`)
**Analog TV static and interference**
- Multiple noise types (white noise, perlin noise, fractal)
- Horizontal static lines
- Color channel noise
- Signal dropout effects
- Analog desaturation
- Perfect for: Industrial, noise music, analog aesthetics

**Parameters:**
- `noise_intensity` (0.0-1.0): Overall noise strength
- `noise_scale` (50-200): Noise pattern scale
- `static_lines` (bool): Enable horizontal static lines
- `color_noise` (bool): Apply noise to color channels
- `signal`: Audio signal controlling noise intensity

### 6. BeatHueShift (`beat_hue_shift.py`)
**Beat-synchronized hue shifting and color cycling**
- Changes hue/color filter on each detected beat
- Smooth transitions between colors
- Sequential rainbow cycling or random hues
- Saturation boosting for vibrant colors
- Perfect for: Dance music, EDM, house, techno

**Parameters:**
- `hue_shift_amount` (0-360): Degrees to shift hue on each beat
- `saturation_boost` (0.5-2.0): Multiply saturation for vibrancy
- `transition_speed` (1.0-20.0): Speed of color transitions
- `random_hues` (bool): Random colors vs sequential rainbow
- `signal`: Beat signal that triggers hue changes (typically `pulse`)

## Usage Examples

### Basic Usage
```python
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.video_player import VideoPlayer

# Apply datamosh to video
video = VideoPlayer(fn_group="bg")
glitched = DatamoshEffect(video, displacement_strength=0.05)

# Add beat-synchronized color changes
colored = BeatHueShift(video, signal=FrameSignal.pulse)
```

### Chaining Effects
```python
# Create a heavily glitched composition
video = VideoPlayer(fn_group="bg")
video = DatamoshEffect(video, displacement_strength=0.08)
video = RGBShiftEffect(video, shift_strength=0.02)
video = ScanlinesEffect(video, scanline_intensity=0.3)
final = NoiseEffect(video, noise_intensity=0.2)
```

### VHS Aesthetic
```python
def create_vhs_look():
    video = VideoPlayer(fn_group="bg")
    vhs = RGBShiftEffect(video, shift_strength=0.015, vertical_shift=False)
    vhs = ScanlinesEffect(vhs, curvature=0.2, scanline_intensity=0.5)
    return vhs
```

### 8-bit Retro
```python
def create_8bit_look():
    video = VideoPlayer(fn_group="bg")
    retro = PixelateEffect(video, pixel_size=12.0, color_depth=8)
    retro = NoiseEffect(retro, noise_intensity=0.1, color_noise=False)
    return retro
```

### Beat-Synchronized Colors
```python
def create_dance_floor_colors():
    video = VideoPlayer(fn_group="bg")
    # Random color changes on each beat
    dance = BeatHueShift(video, random_hues=True, signal=FrameSignal.pulse)
    return dance

def create_rainbow_cycle():
    video = VideoPlayer(fn_group="bg")
    # Sequential rainbow colors
    rainbow = BeatHueShift(video, random_hues=False, signal=FrameSignal.pulse)
    return rainbow
```

## Integration with VJ Director

To use these effects in your VJ Director, modify the `__init__` method:

```python
def __init__(self):
    # Base video with text
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)
    
    text = TextRenderer(text="GLITCH", font_size=120)
    text = BrightnessPulse(text, signal=FrameSignal.freq_high)
    
    # Multiply compose
    masked = MultiplyCompose(video, text)
    
    # Add glitch effects
    glitched = DatamoshEffect(masked, signal=FrameSignal.freq_high)
    glitched = RGBShiftEffect(glitched, signal=FrameSignal.freq_all)
    
    # Add beat-synchronized color changes
    colored = BeatHueShift(glitched, signal=FrameSignal.pulse)
    
    self.canvas = CameraZoom(colored)
```

## Audio Reactivity

All effects respond to different audio signals:
- `freq_low`: Bass frequencies (good for slow effects)
- `freq_high`: Treble frequencies (good for fast glitches)  
- `freq_all`: All frequencies combined
- `sustained_low`/`sustained_high`: Sustained audio levels
- `strobe`, `pulse`: Beat-synchronized signals (perfect for BeatHueShift)
- `big_blinder`, `small_blinder`: Flash effects

## Performance Notes

- Effects are GPU-accelerated using OpenGL shaders
- Can be chained together for complex looks
- Each effect adds minimal performance overhead
- BeatHueShift includes beat detection with minimal CPU usage
- Tested with 1280x720 resolution at 30+ FPS

## Creative Tips

1. **Layer effects gradually** - Start with one effect and add more
2. **Use different signals** - Map different effects to different frequency ranges
3. **Adjust intensity** - Lower values often look more authentic
4. **Combine with existing effects** - Works great with BrightnessPulse, CameraZoom
5. **Match the music** - Datamosh for glitch hop, scanlines for synthwave, BeatHueShift for dance music
6. **Use beat sync wisely** - BeatHueShift works best with clear, consistent beats

Enjoy creating glitchy retro visuals! 🎛️✨
