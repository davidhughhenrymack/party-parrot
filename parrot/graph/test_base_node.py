import pytest
from typing import List
from unittest.mock import Mock

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe, Random
from parrot.director.frame import Frame
from parrot.director.mode import Mode
from parrot.director.color_scheme import ColorScheme


# Simple context type for testing
class SimpleContext:
    def __init__(self, value: int = 0):
        self.value = value


# Arithmetic nodes for testing
class ConstantNode(BaseInterpretationNode[SimpleContext, None, float]):
    """A node that always returns a constant value."""

    def __init__(self, value: float):
        super().__init__([])
        self.value = value
        self.entered = False

    def enter(self, context: SimpleContext):
        self.entered = True

    def exit(self):
        self.entered = False

    def generate(self, vibe: Vibe):
        # Could randomize the constant based on vibe
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: SimpleContext
    ) -> float:
        return self.value


class AddNode(BaseInterpretationNode[SimpleContext, float, float]):
    """A node that adds the results of its children."""

    def __init__(
        self, children: List[BaseInterpretationNode[SimpleContext, None, float]]
    ):
        super().__init__(children)
        self.entered = False

    def enter(self, context: SimpleContext):
        self.entered = True

    def exit(self):
        self.entered = False

    def generate(self, vibe: Vibe):
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: SimpleContext
    ) -> float:
        total = 0.0
        for child in self.children:
            total += child.render(frame, scheme, context)
        return total


class MultiplyNode(BaseInterpretationNode[SimpleContext, float, float]):
    """A node that multiplies the results of its children."""

    def __init__(
        self, children: List[BaseInterpretationNode[SimpleContext, None, float]]
    ):
        super().__init__(children)
        self.entered = False

    def enter(self, context: SimpleContext):
        self.entered = True

    def exit(self):
        self.entered = False

    def generate(self, vibe: Vibe):
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: SimpleContext
    ) -> float:
        result = 1.0
        for child in self.children:
            result *= child.render(frame, scheme, context)
        return result


class ContextValueNode(BaseInterpretationNode[SimpleContext, None, float]):
    """A node that returns a value from the context."""

    def __init__(self):
        super().__init__([])
        self.entered = False

    def enter(self, context: SimpleContext):
        self.entered = True

    def exit(self):
        self.entered = False

    def generate(self, vibe: Vibe):
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: SimpleContext
    ) -> float:
        return float(context.value)


class TestBaseInterpretationNode:
    """Test cases for the BaseInterpretationNode system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_frame = Mock(spec=Frame)
        self.mock_scheme = Mock(spec=ColorScheme)
        self.mock_vibe = Mock(spec=Vibe)
        self.mock_vibe.mode = Mock(spec=Mode)
        self.context = SimpleContext(value=10)

    def test_constant_node(self):
        """Test that constant nodes return their constant value."""
        node = ConstantNode(42.0)

        node.enter_recursive(SimpleContext())
        assert node.entered

        result = node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 42.0

        node.exit_recursive()
        assert not node.entered

    def test_add_node_simple(self):
        """Test addition of two constant nodes."""
        child1 = ConstantNode(10.0)
        child2 = ConstantNode(20.0)
        add_node = AddNode([child1, child2])

        add_node.enter_recursive(SimpleContext())
        assert add_node.entered
        assert child1.entered
        assert child2.entered

        result = add_node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 30.0

        add_node.exit_recursive()
        assert not add_node.entered
        assert not child1.entered
        assert not child2.entered

    def test_multiply_node_simple(self):
        """Test multiplication of two constant nodes."""
        child1 = ConstantNode(3.0)
        child2 = ConstantNode(4.0)
        multiply_node = MultiplyNode([child1, child2])

        multiply_node.enter_recursive(SimpleContext())
        result = multiply_node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 12.0
        multiply_node.exit_recursive()

    def test_context_value_node(self):
        """Test that context value node reads from context."""
        node = ContextValueNode()

        node.enter_recursive(SimpleContext())
        result = node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 10.0

        # Test with different context value
        different_context = SimpleContext(value=25)
        result = node.render(self.mock_frame, self.mock_scheme, different_context)
        assert result == 25.0

        node.exit_recursive()

    def test_nested_operations(self):
        """Test nested arithmetic operations: (10 + 20) * (3 * 4)."""
        # Left side: 10 + 20 = 30
        left_child1 = ConstantNode(10.0)
        left_child2 = ConstantNode(20.0)
        left_add = AddNode([left_child1, left_child2])

        # Right side: 3 * 4 = 12
        right_child1 = ConstantNode(3.0)
        right_child2 = ConstantNode(4.0)
        right_multiply = MultiplyNode([right_child1, right_child2])

        # Top level: 30 * 12 = 360
        # Note: This requires a different type structure since we're mixing operations
        # For now, let's test the components separately

        left_add.enter_recursive(SimpleContext())
        left_result = left_add.render(self.mock_frame, self.mock_scheme, self.context)
        assert left_result == 30.0
        left_add.exit_recursive()

        right_multiply.enter_recursive(SimpleContext())
        right_result = right_multiply.render(
            self.mock_frame, self.mock_scheme, self.context
        )
        assert right_result == 12.0
        right_multiply.exit_recursive()

    def test_generate_recursive(self):
        """Test that generate_recursive calls generate on all input nodes."""
        child1 = ConstantNode(5.0)
        child2 = ConstantNode(7.0)
        add_node = AddNode([child1, child2])

        # Mock the generate methods to track calls
        child1.generate = Mock()
        child2.generate = Mock()
        add_node.generate = Mock()

        add_node.generate_recursive(self.mock_vibe)

        # Verify that generate was called on the parent and all children
        add_node.generate.assert_called_once_with(self.mock_vibe)
        child1.generate.assert_called_once_with(self.mock_vibe)
        child2.generate.assert_called_once_with(self.mock_vibe)

    def test_empty_add_node(self):
        """Test add node with no children."""
        add_node = AddNode([])

        add_node.enter_recursive(SimpleContext())
        result = add_node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 0.0
        add_node.exit_recursive()

    def test_empty_multiply_node(self):
        """Test multiply node with no children."""
        multiply_node = MultiplyNode([])

        multiply_node.enter_recursive(SimpleContext())
        result = multiply_node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 1.0
        multiply_node.exit_recursive()

    def test_single_child_operations(self):
        """Test operations with single children."""
        child = ConstantNode(42.0)

        add_node = AddNode([child])
        add_node.enter_recursive(SimpleContext())
        assert add_node.render(self.mock_frame, self.mock_scheme, self.context) == 42.0
        add_node.exit_recursive()

        multiply_node = MultiplyNode([child])
        multiply_node.enter_recursive(SimpleContext())
        assert (
            multiply_node.render(self.mock_frame, self.mock_scheme, self.context)
            == 42.0
        )
        multiply_node.exit_recursive()

    def test_all_inputs_property(self):
        """Test that all_inputs property returns children by default."""
        child1 = ConstantNode(10.0)
        child2 = ConstantNode(20.0)
        add_node = AddNode([child1, child2])

        # Test that all_inputs returns the same as children
        assert add_node.all_inputs == add_node.children
        assert len(add_node.all_inputs) == 2
        assert child1 in add_node.all_inputs
        assert child2 in add_node.all_inputs

    def test_enter_recursive(self):
        """Test that enter_recursive calls enter on this node and all input nodes."""
        child1 = ConstantNode(5.0)
        child2 = ConstantNode(7.0)
        add_node = AddNode([child1, child2])

        # Mock the enter methods to track calls
        child1.enter = Mock()
        child2.enter = Mock()
        add_node.enter = Mock()

        add_node.enter_recursive(SimpleContext())

        # Verify that enter was called on the parent and all children
        add_node.enter.assert_called_once()
        child1.enter.assert_called_once()
        child2.enter.assert_called_once()

    def test_exit_recursive(self):
        """Test that exit_recursive calls exit on this node and all input nodes."""
        child1 = ConstantNode(5.0)
        child2 = ConstantNode(7.0)
        add_node = AddNode([child1, child2])

        # Mock the exit methods to track calls
        child1.exit = Mock()
        child2.exit = Mock()
        add_node.exit = Mock()

        add_node.exit_recursive()

        # Verify that exit was called on the parent and all children
        add_node.exit.assert_called_once()
        child1.exit.assert_called_once()
        child2.exit.assert_called_once()

    def test_recursive_methods_integration(self):
        """Test integration of recursive enter, generate, and exit methods."""
        child1 = ConstantNode(10.0)
        child2 = ConstantNode(20.0)
        add_node = AddNode([child1, child2])

        # Test full lifecycle with recursive methods
        add_node.enter_recursive(SimpleContext())

        # Verify all nodes are entered
        assert add_node.entered
        assert child1.entered
        assert child2.entered

        # Test recursive generation
        add_node.generate_recursive(self.mock_vibe)

        # Test rendering still works
        result = add_node.render(self.mock_frame, self.mock_scheme, self.context)
        assert result == 30.0

        # Test recursive exit
        add_node.exit_recursive()

        # Verify all nodes are exited
        assert not add_node.entered
        assert not child1.entered
        assert not child2.entered


class TestRandomNode:
    """Test cases for the Random node."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_frame = Mock(spec=Frame)
        self.mock_scheme = Mock(spec=ColorScheme)
        self.mock_vibe = Mock(spec=Vibe)
        self.mock_vibe.mode = Mock(spec=Mode)
        self.context = SimpleContext(value=5)

    def test_random_node_initialization(self):
        """Test that Random node initializes with operations."""
        children = [ConstantNode(10.0), ConstantNode(20.0)]
        operations = [AddNode, MultiplyNode]

        random_node = Random(children, operations)

        # Should have realized operations
        assert len(random_node.realized_operations) == 2
        assert random_node.current_operation is not None
        assert random_node.current_operation in random_node.realized_operations

    def test_random_node_enter_exit(self):
        """Test that Random node properly manages enter/exit of current operation."""
        children = [ConstantNode(10.0)]
        operations = [AddNode]

        random_node = Random(children, operations)

        # Mock the current operation
        random_node.current_operation.enter = Mock()
        random_node.current_operation.exit = Mock()

        random_node.enter_recursive(SimpleContext())
        random_node.current_operation.enter.assert_called_once()

        random_node.exit_recursive()
        random_node.current_operation.exit.assert_called_once()

    def test_random_node_render_delegation(self):
        """Test that Random node delegates render to current operation."""
        children = [ConstantNode(15.0)]
        operations = [AddNode]

        random_node = Random(children, operations)

        # Mock the render method
        expected_result = 42.0
        random_node.current_operation.render = Mock(return_value=expected_result)

        result = random_node.render(self.mock_frame, self.mock_scheme, self.context)

        assert result == expected_result
        random_node.current_operation.render.assert_called_once_with(
            self.mock_frame, self.mock_scheme, self.context
        )

    def test_random_node_all_inputs(self):
        """Test that Random node's all_inputs returns children."""
        children = [ConstantNode(10.0), ConstantNode(20.0)]
        operations = [AddNode]

        random_node = Random(children, operations)

        # Random node should return its children as all_inputs
        assert random_node.all_inputs == children
        assert len(random_node.all_inputs) == 2

    def test_random_node_generate_recursive(self):
        """Test that Random node properly delegates generate_recursive."""
        children = [ConstantNode(10.0)]
        operations = [AddNode]

        random_node = Random(children, operations)

        # Mock the generate_recursive method on current operation
        random_node.current_operation.generate_recursive = Mock()
        random_node.generate = Mock()

        random_node.generate_recursive(self.mock_vibe)

        # Verify that generate was called on random node and generate_recursive on current operation
        random_node.generate.assert_called_once_with(self.mock_vibe)
        random_node.current_operation.generate_recursive.assert_called_once_with(
            self.mock_vibe, 1.0
        )


if __name__ == "__main__":
    pytest.main([__file__])
