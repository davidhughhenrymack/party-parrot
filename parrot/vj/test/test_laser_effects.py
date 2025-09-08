import pytest
import math
import numpy as np
from parrot.vj.interpreters.laser_effects import (
    ConcertLasers,
    LaserScan,
    LaserMatrix,
    LaserChase,
    LaserBurst,
    LaserSpiral,
)
from parrot.vj.layers.laser import LaserLayer, LaserHaze, LaserBeamRenderer
from parrot.vj.base import SolidLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


class TestConcertLasers:
    """Test concert-style laser effects"""

    def test_concert_lasers_creation(self):
        """Test ConcertLasers creation"""
        layers = [SolidLayer("test", width=400, height=300)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=8, fan_angle=120.0)

        assert interpreter.num_lasers == 8
        assert len(interpreter.lasers) == 8
        assert (
            abs(math.degrees(interpreter.fan_angle) - 120.0) < 0.01
        )  # Allow for floating point precision
        assert interpreter.origin_x == 0.5
        assert interpreter.origin_y == 0.9

    def test_laser_initialization(self):
        """Test laser beam initialization"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=4)

        # Check laser properties
        for laser in interpreter.lasers:
            assert "id" in laser
            assert "base_angle" in laser
            assert "current_angle" in laser
            assert "intensity" in laser
            assert "color" in laser
            assert "length" in laser
            assert "enabled" in laser

            # Angles should be distributed across fan
            assert -math.pi <= laser["base_angle"] <= math.pi

    def test_laser_audio_response(self):
        """Test laser response to audio signals"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=6)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Test with different audio levels
        frames = [
            Frame(
                {  # Low energy
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_high: 0.1,
                    FrameSignal.freq_all: 0.15,
                    FrameSignal.sustained_low: 0.3,
                }
            ),
            Frame(
                {  # High energy
                    FrameSignal.freq_low: 0.9,
                    FrameSignal.freq_high: 0.8,
                    FrameSignal.freq_all: 0.85,
                    FrameSignal.sustained_low: 0.9,
                }
            ),
        ]

        intensities_low = []
        intensities_high = []

        # Low energy
        interpreter.step(frames[0], scheme)
        intensities_low = [laser["intensity"] for laser in interpreter.lasers]

        # High energy
        interpreter.step(frames[1], scheme)
        intensities_high = [laser["intensity"] for laser in interpreter.lasers]

        # High energy should generally produce higher intensities
        avg_low = sum(intensities_low) / len(intensities_low)
        avg_high = sum(intensities_high) / len(intensities_high)

        assert avg_high > avg_low

    def test_laser_endpoints(self):
        """Test laser endpoint calculations"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=3)

        endpoints = interpreter.calculate_laser_endpoints()

        # Should have endpoints for enabled lasers
        assert len(endpoints) <= 3  # Some might be disabled

        for start, end in endpoints:
            start_x, start_y = start
            end_x, end_y = end

            # Coordinates should be in 0-1 range
            assert 0.0 <= start_x <= 1.0
            assert 0.0 <= start_y <= 1.0
            assert 0.0 <= end_x <= 1.0
            assert 0.0 <= end_y <= 1.0

    def test_laser_info(self):
        """Test laser info retrieval"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=4)

        laser_info = interpreter.get_laser_info()

        # Should return enabled lasers only
        assert len(laser_info) <= 4

        for laser in laser_info:
            assert laser["enabled"] == True


class TestLaserScan:
    """Test scanning laser effects"""

    def test_laser_scan_creation(self):
        """Test LaserScan creation"""
        layers = [SolidLayer("test", width=300, height=200)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = LaserScan(layers, args, num_beams=4, scan_speed=0.05)

        assert interpreter.num_beams == 4
        assert interpreter.scan_speed == 0.05
        assert len(interpreter.beams) == 4
        assert interpreter.scan_direction == 1  # Start scanning right

    def test_scan_movement(self):
        """Test scanning movement"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = LaserScan(layers, args, num_beams=2, scan_speed=0.1)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        initial_phase = interpreter.scan_phase

        # Multiple steps should advance scan
        frame = Frame({FrameSignal.freq_high: 0.6, FrameSignal.freq_all: 0.5})

        for _ in range(5):
            interpreter.step(frame, scheme)

        # Phase should have advanced
        assert interpreter.scan_phase != initial_phase

    def test_scan_direction_reversal(self):
        """Test scan direction reversal at limits"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = LaserScan(layers, args, scan_speed=0.5)  # Fast for testing
        scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

        frame = Frame({FrameSignal.freq_high: 0.8, FrameSignal.freq_all: 0.7})

        # Scan to one limit
        for _ in range(20):
            interpreter.step(frame, scheme)
            if interpreter.scan_direction == -1:  # Direction reversed
                break

        # Should have reversed direction
        assert interpreter.scan_direction == -1


class TestLaserMatrix:
    """Test laser matrix effects"""

    def test_laser_matrix_creation(self):
        """Test LaserMatrix creation"""
        layers = [SolidLayer("test", width=400, height=300)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = LaserMatrix(layers, args, grid_size=(6, 4))

        assert interpreter.grid_width == 6
        assert interpreter.grid_height == 4
        assert len(interpreter.laser_grid) == 4  # Rows
        assert len(interpreter.laser_grid[0]) == 6  # Columns

    def test_matrix_wave_patterns(self):
        """Test matrix wave pattern generation"""
        layers = [SolidLayer("test", width=300, height=200)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = LaserMatrix(layers, args, grid_size=(4, 3))
        scheme = ColorScheme(Color("cyan"), Color("magenta"), Color("yellow"))

        frame = Frame(
            {
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_high: 0.6,
                FrameSignal.freq_all: 0.65,
            }
        )

        # Multiple steps should create wave patterns
        for _ in range(10):
            interpreter.step(frame, scheme)

        # Check that lasers have different intensities (wave effect)
        intensities = [
            laser["intensity"] for row in interpreter.laser_grid for laser in row
        ]

        # Should have variation in intensities
        assert len(set(intensities)) > 1
        assert min(intensities) >= 0.0
        assert max(intensities) <= 1.0

    def test_matrix_info(self):
        """Test matrix info retrieval"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = LaserMatrix(layers, args, grid_size=(3, 2))

        matrix_info = interpreter.get_matrix_info()

        assert "grid" in matrix_info
        assert "grid_size" in matrix_info
        assert "pulse_phase" in matrix_info
        assert matrix_info["grid_size"] == (3, 2)


class TestLaserChase:
    """Test chasing laser effects"""

    def test_laser_chase_creation(self):
        """Test LaserChase creation"""
        layers = [SolidLayer("test", width=300, height=200)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = LaserChase(layers, args, num_chasers=6, trail_length=3)

        assert interpreter.num_chasers == 6
        assert interpreter.trail_length == 3
        assert len(interpreter.chasers) == 6

    def test_chase_beat_response(self):
        """Test chase response to beats"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = LaserChase(layers, args, chase_speed=0.1)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        initial_phase = interpreter.chase_phase

        # Beat trigger should accelerate chase
        frame_beat = Frame(
            {
                FrameSignal.freq_high: 0.8,  # Beat signal
                FrameSignal.freq_low: 0.5,
                FrameSignal.freq_all: 0.6,
            }
        )

        interpreter.step(frame_beat, scheme)

        # Phase should advance more on beat
        phase_advance = interpreter.chase_phase - initial_phase
        assert phase_advance > 0

    def test_chase_trail_effect(self):
        """Test chase trail generation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = LaserChase(layers, args, num_chasers=2, trail_length=4)
        scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

        frame = Frame({FrameSignal.freq_all: 0.5})

        # Multiple steps should build trails
        for _ in range(6):
            interpreter.step(frame, scheme)

        # Chasers should have trails
        for chaser in interpreter.chasers:
            assert len(chaser["trail"]) <= interpreter.trail_length

            # Trail should have position and intensity info
            for trail_point in chaser["trail"]:
                assert "position" in trail_point
                assert "intensity" in trail_point


class TestLaserBurst:
    """Test explosive laser burst effects"""

    def test_laser_burst_creation(self):
        """Test LaserBurst creation"""
        layers = [SolidLayer("test", width=400, height=300)]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = LaserBurst(layers, args, burst_threshold=0.8, max_burst_lasers=16)

        assert interpreter.burst_threshold == 0.8
        assert interpreter.max_burst_lasers == 16
        assert interpreter.is_bursting == False
        assert len(interpreter.burst_lasers) == 0

    def test_burst_trigger(self):
        """Test burst triggering on energy spike"""
        layers = [SolidLayer("test", width=300, height=200)]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = LaserBurst(layers, args, burst_threshold=0.7)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Low energy - no burst
        frame_low = Frame(
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.2,
                FrameSignal.freq_all: 0.25,
            }
        )
        interpreter.step(frame_low, scheme)
        assert interpreter.is_bursting == False

        # High energy - should trigger burst
        frame_high = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.85,
            }
        )
        interpreter.step(frame_high, scheme)

        assert interpreter.is_bursting == True
        assert len(interpreter.burst_lasers) > 0
        assert interpreter.burst_frames_remaining > 0

    def test_burst_decay(self):
        """Test burst decay over time"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = LaserBurst(layers, args, burst_duration=5)
        scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

        # Trigger burst
        frame_trigger = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.85,
            }
        )
        interpreter.step(frame_trigger, scheme)

        initial_laser_count = len(interpreter.burst_lasers)

        # Continue with low energy to decay burst
        frame_low = Frame(
            {
                FrameSignal.freq_low: 0.2,
                FrameSignal.freq_high: 0.1,
                FrameSignal.freq_all: 0.15,
            }
        )

        # Step through burst duration
        for _ in range(10):  # More than burst_duration
            interpreter.step(frame_low, scheme)

        # Burst should have ended
        assert (
            interpreter.is_bursting == False or interpreter.burst_frames_remaining == 0
        )


class TestLaserSpiral:
    """Test spiral laser effects"""

    def test_laser_spiral_creation(self):
        """Test LaserSpiral creation"""
        layers = [SolidLayer("test", width=300, height=200)]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = LaserSpiral(layers, args, num_spirals=3)

        assert interpreter.num_spirals == 3
        assert len(interpreter.spirals) == 3

    def test_spiral_point_generation(self):
        """Test spiral point generation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = LaserSpiral(layers, args, num_spirals=2)
        scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

        frame = Frame({FrameSignal.freq_high: 0.7, FrameSignal.freq_all: 0.6})

        interpreter.step(frame, scheme)

        # Each spiral should have points
        for spiral in interpreter.spirals:
            assert len(spiral["points"]) > 0

            for point in spiral["points"]:
                assert "x" in point
                assert "y" in point
                assert "intensity" in point

                # Points should be in valid range
                assert 0.0 <= point["x"] <= 1.0
                assert 0.0 <= point["y"] <= 1.0
                assert 0.0 <= point["intensity"] <= 1.0


class TestLaserLayers:
    """Test laser rendering layers"""

    def test_laser_layer_creation(self):
        """Test LaserLayer creation"""
        layer = LaserLayer("test_lasers", z_order=12, width=400, height=300)

        assert layer.name == "test_lasers"
        assert layer.z_order == 12
        assert layer.get_size() == (400, 300)
        assert layer.beam_glow == True
        assert layer.beam_intensity == 0.8

    def test_laser_layer_render_empty(self):
        """Test laser layer with no laser data"""
        layer = LaserLayer("empty", width=200, height=150)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        result = layer.render(frame, scheme)

        # Should return None when no laser effects
        assert result is None

    def test_laser_layer_with_beams(self):
        """Test laser layer with beam data"""
        layer = LaserLayer("beams", width=200, height=150)

        # Simulate laser beam data from interpreter
        layer._laser_beams = [
            {
                "current_angle": 0.0,  # Straight up
                "length": 0.5,
                "intensity": 0.8,
                "color": (1.0, 0.0, 0.0),  # Red
                "width": 3,
                "enabled": True,
            }
        ]

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        result = layer.render(frame, scheme)

        assert result is not None
        assert result.shape == (150, 200, 4)

        # Should have some laser content
        assert np.any(result > 0)

    def test_laser_haze_layer(self):
        """Test laser haze layer"""
        layer = LaserHaze("haze", z_order=11, width=200, height=150, haze_density=0.5)

        assert layer.name == "haze"
        assert layer.haze_density == 0.5

        # Test rendering
        frame = Frame({FrameSignal.freq_low: 0.6, FrameSignal.sustained_low: 0.7})
        scheme = ColorScheme(Color("white"), Color("black"), Color("gray"))

        result = layer.render(frame, scheme)

        if result is not None:  # Might be None if haze is too light
            assert result.shape == (150, 200, 4)

    def test_laser_beam_renderer(self):
        """Test specialized laser beam renderer"""
        layer = LaserBeamRenderer("beam_renderer", width=300, height=200)

        # Add some beams
        layer.add_beam((0.2, 0.8), (0.8, 0.2), (1.0, 0.0, 0.0), 0.9, 3)  # Red diagonal
        layer.add_beam(
            (0.5, 0.9), (0.5, 0.1), (0.0, 1.0, 0.0), 0.7, 2
        )  # Green vertical

        assert len(layer.beam_data) == 2

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        result = layer.render(frame, scheme)

        assert result is not None
        assert result.shape == (200, 300, 4)

        # Beams should be cleared after rendering
        assert len(layer.beam_data) == 0

    def test_laser_stats(self):
        """Test laser statistics"""
        layer = LaserLayer("stats_test", width=200, height=150)

        # Add various laser effects
        layer._laser_beams = [{"enabled": True}, {"enabled": True}]
        layer._scan_beams = [{"intensity": 0.5}]
        layer._laser_chasers = [{"id": 1}, {"id": 2}, {"id": 3}]

        stats = layer.get_laser_stats()

        assert stats["fan_beams"] == 2
        assert stats["scan_beams"] == 1
        assert stats["chasers"] == 3
        assert isinstance(stats, dict)


class TestLaserIntegration:
    """Test laser effect integration"""

    def test_multiple_laser_interpreters(self):
        """Test multiple laser interpreters working together"""
        laser_layer = LaserLayer("multi_laser", width=400, height=300)
        layers = [laser_layer]
        args = InterpreterArgs(80, True, 0, 100)

        # Create multiple laser interpreters
        interpreters = [
            ConcertLasers(layers, args, num_lasers=4),
            LaserScan(layers, args, num_beams=2),
            LaserMatrix(layers, args, grid_size=(4, 3)),
        ]

        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
        frame = Frame(
            {
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_high: 0.6,
                FrameSignal.freq_all: 0.65,
                FrameSignal.sustained_low: 0.8,
            }
        )

        # Update all interpreters
        for interp in interpreters:
            interp.step(frame, scheme)

        # Render combined effect
        result = laser_layer.render(frame, scheme)

        if result is not None:
            assert result.shape == (300, 400, 4)
            # Should have laser content from multiple sources
            assert np.any(result > 0)

    def test_laser_color_scheme_integration(self):
        """Test laser color integration with schemes"""
        layers = [LaserLayer("color_test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ConcertLasers(layers, args, num_lasers=3)

        # Test different color schemes
        schemes = [
            ColorScheme(Color("red"), Color("black"), Color("white")),
            ColorScheme(Color("blue"), Color("orange"), Color("cyan")),
            ColorScheme(Color("purple"), Color("green"), Color("yellow")),
        ]

        frame = Frame({FrameSignal.freq_all: 0.6, FrameSignal.sustained_low: 0.7})

        for scheme in schemes:
            interpreter.step(frame, scheme)

            # Lasers should use colors from scheme
            for laser in interpreter.lasers:
                laser_color = laser["color"]

                # Should be a valid RGB tuple
                assert len(laser_color) == 3
                assert all(0.0 <= c <= 1.0 for c in laser_color)

    def test_laser_performance_with_many_beams(self):
        """Test performance with many laser beams"""
        layer = LaserLayer("performance_test", width=800, height=600)
        layers = [layer]
        args = InterpreterArgs(85, True, 0, 100)

        # Create high-intensity laser setup
        interpreters = [
            ConcertLasers(layers, args, num_lasers=12),
            LaserMatrix(layers, args, grid_size=(8, 6)),
            LaserBurst(layers, args, max_burst_lasers=20),
        ]

        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # High energy frame to activate all effects
        frame = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_all: 0.9,
                FrameSignal.sustained_low: 0.9,
            }
        )

        # Update all interpreters
        for interp in interpreters:
            interp.step(frame, scheme)

        # Should not crash with many laser effects
        result = layer.render(frame, scheme)

        if result is not None:
            assert result.shape == (600, 800, 4)

    def test_laser_string_representations(self):
        """Test string representations of laser interpreters"""
        layers = [LaserLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreters = [
            ConcertLasers(layers, args, num_lasers=6),
            LaserScan(layers, args, num_beams=4),
            LaserMatrix(layers, args, grid_size=(5, 3)),
            LaserChase(layers, args, num_chasers=4),
            LaserBurst(layers, args),
            LaserSpiral(layers, args, num_spirals=2),
        ]

        for interp in interpreters:
            str_repr = str(interp)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
            # Should contain class name or laser-related emoji
            assert interp.__class__.__name__ in str_repr or any(
                emoji in str_repr for emoji in ["🔴", "🔍", "🔳", "🏃", "💥", "🌀"]
            )

    def test_laser_hype_levels(self):
        """Test laser interpreter hype levels"""
        layers = [LaserLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreters_and_hypes = [
            (LaserSpiral(layers, args), 65),
            (LaserChase(layers, args), 70),
            (ConcertLasers(layers, args), 75),
            (LaserScan(layers, args), 80),
            (LaserMatrix(layers, args), 85),
            (LaserBurst(layers, args), 90),
        ]

        for interp, expected_hype in interpreters_and_hypes:
            assert interp.get_hype() == expected_hype
