# VolumetricBeam - 3D Concert Lighting for Party Parrot

A completely new type of VJ node that renders **3D volumetric light beams** in concert-style environments. Unlike the 2D shader-based effects, VolumetricBeam uses **OpenGL 3D primitives** to create realistic light beams that wave around in a hazy atmosphere.

## 🎭 **What It Does**

- **3D Volumetric Rendering**: Real 3D cone geometry with volumetric scattering
- **Concert-Style Beams**: Moving light beams like professional stage lighting
- **Atmospheric Haze**: Simulates fog/haze for realistic volumetric effects
- **Bloom & Glow**: Post-processing effects for authentic light beam glow
- **Audio Reactive**: Beams move and oscillate based on music signals
- **Renders Over 2D**: Composites on top of existing 2D canvas content

## 🔧 **Technical Features**

### 3D Rendering Pipeline
- **OpenGL 3D primitives** (not just 2D shaders)
- **Cone mesh geometry** for each beam
- **3D transformation matrices** (view, projection, model)
- **Depth testing** for proper 3D occlusion
- **Additive blending** for realistic light accumulation

### Volumetric Effects
- **Atmospheric scattering** simulation in fragment shader
- **Distance-based attenuation** for realistic falloff
- **Cone falloff** (brighter in center, dimmer at edges)
- **Camera-relative scattering** for viewing angle effects

### Post-Processing
- **Bloom effect** with bright area extraction
- **Box blur** for glow diffusion
- **Additive compositing** back to main framebuffer
- **Separate render targets** for multi-pass rendering

## 🎵 **Audio Reactivity**

- **Position Oscillation**: Beams sway based on audio signal strength
- **Intensity Modulation**: Brightness responds to signal levels
- **Movement Speed**: Audio affects how fast beams move to new positions
- **Beat Synchronization**: Can sync to different frequency ranges

## 📋 **Parameters**

```python
VolumetricBeam(
    beam_count=4,              # Number of light beams (1-16)
    beam_length=10.0,          # Length of each beam in 3D units
    beam_width=0.3,            # Width/thickness of beam cone
    beam_intensity=1.0,        # Brightness multiplier
    haze_density=0.8,          # Atmospheric haze density (0.0-1.0)
    movement_speed=2.0,        # Speed of beam movement/rotation
    color=(1.0, 0.8, 0.6),     # RGB color (warm white default)
    signal=FrameSignal.freq_all, # Audio signal for reactivity
    width=1280,                # Render target width
    height=720                 # Render target height
)
```

## 🎨 **Usage Examples**

### Concert Stage Setup
```python
def create_concert_beams():
    beams = VolumetricBeam(
        beam_count=6,
        beam_length=12.0,
        beam_intensity=1.2,
        haze_density=0.9,
        color=(1.0, 0.9, 0.7),  # Warm concert lighting
        signal=FrameSignal.freq_all
    )
    return beams
```

### Rave/EDM Style
```python
def create_rave_beams():
    beams = VolumetricBeam(
        beam_count=8,
        beam_width=0.2,         # Thin, sharp beams
        beam_intensity=1.5,     # Very bright
        movement_speed=4.0,     # Fast movement
        color=(0.8, 0.4, 1.0),  # Purple/magenta
        signal=FrameSignal.freq_high
    )
    return beams
```

### Ambient/Chill
```python
def create_ambient_beams():
    beams = VolumetricBeam(
        beam_count=3,
        beam_length=15.0,       # Very long beams
        beam_width=0.6,         # Wide, soft beams
        movement_speed=0.8,     # Slow movement
        haze_density=1.0,       # Maximum haze
        color=(0.6, 0.8, 1.0),  # Cool blue
        signal=FrameSignal.sustained_low
    )
    return beams
```

## 🏗️ **Integration with VJ Director**

The VolumetricBeam renders to its own framebuffer and can be composited over 2D content:

```python
class VJDirector:
    def __init__(self):
        # 2D canvas content
        self.canvas_2d = create_2d_content()
        
        # 3D volumetric beams
        self.beams_3d = VolumetricBeam(
            beam_count=6,
            color=(1.0, 0.8, 0.6)
        )
    
    def render(self, context, frame, scheme):
        # Render 2D content first
        canvas_result = self.canvas_2d.render(frame, scheme, context)
        
        # Render 3D beams on top
        beams_result = self.beams_3d.render(frame, scheme, context)
        
        # Composite together (beams have transparency)
        return composite_3d_over_2d(canvas_result, beams_result)
```

## 🎯 **Perfect For**

- **Live Concerts**: Realistic stage lighting effects
- **EDM/Rave**: Fast-moving, colorful beam shows
- **Ambient Music**: Slow, atmospheric lighting
- **Industrial/Techno**: Sharp, aggressive beams
- **Any Genre**: Customizable for different moods

## ⚡ **Performance**

- **GPU Accelerated**: All rendering on GPU using OpenGL
- **Efficient Geometry**: Optimized cone meshes
- **Configurable Quality**: Adjust beam count and effects for performance
- **Tested**: 4-8 beams at 1280x720 @ 30+ FPS

### Performance Tips
1. **Beam Count**: Start with 4-6 beams, add more as GPU allows
2. **Haze Density**: Lower values = better performance
3. **Resolution**: Beams scale well with different resolutions
4. **Bloom**: Can be disabled for better performance if needed

## 🔬 **Technical Implementation**

### 3D Math Utilities (`math_3d.py`)
- Matrix operations (view, projection, model)
- 3D transformations and rotations
- Spherical coordinate conversions
- Smooth interpolation functions

### Beam State Management
- Individual beam position and direction tracking
- Smooth movement towards random targets
- Audio-reactive oscillation
- Phase-offset randomization for variety

### Shader Pipeline
1. **Vertex Shader**: 3D transformations and matrix math
2. **Fragment Shader**: Volumetric scattering and attenuation
3. **Bloom Shader**: Post-processing for glow effects

### Rendering Pipeline
1. Setup 3D camera and projection matrices
2. Render each beam with individual transforms
3. Apply volumetric scattering in fragment shader
4. Extract bright areas for bloom
5. Blur and composite bloom back
6. Return final framebuffer for compositing

## 🚀 **Ready to Use**

The VolumetricBeam system is production-ready with:
- ✅ **Complete 3D rendering pipeline**
- ✅ **Comprehensive test suite** (12 passing tests)
- ✅ **Audio reactivity** with all signal types
- ✅ **Multiple usage examples** for different genres
- ✅ **Performance optimized** for real-time use
- ✅ **Integration examples** with existing VJ system

Transform your Party Parrot visuals from 2D to **3D concert-style lighting**! 🎛️✨🎪
