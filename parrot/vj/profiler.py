#!/usr/bin/env python3

import os
import sys
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from functools import wraps
from itertools import count
from threading import local
from weakref import WeakKeyDictionary

from beartype import beartype
from beartype.typing import Any, Callable, Dict, List

try:
    import moderngl as mgl  # type: ignore
except ImportError:  # pragma: no cover - optional dependency isn't always present
    mgl = None
else:
    sys.modules.setdefault("mgl", mgl)


_render_stack_local = local()
_node_ids: WeakKeyDictionary[Any, int] = WeakKeyDictionary()
_node_id_counter = count(1)
_hook_installed = False


@beartype
def _record_render_timing(operation_name: str, duration: float) -> None:
    if not vj_profiler.enabled:
        return
    vj_profiler.timings[operation_name].append(duration)
    vj_profiler.call_counts[operation_name] += 1
    vj_profiler._maybe_report()


@beartype
def _instrument_render_call(
    node: Any,
    render_fn: Callable[[Any, Any, Any, Any], Any],
    frame: Any,
    scheme: Any,
    context: Any,
) -> Any:
    stack = getattr(_render_stack_local, "stack", None)
    if stack is None:
        stack = []
        _render_stack_local.stack = stack

    if not vj_profiler.enabled:
        stack.append(None)
        try:
            return render_fn(node, frame, scheme, context)
        finally:
            stack.pop()

    node_id = _node_ids.get(node)
    if node_id is None:
        node_id = next(_node_id_counter)
        _node_ids[node] = node_id

    entry_name = f"node_render:{node.__class__.__name__}#{node_id}"

    start = time.perf_counter()
    stack.append(entry_name)
    try:
        return render_fn(node, frame, scheme, context)
    finally:
        end = time.perf_counter()
        stack.pop()
        _record_render_timing(entry_name, end - start)


@beartype
def _install_node_render_profiling() -> None:
    global _hook_installed
    if _hook_installed:
        return

    try:
        from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
    except Exception:
        return

    def wrap_render_for_class(cls: type[Any]) -> None:
        if not issubclass(cls, BaseInterpretationNode):
            return

        render_fn = cls.__dict__.get("render")
        if render_fn is None or getattr(render_fn, "__vj_profiler_wrapped__", False):
            return

        @wraps(render_fn)
        def instrumented_render(
            self: Any, frame: Any, scheme: Any, context: Any
        ) -> Any:
            return _instrument_render_call(self, render_fn, frame, scheme, context)

        instrumented_render.__vj_profiler_wrapped__ = True
        setattr(cls, "render", instrumented_render)

    def wrap_render_tree(root: type[Any]) -> None:
        wrap_render_for_class(root)
        for subclass in list(root.__subclasses__()):
            wrap_render_tree(subclass)

    wrap_render_tree(BaseInterpretationNode)

    original_init_subclass = BaseInterpretationNode.__dict__.get("__init_subclass__")

    def instrumented_init_subclass(cls: type[Any], **kwargs: Any) -> None:
        if original_init_subclass is not None:
            original_init_subclass(cls, **kwargs)
        wrap_render_for_class(cls)
        for subclass in list(cls.__subclasses__()):
            wrap_render_tree(subclass)

    instrumented_init_subclass.__vj_profiler_wrapped__ = True
    BaseInterpretationNode.__init_subclass__ = classmethod(instrumented_init_subclass)

    _hook_installed = True


@beartype
class VJProfiler:
    """Runtime profiler that records timing metrics for VJ operations and nodes."""

    def __init__(self) -> None:
        self.enabled = os.getenv("PROFILE_VJ", "").lower() in ("true", "1", "yes")
        self.timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.call_counts: Dict[str, int] = defaultdict(int)
        self.last_report_time = time.time()

        interval_env = os.getenv("PROFILE_VJ_INTERVAL", "60")
        try:
            self.report_interval = max(1.0, float(interval_env))
        except ValueError:
            print(
                f"Warning: PROFILE_VJ_INTERVAL='{interval_env}' invalid, falling back to 60 seconds"
            )
            self.report_interval = 60.0

        if self.enabled:
            print(
                f"🟢 VJ profiler enabled (reporting every {self.report_interval:.0f}s)"
            )

        self.operation_stack: List[str] = []
        self.start_times: Dict[str, float] = {}

        _install_node_render_profiling()

    @contextmanager
    def profile(self, operation_name: str):
        if not self.enabled:
            yield
            return

        start_time = time.perf_counter()
        self.operation_stack.append(operation_name)
        try:
            yield
        finally:
            end_time = time.perf_counter()
            self.timings[operation_name].append(end_time - start_time)
            self.call_counts[operation_name] += 1

            if self.operation_stack and self.operation_stack[-1] == operation_name:
                self.operation_stack.pop()

            self._maybe_report()

    def record_timing(self, operation_name: str, duration: float) -> None:
        if not self.enabled:
            return
        self.timings[operation_name].append(duration)
        self.call_counts[operation_name] += 1
        self._maybe_report()

    def _maybe_report(self) -> None:
        current_time = time.time()
        if current_time - self.last_report_time >= self.report_interval:
            self.print_stats()
            self.last_report_time = current_time

    def print_stats(self) -> None:
        if not self.enabled or not self.timings:
            return

        print("\n" + "=" * 80)
        print(f"VJ PROFILING STATS (last {self.report_interval:.0f}s)")
        print("=" * 80)

        stats: List[Dict[str, Any]] = []
        for operation, times in self.timings.items():
            if not times:
                continue

            times_list = list(times)
            count = len(times_list)
            total_time = sum(times_list)
            avg_time = total_time / count
            min_time = min(times_list)
            max_time = max(times_list)
            sorted_times = sorted(times_list)
            p50 = sorted_times[len(sorted_times) // 2]
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[min(p95_idx, len(sorted_times) - 1)]

            stats.append(
                {
                    "operation": operation,
                    "count": count,
                    "total_calls": self.call_counts[operation],
                    "avg_ms": avg_time * 1000,
                    "min_ms": min_time * 1000,
                    "max_ms": max_time * 1000,
                    "p50_ms": p50 * 1000,
                    "p95_ms": p95 * 1000,
                    "total_ms": total_time * 1000,
                    "fps": count / self.report_interval if count > 0 else 0,
                }
            )

        stats.sort(key=lambda x: x["total_ms"], reverse=True)

        print(
            f"{'Operation':<25} {'Count':<6} {'Avg(ms)':<8} {'Min(ms)':<8} {'Max(ms)':<8} {'P50(ms)':<8} {'P95(ms)':<8} {'Total(ms)':<10} {'FPS':<6}"
        )
        print("-" * 80)
        for stat in stats:
            print(
                f"{stat['operation']:<25} "
                f"{stat['count']:<6} "
                f"{stat['avg_ms']:<8.2f} "
                f"{stat['min_ms']:<8.2f} "
                f"{stat['max_ms']:<8.2f} "
                f"{stat['p50_ms']:<8.2f} "
                f"{stat['p95_ms']:<8.2f} "
                f"{stat['total_ms']:<10.2f} "
                f"{stat['fps']:<6.1f}"
            )
        print("-" * 80)

        animate_stats = next(
            (s for s in stats if s["operation"] == "vj_animate_loop"), None
        )
        if animate_stats:
            avg_frame_time_ms = animate_stats["avg_ms"]
            achieved_fps = 1000.0 / avg_frame_time_ms if avg_frame_time_ms > 0 else 0.0
            print(f"Achieved FPS (end-to-end): {achieved_fps:.1f}")

        op_to_avg_ms = {s["operation"]: s["avg_ms"] for s in stats}
        critical_ops = [
            "vj_director_render",
            "concert_stage_render",
            "vj_render_to_fbo",
            "vj_gpu_scale",
            "vj_fbo_read",
            "vj_image_processing",
            "vj_blit_to_screen",
        ]
        critical_total_ms = sum(op_to_avg_ms.get(name, 0.0) for name in critical_ops)
        if critical_total_ms > 0:
            achievable_fps = 1000.0 / critical_total_ms
            print(f"Achievable FPS (critical path est.): {achievable_fps:.1f}")

        total_render_time = sum(
            stat["total_ms"] for stat in stats if "render" in stat["operation"].lower()
        )
        if total_render_time > 0 and stats:
            avg_render_only_frame_time = total_render_time / max(1, stats[0]["count"])
            theoretical_fps = (
                1000.0 / avg_render_only_frame_time
                if avg_render_only_frame_time > 0
                else 0
            )
            print(f"Total render time: {total_render_time:.2f}ms")
            print(f"Avg render-only frame time: {avg_render_only_frame_time:.2f}ms")
            print(f"Theoretical max FPS (render-only): {theoretical_fps:.1f}")

        print("=" * 80)

    def get_stats(self) -> Dict[str, Any]:
        if not self.enabled:
            return {}
        stats: Dict[str, Any] = {}
        for operation, times in self.timings.items():
            if not times:
                continue
            times_list = list(times)
            count = len(times_list)
            total_time = sum(times_list)
            stats[operation] = {
                "count": count,
                "total_calls": self.call_counts[operation],
                "avg_ms": (total_time / count) * 1000,
                "total_ms": total_time * 1000,
                "fps": count / self.report_interval if count > 0 else 0,
            }
        return stats

    def reset_stats(self) -> None:
        self.timings.clear()
        self.call_counts.clear()
        self.last_report_time = time.time()

    def is_enabled(self) -> bool:
        return self.enabled


vj_profiler = VJProfiler()
