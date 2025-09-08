"""
Color scheme lighting interpreters that apply multiplicative lighting effects
"""

import math
import random
from typing import List, Tuple
import numpy as np
from parrot.vj.base import VJInterpreterBase, LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs


class ColorSchemeLighting(VJInterpreterBase):
    """Applies color scheme as multiplicative lighting to video layers"""

    hype = 40

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        color_source: str = "fg",  # "fg", "bg", "bg_contrast", "cycle"
        intensity: float = 1.5,
        response_signal: FrameSignal = FrameSignal.freq_all,
    ):
        super().__init__(layers, args)
        self.color_source = color_source
        self.base_intensity = intensity
        self.response_signal = response_signal
        self.current_intensity = intensity
        self.cycle_phase = 0.0

        # Filter for video layers that support color lighting
        self.video_layers = []
        for layer in layers:
            if hasattr(layer, "render") and (
                "video" in layer.name.lower() or hasattr(layer, "current_frame")
            ):
                self.video_layers.append(layer)

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply color scheme lighting to video layers"""
        # Get signal strength for intensity modulation
        signal_strength = frame[self.response_signal]
        self.current_intensity = self.base_intensity * (0.5 + 1.5 * signal_strength)

        # Get the lighting color from the color scheme
        lighting_color = self._get_lighting_color(scheme)

        # Apply to compatible layers
        for layer in self.video_layers:
            self._apply_color_lighting(layer, lighting_color, self.current_intensity)

    def _get_lighting_color(self, scheme: ColorScheme) -> Tuple[float, float, float]:
        """Get the lighting color from the color scheme"""
        if self.color_source == "fg":
            color = scheme.fg
        elif self.color_source == "bg":
            color = scheme.bg
        elif self.color_source == "bg_contrast":
            color = scheme.bg_contrast
        elif self.color_source == "cycle":
            # Cycle through all colors
            self.cycle_phase += 0.02
            colors = [scheme.fg, scheme.bg, scheme.bg_contrast]
            color_index = int(self.cycle_phase) % len(colors)
            color = colors[color_index]
        else:
            color = scheme.fg  # Default fallback

        # Convert to 0-1 range RGB
        return color.rgb

    def _apply_color_lighting(
        self,
        layer: LayerBase,
        lighting_color: Tuple[float, float, float],
        intensity: float,
    ):
        """Apply multiplicative color lighting to a layer"""
        # Store lighting info on the layer for the renderer to use
        # This is a simplified approach - in a full implementation,
        # this would be handled by a specialized lighting layer or shader

        if hasattr(layer, "_lighting_color"):
            layer._lighting_color = lighting_color
        if hasattr(layer, "_lighting_intensity"):
            layer._lighting_intensity = intensity

        # For layers that support direct color modification
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            # Apply multiplicative lighting to existing color
            base_color = getattr(layer, "color", (128, 128, 128))

            # Convert base color to 0-1 range
            base_r, base_g, base_b = [c / 255.0 for c in base_color]

            # Apply multiplicative lighting
            lit_r = base_r * (1.0 + (lighting_color[0] - 0.5) * intensity)
            lit_g = base_g * (1.0 + (lighting_color[1] - 0.5) * intensity)
            lit_b = base_b * (1.0 + (lighting_color[2] - 0.5) * intensity)

            # Clamp and convert back to 0-255 range
            final_color = (
                max(0, min(255, int(lit_r * 255))),
                max(0, min(255, int(lit_g * 255))),
                max(0, min(255, int(lit_b * 255))),
            )

            layer.set_color(final_color)

    def __str__(self) -> str:
        return (
            f"🔦ColorSchemeLighting({self.color_source}, {self.current_intensity:.1f})"
        )


class RedLighting(VJInterpreterBase):
    """Red lighting that picks out red and white parts of video"""

    hype = 50

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        red_intensity: float = 2.0,
        white_boost: float = 1.5,
        response_signal: FrameSignal = FrameSignal.freq_low,
    ):
        super().__init__(layers, args)
        self.red_intensity = red_intensity
        self.white_boost = white_boost
        self.response_signal = response_signal
        self.current_red_intensity = red_intensity

        # Filter for video layers
        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        """Filter for video layers that can be lit"""
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply red lighting effect"""
        # Modulate intensity with audio signal
        signal_strength = frame[self.response_signal]
        self.current_red_intensity = self.red_intensity * (0.3 + 1.7 * signal_strength)

        # Apply red lighting to video layers
        for layer in self.video_layers:
            self._apply_red_lighting(layer, self.current_red_intensity)

    def _apply_red_lighting(self, layer: LayerBase, intensity: float):
        """Apply red multiplicative lighting"""
        # Store lighting parameters for rendering
        if hasattr(layer, "set_alpha"):
            # Use alpha to simulate lighting intensity
            layer.set_alpha(0.5 + 0.5 * min(1.0, intensity / 2.0))

        # For mock layers or layers with direct color control
        if hasattr(layer, "set_color"):
            # Enhance red channel, reduce others
            red_factor = 1.0 + intensity * 0.5
            other_factor = max(0.3, 1.0 - intensity * 0.3)

            # This would ideally be applied to the video frame data
            # For now, we'll simulate by adjusting layer properties
            if hasattr(layer, "color"):
                base_color = layer.color
                lit_color = (
                    min(255, int(base_color[0] * red_factor)),
                    int(base_color[1] * other_factor),
                    int(base_color[2] * other_factor),
                )
                layer.set_color(lit_color)

    def __str__(self) -> str:
        return f"🔴RedLighting({self.current_red_intensity:.1f})"


class BlueLighting(VJInterpreterBase):
    """Blue/cyan lighting that picks out blue and white parts"""

    hype = 45

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        blue_intensity: float = 1.8,
        cyan_boost: float = 1.3,
        response_signal: FrameSignal = FrameSignal.freq_high,
    ):
        super().__init__(layers, args)
        self.blue_intensity = blue_intensity
        self.cyan_boost = cyan_boost
        self.response_signal = response_signal
        self.current_blue_intensity = blue_intensity

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply blue lighting effect"""
        signal_strength = frame[self.response_signal]
        self.current_blue_intensity = self.blue_intensity * (
            0.4 + 1.6 * signal_strength
        )

        for layer in self.video_layers:
            self._apply_blue_lighting(layer, self.current_blue_intensity)

    def _apply_blue_lighting(self, layer: LayerBase, intensity: float):
        """Apply blue multiplicative lighting"""
        if hasattr(layer, "set_alpha"):
            layer.set_alpha(0.4 + 0.6 * min(1.0, intensity / 2.0))

        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color

            # Enhance blue/cyan, reduce red
            blue_factor = 1.0 + intensity * 0.6
            green_factor = 1.0 + intensity * 0.3  # Some cyan effect
            red_factor = max(0.2, 1.0 - intensity * 0.4)

            lit_color = (
                int(base_color[0] * red_factor),
                min(255, int(base_color[1] * green_factor)),
                min(255, int(base_color[2] * blue_factor)),
            )
            layer.set_color(lit_color)

    def __str__(self) -> str:
        return f"🔵BlueLighting({self.current_blue_intensity:.1f})"


class DynamicColorLighting(VJInterpreterBase):
    """Dynamic lighting that cycles through color scheme elements"""

    hype = 60

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        cycle_speed: float = 0.03,
        intensity_range: Tuple[float, float] = (1.0, 2.5),
        beat_boost: bool = True,
    ):
        super().__init__(layers, args)
        self.cycle_speed = cycle_speed
        self.min_intensity, self.max_intensity = intensity_range
        self.beat_boost = beat_boost
        self.cycle_phase = 0.0
        self.beat_boost_remaining = 0
        self.last_beat_signal = 0.0

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply dynamic color lighting"""
        # Update cycle
        energy = frame[FrameSignal.freq_all]
        effective_speed = self.cycle_speed * (0.5 + 1.5 * energy)
        self.cycle_phase += effective_speed

        # Check for beat boost
        if self.beat_boost:
            beat_signal = frame[FrameSignal.freq_high]
            if beat_signal > 0.7 and self.last_beat_signal <= 0.7:
                self.beat_boost_remaining = 20  # 20 frames of boost
            self.last_beat_signal = beat_signal

        # Calculate current lighting color and intensity
        lighting_color, intensity = self._calculate_lighting(scheme, energy)

        # Apply to video layers
        for layer in self.video_layers:
            self._apply_dynamic_lighting(layer, lighting_color, intensity)

    def _calculate_lighting(
        self, scheme: ColorScheme, energy: float
    ) -> Tuple[Tuple[float, float, float], float]:
        """Calculate current lighting color and intensity"""
        # Cycle through scheme colors
        colors = [scheme.fg, scheme.bg, scheme.bg_contrast]
        color_index = int(self.cycle_phase) % len(colors)
        color_blend = self.cycle_phase - int(self.cycle_phase)

        current_color = colors[color_index]
        next_color = colors[(color_index + 1) % len(colors)]

        # Blend between colors
        blended_rgb = (
            current_color.red * (1 - color_blend) + next_color.red * color_blend,
            current_color.green * (1 - color_blend) + next_color.green * color_blend,
            current_color.blue * (1 - color_blend) + next_color.blue * color_blend,
        )

        # Calculate intensity
        base_intensity = (
            self.min_intensity + (self.max_intensity - self.min_intensity) * energy
        )

        # Apply beat boost
        if self.beat_boost_remaining > 0:
            self.beat_boost_remaining -= 1
            boost_factor = 1.0 + 0.5 * (self.beat_boost_remaining / 20.0)
            base_intensity *= boost_factor

        return blended_rgb, base_intensity

    def _apply_dynamic_lighting(
        self,
        layer: LayerBase,
        lighting_color: Tuple[float, float, float],
        intensity: float,
    ):
        """Apply dynamic color lighting"""
        # Store lighting parameters
        if hasattr(layer, "_lighting_color"):
            layer._lighting_color = lighting_color
        if hasattr(layer, "_lighting_intensity"):
            layer._lighting_intensity = intensity

        # For mock layers, apply color directly
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color

            # Apply multiplicative lighting
            lit_color = (
                min(
                    255,
                    int(base_color[0] * (1.0 + (lighting_color[0] - 0.5) * intensity)),
                ),
                min(
                    255,
                    int(base_color[1] * (1.0 + (lighting_color[1] - 0.5) * intensity)),
                ),
                min(
                    255,
                    int(base_color[2] * (1.0 + (lighting_color[2] - 0.5) * intensity)),
                ),
            )
            layer.set_color(lit_color)

        # Adjust alpha based on lighting intensity
        if hasattr(layer, "set_alpha"):
            alpha = min(1.0, 0.6 + 0.4 * (intensity / self.max_intensity))
            layer.set_alpha(alpha)

    def __str__(self) -> str:
        boost_indicator = " BOOST!" if self.beat_boost_remaining > 0 else ""
        return f"🌈DynamicColorLighting(cycle{boost_indicator})"


class SelectiveLighting(VJInterpreterBase):
    """Selective lighting that enhances specific color ranges in video"""

    hype = 55

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        target_color: Tuple[float, float, float] = (1.0, 0.0, 0.0),  # Red
        color_tolerance: float = 0.3,
        enhancement_factor: float = 2.0,
        response_signal: FrameSignal = FrameSignal.freq_low,
    ):
        super().__init__(layers, args)
        self.target_color = target_color
        self.color_tolerance = color_tolerance
        self.enhancement_factor = enhancement_factor
        self.response_signal = response_signal
        self.current_enhancement = enhancement_factor

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply selective color lighting"""
        signal_strength = frame[self.response_signal]
        self.current_enhancement = self.enhancement_factor * (
            0.2 + 1.8 * signal_strength
        )

        # Update target color from scheme (use the dominant color)
        scheme_rgb = scheme.fg.rgb
        self.target_color = scheme_rgb

        # Apply to video layers
        for layer in self.video_layers:
            self._apply_selective_lighting(layer)

    def _apply_selective_lighting(self, layer: LayerBase):
        """Apply selective color enhancement"""
        # Store selective lighting parameters for rendering
        if hasattr(layer, "_selective_target"):
            layer._selective_target = self.target_color
        if hasattr(layer, "_selective_enhancement"):
            layer._selective_enhancement = self.current_enhancement
        if hasattr(layer, "_selective_tolerance"):
            layer._selective_tolerance = self.color_tolerance

        # For mock layers, simulate the effect
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color
            base_rgb = [c / 255.0 for c in base_color]

            # Calculate color distance from target
            color_distance = math.sqrt(
                sum((base_rgb[i] - self.target_color[i]) ** 2 for i in range(3))
            )

            # Apply enhancement if color is close to target
            if color_distance <= self.color_tolerance:
                enhancement = 1.0 + self.current_enhancement * (
                    1.0 - color_distance / self.color_tolerance
                )

                enhanced_color = (
                    min(255, int(base_color[0] * enhancement)),
                    min(255, int(base_color[1] * enhancement)),
                    min(255, int(base_color[2] * enhancement)),
                )
                layer.set_color(enhanced_color)

    def __str__(self) -> str:
        color_name = self._get_color_name(self.target_color)
        return f"🎯SelectiveLighting({color_name}, {self.current_enhancement:.1f})"

    def _get_color_name(self, rgb: Tuple[float, float, float]) -> str:
        """Get a human-readable color name"""
        r, g, b = rgb

        if r > 0.7 and g < 0.3 and b < 0.3:
            return "Red"
        elif g > 0.7 and r < 0.3 and b < 0.3:
            return "Green"
        elif b > 0.7 and r < 0.3 and g < 0.3:
            return "Blue"
        elif r > 0.7 and g > 0.7 and b < 0.3:
            return "Yellow"
        elif r > 0.7 and b > 0.7 and g < 0.3:
            return "Magenta"
        elif g > 0.7 and b > 0.7 and r < 0.3:
            return "Cyan"
        elif r > 0.8 and g > 0.8 and b > 0.8:
            return "White"
        elif r < 0.2 and g < 0.2 and b < 0.2:
            return "Black"
        else:
            return "Mixed"


class StrobeLighting(VJInterpreterBase):
    """Strobing color lighting effects"""

    hype = 80

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        strobe_speed: float = 0.5,
        color_palette: List[Tuple[float, float, float]] = None,
    ):
        super().__init__(layers, args)
        self.strobe_speed = strobe_speed
        self.color_palette = color_palette or [
            (1.0, 0.0, 0.0),  # Red
            (0.0, 1.0, 0.0),  # Green
            (0.0, 0.0, 1.0),  # Blue
            (1.0, 1.0, 1.0),  # White
            (0.0, 0.0, 0.0),  # Black (off)
        ]
        self.strobe_phase = 0.0
        self.current_color_index = 0

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply strobing color lighting"""
        # Get strobe triggers
        manual_strobe = frame[FrameSignal.strobe]
        energy = frame[FrameSignal.freq_all]

        # Adjust strobe speed based on input
        if manual_strobe > 0.5:
            effective_speed = self.strobe_speed * 15  # Fast manual strobe
        else:
            effective_speed = self.strobe_speed * (
                1 + energy * 5
            )  # Energy-based strobe

        self.strobe_phase += effective_speed

        # Update color index
        new_color_index = int(self.strobe_phase) % len(self.color_palette)
        if new_color_index != self.current_color_index:
            self.current_color_index = new_color_index

        current_lighting_color = self.color_palette[self.current_color_index]

        # Apply strobing lighting
        for layer in self.video_layers:
            self._apply_strobe_lighting(layer, current_lighting_color, effective_speed)

    def _apply_strobe_lighting(
        self,
        layer: LayerBase,
        lighting_color: Tuple[float, float, float],
        strobe_speed: float,
    ):
        """Apply strobing color lighting"""
        # Store strobe parameters
        if hasattr(layer, "_strobe_color"):
            layer._strobe_color = lighting_color
        if hasattr(layer, "_strobe_speed"):
            layer._strobe_speed = strobe_speed

        # For mock layers
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color

            # Apply color lighting
            if lighting_color != (0.0, 0.0, 0.0):  # Not black/off
                lit_color = (
                    min(255, int(base_color[0] * (0.5 + lighting_color[0] * 1.5))),
                    min(255, int(base_color[1] * (0.5 + lighting_color[1] * 1.5))),
                    min(255, int(base_color[2] * (0.5 + lighting_color[2] * 1.5))),
                )
                layer.set_color(lit_color)

                if hasattr(layer, "set_alpha"):
                    layer.set_alpha(0.8 + 0.2 * max(lighting_color))
            else:
                # Black/off - reduce alpha
                if hasattr(layer, "set_alpha"):
                    layer.set_alpha(0.1)

    def __str__(self) -> str:
        color = self.color_palette[self.current_color_index]
        color_name = f"RGB({color[0]:.1f},{color[1]:.1f},{color[2]:.1f})"
        return f"⚡StrobeLighting({color_name})"


class WarmCoolLighting(VJInterpreterBase):
    """Warm/cool lighting that shifts between warm and cool tones"""

    hype = 35

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        warm_color: Tuple[float, float, float] = (1.0, 0.7, 0.4),  # Warm orange
        cool_color: Tuple[float, float, float] = (0.4, 0.7, 1.0),  # Cool blue
        transition_speed: float = 0.02,
    ):
        super().__init__(layers, args)
        self.warm_color = warm_color
        self.cool_color = cool_color
        self.transition_speed = transition_speed
        self.temperature_phase = 0.0

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply warm/cool lighting transitions"""
        # Bass = warm, treble = cool
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]

        # Calculate temperature bias
        temperature_bias = bass - treble  # Positive = warm, negative = cool

        # Update phase
        self.temperature_phase += self.transition_speed * (1 + abs(temperature_bias))

        # Calculate current lighting color
        # Sine wave with bias toward warm/cool based on audio
        base_temp = (math.sin(self.temperature_phase) + 1.0) / 2.0  # 0-1
        biased_temp = max(0.0, min(1.0, base_temp + temperature_bias * 0.5))

        # Blend between warm and cool
        current_lighting = (
            self.cool_color[0] * (1 - biased_temp) + self.warm_color[0] * biased_temp,
            self.cool_color[1] * (1 - biased_temp) + self.warm_color[1] * biased_temp,
            self.cool_color[2] * (1 - biased_temp) + self.warm_color[2] * biased_temp,
        )

        # Apply to layers
        for layer in self.video_layers:
            self._apply_temperature_lighting(
                layer, current_lighting, 1.0 + abs(temperature_bias)
            )

    def _apply_temperature_lighting(
        self,
        layer: LayerBase,
        lighting_color: Tuple[float, float, float],
        intensity: float,
    ):
        """Apply warm/cool lighting"""
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color

            # Apply temperature lighting
            lit_color = (
                min(
                    255,
                    int(base_color[0] * (0.7 + lighting_color[0] * intensity * 0.6)),
                ),
                min(
                    255,
                    int(base_color[1] * (0.7 + lighting_color[1] * intensity * 0.6)),
                ),
                min(
                    255,
                    int(base_color[2] * (0.7 + lighting_color[2] * intensity * 0.6)),
                ),
            )
            layer.set_color(lit_color)

    def __str__(self) -> str:
        temp_indicator = "🔥" if self.temperature_phase > 0 else "❄️"
        return f"{temp_indicator}WarmCoolLighting({self.temperature_phase:.1f})"


class SpotlightEffect(VJInterpreterBase):
    """Moving spotlight that highlights parts of the video"""

    hype = 65

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        num_spots: int = 2,
        spot_size_range: Tuple[float, float] = (0.1, 0.3),
        movement_speed: float = 0.02,
    ):
        super().__init__(layers, args)
        self.num_spots = num_spots
        self.min_size, self.max_size = spot_size_range
        self.movement_speed = movement_speed

        # Initialize spotlights
        self.spots = []
        for i in range(num_spots):
            self.spots.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "size": random.uniform(self.min_size, self.max_size),
                    "intensity": random.uniform(0.5, 1.0),
                    "phase": random.random() * math.pi * 2,
                    "speed": random.uniform(0.01, 0.03),
                    "color": (1.0, 1.0, 1.0),  # Start with white
                    "movement_pattern": random.choice(["circle", "figure8", "random"]),
                }
            )

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update moving spotlights"""
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update spotlight colors from scheme
        scheme_colors = [scheme.fg.rgb, scheme.bg.rgb, scheme.bg_contrast.rgb]

        # Update each spotlight
        for i, spot in enumerate(self.spots):
            # Update movement
            spot["phase"] += spot["speed"] * (1.0 + energy)

            # Move based on pattern
            if spot["movement_pattern"] == "circle":
                spot["x"] = 0.5 + 0.3 * math.cos(spot["phase"])
                spot["y"] = 0.5 + 0.3 * math.sin(spot["phase"])
            elif spot["movement_pattern"] == "figure8":
                spot["x"] = 0.5 + 0.3 * math.cos(spot["phase"])
                spot["y"] = 0.5 + 0.2 * math.sin(spot["phase"] * 2)
            elif spot["movement_pattern"] == "random":
                spot["x"] += random.uniform(-0.01, 0.01)
                spot["y"] += random.uniform(-0.01, 0.01)
                spot["x"] = max(0.1, min(0.9, spot["x"]))
                spot["y"] = max(0.1, min(0.9, spot["y"]))

            # Update size based on audio
            if i % 2 == 0:
                spot["size"] = self.min_size + (self.max_size - self.min_size) * bass
            else:
                spot["size"] = self.min_size + (self.max_size - self.min_size) * treble

            # Update intensity
            spot["intensity"] = 0.4 + 0.6 * energy

            # Update color
            spot["color"] = scheme_colors[i % len(scheme_colors)]

        # Apply spotlight effects to layers
        for layer in self.video_layers:
            self._apply_spotlights(layer)

    def _apply_spotlights(self, layer: LayerBase):
        """Apply spotlight effects to layer"""
        # Store spotlight info for rendering
        if hasattr(layer, "_spotlights"):
            layer._spotlights = self.spots.copy()

        # For mock layers, apply average spotlight effect
        if hasattr(layer, "set_alpha"):
            avg_intensity = sum(spot["intensity"] for spot in self.spots) / len(
                self.spots
            )
            layer.set_alpha(0.3 + 0.7 * avg_intensity)

    def get_spotlight_info(self) -> List[dict]:
        """Get current spotlight positions for rendering"""
        return self.spots.copy()

    def __str__(self) -> str:
        return f"💡SpotlightEffect({self.num_spots} spots)"


class ColorChannelSeparation(VJInterpreterBase):
    """Separates and enhances individual color channels"""

    hype = 70

    def __init__(
        self,
        layers: List[LayerBase],
        args: InterpreterArgs,
        separation_intensity: float = 1.5,
        channel_signals: dict = None,
    ):
        super().__init__(layers, args)
        self.separation_intensity = separation_intensity

        # Map audio signals to color channels
        self.channel_signals = channel_signals or {
            "red": FrameSignal.freq_low,
            "green": FrameSignal.freq_all,
            "blue": FrameSignal.freq_high,
        }

        self.video_layers = self._filter_video_layers(layers)

    def _filter_video_layers(self, layers: List[LayerBase]) -> List[LayerBase]:
        return [
            layer
            for layer in layers
            if "video" in layer.name.lower() or hasattr(layer, "current_frame")
        ]

    def step(self, frame: Frame, scheme: ColorScheme):
        """Apply color channel separation"""
        # Get signal strengths for each channel
        red_strength = frame[self.channel_signals["red"]]
        green_strength = frame[self.channel_signals["green"]]
        blue_strength = frame[self.channel_signals["blue"]]

        # Calculate channel multipliers
        red_mult = 0.5 + self.separation_intensity * red_strength
        green_mult = 0.5 + self.separation_intensity * green_strength
        blue_mult = 0.5 + self.separation_intensity * blue_strength

        # Apply to video layers
        for layer in self.video_layers:
            self._apply_channel_separation(layer, (red_mult, green_mult, blue_mult))

    def _apply_channel_separation(
        self, layer: LayerBase, multipliers: Tuple[float, float, float]
    ):
        """Apply color channel separation"""
        # Store channel multipliers for rendering
        if hasattr(layer, "_channel_multipliers"):
            layer._channel_multipliers = multipliers

        # For mock layers
        if hasattr(layer, "set_color") and hasattr(layer, "color"):
            base_color = layer.color

            separated_color = (
                min(255, int(base_color[0] * multipliers[0])),
                min(255, int(base_color[1] * multipliers[1])),
                min(255, int(base_color[2] * multipliers[2])),
            )
            layer.set_color(separated_color)

    def __str__(self) -> str:
        return f"🌈ColorChannelSeparation({self.separation_intensity:.1f})"
