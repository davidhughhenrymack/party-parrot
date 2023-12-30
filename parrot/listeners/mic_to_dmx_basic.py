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
from parrot.utils.dmx_utils import get_controller

THRESHOLD = 0  # dB
RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001  # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
TIME_IN_GRAPH = 1000
BLOCKS_IN_GRAPH = int(TIME_IN_GRAPH / INPUT_BLOCK_TIME)

SHOW_PLOT = os.environ.get("SHOW_PLOT", False)

if SHOW_PLOT:
    matplotlib.use("macosx")


def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))


class MicToDmxBasic(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.threshold = THRESHOLD
        self.plot_counter = 0

        # self.fig, (self.ax1, self.ax2) = plt.subplots(nrows=2, sharex=False)

        self.power_max = 0
        self.power_min = 99999999999999999

        self.spectrogram_buffer = None
        self.lookback_buffer_size = 10000

        self.sustain_buffer = []

        self.dmx = get_controller()
        self.director = Director()
        self.frame = 0

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None
        for i in range(self.pa.get_device_count()):
            devinfo = self.pa.get_device_info_by_index(i)
            # print("Device %{}: %{}".format(i, devinfo["name"]))

            for keyword in ["mic", "input"]:
                if keyword in devinfo["name"].lower():
                    # print("Found an input: device {} - {}".format(i, devinfo["name"]))
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

    def processBlockSpectrum(self, snd_block):
        f, t, Sxx = signal.spectrogram(snd_block, RATE)
        zmin = Sxx.min()
        zmax = Sxx.max()

        plt.clf()
        plt.pcolormesh(t, f, Sxx, cmap="RdBu", norm=LogNorm(vmin=zmin, vmax=zmax))
        plt.ylabel("Frequency [Hz]")
        plt.xlabel("Time [sec]")
        plt.axis([t.min(), t.max(), f.min(), f.max()])
        plt.colorbar()
        plt.draw()
        plt.pause(0.001)
        # plt.show(block=False)
        # plt.savefig('output/spec{}.png'.format(self.plot_counter), bbox_inches='tight')
        # plt.close()
        # write('output/audio{}.wav'.format(self.plot_counter),RATE,snd_block)
        self.plot_counter += 1

    def processBlockPower(self, spectrogram_block):
        ranges = {
            "all": (0, 129),
            "drums": (60, 129),
            "bass": (0, 60),
        }

        values = {}
        timeseries = {}

        for name, range in ranges.items():
            x = np.sum(np.abs(spectrogram_block[range[0] : range[1], :]), axis=0)
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
        # self.sustain_buffer.append(sustained)
        # self.sustain_buffer = self.sustain_buffer[-self.lookback_buffer_size :]

        # spectrum_bins = 4
        # log_spectrogram = np.log10(spectrogram_block)
        # log_spectrogram = (log_spectrogram - log_spectrogram.min()) / (
        #     log_spectrogram.max() - log_spectrogram.min()
        # )
        # log_spectrogram = log_spectrogram[
        #     : int(log_spectrogram.shape[0] / spectrum_bins) * spectrum_bins, :
        # ]
        # log_spectrogram = log_spectrogram.reshape(
        #     spectrum_bins, -1, log_spectrogram.shape[1]
        # )
        # log_spectrogram = np.mean(log_spectrogram, axis=1)

        self.director.step(
            Frame(
                **values,
            )
        )
        self.director.render(self.dmx)

        if SHOW_PLOT:
            plt.clf()
            plt.subplot(2, 1, 1)

            for name, x in timeseries.items():
                plt.plot(x, label=name)
            plt.legend(loc="upper left")
            plt.ylabel("Power")
            plt.xlabel("Time [sec]")

            plt.subplot(2, 1, 2)
            plt.plot(self.sustain_buffer, label="Sustained")
            # plt.pcolormesh(log_spectrogram, label="Spectrogram")

            plt.draw()
            plt.pause(0.001)

    def listen(self):
        # try:
        # print("start", self.stream.is_active(), self.stream.is_stopped())
        # raw_block = self.stream.read(INPUT_FRAMES_PER_BLOCK, exception_on_overflow = False)

        total = 0

        frame_buffer = []

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

        # f : ndarray
        #     Array of sample frequencies.
        # t : ndarray
        #     Array of segment times.
        # Sxx : ndarray
        #     Spectrogram of x. By default, the last axis of Sxx corresponds
        #     to the segment times.
        f, t, Sxx = signal.spectrogram(snd_block, RATE)

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
