#!/usr/bin/env ipython

import os
import sys
import pyaudio
import numpy as np
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import time

import math
from parrot.director.director import Director
from parrot.director.director import Frame
from parrot.gui.plot import Plotter
from parrot.utils.dmx_utils import get_controller
from parrot.gui.gui import Window
from parrot.state import State

THRESHOLD = 0  # dB
RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001  # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
TIME_IN_GRAPH = 1000
BLOCKS_IN_GRAPH = int(TIME_IN_GRAPH / INPUT_BLOCK_TIME)

SHOW_PLOT = os.environ.get("SHOW_PLOT") == "True"
SHOW_GUI = os.environ.get("SHOW_GUI", "True") == "True"

if SHOW_PLOT:
    matplotlib.use("macosx")


def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))


class MicToDmx(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()

        self.avg_rate = RATE

        self.threshold = THRESHOLD
        self.power_max = 0
        self.power_min = 99999999999999999

        self.spectrogram_buffer = None
        self.lookback_buffer_size = RATE * 6
        self.sustain_buffer = []

        self.state = State()

        self.should_stop = False

        self.dmx = get_controller()
        self.director = Director(self.state)

        if SHOW_GUI:
            self.window = Window(self.state, lambda: self.quit())

        if SHOW_PLOT:
            self.plotter = Plotter()

        self.frame_count = 0

    def quit(self):
        self.should_stop = True

    def run(self):
        while not self.should_stop:
            try:
                self.listen()
            except (KeyboardInterrupt, SystemExit) as e:
                break

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

    def processBlockPower(self, spectrogram_block):
        ranges = {
            "all": (0, 129),
            "drums": (60, 129),
            "bass": (0, 60),
        }

        values = {}
        timeseries = {}

        raw_timeseries = {}

        for name, range in ranges.items():
            x = np.sum(np.abs(spectrogram_block[range[0] : range[1], :]), axis=0)
            raw_timeseries[name] = x
            N = round(RATE / 5000)
            x = np.convolve(x, np.ones(N) / N, mode="valid")

            # Discard outliers and clamp to 0-1
            x_min = np.percentile(x, 5)
            x_max = np.percentile(x, 95)
            x = (x - x_min) / (x_max - x_min + sys.float_info.epsilon)
            x = np.clip(x, 0, 1)

            timeseries[name] = x
            v = x[-1]
            if math.isnan(v):
                v = 0
            values[name] = v

        sustained = timeseries["bass"][-200:].mean()
        values["sustained"] = sustained

        # Calculate BPM by getting the FFT of the drum range
        x = raw_timeseries["bass"][-round(self.spectrogram_rate * 4) :]
        # x = x - x.mean()
        # x = x * np.hanning(len(x))
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

        frame = Frame(
            **values,
        )

        if SHOW_PLOT:
            self.plotter.step(frame, raw_timeseries, np.abs(X), self.spectrogram_rate)

        self.director.step(frame)
        self.director.render(self.dmx)

        if SHOW_GUI:
            self.window.step(frame)
            self.window.update()

    def listen(self):
        total = 0
        frame_buffer = []

        start_time = time.time()

        while total < INPUT_FRAMES_PER_BLOCK:
            while self.stream.get_read_available() <= 0:
                time.sleep(0.01)
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
        time_elapsed = time.time() - start_time
        self.avg_rate = len(snd_block) / time_elapsed
        # print("Time elapsed: {}".format(time_elapsed))
        # print("Snd block length: {}".format(len(snd_block)))
        # print("Expected block length: {}".format(time_elapsed * RATE))
        # print("---")

        # f : ndarray
        #     Array of sample frequencies.
        # t : ndarray
        #     Array of segment times.
        # Sxx : ndarray
        #     Spectrogram of x. By default, the last axis of Sxx corresponds
        #     to the segment times.
        f, t, Sxx = signal.spectrogram(snd_block, self.avg_rate)

        self.spectrogram_rate = len(t) / time_elapsed

        if self.spectrogram_buffer is None:
            self.spectrogram_buffer = Sxx
        else:
            self.spectrogram_buffer = np.concatenate(
                [self.spectrogram_buffer, Sxx], axis=1
            )

        self.spectrogram_buffer = self.spectrogram_buffer[
            :, -self.lookback_buffer_size :
        ]
        self.processBlockPower(self.spectrogram_buffer)

    # except Exception as e:
    #     print('Error recording: {}'.format(e))
    #     return
