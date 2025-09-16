#!/usr/bin/env python3

"""
Example usage of VolumetricBeam for 3D concert-style lighting effects.
Shows how to integrate 3D volumetric beams with the existing 2D VJ system.
"""

from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.volumetric_beam import VolumetricBeam

# Import some glitch effects for combination
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect

from parrot.director.frame import FrameSignal


def create_concert_stage_with_beams():
    """
    Create a concert-style setup with 3D volumetric beams over 2D content.
    The beams render in front of the 2D canvas content.
    """
    # Base 2D content - video with text overlay
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)

    text = TextRenderer(
        text="LIVE\nCONCERT",
        font_size=120,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )
    text = BrightnessPulse(text, signal=FrameSignal.freq_high)

    # Combine 2D content
    canvas_2d = MultiplyCompose(video, text)
    canvas_2d = CameraZoom(canvas_2d, signal=FrameSignal.freq_low)

    # Create 3D volumetric beams
    beams = VolumetricBeam(
        beam_count=6,  # Multiple beams for concert effect
        beam_length=12.0,  # Long beams
        beam_width=0.4,  # Thick beams for visibility
        beam_intensity=1.2,  # Bright beams
        haze_density=0.9,  # Heavy haze for volumetric effect
        movement_speed=1.5,  # Smooth movement
        color=(1.0, 0.9, 0.7),  # Warm concert lighting
        signal=FrameSignal.freq_all,  # React to all frequencies
    )

    return canvas_2d, beams


def create_rave_beams():
    """
    Create fast-moving, colorful beams for rave/EDM style.
    """
    # Fast 2D background with beat-synchronized colors
    video = VideoPlayer(fn_group="bg")
    video = BeatHueShift(video, random_hues=True, signal=FrameSignal.pulse)
    video = ScanlinesEffect(video, scanline_intensity=0.3)

    # High-energy 3D beams
    beams = VolumetricBeam(
        beam_count=8,  # Many beams
        beam_length=8.0,  # Shorter, more intense
        beam_width=0.2,  # Thin, sharp beams
        beam_intensity=1.5,  # Very bright
        haze_density=0.7,  # Medium haze
        movement_speed=4.0,  # Fast movement
        color=(0.8, 0.4, 1.0),  # Purple/magenta
        signal=FrameSignal.freq_high,  # React to treble
    )

    return video, beams


def create_ambient_beams():
    """
    Create slow, atmospheric beams for ambient/chill music.
    """
    # Subtle 2D background
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=0.3, base_brightness=0.7)

    # Gentle 3D beams
    beams = VolumetricBeam(
        beam_count=3,  # Few beams
        beam_length=15.0,  # Very long beams
        beam_width=0.6,  # Wide, soft beams
        beam_intensity=0.8,  # Gentle intensity
        haze_density=1.0,  # Maximum haze for soft look
        movement_speed=0.8,  # Slow movement
        color=(0.6, 0.8, 1.0),  # Cool blue
        signal=FrameSignal.sustained_low,  # React to sustained bass
    )

    return video, beams


def create_industrial_beams():
    """
    Create harsh, mechanical beams for industrial/techno music.
    """
    # Harsh 2D background with glitch effects
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=1.0, base_brightness=0.3)

    text = TextRenderer(
        text="SYSTEM\nERROR",
        font_size=100,
        text_color=(255, 0, 0),  # Red text
        bg_color=(0, 0, 0),
    )

    canvas_2d = MultiplyCompose(video, text)

    # Sharp, aggressive beams
    beams = VolumetricBeam(
        beam_count=4,  # Moderate count
        beam_length=10.0,  # Medium length
        beam_width=0.15,  # Very thin, sharp
        beam_intensity=2.0,  # Very intense
        haze_density=0.5,  # Less haze for sharp edges
        movement_speed=3.0,  # Aggressive movement
        color=(1.0, 0.2, 0.0),  # Red/orange
        signal=FrameSignal.strobe,  # React to strobe effects
    )

    return canvas_2d, beams


# Integration with VJ Director:
"""
To integrate 3D beams with your VJ Director, you would modify the VJ system
to handle both 2D and 3D rendering:

class VJDirector:
    def __init__(self):
        # Create 2D canvas and 3D beams
        self.canvas_2d, self.beams_3d = create_concert_stage_with_beams()
        
        # ... rest of initialization
    
    def render(self, context, frame, scheme):
        # First render 2D content
        canvas_result = self.canvas_2d.render(frame, scheme, context)
        
        # Then render 3D beams on top
        beams_result = self.beams_3d.render(frame, scheme, context)
        
        # Composite 3D beams over 2D canvas
        # (This would require additional compositing logic)
        
        return final_composite

The 3D beams render to their own framebuffer with transparency, so they can be
composited over the 2D content using additive blending or alpha blending.
"""


# Usage examples:
def get_beam_setup_for_genre(genre: str):
    """Get appropriate beam setup for different music genres"""
    setups = {
        "concert": create_concert_stage_with_beams,
        "rave": create_rave_beams,
        "ambient": create_ambient_beams,
        "industrial": create_industrial_beams,
    }

    return setups.get(genre, create_concert_stage_with_beams)()


# Performance tips:
"""
1. Beam Count: More beams = more GPU load. Start with 4-6 beams.
2. Haze Density: Higher density = more volumetric effect but more GPU load.
3. Beam Length: Longer beams = more geometry to render.
4. Movement Speed: Higher speeds create more dynamic visuals.
5. Bloom Effect: The built-in bloom adds significant visual impact.

For best performance:
- Use fewer beams for complex 2D backgrounds
- Reduce haze density if frame rate drops
- Consider beam count based on target resolution
"""
