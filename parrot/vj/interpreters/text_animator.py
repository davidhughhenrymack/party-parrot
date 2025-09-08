import math
import random
from typing import List
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.vj.layers.text import TextLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class TextAnimator(VJInterpreterBase):
    """Animates text properties based on audio signals"""

    hype = 35

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        animate_scale: bool = True,
        animate_position: bool = False,
        animate_color: bool = True,
    ):
        super().__init__(layers, args)
        self.animate_scale = animate_scale
        self.animate_position = animate_position
        self.animate_color = animate_color
        self.frame_count = 0

        # Filter for text layers only (including mock layers)
        from parrot.vj.layers.text import MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Animate text properties"""
        self.frame_count += 1

        # Get audio signals for animation
        low_freq = frame[FrameSignal.freq_low]
        mid_freq = frame[FrameSignal.freq_all]  # Use freq_all instead of freq_mid
        high_freq = frame[FrameSignal.freq_high]

        for text_layer in self.text_layers:
            if not hasattr(text_layer, "set_scale"):
                continue

            # Animate scale based on low frequency
            if self.animate_scale:
                base_scale = 1.0
                scale_variation = 0.3 * low_freq
                scale = base_scale + scale_variation
                text_layer.set_scale(scale)

            # Animate position based on mid frequency
            if self.animate_position:
                base_x, base_y = 0.5, 0.5
                position_variation = 0.05

                x_offset = (
                    position_variation * mid_freq * math.sin(self.frame_count * 0.1)
                )
                y_offset = (
                    position_variation * mid_freq * math.cos(self.frame_count * 0.1)
                )

                text_layer.set_position(base_x + x_offset, base_y + y_offset)

            # Animate color based on high frequency and color scheme
            if self.animate_color and hasattr(text_layer, "set_color"):
                # Use color scheme with high frequency influence
                base_color = scheme.fg.rgb
                # Convert to 0-255 range
                base_color = tuple(int(c * 255) for c in base_color)

                # Add high frequency sparkle
                sparkle = int(high_freq * 100)
                color = tuple(min(255, c + sparkle) for c in base_color)

                text_layer.set_color(color)

    def __str__(self) -> str:
        features = []
        if self.animate_scale:
            features.append("scale")
        if self.animate_position:
            features.append("pos")
        if self.animate_color:
            features.append("color")
        return f"TextAnimator({','.join(features)})"


class TextPulse(VJInterpreterBase):
    """Makes text pulse with the beat"""

    hype = 50

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        pulse_signal: FrameSignal = FrameSignal.freq_high,
        min_scale: float = 0.8,
        max_scale: float = 1.5,
        decay_rate: float = 0.05,
    ):
        super().__init__(layers, args)
        self.pulse_signal = pulse_signal
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.decay_rate = decay_rate
        self.current_scale = 1.0

        # Filter for text layers only (including mock layers)
        from parrot.vj.layers.text import MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Pulse text scale with audio"""
        signal_value = frame[self.pulse_signal]

        # Set target scale based on signal
        target_scale = self.min_scale + (self.max_scale - self.min_scale) * signal_value

        # Smooth transition to target scale
        self.current_scale += (target_scale - self.current_scale) * 0.3

        # Apply scale to all text layers
        for text_layer in self.text_layers:
            if hasattr(text_layer, "set_scale"):
                text_layer.set_scale(self.current_scale)

    def __str__(self) -> str:
        return f"TextPulse({self.pulse_signal.name})"


class TextColorCycle(VJInterpreterBase):
    """Cycles text color through the color scheme"""

    hype = 25

    def __init__(
        self, layers: List[LayerBase], args: InterpreterArgs, cycle_speed: float = 0.02
    ):
        super().__init__(layers, args)
        self.cycle_speed = cycle_speed
        self.cycle_phase = 0.0

        # Filter for text layers only (including mock layers)
        from parrot.vj.layers.text import MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Cycle through colors in the scheme"""
        self.cycle_phase += self.cycle_speed

        # Get colors from scheme
        colors = [scheme.fg, scheme.bg, scheme.bg_contrast]

        # Calculate which color to use based on phase
        color_index = int(self.cycle_phase) % len(colors)
        color_blend = self.cycle_phase - int(self.cycle_phase)

        current_color = colors[color_index]
        next_color = colors[(color_index + 1) % len(colors)]

        # Blend between current and next color
        r = int(
            (current_color.red * (1 - color_blend) + next_color.red * color_blend) * 255
        )
        g = int(
            (current_color.green * (1 - color_blend) + next_color.green * color_blend)
            * 255
        )
        b = int(
            (current_color.blue * (1 - color_blend) + next_color.blue * color_blend)
            * 255
        )

        blended_color = (r, g, b)

        # Apply to all text layers
        for text_layer in self.text_layers:
            if hasattr(text_layer, "set_color"):
                text_layer.set_color(blended_color)

    def __str__(self) -> str:
        return f"TextColorCycle({self.cycle_speed:.3f})"


class TextFlash(VJInterpreterBase):
    """Flashes text color on beat triggers"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        flash_signal: FrameSignal = FrameSignal.freq_high,
        flash_threshold: float = 0.6,
        flash_color: tuple = (255, 255, 255),
        flash_duration: int = 5,
    ):  # frames
        super().__init__(layers, args)
        self.flash_signal = flash_signal
        self.flash_threshold = flash_threshold
        self.flash_color = flash_color
        self.flash_duration = flash_duration
        self.flash_frames_remaining = 0
        self.last_signal_value = 0.0
        self.normal_color = (255, 255, 255)

        # Filter for text layers only (including mock layers)
        from parrot.vj.layers.text import MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Flash text on signal triggers"""
        signal_value = frame[self.flash_signal]

        # Store normal color from scheme
        rgb = scheme.fg.rgb
        self.normal_color = tuple(int(c * 255) for c in rgb)

        # Trigger flash on signal edge
        if (
            signal_value > self.flash_threshold
            and self.last_signal_value <= self.flash_threshold
        ):
            self.flash_frames_remaining = self.flash_duration

        # Update flash countdown
        if self.flash_frames_remaining > 0:
            self.flash_frames_remaining -= 1
            color = self.flash_color
        else:
            color = self.normal_color

        # Apply color to all text layers
        for text_layer in self.text_layers:
            if hasattr(text_layer, "set_color"):
                text_layer.set_color(color)

        self.last_signal_value = signal_value

    def __str__(self) -> str:
        return f"TextFlash({self.flash_signal.name})"


class TextStatic(VJInterpreterBase):
    """Keeps text properties static"""

    hype = 5

    def __init__(self, layers: List[LayerBase], args: InterpreterArgs):
        super().__init__(layers, args)

        # Filter for text layers only (including mock layers)
        from parrot.vj.layers.text import MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Keep text static but update color from scheme"""
        rgb = scheme.fg.rgb
        color = tuple(int(c * 255) for c in rgb)

        for text_layer in self.text_layers:
            if hasattr(text_layer, "set_color"):
                text_layer.set_color(color)

    def __str__(self) -> str:
        return "TextStatic"
