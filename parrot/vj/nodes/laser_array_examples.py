#!/usr/bin/env python3

"""
Example usage of LaserArray for 3D laser show effects.
Shows how to create different laser configurations for various music genres and effects.
"""

import math
from parrot.vj.nodes.laser_array import LaserArray
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect

from parrot.director.frame import FrameSignal


def create_classic_green_laser_show():
    """
    Create a classic green laser show like in 80s/90s clubs.
    Multiple green lasers scanning in synchronized patterns.
    """
    # 2D background with retro aesthetics
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=0.4, base_brightness=0.6)
    video = ScanlinesEffect(video, scanline_intensity=0.2)

    # Classic green laser array
    lasers = LaserArray(
        laser_count=6,  # Classic setup
        array_radius=1.5,  # Tight formation
        laser_length=25.0,  # Long reach
        laser_width=0.015,  # Very thin, sharp beams
        fan_angle=math.pi / 4,  # 45-degree fan
        scan_speed=1.5,  # Smooth scanning
        strobe_frequency=0.0,  # No strobe for classic look
        laser_intensity=2.5,  # Bright green
        color=(0.0, 1.0, 0.0),  # Classic green
        signal=FrameSignal.freq_all,  # React to all frequencies
    )

    return video, lasers


def create_rave_strobe_lasers():
    """
    Create high-energy rave laser show with fast strobing and color changes.
    """
    # High-energy 2D background
    video = VideoPlayer(fn_group="bg")
    video = BeatHueShift(video, random_hues=True, signal=FrameSignal.pulse)

    # High-energy strobe lasers
    lasers = LaserArray(
        laser_count=12,  # Many lasers for intensity
        array_radius=2.5,  # Wide spread
        laser_length=18.0,  # Medium length for fast movement
        laser_width=0.025,  # Slightly thicker for visibility
        fan_angle=math.pi / 2,  # Wide 90-degree fan
        scan_speed=4.0,  # Very fast scanning
        strobe_frequency=8.0,  # 8 Hz strobe
        laser_intensity=3.0,  # Maximum intensity
        color=(1.0, 0.0, 1.0),  # Magenta/purple
        signal=FrameSignal.freq_high,  # React to treble
    )

    return video, lasers


def create_ambient_laser_ceiling():
    """
    Create slow, atmospheric laser patterns for ambient/chill music.
    Lasers move slowly like a laser ceiling installation.
    """
    # Subtle 2D background
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=0.2, base_brightness=0.8)

    # Gentle ceiling-style lasers
    lasers = LaserArray(
        laser_count=8,  # Moderate count
        array_radius=3.0,  # Wide, ceiling-like spread
        laser_length=30.0,  # Very long for ceiling effect
        laser_width=0.01,  # Ultra-thin for elegance
        fan_angle=math.pi / 6,  # Narrow 30-degree fan
        scan_speed=0.5,  # Very slow movement
        strobe_frequency=0.0,  # No strobe
        laser_intensity=1.5,  # Gentle intensity
        color=(0.0, 0.7, 1.0),  # Cool blue
        signal=FrameSignal.sustained_low,  # React to sustained bass
    )

    return video, lasers


def create_industrial_laser_grid():
    """
    Create harsh, geometric laser patterns for industrial/techno music.
    """
    # Industrial 2D background
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=1.0, base_brightness=0.2)

    text = TextRenderer(
        text="SYSTEM\nONLINE",
        font_size=80,
        text_color=(255, 0, 0),  # Red text
        bg_color=(0, 0, 0),
    )

    canvas_2d = MultiplyCompose(video, text)

    # Sharp, geometric lasers
    lasers = LaserArray(
        laser_count=16,  # Many lasers for grid effect
        array_radius=2.0,  # Tight grid formation
        laser_length=20.0,  # Medium length
        laser_width=0.008,  # Ultra-thin for sharpness
        fan_angle=math.pi / 8,  # Very narrow fan
        scan_speed=2.5,  # Mechanical movement
        strobe_frequency=4.0,  # 4 Hz strobe
        laser_intensity=2.8,  # Very bright
        color=(1.0, 0.1, 0.0),  # Red/orange
        signal=FrameSignal.strobe,  # React to strobe signals
    )

    return canvas_2d, lasers


def create_concert_laser_finale():
    """
    Create epic concert finale with wide-fanning lasers and high intensity.
    """
    # Epic 2D background
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=0.8, base_brightness=0.4)

    text = TextRenderer(
        text="FINALE",
        font_size=200,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
    )
    text = BrightnessPulse(text, signal=FrameSignal.freq_all)

    canvas_2d = MultiplyCompose(video, text)

    # Epic finale lasers
    lasers = LaserArray(
        laser_count=20,  # Maximum laser count
        array_radius=4.0,  # Very wide spread
        laser_length=35.0,  # Maximum reach
        laser_width=0.03,  # Thick for visibility
        fan_angle=math.pi * 0.75,  # Nearly full circle fan
        scan_speed=3.0,  # Dynamic movement
        strobe_frequency=0.0,  # No strobe for finale
        laser_intensity=4.0,  # Maximum intensity
        color=(1.0, 1.0, 0.0),  # Bright yellow/white
        signal=FrameSignal.freq_all,  # React to everything
    )

    return canvas_2d, lasers


def create_rgb_color_cycling_lasers():
    """
    Create lasers that cycle through RGB colors (requires multiple LaserArray instances).
    """
    # Base 2D content
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, signal=FrameSignal.freq_low)

    # Red laser array
    red_lasers = LaserArray(
        laser_count=4,
        array_radius=1.5,
        laser_length=22.0,
        fan_angle=math.pi / 3,
        scan_speed=2.0,
        color=(1.0, 0.0, 0.0),  # Red
        signal=FrameSignal.freq_low,
    )

    # Green laser array (offset position)
    green_lasers = LaserArray(
        laser_count=4,
        array_radius=2.0,
        laser_length=22.0,
        fan_angle=math.pi / 3,
        scan_speed=2.2,  # Slightly different speed
        color=(0.0, 1.0, 0.0),  # Green
        signal=FrameSignal.freq_all,
    )

    # Blue laser array (different position)
    blue_lasers = LaserArray(
        laser_count=4,
        array_radius=2.5,
        laser_length=22.0,
        fan_angle=math.pi / 3,
        scan_speed=1.8,  # Different speed
        color=(0.0, 0.0, 1.0),  # Blue
        signal=FrameSignal.freq_high,
    )

    return video, red_lasers, green_lasers, blue_lasers


def create_scanning_laser_tunnel():
    """
    Create a laser tunnel effect with synchronized scanning patterns.
    """
    # Dark background for tunnel effect
    video = VideoPlayer(fn_group="bg")
    video = BrightnessPulse(video, intensity=0.1, base_brightness=0.9)

    # Tunnel laser array
    lasers = LaserArray(
        laser_count=24,  # Many lasers for tunnel effect
        array_radius=1.0,  # Tight circle
        laser_length=40.0,  # Very long for tunnel depth
        laser_width=0.012,  # Thin for tunnel lines
        fan_angle=math.pi / 12,  # Very narrow fan
        scan_speed=1.0,  # Synchronized movement
        strobe_frequency=0.0,  # Solid beams
        laser_intensity=2.0,  # Moderate intensity
        color=(0.0, 1.0, 0.5),  # Cyan-green
        signal=FrameSignal.freq_all,
    )

    return video, lasers


# Dynamic laser control examples
def demonstrate_dynamic_laser_control():
    """
    Show how to dynamically control laser parameters during performance.
    """
    lasers = LaserArray(
        laser_count=8,
        color=(0.0, 1.0, 0.0),
        signal=FrameSignal.freq_high,
    )

    # Example of dynamic control during performance:
    def update_lasers_based_on_music(signal_strength):
        """Update laser parameters based on music intensity"""
        if signal_strength > 0.8:
            # High energy: fan out and strobe
            lasers.fan_out_beams()
            lasers.set_strobe_frequency(12.0)
            lasers.set_fan_angle(math.pi / 2)
        elif signal_strength > 0.5:
            # Medium energy: moderate fan
            lasers.set_strobe_frequency(4.0)
            lasers.set_fan_angle(math.pi / 4)
        else:
            # Low energy: narrow beams, no strobe
            lasers.narrow_beams()
            lasers.set_strobe_frequency(0.0)
            lasers.set_fan_angle(math.pi / 8)

    return lasers, update_lasers_based_on_music


# Integration examples
def integrate_with_vj_director():
    """
    Example of integrating LaserArray with VJ Director.
    """
    # This would be integrated into the VJ Director class:
    """
    class VJDirector:
        def __init__(self):
            # 2D canvas content
            self.canvas_2d = create_2d_content()
            
            # 3D laser arrays
            self.main_lasers = LaserArray(
                laser_count=8,
                color=(0.0, 1.0, 0.0),
                signal=FrameSignal.freq_high
            )
            
            self.accent_lasers = LaserArray(
                laser_count=4,
                array_radius=3.0,
                color=(1.0, 0.0, 1.0),
                signal=FrameSignal.pulse
            )
        
        def render(self, context, frame, scheme):
            # Render 2D content first
            canvas_result = self.canvas_2d.render(frame, scheme, context)
            
            # Render laser arrays on top
            main_result = self.main_lasers.render(frame, scheme, context)
            accent_result = self.accent_lasers.render(frame, scheme, context)
            
            # Composite all layers together
            return composite_3d_layers(canvas_result, main_result, accent_result)
    """
    pass


# Genre-specific configurations
def get_laser_setup_for_genre(genre: str):
    """Get appropriate laser setup for different music genres"""
    setups = {
        "classic": create_classic_green_laser_show,
        "rave": create_rave_strobe_lasers,
        "ambient": create_ambient_laser_ceiling,
        "industrial": create_industrial_laser_grid,
        "concert": create_concert_laser_finale,
        "tunnel": create_scanning_laser_tunnel,
    }

    return setups.get(genre, create_classic_green_laser_show)()


# Performance optimization tips
"""
LASER ARRAY PERFORMANCE TIPS:

1. Laser Count:
   - 4-8 lasers: Good for most applications
   - 12-16 lasers: High-energy shows, requires more GPU
   - 20+ lasers: Epic effects, high-end hardware only

2. Scan Speed:
   - 0.5-1.0: Slow, atmospheric
   - 1.5-2.5: Normal club/concert speed
   - 3.0+: High-energy rave speed

3. Strobe Frequency:
   - 0 Hz: No strobe (smooth beams)
   - 2-4 Hz: Subtle strobe effect
   - 8-12 Hz: High-energy strobe
   - 15+ Hz: Epilepsy warning territory

4. Fan Angle:
   - π/12 (15°): Narrow, focused beams
   - π/6 (30°): Moderate spread
   - π/4 (45°): Wide fan
   - π/2 (90°): Very wide spread

5. Laser Width:
   - 0.008-0.015: Ultra-thin, sharp
   - 0.02-0.03: Standard visibility
   - 0.04+: Thick, more visible but less laser-like

6. Colors:
   - Green (0,1,0): Classic, most visible
   - Red (1,0,0): Warm, aggressive
   - Blue (0,0,1): Cool, futuristic
   - Cyan (0,1,1): Modern, bright
   - Magenta (1,0,1): Rave, high-energy
   - Yellow (1,1,0): Finale, maximum impact
"""

# Usage examples for testing
if __name__ == "__main__":
    # Test different laser configurations
    print("🔴 Creating classic green laser show...")
    video1, lasers1 = create_classic_green_laser_show()
    print(f"  - {lasers1.laser_count} green lasers")
    print(f"  - Fan angle: {math.degrees(lasers1.fan_angle):.1f}°")

    print("\n🟣 Creating rave strobe lasers...")
    video2, lasers2 = create_rave_strobe_lasers()
    print(f"  - {lasers2.laser_count} magenta lasers")
    print(f"  - Strobe: {lasers2.strobe_frequency} Hz")

    print("\n🔵 Creating ambient laser ceiling...")
    video3, lasers3 = create_ambient_laser_ceiling()
    print(f"  - {lasers3.laser_count} blue lasers")
    print(f"  - Scan speed: {lasers3.scan_speed}")

    print("\n🟠 Creating industrial laser grid...")
    video4, lasers4 = create_industrial_laser_grid()
    print(f"  - {lasers4.laser_count} red lasers")
    print(f"  - Array radius: {lasers4.array_radius}m")

    print("\n🟡 Creating concert finale...")
    video5, lasers5 = create_concert_laser_finale()
    print(f"  - {lasers5.laser_count} yellow lasers")
    print(f"  - Intensity: {lasers5.laser_intensity}")

    print("\n✅ All laser configurations created successfully!")
    print("Ready to light up the dance floor! 🎛️✨🔥")
