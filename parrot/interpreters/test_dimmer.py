import pytest
import math
import random
from unittest.mock import MagicMock, patch
from parrot.interpreters.dimmer import (
    Dimmer255,
    Dimmer30,
    Dimmer0,
    DimmerFadeIn,
    SequenceDimmers,
    SequenceFadeDimmers,
    DimmersBeatChase,
    GentlePulse,
    LightningStab,
    StabPulse,
    Twinkle,
)
from parrot.interpreters.base import InterpreterArgs
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import FixtureBase
from parrot.utils.colour import Color


class TestDimmer255:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmer255_step(self):
        """Test Dimmer255 sets all fixtures to full brightness"""
        interpreter = Dimmer255(self.group, self.args)
        frame = MagicMock()
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        self.fixture1.set_dimmer.assert_called_with(255)
        self.fixture2.set_dimmer.assert_called_with(255)


class TestDimmer30:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmer30_step(self):
        """Test Dimmer30 sets all fixtures to 30"""
        interpreter = Dimmer30(self.group, self.args)
        frame = MagicMock()
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        self.fixture1.set_dimmer.assert_called_with(30)
        self.fixture2.set_dimmer.assert_called_with(30)


class TestDimmer0:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmer0_step(self):
        """Test Dimmer0 turns off all fixtures"""
        interpreter = Dimmer0(self.group, self.args)
        frame = MagicMock()
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        self.fixture1.set_dimmer.assert_called_with(0)
        self.fixture1.set_strobe.assert_called_with(0)
        self.fixture2.set_dimmer.assert_called_with(0)
        self.fixture2.set_strobe.assert_called_with(0)


class TestDimmerFadeIn:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmer_fade_in_initialization(self):
        """Test DimmerFadeIn initialization"""
        interpreter = DimmerFadeIn(self.group, self.args, fade_time=5)
        assert interpreter.fade_time == 5
        assert interpreter.memory == 0

    def test_dimmer_fade_in_progression(self):
        """Test DimmerFadeIn gradually increases brightness"""
        interpreter = DimmerFadeIn(self.group, self.args, fade_time=3)
        frame = MagicMock()
        scheme = MagicMock()

        # First step
        interpreter.step(frame, scheme)
        first_call = self.fixture.set_dimmer.call_args[0][0]
        assert first_call > 0

        # Second step should be higher
        interpreter.step(frame, scheme)
        second_call = self.fixture.set_dimmer.call_args[0][0]
        assert second_call > first_call

    def test_dimmer_fade_in_max_value(self):
        """Test DimmerFadeIn doesn't exceed 255"""
        interpreter = DimmerFadeIn(
            self.group, self.args, fade_time=0.1
        )  # Very fast fade
        frame = MagicMock()
        scheme = MagicMock()

        # Run many steps to ensure it caps at 255
        for _ in range(100):
            interpreter.step(frame, scheme)

        final_call = self.fixture.set_dimmer.call_args[0][0]
        assert final_call <= 255


class TestSequenceDimmers:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.fixture3 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2, self.fixture3]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_sequence_dimmers_hype(self):
        """Test SequenceDimmers hype level"""
        assert SequenceDimmers.hype == 30

    def test_sequence_dimmers_initialization(self):
        """Test SequenceDimmers initialization"""
        interpreter = SequenceDimmers(self.group, self.args, dimmer=200, wait_time=2)
        assert interpreter.dimmer == 200
        assert interpreter.wait_time == 2

    def test_sequence_dimmers_step(self):
        """Test SequenceDimmers cycles through fixtures"""
        interpreter = SequenceDimmers(self.group, self.args, dimmer=150, wait_time=1)
        frame = MagicMock()
        frame.time = 0  # Should light fixture 0
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        # At time 0, fixture 0 should be on, others off
        self.fixture1.set_dimmer.assert_called_with(150)
        self.fixture2.set_dimmer.assert_called_with(0)
        self.fixture3.set_dimmer.assert_called_with(0)

    def test_sequence_dimmers_progression(self):
        """Test SequenceDimmers moves to next fixture over time"""
        interpreter = SequenceDimmers(self.group, self.args, dimmer=150, wait_time=1)
        frame = MagicMock()
        scheme = MagicMock()

        # Time 1 should light fixture 1
        frame.time = 1
        interpreter.step(frame, scheme)
        self.fixture2.set_dimmer.assert_called_with(150)


class TestSequenceFadeDimmers:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_sequence_fade_dimmers_hype(self):
        """Test SequenceFadeDimmers hype level"""
        assert SequenceFadeDimmers.hype == 20

    def test_sequence_fade_dimmers_initialization(self):
        """Test SequenceFadeDimmers initialization"""
        interpreter = SequenceFadeDimmers(self.group, self.args, wait_time=5)
        assert interpreter.wait_time == 5

    def test_sequence_fade_dimmers_step(self):
        """Test SequenceFadeDimmers creates smooth fades"""
        interpreter = SequenceFadeDimmers(self.group, self.args, wait_time=3)
        frame = MagicMock()
        frame.time = 0
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        # Both fixtures should get dimmer values
        self.fixture1.set_dimmer.assert_called_once()
        self.fixture2.set_dimmer.assert_called_once()

        # Values should be between 0 and 255
        dim1 = self.fixture1.set_dimmer.call_args[0][0]
        dim2 = self.fixture2.set_dimmer.call_args[0][0]
        assert 0 <= dim1 <= 255
        assert 0 <= dim2 <= 255


class TestDimmersBeatChase:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.fixture3 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2, self.fixture3]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmers_beat_chase_hype(self):
        """Test DimmersBeatChase hype level"""
        assert DimmersBeatChase.hype == 75

    def test_dimmers_beat_chase_initialization(self):
        """Test DimmersBeatChase initialization"""
        with patch("random.choice") as mock_choice:
            mock_choice.return_value = FrameSignal.freq_high
            interpreter = DimmersBeatChase(self.group, self.args)
            assert interpreter.signal == FrameSignal.freq_high
            assert interpreter.on == False

    def test_dimmers_beat_chase_trigger(self):
        """Test DimmersBeatChase triggers on beat"""
        with patch("random.choice") as mock_choice, patch(
            "random.randint"
        ) as mock_randint:
            mock_choice.return_value = FrameSignal.freq_high
            mock_randint.return_value = 1  # Select fixture 1

            interpreter = DimmersBeatChase(self.group, self.args)

            # Create frame with high signal
            frame_values = {FrameSignal.freq_high: 0.5}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Selected fixture should be bright, others should be off
            self.fixture1.set_dimmer.assert_called_with(0)
            self.fixture2.set_dimmer.assert_called_with(127.5)  # 0.5 * 255
            self.fixture3.set_dimmer.assert_called_with(0)

    def test_dimmers_beat_chase_no_signal(self):
        """Test DimmersBeatChase with no signal"""
        interpreter = DimmersBeatChase(self.group, self.args)

        # Create frame with low signal
        frame_values = {FrameSignal.freq_high: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        scheme = MagicMock()

        interpreter.step(frame, scheme)

        # All fixtures should be off
        self.fixture1.set_dimmer.assert_called_with(0)
        self.fixture2.set_dimmer.assert_called_with(0)
        self.fixture3.set_dimmer.assert_called_with(0)


class TestGentlePulse:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_gentle_pulse_hype(self):
        """Test GentlePulse hype level"""
        assert GentlePulse.hype == 10

    def test_gentle_pulse_initialization(self):
        """Test GentlePulse initialization"""
        interpreter = GentlePulse(
            self.group, self.args, signal=FrameSignal.freq_low, trigger_level=0.3
        )
        assert interpreter.signal == FrameSignal.freq_low
        assert interpreter.trigger_level == 0.3
        assert interpreter.on == False
        assert len(interpreter.memory) == 2

    def test_gentle_pulse_trigger(self):
        """Test GentlePulse triggers and decays"""
        with patch("random.randint") as mock_randint:
            mock_randint.return_value = 0  # Select fixture 0

            interpreter = GentlePulse(self.group, self.args, trigger_level=0.3)

            # Create frame with high signal
            frame_values = {FrameSignal.freq_all: 0.8}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Selected fixture should get the signal value
            dim1 = self.fixture1.set_dimmer.call_args[0][0]
            assert dim1 == 0.8 * 255

    def test_gentle_pulse_decay(self):
        """Test GentlePulse decays over time"""
        with patch("random.randint") as mock_randint:
            mock_randint.return_value = 0

            interpreter = GentlePulse(self.group, self.args)
            scheme = MagicMock()

            # First step with high signal
            frame_values = {FrameSignal.freq_all: 0.8}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            interpreter.step(frame, scheme)
            first_dim = self.fixture1.set_dimmer.call_args[0][0]

            # Second step with low signal
            frame_values = {FrameSignal.freq_all: 0.1}
            frame = Frame(frame_values, timeseries)
            interpreter.step(frame, scheme)
            second_dim = self.fixture1.set_dimmer.call_args[0][0]

            # Should decay (be less than first)
            assert second_dim < first_dim


class TestStabPulse:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_stab_pulse_hype(self):
        """Test StabPulse hype level"""
        assert StabPulse.hype == 50

    def test_stab_pulse_faster_decay_than_gentle(self):
        """Test StabPulse decays faster than GentlePulse"""
        with patch("random.randint") as mock_randint:
            mock_randint.return_value = 0

            gentle_interp = GentlePulse(self.group, self.args)
            stab_interp = StabPulse(self.group, self.args)
            scheme = MagicMock()

            # First step with high signal for both
            frame_values = {FrameSignal.freq_all: 0.8}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            gentle_interp.step(frame, scheme)
            stab_interp.step(frame, scheme)

            # Second step with low signal for both
            frame_values = {FrameSignal.freq_all: 0.1}
            frame = Frame(frame_values, timeseries)
            gentle_interp.step(frame, scheme)
            stab_interp.step(frame, scheme)

            gentle_dim = self.fixture1.set_dimmer.call_args_list[-2][0][0]
            stab_dim = self.fixture1.set_dimmer.call_args_list[-1][0][0]

            # StabPulse should have decayed more (lower value)
            assert stab_dim < gentle_dim


class TestLightingStab:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_lighting_stab_hype(self):
        """Test LightingStab hype level"""
        assert LightningStab.hype == 60

    def test_lighting_stab_initialization(self):
        """Test LightingStab initialization"""
        interpreter = LightningStab(self.group, self.args, trigger_level=0.3)
        assert interpreter.trigger_level == 0.3
        assert interpreter.on_low == False
        assert interpreter.on_high == False
        assert len(interpreter.memory) == 2
        assert len(interpreter.strobe_memory) == 2

    def test_lighting_stab_freq_low_trigger(self):
        """Test LightingStab triggers on freq_low"""
        with patch("parrot.interpreters.dimmer.random.randint") as mock_randint:
            mock_randint.return_value = 0

            interpreter = LightningStab(self.group, self.args, trigger_level=0.2)

            # Create frame with high freq_low signal
            frame_values = {FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.0}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Selected fixture should get the signal value
            dim1 = self.fixture1.set_dimmer.call_args[0][0]
            assert dim1 == 0.8 * 255

    def test_lighting_stab_freq_high_white_strobe(self):
        """Test LightingStab triggers white strobe on freq_high"""
        with patch("parrot.interpreters.dimmer.random.randint") as mock_randint:
            mock_randint.return_value = 1  # Select fixture 1

            interpreter = LightningStab(self.group, self.args, trigger_level=0.2)

            # Create frame with high freq_high signal
            frame_values = {FrameSignal.freq_low: 0.0, FrameSignal.freq_high: 0.9}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Fixture 1 should be set to white and brightness based on strobe_memory (1.0)
            self.fixture2.set_color.assert_called_once()
            color_arg = self.fixture2.set_color.call_args[0][0]
            assert color_arg.hex_l == Color("white").hex_l
            # Initial strobe_memory is 1.0, so dimmer should be 255
            self.fixture2.set_dimmer.assert_called_with(1.0 * 255)

    def test_lighting_stab_strobe_decay(self):
        """Test LightingStab white strobe decays quickly"""
        with patch("parrot.interpreters.dimmer.random.randint") as mock_randint:
            mock_randint.return_value = 0

            interpreter = LightningStab(self.group, self.args, trigger_level=0.2)
            scheme = MagicMock()

            # First step with high freq_high to trigger strobe
            frame_values = {FrameSignal.freq_low: 0.0, FrameSignal.freq_high: 0.9}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            interpreter.step(frame, scheme)
            first_dim = self.fixture1.set_dimmer.call_args[0][0]
            assert first_dim == 255  # 1.0 * 255

            # Second step with no signal - should decay
            frame_values = {FrameSignal.freq_low: 0.0, FrameSignal.freq_high: 0.0}
            frame = Frame(frame_values, timeseries)
            interpreter.step(frame, scheme)
            second_dim = self.fixture1.set_dimmer.call_args[0][0]
            assert second_dim == 0.3 * 255  # Decayed to 0.3

            # Third step - should decay further
            interpreter.step(frame, scheme)
            third_dim = self.fixture1.set_dimmer.call_args[0][0]
            assert third_dim == 0.3 * 0.3 * 255  # Decayed to 0.09

    def test_lighting_stab_both_signals(self):
        """Test LightingStab handles both freq_low and freq_high simultaneously"""
        with patch("parrot.interpreters.dimmer.random.randint") as mock_randint:
            mock_randint.side_effect = [0, 1]

            interpreter = LightningStab(self.group, self.args, trigger_level=0.2)

            # Create frame with both signals high
            frame_values = {FrameSignal.freq_low: 0.7, FrameSignal.freq_high: 0.8}
            timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
            frame = Frame(frame_values, timeseries)
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Both fixtures should be affected
            assert self.fixture1.set_dimmer.called
            assert self.fixture2.set_dimmer.called


class TestTwinkle:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_twinkle_hype(self):
        """Test Twinkle hype level"""
        assert Twinkle.hype == 5

    def test_twinkle_initialization(self):
        """Test Twinkle initialization"""
        interpreter = Twinkle(self.group, self.args)
        assert len(interpreter.memory) == 2
        assert all(mem == 0 for mem in interpreter.memory)

    def test_twinkle_step_no_trigger(self):
        """Test Twinkle step without random trigger"""
        with patch(
            "random.random", return_value=0.98
        ):  # Won't trigger (< 0.99, needs > 0.99)
            interpreter = Twinkle(self.group, self.args)
            frame = MagicMock()
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # Should set dimmer to 0 (no memory)
            self.fixture1.set_dimmer.assert_called_with(0)
            self.fixture2.set_dimmer.assert_called_with(0)

    def test_twinkle_step_with_trigger(self):
        """Test Twinkle step with random trigger"""
        with patch("random.random", return_value=0.995):  # Will trigger (> 0.99)
            interpreter = Twinkle(self.group, self.args)
            frame = MagicMock()
            scheme = MagicMock()

            interpreter.step(frame, scheme)

            # At least one fixture should have been triggered
            calls = [
                call[0][0]
                for call in [
                    self.fixture1.set_dimmer.call_args,
                    self.fixture2.set_dimmer.call_args,
                ]
            ]
            assert any(call > 0 for call in calls)

    def test_twinkle_decay(self):
        """Test Twinkle memory decay"""
        interpreter = Twinkle(self.group, self.args)
        # Manually set memory
        interpreter.memory[0] = 1.0

        frame = MagicMock()
        scheme = MagicMock()

        with patch("random.random", return_value=0.98):  # No new triggers (< 0.99)
            interpreter.step(frame, scheme)

            # Memory should have decayed
            assert interpreter.memory[0] < 1.0
            assert interpreter.memory[0] == 0.9  # 1.0 * 0.9
