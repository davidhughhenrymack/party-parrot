#!/usr/bin/env python3
"""Integration tests for strobe max behavior with actual interpreter patterns"""

import unittest
from unittest.mock import MagicMock
from parrot.fixtures.led_par import ParRGB
from parrot.fixtures.base import FixtureGroup
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestStrobeIntegrationWithInterpreters(unittest.TestCase):
    """Test strobe max behavior with actual interpreter step() patterns"""

    def setUp(self):
        self.fixture = ParRGB(patch=1)
        self.frame = Frame(
            {
                FrameSignal.freq_all: 0.8,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_low: 0.8,
                FrameSignal.sustained_low: 0.1,
                FrameSignal.sustained_high: 0.8,
                FrameSignal.dampen: 0.0,
                FrameSignal.strobe: 0.9,  # High strobe signal
                FrameSignal.pulse: 0.5,
            },
            {},
        )
        self.scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

    def test_multiple_set_strobe_calls_in_sequence(self):
        """Simulate multiple interpreters calling set_strobe in sequence"""
        # Simulate director.step() calling begin() first
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0
        assert self.fixture.values[4] == 0
        
        # Simulate interpreter 1: sets strobe to 50
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        
        # Simulate interpreter 2: sets strobe to 30 (lower, should be ignored)
        self.fixture.set_strobe(30)
        assert self.fixture.get_strobe() == 50
        
        # Simulate interpreter 3: sets strobe to 200 (higher, should take precedence)
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        # Simulate interpreter 4: sets strobe to 100 (lower, should be ignored)
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 200
        
        # Final DMX value should reflect the max
        assert self.fixture.values[4] == 200

    def test_fixture_group_with_multiple_strobe_calls(self):
        """Test that fixture groups properly accumulate strobe values"""
        fixture1 = ParRGB(patch=1)
        fixture2 = ParRGB(patch=10)
        group = FixtureGroup([fixture1, fixture2])
        
        # Begin frame
        group.begin()
        assert fixture1.get_strobe() == 0
        assert fixture2.get_strobe() == 0
        
        # Set strobe on group
        group.set_strobe(50)
        assert fixture1.get_strobe() == 50
        assert fixture2.get_strobe() == 50
        
        # Set higher strobe on group
        group.set_strobe(200)
        assert fixture1.get_strobe() == 200
        assert fixture2.get_strobe() == 200
        
        # Set lower strobe on group - should not override
        group.set_strobe(100)
        assert fixture1.get_strobe() == 200
        assert fixture2.get_strobe() == 200
        
        # Verify DMX values
        assert fixture1.values[4] == 200
        assert fixture2.values[4] == 200

    def test_reset_and_accumulate_cycle(self):
        """Test that begin() properly resets for next frame"""
        # Frame 1
        self.fixture.begin()
        self.fixture.set_strobe(100)
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        # Frame 2 - should reset and start fresh
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0
        
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 150


if __name__ == "__main__":
    unittest.main()

