class Plotter:
    def __init__(self):
        self.plot_counter = 0

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

    def step(self, frame):

        self.sustain_buffer.append(sustained)
        self.sustain_buffer = self.sustain_buffer[-self.lookback_buffer_size :]

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
