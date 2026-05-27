#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np
from beartype import beartype
from scipy import signal

from parrot.audio.beat_tracker import BeatTracker
from parrot.director.frame import FrameSignal

RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
SPECTOGRAPH_BUFFER_SIZE = 275 * 3
SIGNAL_STAT_PERIOD_SECONDS = 10.0
SIGNAL_STAT_BUFFER_SIZE = round(60 / SIGNAL_STAT_PERIOD_SECONDS)

KNOWN_TRACKS = (
    (
        Path("/Users/dmackparty/Music/DJ/Playlist/2026 Queer prom cunty/103 - SLUT.mp3"),
        132.0,
    ),
    (
        Path(
            "/Users/dmackparty/Music/DJ/Playlist/2026 Queer prom cunty/66 - Case Of The Ex Whatcha Gonna Do.mp3"
        ),
        98.0,
    ),
)


@beartype
class OfflineLowFrequencyAnalyzer:
    def __init__(self):
        self.spectrogram_buffer: np.ndarray | None = None
        self.signal_stat_buffer = {
            key: {"max": [], "min": []}
            for key in (
                FrameSignal.freq_all,
                FrameSignal.freq_high,
                FrameSignal.freq_low,
            )
        }
        self.signal_stat_last = 0.0

    def process_audio_block(self, snd_block: np.ndarray, now: float) -> float:
        _frequencies, _times, spectrogram = signal.spectrogram(snd_block)
        if self.spectrogram_buffer is None:
            self.spectrogram_buffer = spectrogram
        else:
            self.spectrogram_buffer = np.concatenate(
                [self.spectrogram_buffer, spectrogram], axis=1
            )
        self.spectrogram_buffer = self.spectrogram_buffer[
            :, -SPECTOGRAPH_BUFFER_SIZE:
        ]
        return self.process_spectrogram(self.spectrogram_buffer, now)

    def process_spectrogram(self, spectrogram_block: np.ndarray, now: float) -> float:
        ranges = {
            FrameSignal.freq_all: (0, 129),
            FrameSignal.freq_high: (30, 129),
            FrameSignal.freq_low: (0, 30),
        }
        should_capture_signal_stats = (
            now - self.signal_stat_last > SIGNAL_STAT_PERIOD_SECONDS
        )
        if should_capture_signal_stats:
            self.signal_stat_last = now

        low_energy = 0.0
        for name, rg in ranges.items():
            x = np.sum(np.abs(spectrogram_block[rg[0] : rg[1], :]), axis=0)
            x = np.convolve(x, np.ones(3) / 3, mode="valid")
            x_min = np.percentile(x, 5)
            x_max = np.percentile(x, 95)
            if should_capture_signal_stats:
                self.signal_stat_buffer[name]["max"].append(x_max)
                self.signal_stat_buffer[name]["min"].append(x_min)
                self.signal_stat_buffer[name]["max"] = self.signal_stat_buffer[name][
                    "max"
                ][-SIGNAL_STAT_BUFFER_SIZE:]
                self.signal_stat_buffer[name]["min"] = self.signal_stat_buffer[name][
                    "min"
                ][-SIGNAL_STAT_BUFFER_SIZE:]

            x_min = np.min(
                np.concatenate([self.signal_stat_buffer[name]["min"], [x_min]])
            )
            x_max = np.max(
                np.concatenate([self.signal_stat_buffer[name]["max"], [x_max]])
            )
            x = (x - x_min) / (x_max - x_min + np.finfo(float).eps)
            x = np.clip(x, 0, 1)
            if name is FrameSignal.freq_low:
                low_energy = float(x[-1])
        return low_energy


@beartype
def decode_audio(path: Path) -> np.ndarray:
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(RATE),
        "-f",
        "f32le",
        "pipe:1",
    ]
    output = subprocess.check_output(command)
    return np.frombuffer(output, dtype=np.float32)


@beartype
def measure_bpm(path: Path) -> tuple[float, int]:
    samples = decode_audio(path)
    analyzer = OfflineLowFrequencyAnalyzer()
    tracker = BeatTracker()
    beat_count = 0
    bpm = 0.0
    for start in range(0, len(samples) - INPUT_FRAMES_PER_BLOCK, INPUT_FRAMES_PER_BLOCK):
        now = start / RATE
        block = samples[start : start + INPUT_FRAMES_PER_BLOCK]
        low_energy = analyzer.process_audio_block(block, now)
        state = tracker.update(low_energy, now=now)
        if state.beat:
            beat_count += 1
        bpm = state.bpm
    return bpm, beat_count


@beartype
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate Party Parrot BPM tracking.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional audio files to measure. Defaults to the known calibration tracks.",
    )
    return parser.parse_args()


@beartype
def main() -> int:
    args = parse_args()
    tracks = [(path, None) for path in args.paths] if args.paths else KNOWN_TRACKS
    for path, expected in tracks:
        bpm, beats = measure_bpm(path)
        expected_text = "" if expected is None else f" expected={expected:.1f}"
        delta_text = "" if expected is None else f" delta={bpm - expected:+.1f}"
        print(f"{path.name}: bpm={bpm:.1f}{expected_text}{delta_text} beats={beats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
