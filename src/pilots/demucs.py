#!/usr/bin/env ipython

import pyaudio
import numpy as np
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt
import time
import torch
from torchaudio.pipelines import HDEMUCS_HIGH_MUSDB_PLUS
from scipy.io.wavfile import write

# print(f"mps avail {torch.backends.mps.is_available()}") #the MacOS is higher than 12.3+
# print(f"mps build {torch.backends.mps.is_built()}") #MPS is activated

bundle = HDEMUCS_HIGH_MUSDB_PLUS
model = bundle.get_model()
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model.to(device)
sample_rate = bundle.sample_rate
sources_list = model.sources


THRESHOLD = 0 # dB
RATE = sample_rate
INPUT_BLOCK_TIME = 30 * 0.001 # 30 ms
INPUT_FRAMES_PER_BLOCK = int(RATE * INPUT_BLOCK_TIME)
INPUT_FRAMES_PER_BLOCK_BUFFER = int(RATE * INPUT_BLOCK_TIME)
TIME_IN_GRAPH = 1000
BLOCKS_IN_GRAPH = int(TIME_IN_GRAPH / INPUT_BLOCK_TIME)

ACCEPTED_LATENCY = 0.001 * 60 # 60 ms

matplotlib.use('macosx')

def get_rms(block):
    return np.sqrt(np.mean(np.square(block)))

class AudioHandler(object):
    def __init__(self):
        self.start_time = time.time()
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

        self.stem_blocks = {
            i: [] for i in model.sources
        }

        self.stem_spec_blocks = {
            i: [] for i in model.sources
        }

        self.stem_power_blocks = {
            i: [] for i in model.sources
        }

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


    def stem(self, snd_block):

        ref = snd_block
        two_channel = np.vstack([snd_block, snd_block])
        normalized = (two_channel - ref.mean()) / ref.std()  # normalization
        
        # batch, channels, length = mix.shape
        snd_tensor = torch.from_numpy(normalized).float() \
            .unsqueeze(0) \
            .to(device)
        
        sources = model.forward(snd_tensor)
        sources = sources * ref.std() + ref.mean()  # denormalization
        sources = list(sources.squeeze(0))

        stems = {}
        for i, source in enumerate(sources_list):
            one_channel = sources[i][0].detach().numpy()
            stems[source] = one_channel

        return stems

    def displayGraph(self):


        # print(audios["vocals"][0].detach().numpy())

        plt.clf()

        for (source, blocks) in self.stem_power_blocks.items():
            one_channel = np.hstack(blocks[-40:])
            plt.plot(one_channel, label=source, color=f"C{list(sources_list).index(source)}") 
            plt.ylabel('Amplitude')
            plt.xlabel('Time [sec]')

        plt.legend()
        plt.draw()
        plt.pause(0.001)


    def listen(self):
        try:
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

            stems = self.stem(snd_block)
            for (source, one_channel) in stems.items():
                self.stem_blocks[source].append(one_channel)
                f,t,Sxx = signal.spectrogram(one_channel, RATE)
                self.stem_spec_blocks[source].append(Sxx)
                x = np.sum(np.abs(Sxx), axis=0)
                self.stem_power_blocks[source].append(x)


            self.displayGraph()

            # listen_time = time.time() - self.start_time
            # if listen_time > 5: 
            #     write(f"./output/full.wav", RATE, full_snd_block)
            #     stems = self.stem(full_snd_block)
            #     for (source, one_channel) in stems.items():
            #         write(f"./output/{source}.wav", RATE, one_channel.astype(np.int16))
            #     self.start_time = time.time()
            #     print("wrote files")
                
        except Exception as e:
            print(e)
            return

       

if __name__ == '__main__':
    audio = AudioHandler()
    while True:
        audio.listen()