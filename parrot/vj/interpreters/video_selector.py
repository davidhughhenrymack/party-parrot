import random
from typing import List
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.vj.layers.video import VideoLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class VideoSelector(VJInterpreterBase):
    """Randomly switches videos in video layers"""

    hype = 20

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        switch_probability: float = 0.005,  # Per frame probability
        signal_trigger: FrameSignal = None,
        signal_threshold: float = 0.7,
    ):
        super().__init__(layers, args)
        self.switch_probability = switch_probability
        self.signal_trigger = signal_trigger
        self.signal_threshold = signal_threshold
        self.last_signal_value = 0.0

        # Filter for video layers only (including mock layers)
        from parrot.vj.layers.video import MockVideoLayer

        self.video_layers = [
            layer for layer in layers if isinstance(layer, (VideoLayer, MockVideoLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Randomly switch videos or trigger on signal"""
        should_switch = False

        # Check for signal-based switching
        if self.signal_trigger:
            signal_value = frame[self.signal_trigger]

            # Trigger on signal edge (rising above threshold)
            if (
                signal_value > self.signal_threshold
                and self.last_signal_value <= self.signal_threshold
            ):
                should_switch = True

            self.last_signal_value = signal_value

        # Check for random switching
        if not should_switch and random.random() < self.switch_probability:
            should_switch = True

        # Switch videos in all video layers
        if should_switch:
            for video_layer in self.video_layers:
                if hasattr(video_layer, "switch_video"):
                    video_layer.switch_video()

    def __str__(self) -> str:
        trigger_str = f", {self.signal_trigger.name}" if self.signal_trigger else ""
        return f"VideoSelector(p={self.switch_probability:.3f}{trigger_str})"


class VideoSelectorBeat(VJInterpreterBase):
    """Switches videos on beat detection"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        beat_signal: FrameSignal = FrameSignal.freq_high,
        beat_threshold: float = 0.6,
        cooldown_frames: int = 60,
    ):  # Minimum frames between switches
        super().__init__(layers, args)
        self.beat_signal = beat_signal
        self.beat_threshold = beat_threshold
        self.cooldown_frames = cooldown_frames
        self.frames_since_switch = cooldown_frames
        self.last_beat_value = 0.0

        # Filter for video layers only (including mock layers)
        from parrot.vj.layers.video import MockVideoLayer

        self.video_layers = [
            layer for layer in layers if isinstance(layer, (VideoLayer, MockVideoLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Switch videos on beat detection"""
        self.frames_since_switch += 1

        beat_value = frame[self.beat_signal]

        # Detect beat (rising edge above threshold)
        if (
            beat_value > self.beat_threshold
            and self.last_beat_value <= self.beat_threshold
            and self.frames_since_switch >= self.cooldown_frames
        ):

            # Switch videos
            for video_layer in self.video_layers:
                if hasattr(video_layer, "switch_video"):
                    video_layer.switch_video()

            self.frames_since_switch = 0

        self.last_beat_value = beat_value

    def __str__(self) -> str:
        return f"VideoSelectorBeat({self.beat_signal.name})"


class VideoSelectorTimed(VJInterpreterBase):
    """Switches videos at regular time intervals"""

    hype = 15

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        switch_interval: float = 30.0,
    ):  # Seconds between switches
        super().__init__(layers, args)
        self.switch_interval = switch_interval
        self.frame_count = 0
        self.target_fps = 60  # Assume 60 FPS for timing
        self.frames_per_switch = int(switch_interval * self.target_fps)

        # Filter for video layers only (including mock layers)
        from parrot.vj.layers.video import MockVideoLayer

        self.video_layers = [
            layer for layer in layers if isinstance(layer, (VideoLayer, MockVideoLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Switch videos at regular intervals"""
        self.frame_count += 1

        if self.frame_count >= self.frames_per_switch:
            # Switch videos
            for video_layer in self.video_layers:
                if hasattr(video_layer, "switch_video"):
                    video_layer.switch_video()

            self.frame_count = 0

    def __str__(self) -> str:
        return f"VideoSelectorTimed({self.switch_interval}s)"


class VideoSelectorHype(VJInterpreterBase):
    """Switches videos based on overall audio energy/hype"""

    hype = 40

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        energy_threshold: float = 0.8,
        cooldown_frames: int = 120,
    ):
        super().__init__(layers, args)
        self.energy_threshold = energy_threshold
        self.cooldown_frames = cooldown_frames
        self.frames_since_switch = cooldown_frames

        # Filter for video layers only (including mock layers)
        from parrot.vj.layers.video import MockVideoLayer

        self.video_layers = [
            layer for layer in layers if isinstance(layer, (VideoLayer, MockVideoLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Switch videos based on overall energy"""
        self.frames_since_switch += 1

        # Calculate overall energy from multiple frequency bands
        energy = 0.0
        energy_signals = [
            FrameSignal.freq_low,
            FrameSignal.freq_all,  # Use freq_all instead of freq_mid
            FrameSignal.freq_high,
        ]

        for signal in energy_signals:
            energy += frame[signal]

        energy /= len(energy_signals)  # Average energy

        # Switch if energy is high and cooldown has passed
        if (
            energy > self.energy_threshold
            and self.frames_since_switch >= self.cooldown_frames
        ):
            for video_layer in self.video_layers:
                if hasattr(video_layer, "switch_video"):
                    video_layer.switch_video()

            self.frames_since_switch = 0

    def __str__(self) -> str:
        return f"VideoSelectorHype({self.energy_threshold:.1f})"
