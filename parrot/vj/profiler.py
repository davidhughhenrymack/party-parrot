#!/usr/bin/env python3

import time
import os
from collections import defaultdict, deque
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from beartype import beartype


@beartype
class VJProfiler:
    """
    Profiler for VJ rendering pipeline that tracks timing of major components.
    Provides periodic reporting when PROFILE_VJ environment variable is set.
    """

    def __init__(self):
        self.enabled = os.getenv("PROFILE_VJ", "").lower() in ("true", "1", "yes")

        # Timing data storage - use deques to limit memory usage
        self.timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.call_counts: Dict[str, int] = defaultdict(int)

        # Reporting
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

        # Current operation stack for nested profiling
        self.operation_stack: List[str] = []
        self.start_times: Dict[str, float] = {}

    @contextmanager
    def profile(self, operation_name: str):
        """Context manager for profiling an operation"""
        if not self.enabled:
            yield
            return

        start_time = time.perf_counter()
        self.operation_stack.append(operation_name)

        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration = end_time - start_time

            # Record timing
            self.timings[operation_name].append(duration)
            self.call_counts[operation_name] += 1

            # Remove from stack
            if self.operation_stack and self.operation_stack[-1] == operation_name:
                self.operation_stack.pop()

            # Check if it's time to report
            self._maybe_report()

    def record_timing(self, operation_name: str, duration: float):
        """Manually record a timing measurement"""
        if not self.enabled:
            return

        self.timings[operation_name].append(duration)
        self.call_counts[operation_name] += 1
        self._maybe_report()

    def _maybe_report(self):
        """Check if it's time to print a report and do so if needed"""
        current_time = time.time()
        if current_time - self.last_report_time >= self.report_interval:
            self.print_stats()
            self.last_report_time = current_time

    def print_stats(self):
        """Print profiling statistics to console"""
        if not self.enabled or not self.timings:
            return

        print("\n" + "=" * 80)
        print(f"VJ PROFILING STATS (last {self.report_interval:.0f}s)")
        print("=" * 80)

        # Calculate stats for each operation
        stats = []
        for operation, times in self.timings.items():
            if not times:
                continue

            times_list = list(times)
            count = len(times_list)
            total_time = sum(times_list)
            avg_time = total_time / count
            min_time = min(times_list)
            max_time = max(times_list)

            # Calculate percentiles
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
                    "fps": (
                        count / self.report_interval if count > 0 else 0
                    ),  # Approximate FPS over report interval
                }
            )

        # Sort by total time (most expensive operations first)
        stats.sort(key=lambda x: x["total_ms"], reverse=True)

        # Print header
        print(
            f"{'Operation':<25} {'Count':<6} {'Avg(ms)':<8} {'Min(ms)':<8} {'Max(ms)':<8} {'P50(ms)':<8} {'P95(ms)':<8} {'Total(ms)':<10} {'FPS':<6}"
        )
        print("-" * 80)

        # Print stats
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

        # Calculate total rendering time and theoretical max FPS
        total_render_time = sum(
            stat["total_ms"] for stat in stats if "render" in stat["operation"].lower()
        )
        if total_render_time > 0:
            avg_frame_time = (
                total_render_time / max(1, stats[0]["count"]) if stats else 0
            )
            theoretical_fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0
            print(f"Total render time: {total_render_time:.2f}ms")
            print(f"Avg frame time: {avg_frame_time:.2f}ms")
            print(f"Theoretical max FPS: {theoretical_fps:.1f}")

        print("=" * 80)

    def get_stats(self) -> Dict[str, Any]:
        """Get current profiling statistics as a dictionary"""
        if not self.enabled:
            return {}

        stats = {}
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

    def reset_stats(self):
        """Reset all profiling statistics"""
        self.timings.clear()
        self.call_counts.clear()
        self.last_report_time = time.time()

    def is_enabled(self) -> bool:
        """Check if profiling is enabled"""
        return self.enabled


# Global profiler instance
vj_profiler = VJProfiler()
