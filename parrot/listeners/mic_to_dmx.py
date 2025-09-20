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

        # Always enable both GUI and VJ
        args.gui = True
        args.vj = True

        if args.profile:
            tracemalloc.start()

        # Always import GUI since we always run with GUI now
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

        # Queue for VJ commands (shift, shift_all, etc.)
        self.vj_command_queue = queue.Queue()

        self.dmx = get_controller()

        self.director = Director(self.state)

        # Initialize VJ system (always enabled now)
        from parrot.vj.vj_director import VJDirector

        self.vj_director = VJDirector()
        self.vj_window_manager = None
        # Don't pass VJ director to main director when running in separate process
        # The VJ director will be None, so mode changes will use the command queue instead

        # Add VJ command methods to director for GUI access
        self.director.send_vj_shift = self.send_vj_shift
        self.director.send_vj_shift_all = self.send_vj_shift_all
        self.director.send_vj_mode_change = self.send_vj_mode_change

        # Initialize GUI (always enabled now) with VJ director
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

        # Always start both GUI and VJ windows
        print("🎬 VJ system enabled")
        print("🖥️ GUI system enabled")
        self.should_start_vj_window = True

        self.frame_count = 0

    def quit(self):
        # Save state before quitting
        self.state.save_state()
        self.should_stop = True

    def send_vj_shift(self, threshold: float = 0.3):
        """Send shift command to VJ process"""
        try:
            self.vj_command_queue.put_nowait(
                {"type": "shift", "threshold": threshold, "timestamp": time.time()}
            )
        except queue.Full:
            pass  # Skip if queue is full

    def send_vj_shift_all(self, threshold: float = 1.0):
        """Send shift all command to VJ process"""
        try:
            self.vj_command_queue.put_nowait(
                {"type": "shift_all", "threshold": threshold, "timestamp": time.time()}
            )
        except queue.Full:
            pass  # Skip if queue is full

    def send_vj_mode_change(self, mode, threshold: float = 0.5):
        """Send mode change command to VJ process"""
        try:
            self.vj_command_queue.put_nowait(
                {
                    "type": "mode_change",
                    "mode": mode.name,
                    "threshold": threshold,
                    "timestamp": time.time(),
                }
            )
        except queue.Full:
            pass  # Skip if queue is full

    def run(self):
        # Always run with both GUI and VJ windows
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
        import subprocess
        import sys
        import os
        import tempfile
        import json

        # Create a temporary file for sharing frame data with VJ process
        self.frame_data_file = tempfile.NamedTemporaryFile(
            mode="w+", suffix=".json", delete=False
        )
        self.frame_data_file.close()

        # Start audio processing in background thread
        audio_thread = threading.Thread(target=self._run_audio_loop, daemon=True)
        audio_thread.start()

        # Launch VJ in separate process with frame data sharing
        vj_script = f"""
import sys
import os
import json
import time
sys.path.insert(0, "{os.getcwd()}")

import moderngl_window as mglw
from parrot.vj.vj_window import VJWindowManager
from parrot.vj.vj_director import VJDirector
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe

# Create a simple VJ director that reads frame data from file
class FileBasedVJDirector(VJDirector):
    def __init__(self, frame_file):
        super().__init__()
        self.frame_file = frame_file
        self.last_frame_time = 0
        
        # Create a default color scheme
        self.default_scheme = ColorScheme(
            fg=Color("white"),  # White foreground
            bg=Color("blue"),   # Blue background
            bg_contrast=Color("purple")  # Purple contrast
        )
        
    def get_latest_frame_data(self):
        try:
            # Read frame data from shared file
            with open(self.frame_file, 'r') as f:
                data = json.load(f)
                if data.get('time', 0) > self.last_frame_time:
                    self.last_frame_time = data['time']
                    
                    # Process any VJ commands
                    vj_commands = data.get('vj_commands', [])
                    for cmd in vj_commands:
                        self._process_vj_command(cmd)
                    
                    # Create complete frame with all signals
                    frame_values = {{
                        FrameSignal.freq_low: data.get('freq_low', 0.0),
                        FrameSignal.freq_high: data.get('freq_high', 0.0),
                        FrameSignal.freq_all: data.get('freq_all', 0.0),
                        FrameSignal.sustained_low: data.get('sustained_low', 0.0),
                        FrameSignal.sustained_high: data.get('sustained_high', 0.0),
                        FrameSignal.pulse: data.get('pulse', 0.0),
                        FrameSignal.strobe: data.get('strobe', 0.0),
                        FrameSignal.big_blinder: data.get('big_blinder', 0.0),
                        FrameSignal.small_blinder: data.get('small_blinder', 0.0),
                        FrameSignal.dampen: data.get('dampen', 0.0),
                    }}
                    
                    frame = Frame(frame_values)
                    
                    # Create color scheme from data if available
                    scheme = self.default_scheme
                    if 'color_scheme' in data:
                        cs_data = data['color_scheme']
                        from parrot.utils.colour import Color
                        fg_color = Color("white")
                        fg_color.rgb = (cs_data['fg']['r'], cs_data['fg']['g'], cs_data['fg']['b'])
                        bg_color = Color("white")
                        bg_color.rgb = (cs_data['bg']['r'], cs_data['bg']['g'], cs_data['bg']['b'])
                        bg_contrast_color = Color("white")
                        bg_contrast_color.rgb = (cs_data['bg_contrast']['r'], cs_data['bg_contrast']['g'], cs_data['bg_contrast']['b'])
                        scheme = ColorScheme(
                            fg=fg_color,
                            bg=bg_color,
                            bg_contrast=bg_contrast_color
                        )
                    
                    return frame, scheme
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        return None, None
        
    def _process_vj_command(self, cmd):
        \"\"\"Process VJ commands from the main process\"\"\"
        if cmd['type'] == 'shift':
            # Regular shift with low threshold (subtle changes)
            threshold = cmd.get('threshold', 0.6)
            vibe = Vibe(self.current_mode)
            self.concert_stage.generate_recursive(vibe, threshold)
            print("🎬 VJ Shift (threshold=" + str(threshold) + ")")
            print("VJ Node Tree (after shift):")
            print(self.concert_stage.print_tree())
        elif cmd['type'] == 'shift_all':
            # Shift all with high threshold (major changes)  
            threshold = cmd.get('threshold', 1.0)
            vibe = Vibe(self.current_mode)
            self.concert_stage.generate_recursive(vibe, threshold)
            print("🎬 VJ Shift All (threshold=" + str(threshold) + ")")
            print("VJ Node Tree (after shift all):")
            print(self.concert_stage.print_tree())
        elif cmd['type'] == 'mode_change':
            # Mode change - update current mode and regenerate with new mode
            mode_name = cmd.get('mode', 'gentle')
            threshold = cmd.get('threshold', 0.5)
            try:
                new_mode = Mode[mode_name]
                self.current_mode = new_mode
                vibe = Vibe(new_mode)
                self.concert_stage.generate_recursive(vibe, threshold)
                print("🎬 VJ Mode Change to " + mode_name + " (threshold=" + str(threshold) + ")")
                print("VJ Node Tree (after mode change):")
                print(self.concert_stage.print_tree())
            except KeyError:
                print("🚨 Unknown mode: " + mode_name)

# Create VJ director and window
vj_director = FileBasedVJDirector("{self.frame_data_file.name}")
vj_window_manager = VJWindowManager(vj_director=vj_director)
vj_window_manager.create_window(fullscreen={getattr(self.args, 'vj_fullscreen', False)})
window_cls = vj_window_manager.get_window_class()

# Run the VJ window
try:
    mglw.run_window_config(window_cls)
except KeyboardInterrupt:
    pass
"""

        print("🎵 Running GUI in main thread with integrated VJ window")
        print("🖥️ Both windows will open automatically!")

        try:
            # Run GUI in main thread (VJ window will be opened automatically by GUI)
            self._run_gui_loop()
        finally:
            # Clean up VJ resources
            if self.window:
                self.window.cleanup_vj()

    def _run_vj_window(self):
        """Run VJ window in main thread"""
        import moderngl_window as mglw
        from parrot.vj.vj_window import VJWindowManager
        import sys
        import logging

        # Clear sys.argv to prevent ModernGL from parsing our arguments
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Keep only the script name

        # Suppress verbose ModernGL logging
        logging.getLogger("moderngl_window").setLevel(logging.WARNING)

        # Create VJ window manager
        self.vj_window_manager = VJWindowManager(vj_director=self.vj_director)
        fullscreen = getattr(self.args, "vj_fullscreen", False)
        self.vj_window_manager.create_window(fullscreen=fullscreen)

        # Get the configured window class
        window_cls = self.vj_window_manager.get_window_class()

        # Run the VJ window (director will handle frame updates)
        mglw.run_window_config(window_cls)

        # Restore original argv
        sys.argv = original_argv

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

        # Store the frame for VJ system access
        self.last_frame = frame

        self.director.step(frame)

        # Store the latest color scheme from director for VJ process
        self.last_scheme = self.director.scheme.render()
        self.director.render(self.dmx)

        # Send frame to GUI via queue (thread-safe)
        try:
            self.gui_update_queue.put_nowait(frame)
        except queue.Full:
            # Skip update if queue is full (prevents blocking)
            pass

        # Write frame data to shared file for VJ process
        if hasattr(self, "frame_data_file"):
            try:
                import json

                frame_data = {
                    "time": frame.time,
                    "freq_low": frame[FrameSignal.freq_low],
                    "freq_high": frame[FrameSignal.freq_high],
                    "freq_all": frame[FrameSignal.freq_all],
                    "sustained_low": frame[FrameSignal.sustained_low],
                    "sustained_high": frame[FrameSignal.sustained_high],
                    "pulse": frame[FrameSignal.pulse],
                    "strobe": frame[FrameSignal.strobe],
                    "big_blinder": frame[FrameSignal.big_blinder],
                    "small_blinder": frame[FrameSignal.small_blinder],
                    "dampen": frame[FrameSignal.dampen],
                    # Add color scheme data
                    "color_scheme": {
                        "fg": {
                            "r": self.last_scheme.fg.red,
                            "g": self.last_scheme.fg.green,
                            "b": self.last_scheme.fg.blue,
                        },
                        "bg": {
                            "r": self.last_scheme.bg.red,
                            "g": self.last_scheme.bg.green,
                            "b": self.last_scheme.bg.blue,
                        },
                        "bg_contrast": {
                            "r": self.last_scheme.bg_contrast.red,
                            "g": self.last_scheme.bg_contrast.green,
                            "b": self.last_scheme.bg_contrast.blue,
                        },
                    },
                }

                # Add any pending VJ commands
                vj_commands = []
                while not self.vj_command_queue.empty():
                    try:
                        cmd = self.vj_command_queue.get_nowait()
                        vj_commands.append(cmd)
                    except queue.Empty:
                        break

                if vj_commands:
                    frame_data["vj_commands"] = vj_commands

                with open(self.frame_data_file.name, "w") as f:
                    json.dump(frame_data, f)
            except Exception:
                # Don't let file I/O errors break audio processing
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
