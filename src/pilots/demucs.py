#!/usr/bin/env ipython

import pyaudio
import numpy as np
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
import time
import torch
from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS

print(f"mps avail {torch.backends.mps.is_available()}") #the MacOS is higher than 12.3+
print(f"mps build {torch.backends.mps.is_built()}") #MPS is activated

bundle = HDEMUCS_HIGH_MUSDB_PLUS
model = bundle.get_model()
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model.to(device)
sample_rate = bundle.sample_rate


THRESHOLD = 0 # dB
RATE = sample_rate
INPUT_BLOCK_TIME = 30 * 0.001 # 30 ms
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

        self.snd_blocks = []
        self.spectrogram_blocks = []
        self.power_max = 0
        self.power_min = 99999999999999999

    def stop(self):
        self.stream.close()

    def find_input_device(self):
        device_index = None
        for i in range( self.pa.get_device_count() ):
            devinfo = self.pa.get_device_info_by_index(i)
            # print('Device %{}: %{}'.format(i, devinfo['name']))

            for keyword in ['mic','input']:
                if keyword in devinfo['name'].lower():
                    # print('Found an input: device {} - {}'.format(i, devinfo['name']))
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

  

    def processBlockPower(self, snd_block, spectrogram_block):
        # batch, channels, length = mix.shape
        snd_tensor = torch.from_numpy(snd_block[:-round(RATE/10)]).float() \
            .unsqueeze(0) \
            .repeat(2,1)\
            .unsqueeze(0)\
            .to(device)
        
        # print(f"snd_tensor: {snd_tensor.shape} {snd_tensor.dtype}")
        sources = model.forward(snd_tensor)
        sources_list = model.sources
        sources = list(sources.squeeze(0))
        audios = dict(zip(sources_list, sources))
        # print(audios["vocals"][0].detach().numpy())
        vocal_one_channel = audios["vocals"][0].detach().numpy()
        plt.clf()
        plt.plot(vocal_one_channel, label='Amplitude')
        plt.ylabel('Power')
        plt.xlabel('Time [sec]')
        plt.draw()
        plt.pause(0.001)


    def listen(self):
        try:
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
            self.processBlockPower(full_snd_block, full_spectrogram_block)
        except Exception as e:
            print(e)
            return

       

if __name__ == '__main__':
    audio = AudioHandler()
    while True:
        audio.listen()