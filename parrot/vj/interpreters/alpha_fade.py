from typing import List
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class AlphaFade(VJInterpreterBase):
    """Controls layer alpha based on audio signals"""

    hype = 30

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        signal: FrameSignal = FrameSignal.sustained_low,
        min_alpha: float = 0.0,
        max_alpha: float = 1.0,
        smoothing: float = 0.1,
    ):
        super().__init__(layers, args)
        self.signal = signal
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.smoothing = smoothing  # Smoothing factor for alpha changes
        self.current_alpha = min_alpha

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update layer alpha based on signal strength"""
        signal_value = frame[self.signal]

        # Map signal value to alpha range
        target_alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * signal_value

        # Apply smoothing
        self.current_alpha += (target_alpha - self.current_alpha) * self.smoothing

        # Apply alpha to all layers
        for layer in self.layers:
            layer.set_alpha(self.current_alpha)

    def __str__(self) -> str:
        return f"AlphaFade({self.signal.name})"


class AlphaFlash(VJInterpreterBase):
    """Flashes layer alpha on beat or signal triggers"""

    hype = 50

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        signal: FrameSignal = FrameSignal.freq_high,
        threshold: float = 0.5,
        flash_alpha: float = 1.0,
        base_alpha: float = 0.3,
        decay_rate: float = 0.05,
    ):
        super().__init__(layers, args)
        self.signal = signal
        self.threshold = threshold
        self.flash_alpha = flash_alpha
        self.base_alpha = base_alpha
        self.decay_rate = decay_rate
        self.current_alpha = base_alpha
        self.is_flashing = False

    def step(self, frame: Frame, scheme: ColorScheme):
        """Flash alpha on signal triggers"""
        signal_value = frame[self.signal]

        # Trigger flash if signal exceeds threshold
        if signal_value > self.threshold:
            self.current_alpha = self.flash_alpha
            self.is_flashing = True
        else:
            # Decay back to base alpha
            if self.is_flashing:
                self.current_alpha -= self.decay_rate
                if self.current_alpha <= self.base_alpha:
                    self.current_alpha = self.base_alpha
                    self.is_flashing = False

        # Apply alpha to all layers
        for layer in self.layers:
            layer.set_alpha(self.current_alpha)

    def __str__(self) -> str:
        return f"AlphaFlash({self.signal.name})"


class AlphaPulse(VJInterpreterBase):
    """Creates a pulsing alpha effect based on audio signals"""

    hype = 40

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        signal: FrameSignal = FrameSignal.sustained_low,
        pulse_speed: float = 0.1,
        min_alpha: float = 0.2,
        max_alpha: float = 1.0,
    ):
        super().__init__(layers, args)
        self.signal = signal
        self.pulse_speed = pulse_speed
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.pulse_phase = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create pulsing alpha effect"""
        signal_value = frame[self.signal]

        # Update pulse phase based on signal strength
        self.pulse_phase += self.pulse_speed * (1.0 + signal_value * 2.0)

        # Calculate alpha using sine wave
        import math

        pulse_factor = (math.sin(self.pulse_phase) + 1.0) / 2.0
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * pulse_factor

        # Apply signal influence
        alpha *= 0.5 + 0.5 * signal_value

        # Apply alpha to all layers
        for layer in self.layers:
            layer.set_alpha(alpha)

    def __str__(self) -> str:
        return f"AlphaPulse({self.signal.name})"


class AlphaStatic(VJInterpreterBase):
    """Maintains a static alpha value"""

    hype = 10

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, alpha: float = 1.0
    ):
        super().__init__(layers, args)
        self.static_alpha = alpha

    def step(self, frame: Frame, scheme: ColorScheme):
        """Maintain static alpha"""
        for layer in self.layers:
            layer.set_alpha(self.static_alpha)

    def __str__(self) -> str:
        return f"AlphaStatic({self.static_alpha:.1f})"
