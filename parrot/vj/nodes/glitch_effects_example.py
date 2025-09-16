#!/usr/bin/env python3

"""
Example usage of the new glitch effects for retro distortions.
This demonstrates how to chain multiple effects together for complex glitch aesthetics.
"""

from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.camera_zoom import CameraZoom

# Import the new glitch effects
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.beat_hue_shift import BeatHueShift

from parrot.director.frame import FrameSignal


def create_glitchy_text_video():
    """
    Create a heavily glitched text-on-video composition.
    Combines multiple effects for maximum retro distortion.
    """
    # Base video layer
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)

    # Text mask layer
    text = TextRenderer(
        text="GLITCH\nMODE",
        font_size=120,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )
    text = BrightnessPulse(text, signal=FrameSignal.freq_high)

    # Multiply text with video
    masked_video = MultiplyCompose(video, text)

    # Apply glitch effects in sequence
    # 1. Add datamosh corruption
    glitched = DatamoshEffect(
        masked_video,
        displacement_strength=0.08,
        corruption_intensity=0.4,
        glitch_frequency=0.6,
        signal=FrameSignal.freq_high,
    )

    # 2. Add RGB channel shifting
    glitched = RGBShiftEffect(
        glitched,
        shift_strength=0.02,
        shift_speed=3.0,
        vertical_shift=True,
        signal=FrameSignal.freq_all,
    )

    # 3. Add CRT scanlines
    glitched = ScanlinesEffect(
        glitched,
        scanline_intensity=0.3,
        scanline_count=250.0,
        roll_speed=0.8,
        curvature=0.15,
        signal=FrameSignal.sustained_low,
    )

    # 4. Final camera zoom for movement
    final = CameraZoom(glitched, signal=FrameSignal.freq_low)

    return final


def create_retro_pixelated_video():
    """
    Create a retro 8-bit style video with pixelation and noise.
    """
    # Base video
    video = VideoPlayer(fn_group="bg")

    # Heavy pixelation for 8-bit look
    pixelated = PixelateEffect(
        video,
        pixel_size=12.0,
        color_depth=8,  # Very limited color palette
        dither=True,
        signal=FrameSignal.freq_low,
    )

    # Add analog TV noise
    noisy = NoiseEffect(
        pixelated,
        noise_intensity=0.2,
        noise_scale=150.0,
        static_lines=True,
        color_noise=False,  # Keep colors clean for retro look
        signal=FrameSignal.sustained_high,
    )

    return noisy


def create_vhs_aesthetic():
    """
    Create a VHS-style aesthetic with RGB shift and scanlines.
    """
    # Base video with text overlay
    video = VideoPlayer(fn_group="bg")
    text = TextRenderer(
        text="VHS\nAESTHETIC",
        font_size=100,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )

    # Combine with multiply
    combined = MultiplyCompose(video, text)

    # Add VHS-style RGB shifting
    vhs_shifted = RGBShiftEffect(
        combined,
        shift_strength=0.015,
        shift_speed=1.5,
        vertical_shift=False,  # Classic horizontal VHS distortion
        signal=FrameSignal.freq_all,
    )

    # Add CRT scanlines with curvature
    vhs_final = ScanlinesEffect(
        vhs_shifted,
        scanline_intensity=0.5,
        scanline_count=300.0,
        roll_speed=0.3,
        curvature=0.2,  # More curved for old TV look
        signal=FrameSignal.sustained_low,
    )

    return vhs_final


def create_digital_corruption():
    """
    Create extreme digital corruption effects.
    """
    # Base video
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)

    # Extreme datamoshing
    corrupted = DatamoshEffect(
        video,
        displacement_strength=0.15,  # Very high displacement
        corruption_intensity=0.8,  # Heavy corruption
        glitch_frequency=0.9,  # Almost constant glitching
        signal=FrameSignal.freq_high,
    )

    # Add heavy noise
    noisy = NoiseEffect(
        corrupted,
        noise_intensity=0.5,
        noise_scale=80.0,
        static_lines=True,
        color_noise=True,
        signal=FrameSignal.sustained_high,
    )

    # Pixelate for digital artifact look
    final = PixelateEffect(
        noisy,
        pixel_size=6.0,
        color_depth=4,  # Very limited colors
        dither=False,  # No dithering for harsh digital look
        signal=FrameSignal.freq_low,
    )

    return final


def create_beat_synchronized_colors():
    """
    Create a beat-synchronized color-changing video with hue shifts.
    Perfect for dance music and electronic genres.
    """
    # Base video with text
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)

    text = TextRenderer(
        text="BEAT\nDROP",
        font_size=140,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )
    text = BrightnessPulse(text, signal=FrameSignal.freq_high)

    # Multiply compose
    combined = MultiplyCompose(video, text)

    # Add beat-synchronized hue shifting
    hue_shifted = BeatHueShift(
        combined,
        hue_shift_amount=90.0,  # Large hue jumps for dramatic effect
        saturation_boost=1.4,  # Boost saturation for vibrant colors
        transition_speed=12.0,  # Fast transitions
        random_hues=True,  # Random colors for variety
        signal=FrameSignal.pulse,  # Sync to beat pulses
    )

    # Add subtle camera zoom for movement
    final = CameraZoom(hue_shifted, signal=FrameSignal.freq_low)

    return final


def create_rainbow_cycling_video():
    """
    Create a video that cycles through rainbow colors in sequence.
    """
    # Base video
    video = VideoPlayer(fn_group="bg")

    # Cycle through rainbow hues in order
    rainbow = BeatHueShift(
        video,
        hue_shift_amount=60.0,  # 60-degree steps through color wheel
        saturation_boost=1.3,
        transition_speed=6.0,  # Smooth transitions
        random_hues=False,  # Sequential rainbow colors
        signal=FrameSignal.pulse,
    )

    return rainbow


# Example usage in VJ Director:
"""
To use these in your VJ Director, you could modify the __init__ method:

def __init__(self):
    # Choose one of the glitch compositions
    self.canvas = create_glitchy_text_video()
    # or
    # self.canvas = create_retro_pixelated_video()
    # or  
    # self.canvas = create_vhs_aesthetic()
    # or
    # self.canvas = create_digital_corruption()
    # or
    # self.canvas = create_beat_synchronized_colors()
    # or
    # self.canvas = create_rainbow_cycling_video()
    
    # ... rest of initialization
"""
