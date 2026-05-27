from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from beartype import beartype


@beartype
@dataclass(frozen=True)
class BeatState:
    bpm: float
    beat: bool
    beat_count: int
    bar_progress: float


@beartype
class BeatTracker:
    """Track low-frequency energy spikes as musical beats."""

    def __init__(
        self,
        min_bpm: float = 60.0,
        max_bpm: float = 160.0,
        default_bpm: float = 120.0,
        history_seconds: float = 6.0,
    ):
        self.min_bpm = min_bpm
        self.max_bpm = max_bpm
        self.default_bpm = default_bpm
        self.history_seconds = history_seconds
        self._min_interval = 60.0 / max_bpm
        self._max_interval = 60.0 / min_bpm
        self._refractory_seconds = self._min_interval * 0.72
        self._energy_history: list[tuple[float, float]] = []
        self._beat_intervals: list[float] = []
        self._last_energy: float | None = None
        self._last_beat_time: float | None = None
        self._beat_count = -1
        self._bpm = 0.0

    def update(self, low_energy: float, now: float | None = None) -> BeatState:
        now = time.perf_counter() if now is None else now
        energy = float(np.clip(low_energy, 0.0, 1.0))
        threshold = self._current_threshold()

        beat = False
        previous = self._last_energy
        if previous is not None:
            crossed_threshold = previous < threshold <= energy
            sharp_rise = energy >= threshold and energy - previous >= 0.18
            enough_time_elapsed = (
                self._last_beat_time is None
                or now - self._last_beat_time >= self._refractory_seconds
            )
            beat = enough_time_elapsed and (crossed_threshold or sharp_rise)

        self._remember_energy(now, energy)
        self._last_energy = energy

        if beat:
            self._record_beat(now)

        return BeatState(
            bpm=self._bpm,
            beat=beat,
            beat_count=max(self._beat_count, 0),
            bar_progress=self._bar_progress(now),
        )

    def _remember_energy(self, now: float, energy: float) -> None:
        self._energy_history.append((now, energy))
        cutoff = now - self.history_seconds
        self._energy_history = [
            (sample_time, sample_energy)
            for sample_time, sample_energy in self._energy_history
            if sample_time >= cutoff
        ]

    def _current_threshold(self) -> float:
        if len(self._energy_history) < 8:
            return 0.45
        energies = np.array([energy for _, energy in self._energy_history])
        floor = float(np.percentile(energies, 50))
        peak = float(np.percentile(energies, 95))
        threshold = floor + (peak - floor) * 0.62
        return float(np.clip(threshold, 0.35, 0.85))

    def _record_beat(self, now: float) -> None:
        if self._last_beat_time is not None:
            interval = now - self._last_beat_time
            if interval > self._max_interval * 2.0:
                self._beat_intervals = []
            elif self._min_interval * 0.8 <= interval <= self._max_interval * 1.2:
                self._beat_intervals.append(interval)
                self._beat_intervals = self._beat_intervals[-12:]
                median_interval = float(np.median(np.array(self._beat_intervals)))
                measured_bpm = 60.0 / median_interval
                while measured_bpm < self.min_bpm:
                    measured_bpm *= 2.0
                while measured_bpm > self.max_bpm:
                    measured_bpm *= 0.5
                self._bpm = float(np.clip(measured_bpm, self.min_bpm, self.max_bpm))

        self._last_beat_time = now
        self._beat_count = (self._beat_count + 1) % 64

    def _bar_progress(self, now: float) -> float:
        if self._last_beat_time is None or self._beat_count < 0:
            return 0.0
        beat_period = 60.0 / (self._bpm if self._bpm > 0.0 else self.default_bpm)
        elapsed_since_beat = max(0.0, now - self._last_beat_time)
        beat_position = (self._beat_count % 4) + elapsed_since_beat / beat_period
        return float(np.clip(beat_position / 4.0, 0.0, 1.0))
