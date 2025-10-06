#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch
from parrot.vj.vj_director import VJDirector
from parrot.vj.vj_mode import VJMode
from parrot.state import State


class TestVJDirectorEvents:
    """Test VJDirector event subscriptions"""

    def test_subscribes_to_vj_mode_change(self):
        """Test that VJDirector subscribes to VJ mode changes"""
        state = State()
        vj_director = VJDirector(state)

        # Verify the event handler is registered
        assert vj_director._on_vj_mode_change in state.events.on_vj_mode_change

    def test_vj_mode_change_triggers_regeneration(self):
        """Test that changing VJ mode triggers visual regeneration"""
        state = State()
        vj_director = VJDirector(state)

        # Mock the generate_recursive method
        with patch.object(
            vj_director.concert_stage, "generate_recursive"
        ) as mock_generate:
            # Change VJ mode
            state.set_vj_mode(VJMode.blackout)

            # Verify generate_recursive was called with the new mode
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[0][0].mode == VJMode.blackout
            assert call_args[1]["threshold"] == 1.0

    def test_cleanup_unsubscribes_from_events(self):
        """Test that cleanup unsubscribes from VJ mode events"""
        state = State()
        vj_director = VJDirector(state)

        # Verify subscribed
        assert vj_director._on_vj_mode_change in state.events.on_vj_mode_change

        # Cleanup
        vj_director.cleanup()

        # Verify unsubscribed
        assert vj_director._on_vj_mode_change not in state.events.on_vj_mode_change

    def test_multiple_mode_changes(self):
        """Test that mode changes trigger regeneration"""
        state = State()
        initial_mode = state.vj_mode
        vj_director = VJDirector(state)

        with patch.object(
            vj_director.concert_stage, "generate_recursive"
        ) as mock_generate:
            # Change to a different mode twice
            new_mode_1 = (
                VJMode.blackout
                if initial_mode != VJMode.blackout
                else VJMode.golden_age
            )
            new_mode_2 = (
                VJMode.early_rave
                if new_mode_1 != VJMode.early_rave
                else VJMode.full_rave
            )

            state.set_vj_mode(new_mode_1)
            state.set_vj_mode(new_mode_2)

            # Verify generate_recursive was called for both mode changes
            assert mock_generate.call_count == 2

            # Verify calls used the correct modes
            modes_used = [call[0][0].mode for call in mock_generate.call_args_list]
            assert new_mode_1 in modes_used
            assert new_mode_2 in modes_used


if __name__ == "__main__":
    pytest.main([__file__])
