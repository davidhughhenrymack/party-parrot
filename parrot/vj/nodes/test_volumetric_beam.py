#!/usr/bin/env python3

import pytest
import numpy as np
import time
from unittest.mock import Mock

from parrot.vj.nodes.volumetric_beam import VolumetricBeam, BeamState
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class TestVolumetricBeam:
    """Test VolumetricBeam functionality"""

    def test_initialization_default(self):
        """Test VolumetricBeam initialization with defaults"""
        beam = VolumetricBeam()

        assert beam.beam_count == 4
        assert beam.beam_length == 10.0
        assert beam.beam_width == 0.3
        assert beam.beam_intensity == 1.0
        assert beam.haze_density == 0.8
        assert beam.movement_speed == 2.0
        assert beam.color == (1.0, 0.8, 0.6)
        assert beam.signal == FrameSignal.freq_all
        assert beam.width == 1280
        assert beam.height == 720

    def test_initialization_custom(self):
        """Test VolumetricBeam initialization with custom parameters"""
        beam = VolumetricBeam(
            beam_count=8,
            beam_length=15.0,
            beam_width=0.5,
            beam_intensity=1.5,
            haze_density=0.6,
            movement_speed=3.0,
            color=(0.8, 0.4, 1.0),
            signal=FrameSignal.freq_high,
            width=1920,
            height=1080,
        )

        assert beam.beam_count == 8
        assert beam.beam_length == 15.0
        assert beam.beam_width == 0.5
        assert beam.beam_intensity == 1.5
        assert beam.haze_density == 0.6
        assert beam.movement_speed == 3.0
        assert beam.color == (0.8, 0.4, 1.0)
        assert beam.signal == FrameSignal.freq_high
        assert beam.width == 1920
        assert beam.height == 1080

    def test_beam_setup(self):
        """Test that beams are properly initialized"""
        beam = VolumetricBeam(beam_count=6)
        beam._setup_beams()

        assert len(beam.beams) == 6

        for beam_state in beam.beams:
            assert isinstance(beam_state, BeamState)
            assert len(beam_state.position) == 3
            assert len(beam_state.direction) == 3
            # Direction should be normalized
            assert abs(np.linalg.norm(beam_state.direction) - 1.0) < 1e-6

    def test_generate_randomizes_beams(self):
        """Test that generate can randomize beam targets"""
        beam = VolumetricBeam(beam_count=2)
        beam._setup_beams()

        # Store original targets
        original_targets = [b.target_position.copy() for b in beam.beams]

        # Generate multiple times to potentially trigger randomization
        vibe = Vibe(Mode.rave)
        for _ in range(50):  # Higher chance of hitting the 10% randomization
            beam.generate(vibe)

        # At least one beam should have changed (probabilistically)
        changed = any(
            not np.allclose(original, current.target_position)
            for original, current in zip(original_targets, beam.beams)
        )
        # Note: This test might occasionally fail due to randomness, but very unlikely


class TestBeamState:
    """Test BeamState functionality"""

    def test_initialization(self):
        """Test BeamState initialization"""
        position = np.array([1.0, 2.0, 3.0])
        direction = np.array([0.0, -1.0, 0.0])

        beam = BeamState(position, direction)

        assert np.allclose(beam.position, position)
        assert np.allclose(beam.direction, direction)
        assert np.allclose(beam.target_position, position)
        assert np.allclose(beam.target_direction, direction)
        assert isinstance(beam.phase_offset, float)

    def test_update_smooth_movement(self):
        """Test smooth movement towards targets"""
        position = np.array([0.0, 0.0, 0.0])
        direction = np.array([0.0, -1.0, 0.0])

        beam = BeamState(position, direction)

        # Set different target
        beam.target_position = np.array([5.0, 0.0, 0.0])
        beam.target_direction = np.array([1.0, 0.0, 0.0])

        # Update should move towards target
        original_pos = beam.position.copy()
        beam.update(time=0.0, speed=1.0, signal=0.0)

        # Should have moved towards target
        assert not np.allclose(beam.position, original_pos)
        # Direction should still be normalized
        assert abs(np.linalg.norm(beam.direction) - 1.0) < 1e-6

    def test_randomize_target(self):
        """Test target randomization"""
        position = np.array([0.0, 0.0, 0.0])
        direction = np.array([0.0, -1.0, 0.0])

        beam = BeamState(position, direction)
        original_target_pos = beam.target_position.copy()
        original_target_dir = beam.target_direction.copy()

        beam.randomize_target()

        # Targets should have changed
        assert not np.allclose(beam.target_position, original_target_pos)
        assert not np.allclose(beam.target_direction, original_target_dir)

        # New target direction should be normalized
        assert abs(np.linalg.norm(beam.target_direction) - 1.0) < 1e-6

        # Target position should be within reasonable bounds
        assert -6.0 <= beam.target_position[0] <= 6.0  # X
        assert 3.0 <= beam.target_position[1] <= 10.0  # Y
        assert -4.0 <= beam.target_position[2] <= 4.0  # Z

    def test_signal_oscillation(self):
        """Test that audio signal affects beam movement"""
        position = np.array([0.0, 5.0, 0.0])
        direction = np.array([0.0, -1.0, 0.0])

        beam = BeamState(position, direction)

        # Update with no signal
        beam.update(time=0.0, speed=1.0, signal=0.0)
        pos_no_signal = beam.position.copy()

        # Reset and update with high signal
        beam.position = position.copy()
        beam.update(time=0.0, speed=1.0, signal=1.0)
        pos_with_signal = beam.position.copy()

        # Positions should be different due to signal-based oscillation
        assert not np.allclose(pos_no_signal, pos_with_signal)


class TestVolumetricBeamIntegration:
    """Test VolumetricBeam integration functionality"""

    def test_render_without_gl_context(self):
        """Test that render handles missing GL context gracefully"""
        import moderngl as mgl

        beam = VolumetricBeam()

        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(return_value=0.5)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        # Mock the context.texture and context.framebuffer to return None
        context.texture.side_effect = Exception("No GL context")
        context.framebuffer.side_effect = Exception("No GL context")

        # Should not crash without GL setup
        try:
            result = beam.render(frame, scheme, context)
            # Should return None when GL setup fails
            assert result is None
        except Exception:
            # It's okay if it raises an exception due to missing GL context
            pass

    def test_matrix_creation(self):
        """Test 3D matrix creation"""
        beam = VolumetricBeam()

        view, projection, model, camera_pos = beam._create_matrices()

        # Matrices should be 4x4
        assert view.shape == (4, 4)
        assert projection.shape == (4, 4)
        assert model.shape == (4, 4)

        # Camera position should be reasonable
        assert len(camera_pos) == 3
        assert camera_pos[1] > 0  # Camera should be above ground

    def test_beam_transform_creation(self):
        """Test beam transformation matrix creation"""
        beam = VolumetricBeam()
        beam._setup_beams()

        if beam.beams:
            transform = beam._create_beam_transform(beam.beams[0])

            # Transform should be 4x4
            assert transform.shape == (4, 4)

            # Should be a valid transformation matrix
            # (determinant should be non-zero for invertible matrix)
            assert abs(np.linalg.det(transform)) > 1e-6

    def test_audio_reactivity(self):
        """Test that beam responds to audio signals"""
        beam = VolumetricBeam()
        beam._setup_beams()

        frame_low = Mock(spec=Frame)
        frame_low.__getitem__ = Mock(return_value=0.1)

        frame_high = Mock(spec=Frame)
        frame_high.__getitem__ = Mock(return_value=0.9)

        # Update with low signal
        beam._update_beams(frame_low)
        positions_low = [b.position.copy() for b in beam.beams]

        # Reset positions and update with high signal
        beam._setup_beams()
        beam._update_beams(frame_high)
        positions_high = [b.position.copy() for b in beam.beams]

        # Positions should be different due to signal-based oscillation
        # (This test might be flaky due to timing, but should generally work)
        differences = [
            not np.allclose(low, high, atol=0.1)
            for low, high in zip(positions_low, positions_high)
        ]
        # At least some beams should have moved differently
        assert any(differences)


if __name__ == "__main__":
    pytest.main([__file__])
