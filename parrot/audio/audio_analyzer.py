#!/usr/bin/env python3

import sys
import time
import pyaudio
import numpy as np
from scipy import signal
from beartype import beartype
from typing import Optional, Dict, Callable

from parrot.director.frame import Frame, FrameSignal
from parrot.director.signal_states import SignalStates

# Audio constants
THRESHOLD = 0  # dB
RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001  # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
SPECTOGRAPH_BUFFER_SIZE = 275 * 3  # SPECTOGRAPH_AVG_RATE * 3
SIGNAL_STAT_PERIOD_SECONDS = 10
SIGNAL_STAT_BUFFER_SIZE = round((60) / SIGNAL_STAT_PERIOD_SECONDS)


@beartype
def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))


@beartype
class AudioAnalyzer:
    """Modular audio analyzer that listens to microphone and processes audio into frames"""

    def __init__(self, signal_states: Optional[SignalStates] = None):
        """Initialize audio analyzer

        Args:
            signal_states: Optional signal states to include in frames
        """
        self.signal_states = signal_states or SignalStates()

        # PyAudio setup
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()

        # Audio processing state
        self.threshold = THRESHOLD
        self.spectrogram_buffer: Optional[np.ndarray] = None
        self.signal_lookback = {
            FrameSignal.sustained_low: [],
            FrameSignal.sustained_high: [],
        }

        # Signal statistics for normalization
        self.signal_stat_buffer = {
            **{
                key: {
                    "max": [],
                    "min": [],
                }
                for key in FrameSignal
            },
        }
        self.signal_stat_last = 0

    def find_input_device(self) -> Optional[int]:
        """Find a suitable microphone input device"""
        device_index = None
        for i in range(self.pa.get_device_count()):
            devinfo = self.pa.get_device_info_by_index(i)

            for keyword in ["mic", "input"]:
                if keyword in devinfo["name"].lower():
                    print("Using microphone {}".format(devinfo["name"]))
                    device_index = i
                    return device_index

        if device_index is None:
            print("No preferred input found; using default input device.")

        return device_index

    def open_mic_stream(self):
        """Open and start the microphone stream"""
        device_index = self.find_input_device()

        stream = self.pa.open(
            format=self.pa.get_format_from_width(2, False),
            channels=1,
            rate=RATE,
            input=True,
            input_device_index=device_index,
        )

        stream.start_stream()
        return stream

    def read_audio_block(self) -> np.ndarray:
        """Read a block of audio from the microphone

        Returns:
            Audio samples as numpy array
        """
        total = 0
        frame_buffer = []

        while total < INPUT_FRAMES_PER_BLOCK:
            while self.stream.get_read_available() <= 0:
                time.sleep(0.001)
            while (
                self.stream.get_read_available() > 0 and total < INPUT_FRAMES_PER_BLOCK
            ):
                raw_block = self.stream.read(
                    self.stream.get_read_available(), exception_on_overflow=False
                )
                count = len(raw_block) / 2
                total = total + count
                frame_buffer.append(np.frombuffer(raw_block, dtype=np.int16))

        return np.hstack(frame_buffer)

    def analyze_audio(self) -> Optional[Frame]:
        """Read audio from microphone and analyze it into a Frame

        Returns:
            Frame containing analyzed audio signals, or None on error
        """
        try:
            # Read audio block
            snd_block = self.read_audio_block()

            # Compute spectrogram
            f, t, Sxx = signal.spectrogram(snd_block)

            # Update spectrogram buffer
            if self.spectrogram_buffer is None:
                self.spectrogram_buffer = Sxx
            else:
                self.spectrogram_buffer = np.concatenate(
                    [self.spectrogram_buffer, Sxx], axis=1
                )

            self.spectrogram_buffer = self.spectrogram_buffer[
                :, -SPECTOGRAPH_BUFFER_SIZE:
            ]

            # Process the spectrogram into a frame
            return self.process_spectrogram(self.spectrogram_buffer, len(t))

        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return None

    def process_spectrogram(
        self, spectrogram_block: np.ndarray, num_idx_added: int
    ) -> Frame:
        """Process spectrogram data into a Frame with signal values

        Args:
            spectrogram_block: Spectrogram array
            num_idx_added: Number of time indices added in this block

        Returns:
            Frame with analyzed signal values
        """
        # Define frequency ranges for analysis
        ranges = {
            FrameSignal.freq_all: (0, 129),
            FrameSignal.freq_high: (30, 129),
            FrameSignal.freq_low: (0, 30),
        }

        values = {}
        timeseries = {}

        # Check if we should capture signal statistics for normalization
        should_capture_signal_stats = (
            time.time() - self.signal_stat_last > SIGNAL_STAT_PERIOD_SECONDS
        )
        if should_capture_signal_stats:
            self.signal_stat_last = time.time()

        # Process each frequency range
        for name, rg in ranges.items():
            x = np.sum(np.abs(spectrogram_block[rg[0] : rg[1], :]), axis=0)

            # Smooth with convolution
            N = 3
            x = np.convolve(x, np.ones(N) / N, mode="valid")

            # Calculate percentiles for normalization
            x_min = np.percentile(x, 5)
            x_max = np.percentile(x, 95)

            # Update signal statistics buffer
            if should_capture_signal_stats:
                self.signal_stat_buffer[name]["max"].append(x_max)
                self.signal_stat_buffer[name]["min"].append(x_min)
                self.signal_stat_buffer[name]["max"] = self.signal_stat_buffer[name][
                    "max"
                ][-SIGNAL_STAT_BUFFER_SIZE:]
                self.signal_stat_buffer[name]["min"] = self.signal_stat_buffer[name][
                    "min"
                ][-SIGNAL_STAT_BUFFER_SIZE:]

            # Use historical statistics for normalization
            x_min = np.min(
                np.concatenate([self.signal_stat_buffer[name]["min"], [x_min]])
            )
            x_max = np.max(
                np.concatenate([self.signal_stat_buffer[name]["max"], [x_max]])
            )

            # Normalize to 0-1 range
            x = (x - x_min) / (x_max - x_min + sys.float_info.epsilon)
            x = np.clip(x, 0, 1)

            timeseries[name] = x
            v = x[-1]
            if np.isnan(v):
                v = 0
            values[name] = v

        # Calculate sustained signals (averaged over longer time)
        for src, dest in [
            (FrameSignal.freq_high, FrameSignal.sustained_high),
            (FrameSignal.freq_low, FrameSignal.sustained_low),
        ]:
            v = timeseries[src][-200:].mean()
            values[dest] = v
            self.signal_lookback[dest].extend([v for _ in range(num_idx_added)])
            self.signal_lookback[dest] = self.signal_lookback[dest][
                -SPECTOGRAPH_BUFFER_SIZE:
            ]

        # Create frame with audio values
        frame = Frame(values)

        # Add signal states to the frame
        frame.extend(self.signal_states.get_states())

        # Attach timeseries data for visualization
        frame.timeseries = {
            FrameSignal.freq_high.name: timeseries[FrameSignal.freq_high],
            FrameSignal.freq_low.name: timeseries[FrameSignal.freq_low],
            FrameSignal.sustained_low.name: self.signal_lookback[
                FrameSignal.sustained_low
            ],
            FrameSignal.sustained_high.name: self.signal_lookback[
                FrameSignal.sustained_high
            ],
        }

        return frame

    def cleanup(self):
        """Clean up audio resources"""
        if hasattr(self, "stream") and self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, "pa") and self.pa:
            self.pa.terminate()
