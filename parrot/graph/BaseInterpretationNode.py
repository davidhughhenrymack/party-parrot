from __future__ import annotations
from abc import ABC, abstractmethod
import random
from typing import Any, Generic, List, Optional, Type, TypeVar
from dataclasses import dataclass

from parrot.director.frame import Frame
from parrot.director.frame import FrameSignal
from beartype import beartype
from colorama import Fore, Style
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

    def enter(self, context: C):
        """
        Called when the node is being entered (e.g. when it will start to be rendered)
        In enter resources should be allocated. A call to enter will always be followed
        by a call to generate(), and later, by a call to exit().
        render() will never be called before enter()
        """
        pass

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

    def render(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: C,
    ) -> RR:
        """
        Render the node. Rendering code is expected to call .render() on any children
        or props that are needed.

        Args:
            frame: The current audio frame data
            scheme: The current color scheme
            context: The rendering context (e.g. ModernGL context)
        """
        pass

    def print_self(self) -> str:
        """
        Return a string representation of this node for tree printing.
        Default implementation returns the class name.
        Subclasses can override to provide more information.
        """
        return self.__class__.__name__

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
            return f"{indent}{'└── ' if is_last else '├── '}{self.print_self()} (circular reference)\n"

        visited.add(node_id)

        # Current node
        connector = "└── " if is_last else "├── "
        result = f"{indent}{connector}{self.print_self()}\n"

        # Children
        inputs = self.all_inputs
        for i, input_node in enumerate(inputs):
            is_last_child = i == len(inputs) - 1
            child_indent = indent + ("    " if is_last else "│   ")
            result += input_node.print_tree(child_indent, is_last_child, visited.copy())

        return result

    # Intentionally no base print_self formatting wrapper to avoid implicit emoji registry.


# No global emoji registry: each node supplies its own emoji in print_self.


@beartype
def format_node_status(
    node_name: str,
    *,
    emoji: str | None = None,
    signal: FrameSignal | str | None = None,
    **numeric_props: float | int | tuple[float | int, int | str] | None,
) -> str:
    """
    Build a consistent, colored status string for nodes.

    Example output:
      "✨ GlowEffect [freq_low, intensity:0.75, radius:4.0]"

    Args:
        node_name: Class or display name of the node
        emoji: Optional emoji to prefix
        signal: Optional FrameSignal or string to display
        numeric_props: Numeric key=value pairs to include (floats formatted to 2 decimals)

    Returns:
        Formatted string suitable for print_self()
    """

    # Label with emoji + colored node name
    emoji_part = f"{emoji} " if emoji else ""
    label = f"{emoji_part}{Fore.CYAN}{node_name}{Style.RESET_ALL}"

    # Components inside brackets
    parts: list[str] = []

    if signal is not None:
        sig_str = signal.name if hasattr(signal, "name") else str(signal)
        parts.append(f"{Fore.YELLOW}{sig_str}{Style.RESET_ALL}")

    for key, value in numeric_props.items():
        if value is None:
            continue
        # Support explicit formatting via tuples: (number, precision|format_spec)
        val_str: str
        if isinstance(value, tuple) and len(value) == 2:
            num, fmt = value
            try:
                if isinstance(fmt, int):
                    # Decimal places
                    val_str = f"{float(num):.{fmt}f}"
                elif isinstance(fmt, str):
                    # Either format spec or full format template
                    if "{" in fmt and "}" in fmt:
                        val_str = fmt.format(num)
                    else:
                        val_str = format(num, fmt)
                else:
                    val_str = f"{num}"
            except Exception:
                val_str = f"{num}"
        else:
            if isinstance(value, float):
                val_str = f"{value:.2f}"
            else:
                val_str = f"{value}"
        parts.append(f"{key}:{Fore.WHITE}{val_str}{Style.RESET_ALL}")

    inner = ", ".join(parts)
    return f"{label} [{inner}]" if inner else label


# No mixin; nodes call format_node_status(...) directly inside their own print_self.


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

    def render(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: C,
    ) -> RR:
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

    def __init__(
        self,
        child_options: List[BaseInterpretationNode[C, Any, RR]],
        weights: Optional[List[float]] = None,
    ):
        super().__init__([])
        self.child_options = child_options
        self.weights = weights
        self._current_child: BaseInterpretationNode[C, Any, RR] = None
        self._context: C | None = None
        self._child_entered: bool = False
        self._current_threshold: float = 1.0

        # Validate weights if provided
        if self.weights is not None:
            if len(self.weights) != len(self.child_options):
                raise ValueError(
                    f"Number of weights ({len(self.weights)}) must match number of child options ({len(self.child_options)})"
                )
            if any(w < 0 for w in self.weights):
                raise ValueError("All weights must be non-negative")
            if sum(self.weights) == 0:
                raise ValueError("At least one weight must be positive")

    @property
    def all_inputs(self) -> List[BaseInterpretationNode[C, Any, RI]]:
        # Prevent base enter/exit/generate recursion from touching all children.
        if self._current_child is not None:
            return [self._current_child]
        return []

    def enter(self, context: C):
        self._context = context
        # If we have a current child that wasn't entered yet, enter it now
        if self._current_child is not None and not self._child_entered:
            self._current_child.enter_recursive(self._context)
            self._child_entered = True

    def exit(self):
        self._context = None
        self._child_entered = False

    def generate(self, vibe: Vibe):
        # Select a child at random (if any), and re-enter it fresh every time.
        if not self.child_options:
            new_child = None
        elif self.weights is not None:
            # Use weighted random selection
            new_child = random.choices(self.child_options, weights=self.weights)[0]
        else:
            # Use uniform random selection (original behavior)
            new_child = random.choice(self.child_options)

        # Exit the previous child regardless of whether the selection changes.
        if self._current_child is not None:
            self._current_child.exit_recursive()

        self._current_child = new_child
        self._child_entered = False
        if self._current_child is not None:
            # Only enter the child if we have a context
            if self._context is not None:
                self._current_child.enter_recursive(self._context)
                self._child_entered = True
            self._current_child.generate_recursive(vibe, self._current_threshold)

    def generate_recursive(self, vibe: Vibe, threshold: float = 1.0):
        """
        Override to prevent double generation of the current child.
        The base class would call generate() then generate_recursive() on all_inputs,
        but our generate() already calls generate_recursive() on the selected child.
        """
        if random.random() < threshold:
            self._current_threshold = threshold
            self.generate(vibe)
            # Don't call generate_recursive on all_inputs since generate() already did it

    def render(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: C,
    ) -> RR:
        if self._current_child is None:
            raise RuntimeError(
                "RandomChild has no selected child. Call generate() before render()."
            )
        return self._current_child.render(frame, scheme, context)
