import pytest
from unittest.mock import MagicMock
from parrot.interpreters.combo import Combo, combo
from parrot.interpreters.base import InterpreterBase, InterpreterArgs
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import FixtureBase
from parrot.utils.colour import Color


class TestCombo:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test frame
        frame_values = {signal: 0.0 for signal in FrameSignal}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        self.frame = Frame(frame_values, timeseries)

        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_combo_initialization(self):
        """Test Combo initialization with multiple interpreters"""

        # Create mock interpreter classes
        class MockInterpreter1(InterpreterBase):
            def __init__(self, group, args):
                super().__init__(group, args)
                self.step_called = False

            def step(self, frame, scheme):
                self.step_called = True
                for fixture in self.group:
                    fixture.set_dimmer(100)

        class MockInterpreter2(InterpreterBase):
            def __init__(self, group, args):
                super().__init__(group, args)
                self.step_called = False

            def step(self, frame, scheme):
                self.step_called = True
                for fixture in self.group:
                    fixture.set_color(Color("yellow"))

        interpreters = [MockInterpreter1, MockInterpreter2]
        combo_interpreter = Combo(self.group, self.args, interpreters)

        assert len(combo_interpreter.interpreters) == 2
        assert isinstance(combo_interpreter.interpreters[0], MockInterpreter1)
        assert isinstance(combo_interpreter.interpreters[1], MockInterpreter2)

    def test_combo_step(self):
        """Test Combo step calls all sub-interpreters"""

        class MockInterpreter1(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(100)

        class MockInterpreter2(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_color(Color("yellow"))

        interpreters = [MockInterpreter1, MockInterpreter2]
        combo_interpreter = Combo(self.group, self.args, interpreters)

        combo_interpreter.step(self.frame, self.scheme)

        # Both interpreters should have been called
        self.fixture1.set_dimmer.assert_called_with(100)
        self.fixture1.set_color.assert_called_with(Color("yellow"))
        self.fixture2.set_dimmer.assert_called_with(100)
        self.fixture2.set_color.assert_called_with(Color("yellow"))

    def test_combo_str_representation(self):
        """Test Combo string representation"""

        class MockInterpreter1(InterpreterBase):
            def __str__(self):
                return "Mock1"

        class MockInterpreter2(InterpreterBase):
            def __str__(self):
                return "Mock2"

        interpreters = [MockInterpreter1, MockInterpreter2]
        combo_interpreter = Combo(self.group, self.args, interpreters)

        str_repr = str(combo_interpreter)
        assert "Mock1" in str_repr
        assert "Mock2" in str_repr
        assert "+" in str_repr


class TestComboFunction:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test frame
        frame_values = {signal: 0.0 for signal in FrameSignal}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        self.frame = Frame(frame_values, timeseries)

        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_combo_function_creation(self):
        """Test combo function creates proper wrapper class"""

        class TestInterpreter1(InterpreterBase):
            hype = 20
            has_rainbow = False

            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(150)

        class TestInterpreter2(InterpreterBase):
            hype = 30
            has_rainbow = True

            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_color(Color("purple"))

        ComboClass = combo(TestInterpreter1, TestInterpreter2)
        combo_instance = ComboClass(self.group, self.args)

        assert len(combo_instance.interpreters) == 2

    def test_combo_function_acceptable(self):
        """Test combo function acceptable method"""

        class TestInterpreter1(InterpreterBase):
            hype = 20
            has_rainbow = False

            @classmethod
            def acceptable(cls, args):
                return args.hype >= 15

        class TestInterpreter2(InterpreterBase):
            hype = 80
            has_rainbow = True

            @classmethod
            def acceptable(cls, args):
                return args.hype >= 75

        ComboClass = combo(TestInterpreter1, TestInterpreter2)

        # Should be acceptable only if ALL interpreters are acceptable
        args_low = InterpreterArgs(
            hype=20, allow_rainbows=True, min_hype=0, max_hype=100
        )
        args_high = InterpreterArgs(
            hype=80, allow_rainbows=True, min_hype=0, max_hype=100
        )

        assert (
            ComboClass.acceptable(args_low) == False
        )  # TestInterpreter2 not acceptable
        assert ComboClass.acceptable(args_high) == True  # Both acceptable

    def test_combo_function_step(self):
        """Test combo function step delegation"""

        class TestInterpreter1(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(200)

        class TestInterpreter2(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_strobe(50)

        ComboClass = combo(TestInterpreter1, TestInterpreter2)
        combo_instance = ComboClass(self.group, self.args)

        combo_instance.step(self.frame, self.scheme)

        # Both interpreter effects should be applied
        self.fixture.set_dimmer.assert_called_with(200)
        self.fixture.set_strobe.assert_called_with(50)

    def test_combo_function_exit(self):
        """Test combo function exit delegation"""

        class TestInterpreter1(InterpreterBase):
            def __init__(self, group, args):
                super().__init__(group, args)
                self.exit_called = False

            def exit(self, frame, scheme):
                self.exit_called = True

        class TestInterpreter2(InterpreterBase):
            def __init__(self, group, args):
                super().__init__(group, args)
                self.exit_called = False

            def exit(self, frame, scheme):
                self.exit_called = True

        ComboClass = combo(TestInterpreter1, TestInterpreter2)
        combo_instance = ComboClass(self.group, self.args)

        combo_instance.exit(self.frame, self.scheme)

        # Both interpreters should have exit called
        assert combo_instance.interpreters[0].exit_called == True
        assert combo_instance.interpreters[1].exit_called == True

    def test_combo_function_get_hype(self):
        """Test combo function get_hype returns maximum hype"""

        class TestInterpreter1(InterpreterBase):
            hype = 30

            def get_hype(self):
                return 30

        class TestInterpreter2(InterpreterBase):
            hype = 60

            def get_hype(self):
                return 60

        class TestInterpreter3(InterpreterBase):
            hype = 45

            def get_hype(self):
                return 45

        ComboClass = combo(TestInterpreter1, TestInterpreter2, TestInterpreter3)
        combo_instance = ComboClass(self.group, self.args)

        # Should return the maximum hype
        assert combo_instance.get_hype() == 60

    def test_combo_function_str_representation(self):
        """Test combo function string representation"""

        class TestInterpreter1(InterpreterBase):
            def __str__(self):
                return "Test1"

        class TestInterpreter2(InterpreterBase):
            def __str__(self):
                return "Test2"

        ComboClass = combo(TestInterpreter1, TestInterpreter2)
        combo_instance = ComboClass(self.group, self.args)

        str_repr = str(combo_instance)
        assert "Test1" in str_repr
        assert "Test2" in str_repr
        assert "+" in str_repr

    def test_combo_function_empty_interpreters(self):
        """Test combo function with no interpreters"""
        ComboClass = combo()
        combo_instance = ComboClass(self.group, self.args)

        assert len(combo_instance.interpreters) == 0

        # Should not raise error
        combo_instance.step(self.frame, self.scheme)
        combo_instance.exit(self.frame, self.scheme)

    def test_combo_function_single_interpreter(self):
        """Test combo function with single interpreter"""

        class TestInterpreter(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(75)

        ComboClass = combo(TestInterpreter)
        combo_instance = ComboClass(self.group, self.args)

        combo_instance.step(self.frame, self.scheme)
        self.fixture.set_dimmer.assert_called_with(75)

    def test_combo_function_interpreter_order(self):
        """Test combo function maintains interpreter order"""
        call_order = []

        class TestInterpreter1(InterpreterBase):
            def step(self, frame, scheme):
                call_order.append("first")

        class TestInterpreter2(InterpreterBase):
            def step(self, frame, scheme):
                call_order.append("second")

        class TestInterpreter3(InterpreterBase):
            def step(self, frame, scheme):
                call_order.append("third")

        ComboClass = combo(TestInterpreter1, TestInterpreter2, TestInterpreter3)
        combo_instance = ComboClass(self.group, self.args)

        combo_instance.step(self.frame, self.scheme)

        assert call_order == ["first", "second", "third"]
