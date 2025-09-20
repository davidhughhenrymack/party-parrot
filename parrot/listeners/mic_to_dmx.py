#!/usr/bin/env ipython

import os
import sys
import tracemalloc
import pyaudio
import numpy as np
from scipy import signal
import matplotlib
import time
import queue
import threading

import math
from beartype import beartype

from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.utils.dmx_utils import get_controller

from parrot.state import State
from parrot.utils.colour import Color
from parrot.utils.tracemalloc import display_top
from parrot.api import start_web_server
from parrot.director.signal_states import SignalStates

THRESHOLD = 0  # dB
RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001  # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
SPECTOGRAPH_AVG_RATE = 275
SPECTOGRAPH_BUFFER_SIZE = SPECTOGRAPH_AVG_RATE * 3

SIGNAL_STAT_PERIOD_SECONDS = 10
SIGNAL_STAT_BUFFER_SIZE = round((60) / SIGNAL_STAT_PERIOD_SECONDS)


PROFILE_MEMORY_INTERVAL_SECONDS = 30


@beartype
def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))


@beartype
class MicToDmx(object):
    def __init__(self, args):
        self.args = args

        if args.profile:
            tracemalloc.start()

        from parrot.gui.gui import Window

        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()

        self.avg_rate = RATE

        self.threshold = THRESHOLD
        self.power_max = 0
        self.power_min = 99999999999999999

        self.spectrogram_buffer = None
        self.signal_lookback = {
            FrameSignal.sustained_low: [],
            FrameSignal.sustained_high: [],
        }

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

        self.state = State()
        self.signal_states = SignalStates()

        self.should_stop = False

        # Queue for thread-safe GUI updates
        self.gui_update_queue = queue.Queue()

        self.dmx = get_controller()

        self.director = Director(self.state)

        # Initialize VJ system
        from parrot.vj.vj_director import VJDirector

        self.vj_director = VJDirector()

        # Initialize GUI with VJ director
        self.window = Window(
            self.state,
            lambda: self.quit(),
            self.director,
            self.signal_states,
            self.vj_director,
        )

        # Start the web server if not disabled
        if not getattr(self.args, "no_web", False):
            start_web_server(
                self.state,
                director=self.director,
                port=getattr(self.args, "web_port", 4040),
            )

        print("🎬 VJ system enabled")
        print("🖥️ GUI system enabled")

        self.frame_count = 0

    def quit(self):
        # Save state before quitting
        self.state.save_state()
        self.should_stop = True

    def run(self):
        self._run_with_gui_and_vj()

    def _run_audio_loop(self):
        """Run the main audio processing loop"""
        last_profiled_at = time.time()

        while not self.should_stop:
            try:
                self.listen()

                if self.args.profile:
                    if time.time() - last_profiled_at > self.args.profile_interval:
                        last_profiled_at = time.time()
                        snapshot = tracemalloc.take_snapshot()
                        display_top(snapshot)

            except (KeyboardInterrupt, SystemExit) as e:
                break

    def _run_with_gui_and_vj(self):
        """Run with GUI in main thread and integrated VJ window"""
        import threading

        # Start audio processing in background thread
        audio_thread = threading.Thread(target=self._run_audio_loop, daemon=True)
        audio_thread.start()

        print("🎵 Running GUI in main thread with integrated VJ window")
        print("🖥️ Both windows will open automatically!")

        try:
            # Run GUI in main thread (VJ window will be opened automatically by GUI)
            self._run_gui_loop()
        finally:
            # Clean up VJ resources
            if self.window:
                self.window.cleanup_vj()

    def _run_gui_loop(self):
        """Run GUI in main thread with frame updates from queue"""

        def process_audio_frames():
            """Process frames from audio thread"""
            try:
                while True:
                    frame = self.gui_update_queue.get_nowait()
                    self.window.step(frame)

                    # Also update VJ window with frame data
                    if hasattr(self.window, "update_vj_frame_data"):
                        # Get current color scheme from director
                        color_scheme = self.director.scheme.render()
                        self.window.update_vj_frame_data(frame, color_scheme)

                    break  # Only process one frame per call
            except queue.Empty:
                pass
            # Schedule next check
            if not self.should_stop:
                self.window.after(10, process_audio_frames)

        # Start processing audio frames
        process_audio_frames()

        try:
            self.window.mainloop()
        except (KeyboardInterrupt, SystemExit):
            self.quit()

    def find_input_device(self):
        device_index = None
        for i in range(self.pa.get_device_count()):
            devinfo = self.pa.get_device_info_by_index(i)
            # print("Device %{}: %{}".format(i, devinfo["name"]))

            for keyword in ["mic", "input"]:
                if keyword in devinfo["name"].lower():
                    print("Using microphone {}".format(devinfo["name"]))
                    device_index = i
                    return device_index

        if device_index == None:
            print("No preferred input found; using default input device.")

        return device_index

    def open_mic_stream(self):
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

    def listen(self):
        total = 0
        frame_buffer = []

        # Process any pending GUI updates
        self.state.process_gui_updates()

        while total < INPUT_FRAMES_PER_BLOCK:
            while self.stream.get_read_available() <= 0:
                time.sleep(0.01)
                # Process GUI updates while waiting for audio
                self.state.process_gui_updates()
            while (
                self.stream.get_read_available() > 0 and total < INPUT_FRAMES_PER_BLOCK
            ):
                raw_block = self.stream.read(
                    self.stream.get_read_available(), exception_on_overflow=False
                )
                count = len(raw_block) / 2
                total = total + count
                frame_buffer.append(np.fromstring(raw_block, dtype=np.int16))

        snd_block = np.hstack(frame_buffer)

        # f : ndarray
        #     Array of sample frequencies.
        # t : ndarray
        #     Array of segment times.
        # Sxx : ndarray
        #     Spectrogram of x. By default, the last axis of Sxx corresponds
        #     to the segment times.
        f, t, Sxx = signal.spectrogram(snd_block)

        # self.spectrogram_rate = len(t) / time_elapsed

        if self.spectrogram_buffer is None:
            self.spectrogram_buffer = Sxx
        else:
            self.spectrogram_buffer = np.concatenate(
                [self.spectrogram_buffer, Sxx], axis=1
            )

        self.spectrogram_buffer = self.spectrogram_buffer[:, -SPECTOGRAPH_BUFFER_SIZE:]
        self.process_block(self.spectrogram_buffer, len(t))

    def process_block(self, spectrogram_block, num_idx_added):
        ranges = {
            FrameSignal.freq_all: (0, 129),
            FrameSignal.freq_high: (30, 129),
            FrameSignal.freq_low: (0, 30),
        }

        values = {}
        timeseries = {}

        raw_timeseries = {}

        # print(
        #     f"spectrogram {spectrogram_block.shape} max: {np.max(spectrogram_block):.3f}, sum: {np.sum(spectrogram_block):.3f}, mean: {np.mean(spectrogram_block):.3f}"
        # )

        should_capture_signal_stats = (
            time.time() - self.signal_stat_last > SIGNAL_STAT_PERIOD_SECONDS
        )
        if should_capture_signal_stats:
            self.signal_stat_last = time.time()

        for name, rg in ranges.items():
            x = np.sum(np.abs(spectrogram_block[rg[0] : rg[1], :]), axis=0)
            raw_timeseries[name] = x

            # N = round(RATE / 50000)
            N = 3
            x = np.convolve(x, np.ones(N) / N, mode="valid")

            # Discard outliers and clamp to 0-1
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

            x = (x - x_min) / (x_max - x_min + sys.float_info.epsilon)
            x = np.clip(x, 0, 1)

            timeseries[name] = x
            v = x[-1]
            if math.isnan(v):
                v = 0
            values[name] = v

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

        frame.timeseries = {
            FrameSignal.freq_high.name: timeseries[FrameSignal.freq_high],
            FrameSignal.freq_low.name: timeseries[FrameSignal.freq_low],
            # FrameSignal.freq_all: timeseries[FrameSignal.freq_all][-plot_lookback:],
            FrameSignal.sustained_low.name: self.signal_lookback[
                FrameSignal.sustained_low
            ],
            FrameSignal.sustained_high.name: self.signal_lookback[
                FrameSignal.sustained_high
            ],
        }

        self.director.step(frame)

        self.director.render(self.dmx)

        # Send frame to GUI via queue (thread-safe)
        try:
            self.gui_update_queue.put_nowait(frame)
        except queue.Full:
            # Skip update if queue is full (prevents blocking)
            pass

    def calc_bpm_spec(self, raw_timeseries):

        # Calculate BPM by getting the FFT of the drum range
        x = raw_timeseries[FrameSignal.freq_low][-round(self.spectrogram_rate * 4) :]
        X = np.fft.fft(x)

        bpm_range = np.array([40, 180]) / 60 * self.spectrogram_rate
        X = X[round(bpm_range[0]) : round(bpm_range[1])]

        # Find top 5 peaks
        peaks = np.argsort(np.abs(X))[-10:]
        # Convert to Hz
        peaks = peaks * (self.spectrogram_rate / len(x))
        # Convert to BPM
        peaks = peaks * 60
        peaks = np.sort(peaks)
        # print([round(i) for i in peaks])
