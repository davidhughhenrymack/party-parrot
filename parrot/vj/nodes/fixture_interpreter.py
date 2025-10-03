#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import moderngl as mgl
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterBase


InterpreterFactory = Callable[[Mode, List[FixtureBase]], Optional[InterpreterBase]]


@dataclass
class FixtureInterpreterState:
    """Internal bookkeeping for the interpreter lifecycle."""

    mode: Mode
    interpreter: Optional[InterpreterBase]


@beartype
class FixtureInterpreterNode(
    BaseInterpretationNode[mgl.Context, None, List[FixtureBase]]
):
    """
    Node that drives a list of fixtures using a DMX interpreter each frame.

    The provided interpreter_factory is responsible for returning an
    InterpreterBase instance for the requested Mode. The interpreter is
    re-created on every generate() call so it can respond to Mode shifts in
    the wider render graph.
    """

    def __init__(
        self,
        fixtures: List[FixtureBase],
        interpreter_factory: InterpreterFactory,
        initial_mode: Mode,
    ):
        super().__init__([])
        self._fixtures = fixtures
        self._factory = interpreter_factory
        self._state = FixtureInterpreterState(mode=initial_mode, interpreter=None)
        self._last_frame: Optional[Frame] = None
        self._last_scheme: Optional[ColorScheme] = None

    @property
    def fixtures(self) -> List[FixtureBase]:
        return self._fixtures

    def _create_interpreter(self, mode: Mode) -> Optional[InterpreterBase]:
        interpreter = self._factory(mode, self._fixtures)
        self._state = FixtureInterpreterState(mode=mode, interpreter=interpreter)
        return interpreter

    def _ensure_interpreter(self, mode: Mode) -> Optional[InterpreterBase]:
        state = self._state
        if state.interpreter is not None and state.mode == mode:
            return state.interpreter
        if state.interpreter is not None:
            try:
                state.interpreter.exit(self._last_frame, self._last_scheme)  # type: ignore[arg-type]
            except Exception:
                pass
        return self._create_interpreter(mode)

    def enter(self, context: mgl.Context):
        self._ensure_interpreter(self._state.mode)

    def exit(self):
        if self._state.interpreter is not None:
            try:
                self._state.interpreter.exit(self._last_frame, self._last_scheme)  # type: ignore[arg-type]
            except Exception:
                pass
        self._state = FixtureInterpreterState(mode=self._state.mode, interpreter=None)

    def generate(self, vibe: Vibe):
        self._ensure_interpreter(vibe.mode)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> List[FixtureBase]:
        interpreter = self._ensure_interpreter(self._state.mode)
        if interpreter is not None:
            interpreter.step(frame, scheme)
        self._last_frame = frame
        self._last_scheme = scheme
        return self._fixtures
