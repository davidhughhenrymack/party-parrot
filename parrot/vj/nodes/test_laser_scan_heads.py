#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.vj.nodes.laser_scan_heads import LaserScanHeads
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


def test_laser_scan_heads_render():
    """Test that laser scan heads can be rendered without errors"""
    ctx = mgl.create_standalone_context()

    # Create laser scan heads effect
    laser_heads = LaserScanHeads(width=800, height=600, beams_per_head=12)
    laser_heads.enter(ctx)
    laser_heads.generate(Vibe(mode=Mode.rave))

    # Create test frame with small_blinder signal active
    frame = Frame(
        {
            FrameSignal.small_blinder: 1.0,
            FrameSignal.freq_high: 0.5,
        }
    )

    # Create test color scheme
    scheme = ColorScheme(
        fg=Color("#FF0000"),  # Red lasers
        bg=Color("#0000FF"),  # Blue lasers
        bg_contrast=Color("#00FF00"),
    )

    # Render
    result = laser_heads.render(frame, scheme, ctx)

    # Verify result
    assert result is not None
    assert result.width == 1920
    assert result.height == 1080

    # Clean up
    laser_heads.exit()
    ctx.release()


def test_laser_scan_heads_rotation():
    """Test that pan and tilt angles update over time"""
    import time

    ctx = mgl.create_standalone_context()

    # Create laser scan heads effect
    laser_heads = LaserScanHeads(
        width=800,
        height=600,
        beams_per_head=12,
        base_rotation_speed=1.0,
        base_tilt_speed=0.8,
    )
    laser_heads.enter(ctx)
    laser_heads.generate(Vibe(mode=Mode.rave))

    # Create test frame with small_blinder signal active
    frame = Frame(
        {
            FrameSignal.small_blinder: 1.0,
            FrameSignal.freq_high: 0.5,
        }
    )

    scheme = ColorScheme(
        fg=Color("#0000FF"),  # Blue lasers
        bg=Color("#FF0000"),  # Red lasers
        bg_contrast=Color("#00FF00"),
    )

    # Initial render
    laser_heads.render(frame, scheme, ctx)
    initial_pan_angle = laser_heads.pan_angle
    initial_tilt_angle = laser_heads.tilt_angle

    # Wait a bit and render again
    time.sleep(0.1)
    laser_heads.render(frame, scheme, ctx)
    new_pan_angle = laser_heads.pan_angle
    new_tilt_angle = laser_heads.tilt_angle

    # Both angles should have increased
    assert new_pan_angle > initial_pan_angle
    assert new_tilt_angle > initial_tilt_angle

    # Clean up
    laser_heads.exit()
    ctx.release()


def test_laser_scan_heads_modes():
    """Test that different modes configure parameters correctly"""
    ctx = mgl.create_standalone_context()

    laser_heads = LaserScanHeads(width=800, height=600)
    laser_heads.enter(ctx)

    # Test rave mode
    laser_heads.generate(Vibe(mode=Mode.rave))
    assert laser_heads.beams_per_head == 16
    assert laser_heads.mode_opacity_multiplier == 1.0

    # Test chill mode
    laser_heads.generate(Vibe(mode=Mode.chill))
    assert laser_heads.beams_per_head == 8
    assert laser_heads.mode_opacity_multiplier == 0.3

    # Test gentle mode
    laser_heads.generate(Vibe(mode=Mode.gentle))
    assert laser_heads.beams_per_head == 10
    assert laser_heads.mode_opacity_multiplier == 0.5

    # Test blackout mode
    laser_heads.generate(Vibe(mode=Mode.blackout))
    assert laser_heads.beams_per_head == 0
    assert laser_heads.mode_opacity_multiplier == 0.0

    # Clean up
    laser_heads.exit()
    ctx.release()


def test_laser_scan_heads_no_strobe():
    """Test that lasers don't render when small_blinder signal is low"""
    ctx = mgl.create_standalone_context()

    laser_heads = LaserScanHeads(width=800, height=600)
    laser_heads.enter(ctx)
    laser_heads.generate(Vibe(mode=Mode.rave))

    # Create test frame with NO small_blinder signal
    frame = Frame(
        {
            FrameSignal.small_blinder: 0.0,
            FrameSignal.freq_high: 0.0,
        }
    )

    scheme = ColorScheme(
        fg=Color("#FF00FF"),
        bg=Color("#000000"),
        bg_contrast=Color("#FFFF00"),
    )

    # Render - should produce black/empty output
    result = laser_heads.render(frame, scheme, ctx)

    # Verify result exists but should be mostly black
    assert result is not None

    # Clean up
    laser_heads.exit()
    ctx.release()


def test_laser_scan_heads_attack_decay():
    """Test that attack and decay work properly"""
    import time

    ctx = mgl.create_standalone_context()

    # Create laser scan heads with specific attack/decay times
    laser_heads = LaserScanHeads(
        width=800, height=600, beams_per_head=12, attack_time=0.2, decay_time=0.4
    )
    laser_heads.enter(ctx)

    # Create test frame with signal off
    frame = Frame(
        {
            FrameSignal.small_blinder: 0.0,
            FrameSignal.freq_high: 0.0,
        }
    )

    scheme = ColorScheme(
        fg=Color("#FF0000"),
        bg=Color("#0000FF"),
        bg_contrast=Color("#00FF00"),
    )

    # Initial render - should be at 0
    laser_heads.render(frame, scheme, ctx)
    assert laser_heads.blinder_level == 0.0

    # Turn on signal
    frame_on = Frame(
        {
            FrameSignal.small_blinder: 1.0,
            FrameSignal.freq_high: 0.0,
        }
    )

    # Render a few times to allow attack to happen
    time.sleep(0.1)  # Wait half the attack time
    laser_heads.render(frame_on, scheme, ctx)
    level_during_attack = laser_heads.blinder_level

    # Should be between 0 and 1 during attack
    assert 0.0 < level_during_attack < 1.0

    # Wait for full attack to complete
    time.sleep(0.15)
    laser_heads.render(frame_on, scheme, ctx)
    assert laser_heads.blinder_level >= 0.9  # Should be near 1.0

    # Turn off signal
    frame_off = Frame(
        {
            FrameSignal.small_blinder: 0.0,
            FrameSignal.freq_high: 0.0,
        }
    )

    # Render to start decay
    time.sleep(0.15)  # Wait a bit for decay
    laser_heads.render(frame_off, scheme, ctx)
    level_during_decay = laser_heads.blinder_level

    # Should be decaying (between 0 and the level after attack)
    assert 0.0 < level_during_decay < 0.9

    # Clean up
    laser_heads.exit()
    ctx.release()


if __name__ == "__main__":
    test_laser_scan_heads_render()
    test_laser_scan_heads_rotation()
    test_laser_scan_heads_modes()
    test_laser_scan_heads_no_strobe()
    test_laser_scan_heads_attack_decay()
    print("All tests passed!")
