import time
from matplotlib import pyplot as plt
import matplotlib
from matplotlib.colors import LogNorm
import numpy as np
from scipy import signal

from parrot.listeners.mic import RATE


class Plotter:
    def __init__(self):
        self.last_plotted = time.time()
        pass

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

    def step(self, frame, timeseries, bpm_estimate, spectrogram_rate):

        if frame.time - self.last_plotted < 10:
            return

        plt.clf()
        plt.subplot(2, 1, 1)

        x = np.arange(len(timeseries["drums"])) / spectrogram_rate

        for name, y in timeseries.items():
            plt.plot(x, y, label=name)
        plt.legend(loc="upper left")
        plt.ylabel("Power")
        plt.xlabel("Time [sec]")

        plt.subplot(2, 1, 2)
        plt.plot(bpm_estimate, label="BPM estimate")
        # plt.pcolormesh(log_spectrogram, label="Spectrogram")

        # plt.draw()
        # plt.pause(0.1)
        plt.show()
