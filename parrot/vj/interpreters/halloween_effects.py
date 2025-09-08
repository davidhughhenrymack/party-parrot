"""
Halloween-themed VJ effect interpreters for "Dead Sexy" party
"""

import math
import random
import time
from typing import List
import numpy as np
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class LightningFlash(VJInterpreterBase):
    """Creates dramatic lightning flash effects on high energy"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        energy_threshold: float = 0.7,
        flash_color: tuple = (255, 255, 255),
        flash_duration: int = 3,
        flash_intensity: float = 0.9,
    ):
        super().__init__(layers, args)
        self.energy_threshold = energy_threshold
        self.flash_color = flash_color
        self.flash_duration = flash_duration
        self.flash_intensity = flash_intensity
        self.flash_frames_remaining = 0
        self.last_energy = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create lightning flash on high energy"""
        # Calculate total energy
        energy = (
            frame[FrameSignal.freq_low]
            + frame[FrameSignal.freq_high]
            + frame[FrameSignal.freq_all]
        ) / 3.0

        # Trigger flash on energy spike
        if energy > self.energy_threshold and self.last_energy <= self.energy_threshold:
            self.flash_frames_remaining = self.flash_duration + random.randint(
                0, 3
            )  # Vary duration

        # Apply flash effect
        if self.flash_frames_remaining > 0:
            self.flash_frames_remaining -= 1

            # Create lightning effect - bright white with slight blue tint
            flash_alpha = self.flash_intensity * (
                self.flash_frames_remaining / self.flash_duration
            )

            for layer in self.layers:
                if hasattr(layer, "set_color"):
                    # Lightning color with intensity decay
                    intensity = int(255 * flash_alpha)
                    lightning_color = (
                        intensity,
                        intensity,
                        min(255, intensity + 20),
                    )  # Slight blue
                    layer.set_color(lightning_color)

                if hasattr(layer, "set_alpha"):
                    layer.set_alpha(flash_alpha)

        self.last_energy = energy

    def __str__(self) -> str:
        return f"⚡LightningFlash({self.energy_threshold:.1f})"


class BloodDrip(VJInterpreterBase):
    """Creates blood drip effects that respond to bass"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        drip_threshold: float = 0.6,
        drip_color: tuple = (139, 0, 0),  # Dark red
        drip_speed: float = 0.02,
    ):
        super().__init__(layers, args)
        self.drip_threshold = drip_threshold
        self.drip_color = drip_color
        self.drip_speed = drip_speed
        self.drip_phase = 0.0
        self.drip_intensity = 0.0
        self.last_bass = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create blood drip effects"""
        bass_level = frame[FrameSignal.freq_low]

        # Trigger drip on bass hits
        if bass_level > self.drip_threshold and self.last_bass <= self.drip_threshold:
            self.drip_intensity = min(1.0, self.drip_intensity + 0.3)

        # Decay drip intensity
        self.drip_intensity *= 0.95
        self.drip_phase += self.drip_speed

        # Apply blood effect
        if self.drip_intensity > 0.1:
            # Vary the blood color intensity
            drip_factor = self.drip_intensity * (
                0.7 + 0.3 * math.sin(self.drip_phase * 5)
            )

            for layer in self.layers:
                if hasattr(layer, "set_color"):
                    # Blood red with varying intensity
                    r = int(self.drip_color[0] * drip_factor)
                    g = int(self.drip_color[1] * drip_factor * 0.3)  # Less green
                    b = int(self.drip_color[2] * drip_factor * 0.2)  # Even less blue

                    layer.set_color((r, g, b))

                if hasattr(layer, "set_alpha"):
                    layer.set_alpha(0.3 + 0.7 * drip_factor)

        self.last_bass = bass_level

    def __str__(self) -> str:
        return f"🩸BloodDrip({self.drip_threshold:.1f})"


class HorrorContrast(VJInterpreterBase):
    """Dramatic contrast effects that respond to audio energy"""

    hype = 50

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        contrast_range: tuple = (0.3, 2.0),
        response_speed: float = 0.1,
    ):
        super().__init__(layers, args)
        self.min_contrast, self.max_contrast = contrast_range
        self.response_speed = response_speed
        self.current_contrast = 1.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Adjust contrast based on audio energy"""
        # Calculate overall energy
        energy = (frame[FrameSignal.freq_low] + frame[FrameSignal.freq_high]) / 2.0

        # Map energy to contrast
        target_contrast = (
            self.min_contrast + (self.max_contrast - self.min_contrast) * energy
        )

        # Smooth transition
        self.current_contrast += (
            target_contrast - self.current_contrast
        ) * self.response_speed

        # Apply contrast effect to layers that support it
        for layer in self.layers:
            if hasattr(layer, "set_color") and hasattr(layer, "color"):
                # Adjust layer color for contrast
                base_color = getattr(layer, "color", (128, 128, 128))

                # Apply contrast adjustment
                adjusted_color = tuple(
                    max(0, min(255, int((c - 128) * self.current_contrast + 128)))
                    for c in base_color
                )

                layer.set_color(adjusted_color)

    def __str__(self) -> str:
        return f"🌑HorrorContrast({self.current_contrast:.1f})"


class DeadSexyTextHorror(VJInterpreterBase):
    """Spooky text effects for "DEAD SEXY" text"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        shake_intensity: float = 0.05,
        grow_factor: float = 0.4,
        pulse_speed: float = 0.15,
    ):
        super().__init__(layers, args)
        self.shake_intensity = shake_intensity
        self.grow_factor = grow_factor
        self.pulse_speed = pulse_speed
        self.phase = 0.0
        self.scare_mode = False
        self.scare_countdown = 0

        # Filter for text layers
        from parrot.vj.layers.text import TextLayer, MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply spooky text effects"""
        self.phase += self.pulse_speed

        # Get audio signals
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Random scare events on high energy
        if energy > 0.8 and random.random() < 0.05:  # 5% chance on high energy
            self.scare_mode = True
            self.scare_countdown = 30  # 30 frames of scare

        for text_layer in self.text_layers:
            if self.scare_mode and self.scare_countdown > 0:
                # SCARE MODE - dramatic effects
                self.scare_countdown -= 1

                if hasattr(text_layer, "set_scale"):
                    # Rapid size pulsing
                    scare_scale = 1.0 + 0.8 * math.sin(self.phase * 8) * (
                        self.scare_countdown / 30
                    )
                    text_layer.set_scale(scare_scale)

                if hasattr(text_layer, "set_position"):
                    # Violent shaking
                    shake_x = 0.5 + self.shake_intensity * 3 * math.sin(
                        self.phase * 12
                    ) * (self.scare_countdown / 30)
                    shake_y = 0.5 + self.shake_intensity * 3 * math.cos(
                        self.phase * 15
                    ) * (self.scare_countdown / 30)
                    text_layer.set_position(shake_x, shake_y)

                if hasattr(text_layer, "set_color"):
                    # Flash between red and white
                    if self.scare_countdown % 4 < 2:
                        text_layer.set_color((255, 0, 0))  # Blood red
                    else:
                        text_layer.set_color((255, 255, 255))  # Ghost white

                if self.scare_countdown <= 0:
                    self.scare_mode = False

            else:
                # NORMAL MODE - subtle spooky effects
                if hasattr(text_layer, "set_scale"):
                    # Breathing effect based on bass
                    base_scale = 1.0 + self.grow_factor * bass
                    breath_scale = base_scale + 0.1 * math.sin(self.phase * 2)
                    text_layer.set_scale(breath_scale)

                if hasattr(text_layer, "set_position"):
                    # Subtle floating based on treble
                    float_x = 0.5 + self.shake_intensity * treble * math.sin(self.phase)
                    float_y = 0.5 + self.shake_intensity * treble * math.cos(
                        self.phase * 0.7
                    )
                    text_layer.set_position(float_x, float_y)

                if hasattr(text_layer, "set_color"):
                    # Color shifts between dark red and purple
                    red_intensity = 100 + int(
                        155 * (0.7 + 0.3 * math.sin(self.phase * 0.5))
                    )
                    purple_factor = 0.3 + 0.4 * energy

                    r = red_intensity
                    g = int(purple_factor * 50)
                    b = int(purple_factor * red_intensity * 0.6)

                    text_layer.set_color((r, g, b))

    def __str__(self) -> str:
        return f"💀DeadSexyTextHorror({'SCARE' if self.scare_mode else 'normal'})"


class SpookyLighting(VJInterpreterBase):
    """Multiplicative lighting layer with moving light elements"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_lights: int = 4,
        light_size_range: tuple = (0.05, 0.15),
        light_colors: List[tuple] = None,
    ):
        super().__init__(layers, args)
        self.num_lights = num_lights
        self.min_size, self.max_size = light_size_range
        self.light_colors = light_colors or [
            (255, 255, 200),  # Warm white
            (200, 255, 200),  # Sickly green
            (255, 200, 255),  # Eerie purple
            (255, 100, 100),  # Blood red
        ]

        # Initialize light positions and properties
        self.lights = []
        for i in range(num_lights):
            self.lights.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "size": random.uniform(self.min_size, self.max_size),
                    "phase": random.random() * math.pi * 2,
                    "speed": random.uniform(0.01, 0.03),
                    "color_index": i % len(self.light_colors),
                    "color": self.light_colors[
                        i % len(self.light_colors)
                    ],  # Add actual color
                    "intensity": 0.0,
                }
            )

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update moving lights based on audio"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update each light
        for i, light in enumerate(self.lights):
            # Move lights in circular/figure-8 patterns
            light["phase"] += light["speed"] * (1.0 + energy)

            if i % 2 == 0:
                # Circular motion
                light["x"] = 0.5 + 0.3 * math.cos(light["phase"])
                light["y"] = 0.5 + 0.3 * math.sin(light["phase"])
            else:
                # Figure-8 motion
                light["x"] = 0.5 + 0.3 * math.cos(light["phase"])
                light["y"] = 0.5 + 0.2 * math.sin(light["phase"] * 2)

            # Size responds to different frequency bands
            if i % 3 == 0:
                light["size"] = self.min_size + (self.max_size - self.min_size) * bass
            elif i % 3 == 1:
                light["size"] = self.min_size + (self.max_size - self.min_size) * treble
            else:
                light["size"] = self.min_size + (self.max_size - self.min_size) * energy

            # Intensity flickers
            light["intensity"] = 0.3 + 0.7 * energy + 0.2 * math.sin(light["phase"] * 3)

        # Apply lighting effect to compatible layers
        self._apply_lighting_to_layers()

    def _apply_lighting_to_layers(self):
        """Apply lighting effect to layers (placeholder for now)"""
        # This would be implemented with actual lighting layer rendering
        # For now, we'll just modify layer properties
        for layer in self.layers:
            if hasattr(layer, "set_alpha"):
                # Subtle alpha modulation based on average light intensity
                avg_intensity = sum(light["intensity"] for light in self.lights) / len(
                    self.lights
                )
                layer.set_alpha(0.7 + 0.3 * avg_intensity)

    def get_light_info(self) -> List[dict]:
        """Get current light positions and properties for rendering"""
        return self.lights.copy()

    def __str__(self) -> str:
        return f"🕯️SpookyLighting({self.num_lights} lights)"


class HalloweenGlitch(VJInterpreterBase):
    """Digital glitch effects for horror atmosphere"""

    hype = 75

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        glitch_probability: float = 0.02,
        glitch_intensity: float = 0.5,
        glitch_duration: int = 5,
    ):
        super().__init__(layers, args)
        self.glitch_probability = glitch_probability
        self.glitch_intensity = glitch_intensity
        self.glitch_duration = glitch_duration
        self.glitch_frames_remaining = 0
        self.glitch_type = 0  # 0=color shift, 1=position shift, 2=scale distort

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply glitch effects"""
        energy = frame[FrameSignal.freq_all]

        # Trigger glitch randomly or on high energy
        if random.random() < self.glitch_probability * (1 + energy) or energy > 0.85:
            self.glitch_frames_remaining = self.glitch_duration
            self.glitch_type = random.randint(0, 2)

        # Apply glitch effect
        if self.glitch_frames_remaining > 0:
            self.glitch_frames_remaining -= 1
            intensity = self.glitch_intensity * (
                self.glitch_frames_remaining / self.glitch_duration
            )

            for layer in self.layers:
                if self.glitch_type == 0 and hasattr(layer, "set_color"):
                    # Color channel shift glitch
                    if hasattr(layer, "color"):
                        base_color = layer.color
                        shift = int(intensity * 50)
                        glitch_color = (
                            (base_color[0] + shift) % 256,
                            base_color[1],
                            (base_color[2] - shift) % 256,
                        )
                        layer.set_color(glitch_color)

                elif self.glitch_type == 1 and hasattr(layer, "set_position"):
                    # Position glitch
                    glitch_x = 0.5 + intensity * 0.1 * random.uniform(-1, 1)
                    glitch_y = 0.5 + intensity * 0.1 * random.uniform(-1, 1)
                    layer.set_position(glitch_x, glitch_y)

                elif self.glitch_type == 2 and hasattr(layer, "set_scale"):
                    # Scale distortion glitch
                    glitch_scale = 1.0 + intensity * random.uniform(-0.3, 0.7)
                    layer.set_scale(glitch_scale)

    def __str__(self) -> str:
        return f"📺HalloweenGlitch({'ACTIVE' if self.glitch_frames_remaining > 0 else 'idle'})"


class GhostlyFade(VJInterpreterBase):
    """Ghostly fading in/out effects"""

    hype = 40

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        fade_speed: float = 0.03,
        min_alpha: float = 0.1,
        max_alpha: float = 0.9,
    ):
        super().__init__(layers, args)
        self.fade_speed = fade_speed
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.fade_phase = 0.0
        self.fade_direction = 1

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create ghostly fading effects"""
        sustained = frame[FrameSignal.sustained_low]

        # Fade speed affected by sustained energy
        effective_speed = self.fade_speed * (0.5 + 1.5 * sustained)
        self.fade_phase += effective_speed

        # Create ghostly sine wave fade
        fade_factor = (math.sin(self.fade_phase) + 1.0) / 2.0
        alpha = self.min_alpha + (self.max_alpha - self.min_alpha) * fade_factor

        # Apply to all layers
        for layer in self.layers:
            layer.set_alpha(alpha)

    def __str__(self) -> str:
        return f"👻GhostlyFade({self.fade_phase:.1f})"


class BloodSplatter(VJInterpreterBase):
    """Blood splatter effects on beat hits"""

    hype = 85

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        splatter_threshold: float = 0.7,
        splatter_colors: List[tuple] = None,
    ):
        super().__init__(layers, args)
        self.splatter_threshold = splatter_threshold
        self.splatter_colors = splatter_colors or [
            (139, 0, 0),  # Dark red
            (160, 20, 20),  # Slightly lighter red
            (100, 0, 0),  # Very dark red
            (180, 0, 30),  # Bright red with hint of pink
        ]
        self.splatter_frames = 0
        self.current_splatter_color = self.splatter_colors[0]
        self.last_signal = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create blood splatter on beats"""
        signal = frame[FrameSignal.freq_high]

        # Trigger splatter on beat (rising edge)
        if (
            signal > self.splatter_threshold
            and self.last_signal <= self.splatter_threshold
        ):
            self.splatter_frames = 8 + random.randint(0, 5)  # Variable duration
            self.current_splatter_color = random.choice(self.splatter_colors)

        # Apply splatter effect
        if self.splatter_frames > 0:
            self.splatter_frames -= 1

            # Splatter intensity decays
            intensity = self.splatter_frames / 8.0

            for layer in self.layers:
                if hasattr(layer, "set_color"):
                    # Apply blood color with intensity
                    r, g, b = self.current_splatter_color
                    splatter_color = (
                        int(r * intensity),
                        int(g * intensity),
                        int(b * intensity),
                    )
                    layer.set_color(splatter_color)

                if hasattr(layer, "set_alpha"):
                    # High alpha during splatter
                    layer.set_alpha(0.6 + 0.4 * intensity)

        self.last_signal = signal

    def __str__(self) -> str:
        return f"🩸BloodSplatter({'SPLAT!' if self.splatter_frames > 0 else 'ready'})"


class EerieBreathing(VJInterpreterBase):
    """Breathing effect that creates eerie atmosphere"""

    hype = 30

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        breath_speed: float = 0.04,
        breath_depth: float = 0.3,
    ):
        super().__init__(layers, args)
        self.breath_speed = breath_speed
        self.breath_depth = breath_depth
        self.breath_phase = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create breathing effect"""
        sustained = frame[FrameSignal.sustained_low]

        # Breathing slows down with low sustained energy (more eerie)
        effective_speed = self.breath_speed * (0.3 + 0.7 * sustained)
        self.breath_phase += effective_speed

        # Breathing curve (not perfect sine - more organic)
        breath_curve = math.sin(self.breath_phase)
        breath_curve = breath_curve + 0.3 * math.sin(self.breath_phase * 2.1)
        breath_factor = (breath_curve + 1.0) / 2.0

        # Apply breathing effect
        for layer in self.layers:
            if hasattr(layer, "set_alpha"):
                # Alpha breathing
                alpha = 0.4 + self.breath_depth * breath_factor
                layer.set_alpha(alpha)

            if hasattr(layer, "set_scale"):
                # Scale breathing for text
                scale = 0.9 + 0.2 * breath_factor
                layer.set_scale(scale)

    def __str__(self) -> str:
        return f"🫁EerieBreathing({self.breath_phase:.1f})"


class HalloweenStrobeEffect(VJInterpreterBase):
    """Strobing effects with Halloween colors"""

    hype = 90

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_colors: List[tuple] = None,
        strobe_speed: float = 0.3,
    ):
        super().__init__(layers, args)
        self.strobe_colors = strobe_colors or [
            (255, 0, 0),  # Blood red
            (255, 165, 0),  # Pumpkin orange
            (128, 0, 128),  # Dark purple
            (0, 0, 0),  # Black (off)
            (255, 255, 255),  # Ghost white
        ]
        self.strobe_speed = strobe_speed
        self.strobe_phase = 0.0
        self.current_color_index = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create Halloween strobe effects"""
        # Strobe triggered by manual strobe signal or high energy
        strobe_signal = frame[FrameSignal.strobe]
        energy = frame[FrameSignal.freq_all]

        # Fast strobing on manual trigger, slow on energy
        if strobe_signal > 0.5:
            self.strobe_phase += self.strobe_speed * 10  # Fast strobe
        else:
            self.strobe_phase += self.strobe_speed * (
                1 + energy * 3
            )  # Energy-based speed

        # Change color on phase transitions
        new_color_index = int(self.strobe_phase) % len(self.strobe_colors)
        if new_color_index != self.current_color_index:
            self.current_color_index = new_color_index

        current_color = self.strobe_colors[self.current_color_index]

        # Apply strobe effect
        for layer in self.layers:
            if hasattr(layer, "set_color"):
                layer.set_color(current_color)

            if hasattr(layer, "set_alpha"):
                # Alpha also strobes
                alpha_phase = self.strobe_phase * 2
                alpha = 0.3 + 0.7 * ((math.sin(alpha_phase) + 1.0) / 2.0)
                layer.set_alpha(alpha)

    def __str__(self) -> str:
        return f"🎃HalloweenStrobe({self.strobe_colors[self.current_color_index]})"


class CreepyCrawl(VJInterpreterBase):
    """Text that crawls and moves in creepy ways"""

    hype = 55

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        crawl_speed: float = 0.02,
        crawl_patterns: List[str] = None,
    ):
        super().__init__(layers, args)
        self.crawl_speed = crawl_speed
        self.crawl_patterns = crawl_patterns or ["circle", "zigzag", "spiral", "shake"]
        self.current_pattern = random.choice(self.crawl_patterns)
        self.crawl_phase = 0.0
        self.pattern_change_timer = 0

        # Filter for text layers
        from parrot.vj.layers.text import TextLayer, MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Make text crawl in creepy patterns"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]

        # Speed affected by audio
        effective_speed = self.crawl_speed * (0.5 + 1.5 * bass)
        self.crawl_phase += effective_speed

        # Change pattern occasionally
        self.pattern_change_timer += 1
        if (
            self.pattern_change_timer > 300 or treble > 0.8
        ):  # Change pattern on high treble
            self.current_pattern = random.choice(self.crawl_patterns)
            self.pattern_change_timer = 0

        for text_layer in self.text_layers:
            if hasattr(text_layer, "set_position"):
                x, y = self._calculate_crawl_position()
                text_layer.set_position(x, y)

            if hasattr(text_layer, "set_scale"):
                # Scale varies with pattern
                if self.current_pattern == "shake":
                    scale = 1.0 + 0.2 * treble * random.uniform(-1, 1)
                else:
                    scale = 0.8 + 0.4 * bass
                text_layer.set_scale(scale)

    def _calculate_crawl_position(self) -> tuple:
        """Calculate position based on current crawl pattern"""
        if self.current_pattern == "circle":
            x = 0.5 + 0.2 * math.cos(self.crawl_phase)
            y = 0.5 + 0.2 * math.sin(self.crawl_phase)

        elif self.current_pattern == "zigzag":
            x = 0.2 + 0.6 * ((self.crawl_phase % 2.0) / 2.0)
            y = 0.5 + 0.3 * math.sin(self.crawl_phase * 3)

        elif self.current_pattern == "spiral":
            radius = 0.1 + 0.2 * (self.crawl_phase % 4.0) / 4.0
            x = 0.5 + radius * math.cos(self.crawl_phase * 2)
            y = 0.5 + radius * math.sin(self.crawl_phase * 2)

        elif self.current_pattern == "shake":
            x = 0.5 + 0.05 * random.uniform(-1, 1)
            y = 0.5 + 0.05 * random.uniform(-1, 1)

        else:  # fallback
            x, y = 0.5, 0.5

        return (max(0.1, min(0.9, x)), max(0.1, min(0.9, y)))

    def __str__(self) -> str:
        return f"🕷️CreepyCrawl({self.current_pattern})"


class PumpkinPulse(VJInterpreterBase):
    """Pumpkin-colored pulsing effects"""

    hype = 45

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        pulse_colors: List[tuple] = None,
        pulse_speed: float = 0.08,
    ):
        super().__init__(layers, args)
        self.pulse_colors = pulse_colors or [
            (255, 165, 0),  # Orange
            (255, 140, 0),  # Dark orange
            (255, 69, 0),  # Red orange
            (255, 215, 0),  # Gold
        ]
        self.pulse_speed = pulse_speed
        self.pulse_phase = 0.0

    def step(self, frame: Frame, scheme: ColorScheme):
        """Create pumpkin-colored pulsing"""
        bass = frame[FrameSignal.freq_low]

        # Pulse speed affected by bass
        effective_speed = self.pulse_speed * (0.5 + 1.5 * bass)
        self.pulse_phase += effective_speed

        # Cycle through pumpkin colors
        color_index = int(self.pulse_phase) % len(self.pulse_colors)
        color_blend = self.pulse_phase - int(self.pulse_phase)

        current_color = self.pulse_colors[color_index]
        next_color = self.pulse_colors[(color_index + 1) % len(self.pulse_colors)]

        # Blend between colors
        blended_color = tuple(
            int(current_color[i] * (1 - color_blend) + next_color[i] * color_blend)
            for i in range(3)
        )

        # Apply to layers
        for layer in self.layers:
            if hasattr(layer, "set_color"):
                layer.set_color(blended_color)

            if hasattr(layer, "set_alpha"):
                # Pulse alpha too
                alpha = 0.5 + 0.5 * ((math.sin(self.pulse_phase * 2) + 1.0) / 2.0)
                layer.set_alpha(alpha)

    def __str__(self) -> str:
        return f"🎃PumpkinPulse({self.pulse_phase:.1f})"


class HorrorTextScream(VJInterpreterBase):
    """Makes text "scream" on high energy - dramatic size and shake"""

    hype = 95

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        scream_threshold: float = 0.8,
        max_scale: float = 2.5,
        shake_intensity: float = 0.15,
    ):
        super().__init__(layers, args)
        self.scream_threshold = scream_threshold
        self.max_scale = max_scale
        self.shake_intensity = shake_intensity
        self.is_screaming = False
        self.scream_intensity = 0.0

        # Filter for text layers
        from parrot.vj.layers.text import TextLayer, MockTextLayer

        self.text_layers = [
            layer for layer in layers if isinstance(layer, (TextLayer, MockTextLayer))
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Make text scream on high energy"""
        energy = (frame[FrameSignal.freq_low] + frame[FrameSignal.freq_high]) / 2.0

        # Trigger scream on high energy
        if energy > self.scream_threshold:
            self.is_screaming = True
            self.scream_intensity = min(1.0, self.scream_intensity + 0.2)
        else:
            self.scream_intensity *= 0.8  # Decay
            if self.scream_intensity < 0.1:
                self.is_screaming = False

        for text_layer in self.text_layers:
            if self.is_screaming:
                if hasattr(text_layer, "set_scale"):
                    # Explosive scaling
                    scream_scale = 1.0 + (self.max_scale - 1.0) * self.scream_intensity
                    text_layer.set_scale(scream_scale)

                if hasattr(text_layer, "set_position"):
                    # Violent shaking
                    shake_x = (
                        0.5
                        + self.shake_intensity
                        * random.uniform(-1, 1)
                        * self.scream_intensity
                    )
                    shake_y = (
                        0.5
                        + self.shake_intensity
                        * random.uniform(-1, 1)
                        * self.scream_intensity
                    )
                    text_layer.set_position(shake_x, shake_y)

                if hasattr(text_layer, "set_color"):
                    # Flash between colors
                    if int(time.time() * 20) % 2:
                        text_layer.set_color((255, 0, 0))  # Red
                    else:
                        text_layer.set_color((255, 255, 255))  # White
            else:
                # Return to normal gradually
                if hasattr(text_layer, "set_scale"):
                    normal_scale = 1.0 + 0.1 * energy
                    text_layer.set_scale(normal_scale)

                if hasattr(text_layer, "set_position"):
                    text_layer.set_position(0.5, 0.5)  # Center

                if hasattr(text_layer, "set_color"):
                    # Dark red normal color
                    intensity = 150 + int(105 * energy)
                    text_layer.set_color((intensity, 0, 0))

    def __str__(self) -> str:
        return f"😱HorrorTextScream({'SCREAMING!' if self.is_screaming else 'waiting'})"
