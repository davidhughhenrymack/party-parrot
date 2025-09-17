from __future__ import annotations
from abc import ABC, abstractmethod
import random
from typing import Any, Generic, List, Type, TypeVar
from dataclasses import dataclass

from parrot.director.frame import Frame
from parrot.director.mode import Mode
from parrot.director.color_scheme import ColorScheme


@dataclass
class Vibe:
    mode: Mode


C = TypeVar("RenderContext")
RI = TypeVar("RenderInput")
RR = TypeVar("RenderResult")


class BaseInterpretationNode(ABC, Generic[C, RI, RR]):
    """
    Abstract base class for a node in a graph.
    """

    def __init__(self, children: List[BaseInterpretationNode[C, Any, RI]] = []):
        self.children = children

    @property
    def all_inputs(self) -> List[BaseInterpretationNode[C, Any, RI]]:
        """
        Returns all input nodes that this node depends on.
        Default implementation returns children, but subclasses can override
        to include other types of input nodes.
        """
        return self.children

    @abstractmethod
    def enter(self, context: C):
        """
        Called when the node is being entered (e.g. when it will start to be rendered)
        In enter resources should be allocated. A call to enter will always be followed
        by a call to generate(), and later, by a call to exit().
        render() will never be called before enter()
        """
        pass

    @abstractmethod
    def exit(self):
        """
        Called when the node is being exited (e.g. when it will stop being rendered)
        In exit resources should be freed.
        render() will never be called after exit().
        """
        pass

    def enter_recursive(self, context: C):
        """
        Recursively enters this node and all its input nodes.
        Calls enter() on this node, then enter_recursive() on all nodes in all_inputs.
        """
        self.enter(context)
        for input_node in self.all_inputs:
            input_node.enter_recursive(context)

    def exit_recursive(self):
        """
        Recursively exits this node and all its input nodes.
        Calls exit() on this node, then exit_recursive() on all nodes in all_inputs.
        """
        self.exit()
        for input_node in self.all_inputs:
            input_node.exit_recursive()

    @abstractmethod
    def generate(self, vibe: Vibe):
        """
        This node should configure itself based on the vibe.
        This generally triggers a randomization of the node's parameters.
        Always called at least once after enter() and before any render()
        """
        pass

    def generate_recursive(self, vibe: Vibe, threshold: float = 1.0):
        """
        Recursively generates this node and all its input nodes.
        Calls generate() on this node, then generate_recursive() on all nodes in all_inputs.
        If your class has other types of input nodes beyond all_inputs, override this method.

        Args:
            vibe: The vibe to generate for
            threshold: Probability (0.0-1.0) of calling generate on this node and descendants
        """
        if random.random() < threshold:
            self.generate(vibe)
            for input_node in self.all_inputs:
                input_node.generate_recursive(vibe, threshold)

    def render(self, frame: Frame, scheme: ColorScheme, context: C) -> RR:
        """
        Render the node. Rendering code is expected to call .render() on any children
        or props that are needed.
        """
        pass

    def print_tree(
        self, indent: str = "", is_last: bool = True, visited: set = None
    ) -> str:
        """
        Print a tree representation of this node and all its input nodes.

        Args:
            indent: Current indentation string
            is_last: Whether this is the last child at this level
            visited: Set of visited nodes to prevent infinite loops

        Returns:
            String representation of the tree
        """
        if visited is None:
            visited = set()

        # Prevent infinite loops in case of circular references
        node_id = id(self)
        if node_id in visited:
            return f"{indent}{'└── ' if is_last else '├── '}{self.__class__.__name__} (circular reference)\n"

        visited.add(node_id)

        # Current node
        connector = "└── " if is_last else "├── "
        result = f"{indent}{connector}{self.__class__.__name__}\n"

        # Children
        inputs = self.all_inputs
        for i, input_node in enumerate(inputs):
            is_last_child = i == len(inputs) - 1
            child_indent = indent + ("    " if is_last else "│   ")
            result += input_node.print_tree(child_indent, is_last_child, visited.copy())

        return result


def pipeline(
    children: List[BaseInterpretationNode[C, RR, RR]],
    operations: List[Type[BaseInterpretationNode[C, RR, RR]]],
) -> BaseInterpretationNode[C, RR, RR]:
    result = children
    for operation in operations:
        result = operation(result)
    return result


class RandomOperation(BaseInterpretationNode[C, RR, RR]):
    def __init__(
        self,
        child: BaseInterpretationNode[C, RR, RR],
        operations: List[Type[BaseInterpretationNode[C, RR, RR]]],
    ):
        super().__init__([])
        self.realized_operations = [operation(child) for operation in operations]
        self.current_operation = random.choice(self.realized_operations)
        self._context = None

    @property
    def all_inputs(self) -> List[BaseInterpretationNode[C, Any, RI]]:
        return [self.current_operation] if self.current_operation else []

    def enter(self, context: C):
        self._context = context

    def exit(self):
        self._context = None

    def generate(self, vibe: Vibe):
        new_operation = random.choice(self.realized_operations)
        if new_operation != self.current_operation:
            self.current_operation.exit_recursive()
            self.current_operation = new_operation
            if self._context is not None:
                self.current_operation.enter_recursive(self._context)
            self.current_operation.generate_recursive(vibe)

    def render(self, frame: Frame, scheme: ColorScheme, context: C) -> RR:
        return self.current_operation.render(frame, scheme, context)


class RandomChild(BaseInterpretationNode[C, RI, RR]):
    """
    A node that, on each generate call, selects one child at random and forwards
    render calls to that child. It exits the previously selected child (if any)
    and enters the newly selected child on every generate call, even if the
    selection does not change.

    This class overrides all_inputs to prevent the default recursive lifecycle
    from entering/exiting all children. Lifecycle for children is managed
    explicitly based on the current selection.
    """

    def __init__(self, child_options: List[BaseInterpretationNode[C, Any, RR]]):
        super().__init__([])
        self.child_options = child_options
        self._current_child: BaseInterpretationNode[C, Any, RR] = None
        self._context: C | None = None

    @property
    def all_inputs(self) -> List[BaseInterpretationNode[C, Any, RI]]:
        # Prevent base enter/exit/generate recursion from touching all children.
        if self._current_child is not None:
            return [self._current_child]
        return []

    def enter(self, context: C):
        self._context = context

    def exit(self):
        self._context = None

    def generate(self, vibe: Vibe):
        # Select a child at random (if any), and re-enter it fresh every time.
        new_child = random.choice(self.child_options) if self.child_options else None

        # Exit the previous child regardless of whether the selection changes.
        if self._current_child is not None:
            self._current_child.exit_recursive()

        self._current_child = new_child
        self._current_child.enter_recursive(self._context)
        self._current_child.generate_recursive(vibe)

    def render(self, frame: Frame, scheme: ColorScheme, context: C) -> RR:
        if self._current_child is None:
            raise RuntimeError(
                "RandomChild has no selected child. Call generate() before render()."
            )
        return self._current_child.render(frame, scheme, context)
