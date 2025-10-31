#!/usr/bin/env python3
"""Comprehensive tests for strobe max behavior across all fixture types"""

import unittest
from unittest.mock import MagicMock
from parrot.fixtures.base import FixtureBase, FixtureGroup, FixtureWithBulbs
from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.laser import Laser
from parrot.utils.dmx_utils import Universe


class TestStrobeMaxBehaviorBase(unittest.TestCase):
    """Test max strobe behavior on base fixture"""

    def setUp(self):
        self.fixture = FixtureBase(address=1, name="test", width=3)

    def test_begin_resets_strobe(self):
        """Test that begin() resets strobe to 0"""
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0

    def test_max_behavior_single_fixture(self):
        """Test max behavior with multiple set_strobe calls"""
        self.fixture.begin()
        
        # Lower value first
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        
        # Higher value takes precedence
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        # Lower value doesn't override
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 200
        
        # Reset works
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0


class TestStrobeMaxBehaviorParRGB(unittest.TestCase):
    """Test max strobe behavior on ParRGB fixture"""

    def setUp(self):
        self.fixture = ParRGB(patch=1)

    def test_max_behavior_with_dmx_values(self):
        """Test that max behavior works and DMX values use accumulated strobe_value"""
        self.fixture.begin()
        
        # Set lower value
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        assert self.fixture.values[4] == 100
        
        # Set higher value - should update both strobe_value and DMX
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        assert self.fixture.values[4] == 200
        
        # Set lower value - should not change strobe_value or DMX
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 200
        assert self.fixture.values[4] == 200


class TestStrobeMaxBehaviorParRGBAWU(unittest.TestCase):
    """Test max strobe behavior on ParRGBAWU fixture"""

    def setUp(self):
        self.fixture = ParRGBAWU(patch=1)

    def test_max_behavior_with_dmx_values(self):
        """Test that max behavior works and DMX values use accumulated strobe_value"""
        self.fixture.begin()
        
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        assert self.fixture.values[7] == 100
        
        self.fixture.set_strobe(250)
        assert self.fixture.get_strobe() == 250
        assert self.fixture.values[7] == 250
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 250
        assert self.fixture.values[7] == 250


class TestStrobeMaxBehaviorChauvetParRGBAWU(unittest.TestCase):
    """Test max strobe behavior on ChauvetParRGBAWU fixture"""

    def setUp(self):
        self.fixture = ChauvetParRGBAWU(address=1)

    def test_max_behavior_with_clamp(self):
        """Test that max behavior works with clamped values"""
        self.fixture.begin()
        
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        assert self.fixture.values[6] == 100
        
        self.fixture.set_strobe(300)  # Above clamp limit of 250
        assert self.fixture.get_strobe() == 300
        assert self.fixture.values[6] == 250  # Clamped to 250
        
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 300
        assert self.fixture.values[6] == 250


class TestStrobeMaxBehaviorChauvetDerby(unittest.TestCase):
    """Test max strobe behavior on ChauvetDerby fixture"""

    def setUp(self):
        self.fixture = ChauvetDerby(address=1)

    def test_max_behavior(self):
        """Test that max behavior works correctly"""
        self.fixture.begin()
        
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        assert self.fixture.values[4] == 50
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        assert self.fixture.values[4] == 200


class TestStrobeMaxBehaviorChauvetRotosphere(unittest.TestCase):
    """Test max strobe behavior on ChauvetRotosphere fixture"""

    def setUp(self):
        self.fixture = ChauvetRotosphere_28Ch(address=1)

    def test_max_behavior(self):
        """Test that max behavior works correctly"""
        self.fixture.begin()
        
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        assert self.fixture.values[24] == 50
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        assert self.fixture.values[24] == 200


class TestStrobeMaxBehaviorFixtureGroup(unittest.TestCase):
    """Test max strobe behavior on FixtureGroup"""

    def setUp(self):
        self.fixture1 = FixtureBase(address=1, name="test1", width=3)
        self.fixture2 = FixtureBase(address=4, name="test2", width=3)
        self.group = FixtureGroup([self.fixture1, self.fixture2])

    def test_begin_propagates_to_all_fixtures(self):
        """Test that begin() resets strobe on all fixtures in group"""
        self.fixture1.set_strobe(100)
        self.fixture2.set_strobe(200)
        
        self.group.begin()
        
        assert self.fixture1.get_strobe() == 0
        assert self.fixture2.get_strobe() == 0

    def test_max_behavior_propagates_to_all_fixtures(self):
        """Test that set_strobe() on group accumulates on all fixtures"""
        self.group.begin()
        
        # Set lower value on group
        self.group.set_strobe(50)
        assert self.fixture1.get_strobe() == 50
        assert self.fixture2.get_strobe() == 50
        
        # Set higher value - should accumulate on all
        self.group.set_strobe(200)
        assert self.fixture1.get_strobe() == 200
        assert self.fixture2.get_strobe() == 200
        
        # Set lower value - should not override
        self.group.set_strobe(100)
        assert self.fixture1.get_strobe() == 200
        assert self.fixture2.get_strobe() == 200


class TestStrobeMaxBehaviorFixtureWithBulbs(unittest.TestCase):
    """Test max strobe behavior on FixtureWithBulbs"""

    def setUp(self):
        bulb1 = FixtureBase(address=1, name="bulb1", width=3)
        bulb2 = FixtureBase(address=4, name="bulb2", width=3)
        self.fixture = FixtureWithBulbs(
            address=1, name="test", width=10, bulbs=[bulb1, bulb2]
        )

    def test_begin_propagates_to_bulbs(self):
        """Test that begin() resets strobe on fixture and bulbs"""
        self.fixture.set_strobe(100)
        self.fixture.bulbs[0].set_strobe(50)
        self.fixture.bulbs[1].set_strobe(200)
        
        self.fixture.begin()
        
        assert self.fixture.get_strobe() == 0
        assert self.fixture.bulbs[0].get_strobe() == 0
        assert self.fixture.bulbs[1].get_strobe() == 0


class TestStrobeMaxBehaviorMovingHead(unittest.TestCase):
    """Test max strobe behavior on MovingHead"""

    def setUp(self):
        from parrot.fixtures.base import GoboWheelEntry
        gobo_wheel = [GoboWheelEntry("open", 0)]
        self.fixture = MovingHead(
            address=1, name="moving head", width=12, gobo_wheel=gobo_wheel
        )

    def test_max_behavior(self):
        """Test that max behavior works on MovingHead"""
        self.fixture.begin()
        
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 200


class TestStrobeMaxBehaviorLaser(unittest.TestCase):
    """Test max strobe behavior on Laser fixture"""

    def setUp(self):
        self.fixture = Laser(address=1, name="laser", width=1)

    def test_max_behavior(self):
        """Test that max behavior works on Laser"""
        self.fixture.begin()
        
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200


class TestStrobeMaxBehaviorMotionstrip(unittest.TestCase):
    """Test max strobe behavior on Motionstrip fixture"""

    def setUp(self):
        self.fixture = Motionstrip38(patch=1)

    def test_max_behavior(self):
        """Test that max behavior works on Motionstrip"""
        self.fixture.begin()
        
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 200


class TestStrobeMaxBehaviorMultipleInterpreters(unittest.TestCase):
    """Test max strobe behavior when multiple interpreters call set_strobe"""

    def setUp(self):
        self.fixture = ParRGB(patch=1)

    def test_simulate_multiple_interpreters(self):
        """Simulate multiple interpreters calling set_strobe() in sequence"""
        # Begin frame
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0
        
        # Simulate interpreter 1 calling set_strobe
        self.fixture.set_strobe(50)
        assert self.fixture.get_strobe() == 50
        
        # Simulate interpreter 2 calling set_strobe (lower value)
        self.fixture.set_strobe(30)
        assert self.fixture.get_strobe() == 50  # Should keep 50
        
        # Simulate interpreter 3 calling set_strobe (higher value)
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200  # Should take 200
        
        # Simulate interpreter 4 calling set_strobe (lower value)
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 200  # Should keep 200
        
        # Final DMX value should be the max
        assert self.fixture.values[4] == 200


if __name__ == "__main__":
    unittest.main()

