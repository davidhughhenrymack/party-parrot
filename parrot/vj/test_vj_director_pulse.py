#!/usr/bin/env python3

import pytest
from unittest.mock import Mock

from parrot.vj.vj_director import VJDirector
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.layer_compose import LayerCompose
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


class TestVJDirectorPulse:
    """Test the VJDirector with brightness pulse integration"""

    def test_default_canvas_has_pulse_effect(self):
        """Test that the default canvas includes brightness pulse"""
        director = VJDirector()

        # The canvas should be a BrightnessPulse directly (LayerCompose temporarily disabled due to size mismatch)
        assert isinstance(director.canvas, BrightnessPulse)

        # Check default parameters
        assert director.canvas.intensity == 0.7
        assert director.canvas.base_brightness == 0.6

    def test_create_pulsing_canvas(self):
        """Test creating custom pulsing canvas"""
        director = VJDirector()

        # Create custom pulsing canvas
        canvas = director.create_pulsing_canvas(intensity=0.5, base_brightness=0.7)

        # Should return BrightnessPulse directly (LayerCompose temporarily disabled)
        assert isinstance(canvas, BrightnessPulse)
        assert canvas.intensity == 0.5
        assert canvas.base_brightness == 0.7

    def test_set_pulse_intensity(self):
        """Test changing pulse intensity"""
        director = VJDirector()

        # Change pulse intensity without context
        director.set_pulse_intensity(intensity=1.2, base_brightness=0.1)

        # Verify the new canvas has updated parameters
        assert isinstance(director.canvas, BrightnessPulse)
        assert director.canvas.intensity == 1.2
        assert director.canvas.base_brightness == 0.1

    def test_set_subtle_pulse(self):
        """Test switching to subtle pulse"""
        director = VJDirector()

        director.set_subtle_pulse()

        assert isinstance(director.canvas, BrightnessPulse)
        assert director.canvas.intensity == 0.4
        assert director.canvas.base_brightness == 0.6

    def test_set_dramatic_pulse(self):
        """Test switching to dramatic pulse"""
        director = VJDirector()

        director.set_dramatic_pulse()

        assert isinstance(director.canvas, BrightnessPulse)
        assert director.canvas.intensity == 1.2
        assert director.canvas.base_brightness == 0.2

    def test_set_static_video(self):
        """Test switching to static video without pulse"""
        director = VJDirector()

        # Initially should have pulse
        assert isinstance(director.canvas, BrightnessPulse)

        # Switch to static
        director.set_static_video()

        # Should no longer have pulse effect, just VideoPlayer
        from parrot.vj.nodes.video_player import VideoPlayer

        assert isinstance(director.canvas, VideoPlayer)

    def test_shift_functionality(self):
        """Test that shift functionality works with pulse canvas"""
        director = VJDirector()

        # Shift should work without GL context
        director.shift(Mode.rave, threshold=0.5)

        # Canvas should still be BrightnessPulse
        assert isinstance(director.canvas, BrightnessPulse)

    def test_canvas_switching_without_context(self):
        """Test switching canvas configurations without GL context"""
        director = VJDirector()

        # Switch to different pulse settings without context
        director.set_dramatic_pulse()

        # Verify the change took effect
        assert isinstance(director.canvas, BrightnessPulse)
        assert director.canvas.intensity == 1.2
        assert director.canvas.base_brightness == 0.2
