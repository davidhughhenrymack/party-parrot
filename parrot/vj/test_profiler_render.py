from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
from parrot.vj.profiler import (
    vj_profiler,
    _node_ids,
    _render_stack_local,
    _install_node_render_profiling,
)


class _FrameStub:
    pass


class _SchemeStub:
    pass


class _LeafNode(BaseInterpretationNode[None, None, str]):
    def __init__(self):
        super().__init__([])

    def render(self, frame: _FrameStub, scheme: _SchemeStub, context: None) -> str:
        return "leaf"


class _ParentNode(BaseInterpretationNode[None, None, str]):
    def __init__(self, child: BaseInterpretationNode):
        super().__init__([child])
        self._child = child

    def render(self, frame: _FrameStub, scheme: _SchemeStub, context: None) -> str:
        return self._child.render(frame, scheme, context)


def _clear_profiler_state():
    _install_node_render_profiling()
    vj_profiler.reset_stats()
    _node_ids.clear()
    if hasattr(_render_stack_local, "stack"):
        delattr(_render_stack_local, "stack")


def test_render_profiling_disabled():
    _clear_profiler_state()
    vj_profiler.enabled = False

    parent = _ParentNode(_LeafNode())

    parent.render(_FrameStub(), _SchemeStub(), None)

    assert vj_profiler.get_stats() == {}


def test_render_profiling_records_each_node():
    _clear_profiler_state()
    vj_profiler.enabled = True

    parent = _ParentNode(_LeafNode())

    parent.render(_FrameStub(), _SchemeStub(), None)

    stats = vj_profiler.get_stats()
    assert len(stats) == 2
    assert any(name.startswith("node_render:_ParentNode") for name in stats)
    assert any(name.startswith("node_render:_LeafNode") for name in stats)

    vj_profiler.enabled = False
