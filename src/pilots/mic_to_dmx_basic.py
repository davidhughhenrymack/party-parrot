#!/usr/bin/env ipython

import pyaudio
import numpy as np
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import time

import math
from director.director import Director
from director.director import Frame
from utils.dmx_utils import get_controller

THRESHOLD = 0 # dB
RATE = 44100
INPUT_BLOCK_TIME = 30 * 0.001 # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
TIME_IN_GRAPH = 1000
BLOCKS_IN_GRAPH = int(TIME_IN_GRAPH / INPUT_BLOCK_TIME)


matplotlib.use('macosx')

def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))



class MicToDmxBasic(object):
    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.open_mic_stream()
        self.threshold = THRESHOLD
        self.plot_counter = 0

        self.fig, self.ax1 = plt.subplots()
        self.ax2 = self.ax1.twinx() 

        self.snd_blocks = []
        self.spectrogram_blocks = []
        self.power_max = 0
        self.power_min = 99999999999999999

        self.dmx = get_controller()
        self.director = Director()
        self.frame = 0

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

    def processBlockPower(self, snd_block, spectrogram_block, frame):

        ranges = {
            "intensity": (0, 129),
            "vocals": (40, 129),
            "other": (60, 129),
            "drums": (0, 129),
            "bass": (0, 60),
        }

        values = {}

        for name, range in ranges.items():
            x = np.sum(np.abs(spectrogram_block[range[0]:range[1],-10000:]), axis=0)
            N = round(RATE / 5000)
            x = np.convolve(x, np.ones(N)/N, mode='valid')
            v = (x[-1] - x.min()) / (x.max() - x.min())
            values[name] = v

        self.director.step(Frame(
            values["intensity"], time.time(), values["vocals"], values["other"], values["drums"], values["bass"]
        ))
        self.director.render(self.dmx)


        # x_extra_smooth = np.convolve(x, np.ones(N*10)/N/10, mode='valid')
        # x_ = np.gradient(x_extra_smooth)

        # self.fig.clf()
        plt.clf()
        
        plt.plot(x, label='Power')
        # plt.plot(x_diff, label='Power')
        # plt.plot(x_up, label='Up')
        # plt.plot(x_down, label='Down')

        plt.ylabel('Power')
        plt.xlabel('Time [sec]')

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
          
        # try:
            # print("start", self.stream.is_active(), self.stream.is_stopped())
            #raw_block = self.stream.read(INPUT_FRAMES_PER_BLOCK, exception_on_overflow = False)

            total = 0

            frame_buffer = []
            
            while total < INPUT_FRAMES_PER_BLOCK:
                while self.stream.get_read_available() <= 0:
                #   print('waiting')
                  time.sleep(0.01)
                while self.stream.get_read_available() > 0 and total < INPUT_FRAMES_PER_BLOCK:
                    raw_block = self.stream.read(self.stream.get_read_available(), exception_on_overflow = False)
                    count = len(raw_block) / 2
                    total = total + count
                    frame_buffer.append(np.fromstring(raw_block,dtype=np.int16))

            snd_block = np.hstack(frame_buffer)
            self.snd_blocks.append(snd_block)

            f,t,Sxx = signal.spectrogram(self.snd_blocks[-1], RATE)
            self.spectrogram_blocks.append(Sxx)
            
            # print(f"snd blocks: {[i.shape for i in self.snd_blocks]}")
            full_snd_block = np.hstack(self.snd_blocks)
            # print(f"full_snd_block: {full_snd_block.shape}")
            
            # print(f"specs: {[i.shape for i in self.spectrogram_blocks]}")
            full_spectrogram_block = np.hstack(self.spectrogram_blocks)
            # print(f"full_spectrogram_block: {full_spectrogram_block.shape}")

            # print(f"t_snd_blk: {len(self.t_snd_block)} snd_block: {len(snd_block)}")
            self.processBlockPower(full_snd_block, full_spectrogram_block, self.frame)

            self.frame += 1
        # except Exception as e:
        #     print('Error recording: {}'.format(e))
        #     return

       



