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

    def __init__(self, children: List[BaseInterpretationNode[C, Any, RI]]):
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
    def enter(self):
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

    def enter_recursive(self):
        """
        Recursively enters this node and all its input nodes.
        Calls enter() on this node, then enter_recursive() on all nodes in all_inputs.
        """
        self.enter()
        for input_node in self.all_inputs:
            input_node.enter_recursive()

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
        """
        pass

    def generate_recursive(self, vibe: Vibe):
        """
        Recursively generates this node and all its input nodes.
        Calls generate() on this node, then generate_recursive() on all nodes in all_inputs.
        If your class has other types of input nodes beyond all_inputs, override this method.
        """
        self.generate(vibe)
        for input_node in self.all_inputs:
            input_node.generate_recursive(vibe)

    def render(self, frame: Frame, scheme: ColorScheme, context: C) -> RR:
        """
        Render the node. Rendering code is expected to call .render() on any children
        or props that are needed.
        """
        pass


def pipeline(
    children: List[BaseInterpretationNode[C, RR, RR]],
    operations: List[Type[BaseInterpretationNode[C, RR, RR]]],
) -> BaseInterpretationNode[C, RR, RR]:
    result = children
    for operation in operations:
        result = operation(result)
    return result


class Random(BaseInterpretationNode[C, RR, RR]):
    def __init__(
        self,
        children: List[BaseInterpretationNode[C, RR, RR]],
        operations: List[Type[BaseInterpretationNode[C, RR, RR]]],
    ):
        super().__init__(children)
        self.realized_operations = [operation(children) for operation in operations]

        self.current_operation = random.choice(self.realized_operations)

    def enter(self):
        self.current_operation.enter()

    def exit(self):
        self.current_operation.exit()

    def generate(self, vibe: Vibe):
        new_operation = random.choice(self.realized_operations)
        if new_operation != self.current_operation:
            self.current_operation.exit()
            self.current_operation = new_operation
            self.current_operation.enter()

    def generate_recursive(self, vibe: Vibe):
        self.generate(vibe)
        self.current_operation.generate_recursive(vibe)

    def render(self, frame: Frame, scheme: ColorScheme, context: C) -> RR:
        return self.current_operation.render(frame, scheme, context)
