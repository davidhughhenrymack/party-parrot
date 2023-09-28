#!/usr/bin/env ipython

import pyaudio
import struct
import math
import numpy as np
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import time
from scipy.io.wavfile import write

THRESHOLD = 0 # dB
RATE = 44100
INPUT_BLOCK_TIME = 0.5 # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
TIME_IN_GRAPH = 1000
BLOCKS_IN_GRAPH = int(TIME_IN_GRAPH / INPUT_BLOCK_TIME)

matplotlib.use('macosx')

def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))

class AudioHandler(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.threshold = THRESHOLD
        self.plot_counter = 0

        self.fig, self.ax1 = plt.subplots()
        self.ax2 = self.ax1.twinx() 
        self.t_snd_block = []
        self.power_max = 0
        self.power_min = 99999999999999999

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None
        for i in range( self.pa.get_device_count() ):
            devinfo = self.pa.get_device_info_by_index(i)
            print('Device %{}: %{}'.format(i, devinfo['name']))

            for keyword in ['mic','input']:
                if keyword in devinfo['name'].lower():
                    print('Found an input: device {} - {}'.format(i, devinfo['name']))
                    device_index = i
                    return device_index

        if device_index == None:
            print('No preferred input found; using default input device.')

        return device_index

    def open_mic_stream( self ):
        device_index = self.find_input_device()

        stream = self.pa.open(  format = self.pa.get_format_from_width(2,False),
                                channels = 1,
                                rate = RATE,
                                input = True,
                                input_device_index = device_index)

        stream.start_stream()
        return stream

    def processBlockSpectrum(self, snd_block):
        f, t, Sxx = signal.spectrogram(snd_block, RATE)
        zmin = Sxx.min()
        zmax = Sxx.max()
        
        plt.clf()
        plt.pcolormesh(t, f, Sxx, cmap='RdBu', norm=LogNorm(vmin=zmin, vmax=zmax))
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.axis([t.min(), t.max(), f.min(), f.max()])
        plt.colorbar()
        plt.draw()
        plt.pause(0.001)
        # plt.show(block=False)
        # plt.savefig('output/spec{}.png'.format(self.plot_counter), bbox_inches='tight')
        # plt.close()
        # write('output/audio{}.wav'.format(self.plot_counter),RATE,snd_block)
        self.plot_counter += 1

    def processBlockPower(self, snd_block):
        f, t, Sxx = signal.spectrogram(snd_block, RATE)
        x = np.sum(np.abs(Sxx)**2, axis=0)
        N = round(RATE / 100)
        x = np.convolve(x, np.ones(N)/N, mode='valid')

        self.power_max = max(self.power_max, x.max())
        self.power_min = min(self.power_min, x.min())

        # x_extra_smooth = np.convolve(x, np.ones(N*10)/N/10, mode='valid')
        # x_ = np.gradient(x_extra_smooth)

        # self.fig.clf()
        plt.clf()
        
        plt.plot(x, label='Power')
        self.ax1.set_ylabel('Power')
        self.ax1.set_xlabel('Time [sec]')

        # plt.plot(x_, label='Gradient', )
        # plt.axis([t.min(), t.max(), self.power_min, self.power_max])
        # plt.pcolormesh(t, f, Sxx, cmap='RdBu', norm=LogNorm(vmin=zmin, vmax=zmax))
    
        # self.fig.tight_layout()
        plt.draw()
        plt.pause(0.001)
        # plt.show(block=False)
        # plt.show()
        # self.fig.show()

    def listen(self):
        try:
            # print("start", self.stream.is_active(), self.stream.is_stopped())
            #raw_block = self.stream.read(INPUT_FRAMES_PER_BLOCK, exception_on_overflow = False)

            total = 0
            
            while total < INPUT_FRAMES_PER_BLOCK:
                while self.stream.get_read_available() <= 0:
                #   print('waiting')
                  time.sleep(0.01)
                while self.stream.get_read_available() > 0 and total < INPUT_FRAMES_PER_BLOCK:
                    raw_block = self.stream.read(self.stream.get_read_available(), exception_on_overflow = False)
                    count = len(raw_block) / 2
                    total = total + count
                    # print("done", total,count)
                    format = '%dh' % (count)
                    self.t_snd_block.append(np.fromstring(raw_block,dtype=np.int16))
                    # print(f"Last block len: {len(self.t_snd_block[-1])} total: {total} count: {count} len: {len(raw_block)}")
            
            snd_block = np.hstack(self.t_snd_block)
            # print(f"t_snd_blk: {len(self.t_snd_block)} snd_block: {len(snd_block)}")
        except Exception as e:
            print('Error recording: {}'.format(e))
            return

        self.processBlockPower(snd_block)

if __name__ == '__main__':
    audio = AudioHandler()
    while True:
        audio.listen()