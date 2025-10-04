#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.vj.nodes.stage_blinders import StageBlinders
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


def test_stage_blinders_render():
    """Test that stage blinders can be rendered without errors"""
    ctx = mgl.create_standalone_context()
    
    # Create stage blinders effect
    blinders = StageBlinders(width=800, height=600, num_blinders=8)
    blinders.enter(ctx)
    blinders.generate(Vibe(mode=Mode.rave))
    
    # Create test frame with big blinder signal active
    frame = Frame({
        FrameSignal.big_blinder: 1.0,
        FrameSignal.small_blinder: 0.0,
    })
    
    # Create test color scheme
    scheme = ColorScheme(
        fg=Color("#FFFFFF"),
        bg=Color("#000000"),
        bg_contrast=Color("#FF0000"),
    )
    
    # Render
    result = blinders.render(frame, scheme, ctx)
    
    # Verify result
    assert result is not None
    # Note: framebuffer defaults to 1920x1080 from canvas_effect_base
    assert result.width == 1920
    assert result.height == 1080
    
    # Clean up
    blinders.exit()
    ctx.release()


def test_stage_blinders_big_and_small():
    """Test that both big and small blinders can be rendered together"""
    ctx = mgl.create_standalone_context()
    
    # Create stage blinders effect
    blinders = StageBlinders(width=800, height=600, num_blinders=8)
    blinders.enter(ctx)
    blinders.generate(Vibe(mode=Mode.rave))
    
    # Create test frame with both signals active
    frame = Frame({
        FrameSignal.big_blinder: 1.0,
        FrameSignal.small_blinder: 1.0,
    })
    
    # Create test color scheme
    scheme = ColorScheme(
        fg=Color("#FFFFFF"),
        bg=Color("#000000"),
        bg_contrast=Color("#FF0000"),
    )
    
    # Render
    result = blinders.render(frame, scheme, ctx)
    
    # Verify result
    assert result is not None
    
    # Clean up
    blinders.exit()
    ctx.release()


def test_stage_blinders_attack_decay():
    """Test that attack and decay work properly"""
    import time
    
    ctx = mgl.create_standalone_context()
    
    # Create stage blinders effect with specific attack/decay times
    blinders = StageBlinders(
        width=800, 
        height=600, 
        num_blinders=8,
        attack_time=0.2,  # Longer for more reliable testing
        decay_time=0.4
    )
    blinders.enter(ctx)
    # Don't call generate() here since it would override our custom attack/decay times
    
    # Create test frame with signal off
    frame = Frame({
        FrameSignal.big_blinder: 0.0,
        FrameSignal.small_blinder: 0.0,
    })
    
    scheme = ColorScheme(
        fg=Color("#FFFFFF"),
        bg=Color("#000000"),
        bg_contrast=Color("#FF0000"),
    )
    
    # Initial render - should be at 0
    blinders.render(frame, scheme, ctx)
    assert blinders.big_blinder_level == 0.0
    
    # Turn on signal
    frame_on = Frame({
        FrameSignal.big_blinder: 1.0,
        FrameSignal.small_blinder: 0.0,
    })
    
    # Render a few times to allow attack to happen
    time.sleep(0.1)  # Wait half the attack time
    blinders.render(frame_on, scheme, ctx)
    level_during_attack = blinders.big_blinder_level
    
    # Should be between 0 and 1 during attack
    assert 0.0 < level_during_attack < 1.0
    
    # Wait for full attack to complete
    time.sleep(0.15)
    blinders.render(frame_on, scheme, ctx)
    assert blinders.big_blinder_level >= 0.9  # Should be near 1.0
    
    # Turn off signal
    frame_off = Frame({
        FrameSignal.big_blinder: 0.0,
        FrameSignal.small_blinder: 0.0,
    })
    
    # Render to start decay
    time.sleep(0.15)  # Wait a bit for decay
    blinders.render(frame_off, scheme, ctx)
    level_during_decay = blinders.big_blinder_level
    
    # Should be decaying (between 0 and the level after attack)
    assert 0.0 < level_during_decay < 0.9
    
    # Clean up
    blinders.exit()
    ctx.release()


if __name__ == "__main__":
    test_stage_blinders_render()
    test_stage_blinders_big_and_small()
    test_stage_blinders_attack_decay()
    print("All tests passed!")

