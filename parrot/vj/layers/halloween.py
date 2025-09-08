"""
Halloween-themed VJ layers for spooky effects
"""

import math
import random
from typing import Optional, Tuple, List
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


class LightningLayer(LayerBase):
    """Creates dramatic lightning bolt effects"""

    def __init__(
        self,
        name: str = "lightning",
        z_order: int = 10,
        width: int = 1920,
        height: int = 1080,
    ):
        super().__init__(name, z_order, width, height)
        self.is_flashing = False
        self.flash_intensity = 0.0
        self.bolt_positions = []
        self.regenerate_bolts()

    def regenerate_bolts(self):
        """Generate random lightning bolt paths"""
        self.bolt_positions = []
        num_bolts = random.randint(1, 3)

        for _ in range(num_bolts):
            # Create jagged lightning path
            bolt = []
            x = random.uniform(0.2, 0.8)
            y = 0.0

            while y < 1.0:
                bolt.append((x, y))
                # Jagged movement
                x += random.uniform(-0.1, 0.1)
                y += random.uniform(0.05, 0.15)
                x = max(0.0, min(1.0, x))  # Keep in bounds

            self.bolt_positions.append(bolt)

    def trigger_flash(self, intensity: float = 1.0):
        """Trigger a lightning flash"""
        self.is_flashing = True
        self.flash_intensity = intensity
        self.regenerate_bolts()

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render lightning effect"""
        if not self.enabled or not self.is_flashing:
            return None

        # Create lightning texture
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        if self.flash_intensity > 0.1:
            # Draw lightning bolts
            for bolt in self.bolt_positions:
                self._draw_bolt(texture, bolt)

            # Add screen flash
            flash_alpha = int(self.flash_intensity * 100)
            if flash_alpha > 10:
                texture[:, :] = np.maximum(texture, [200, 200, 255, flash_alpha])

        # Decay flash
        self.flash_intensity *= 0.7
        if self.flash_intensity < 0.05:
            self.is_flashing = False

        return texture

    def _draw_bolt(self, texture: np.ndarray, bolt: List[Tuple[float, float]]):
        """Draw a lightning bolt on the texture"""
        if len(bolt) < 2:
            return

        bolt_color = [255, 255, 200, int(self.flash_intensity * 255)]  # Yellow-white
        bolt_width = max(1, int(self.flash_intensity * 8))

        for i in range(len(bolt) - 1):
            x1, y1 = bolt[i]
            x2, y2 = bolt[i + 1]

            # Convert to pixel coordinates
            px1, py1 = int(x1 * self.width), int(y1 * self.height)
            px2, py2 = int(x2 * self.width), int(y2 * self.height)

            # Draw line segment (simple Bresenham-like)
            self._draw_line(texture, px1, py1, px2, py2, bolt_color, bolt_width)

    def _draw_line(
        self,
        texture: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: List[int],
        width: int,
    ):
        """Draw a thick line on the texture"""
        # Simple line drawing
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        steps = max(dx, dy)

        if steps == 0:
            return

        x_inc = (x2 - x1) / steps
        y_inc = (y2 - y1) / steps

        for i in range(steps):
            x = int(x1 + i * x_inc)
            y = int(y1 + i * y_inc)

            # Draw thick line
            for dx in range(-width // 2, width // 2 + 1):
                for dy in range(-width // 2, width // 2 + 1):
                    px, py = x + dx, y + dy
                    if 0 <= px < self.width and 0 <= py < self.height:
                        texture[py, px] = color


class BloodOverlay(LayerBase):
    """Blood splatter and drip overlay"""

    def __init__(
        self,
        name: str = "blood",
        z_order: int = 8,
        width: int = 1920,
        height: int = 1080,
    ):
        super().__init__(name, z_order, width, height)
        self.blood_splatters = []
        self.drip_streams = []
        self.blood_intensity = 0.0

    def add_splatter(self, x: float, y: float, size: float = 0.1):
        """Add a blood splatter at position"""
        self.blood_splatters.append(
            {
                "x": x,
                "y": y,
                "size": size,
                "age": 0,
                "max_age": 60 + random.randint(0, 40),
            }
        )

    def add_drip(self, x: float):
        """Add a blood drip stream"""
        self.drip_streams.append(
            {
                "x": x,
                "y": 0.0,
                "speed": random.uniform(0.005, 0.02),
                "width": random.uniform(0.01, 0.03),
            }
        )

    def trigger_blood_effect(self, intensity: float = 1.0):
        """Trigger blood effects"""
        self.blood_intensity = intensity

        # Add random splatters
        for _ in range(random.randint(1, 4)):
            self.add_splatter(
                random.uniform(0.1, 0.9),
                random.uniform(0.1, 0.9),
                random.uniform(0.05, 0.2) * intensity,
            )

        # Add drips
        for _ in range(random.randint(0, 2)):
            self.add_drip(random.uniform(0.2, 0.8))

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render blood effects"""
        if not self.enabled:
            return None

        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Update and draw splatters
        self._update_splatters()
        for splatter in self.blood_splatters:
            self._draw_splatter(texture, splatter)

        # Update and draw drips
        self._update_drips()
        for drip in self.drip_streams:
            self._draw_drip(texture, drip)

        # Decay blood intensity
        self.blood_intensity *= 0.95

        return texture if np.any(texture) else None

    def _update_splatters(self):
        """Update splatter aging and remove old ones"""
        self.blood_splatters = [
            splatter
            for splatter in self.blood_splatters
            if splatter["age"] < splatter["max_age"]
        ]

        for splatter in self.blood_splatters:
            splatter["age"] += 1

    def _update_drips(self):
        """Update drip positions and remove finished ones"""
        for drip in self.drip_streams[:]:
            drip["y"] += drip["speed"]
            if drip["y"] > 1.0:
                self.drip_streams.remove(drip)

    def _draw_splatter(self, texture: np.ndarray, splatter: dict):
        """Draw a blood splatter"""
        x = int(splatter["x"] * self.width)
        y = int(splatter["y"] * self.height)
        size = int(splatter["size"] * min(self.width, self.height))

        # Age affects opacity
        age_factor = 1.0 - (splatter["age"] / splatter["max_age"])
        alpha = int(255 * age_factor * 0.8)

        blood_color = [139, 0, 0, alpha]  # Dark red

        # Draw circular splatter with random edges
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    distance = math.sqrt(dx * dx + dy * dy)
                    if distance <= size * (
                        0.7 + 0.3 * random.random()
                    ):  # Irregular edge
                        texture[py, px] = blood_color

    def _draw_drip(self, texture: np.ndarray, drip: dict):
        """Draw a blood drip stream"""
        x = int(drip["x"] * self.width)
        y_start = 0
        y_end = int(drip["y"] * self.height)
        width = int(drip["width"] * self.width)

        blood_color = [139, 0, 0, 180]  # Semi-transparent dark red

        # Draw vertical drip
        for y in range(y_start, min(y_end, self.height)):
            for dx in range(-width // 2, width // 2 + 1):
                px = x + dx
                if 0 <= px < self.width:
                    texture[y, px] = blood_color


class SpookyLightingLayer(LayerBase):
    """Multiplicative lighting layer with moving spooky lights"""

    def __init__(
        self,
        name: str = "spooky_lights",
        z_order: int = 5,
        width: int = 1920,
        height: int = 1080,
        num_lights: int = 6,
    ):
        super().__init__(name, z_order, width, height)
        self.num_lights = num_lights
        self.lights = []
        self.light_colors = [
            (255, 255, 200),  # Warm candle light
            (200, 255, 200),  # Sickly green
            (255, 200, 255),  # Eerie purple
            (255, 100, 100),  # Blood red
            (100, 100, 255),  # Ghost blue
            (255, 140, 0),  # Jack-o'-lantern orange
        ]

        self._initialize_lights()

    def _initialize_lights(self):
        """Initialize light positions and properties"""
        self.lights = []
        for i in range(self.num_lights):
            self.lights.append(
                {
                    "x": random.random(),
                    "y": random.random(),
                    "size": random.uniform(0.05, 0.15),
                    "phase": random.random() * math.pi * 2,
                    "speed": random.uniform(0.01, 0.03),
                    "color": self.light_colors[i % len(self.light_colors)],
                    "intensity": 0.0,
                    "flicker_phase": random.random() * math.pi * 2,
                    "movement_pattern": random.choice(
                        ["circle", "figure8", "drift", "bounce"]
                    ),
                }
            )

    def update_lights(self, bass: float, treble: float, energy: float):
        """Update light positions and properties based on audio"""
        for light in self.lights:
            # Update movement
            light["phase"] += light["speed"] * (1.0 + energy)
            light["flicker_phase"] += 0.2 + treble * 0.5

            # Move based on pattern
            if light["movement_pattern"] == "circle":
                light["x"] = 0.5 + 0.3 * math.cos(light["phase"])
                light["y"] = 0.5 + 0.3 * math.sin(light["phase"])

            elif light["movement_pattern"] == "figure8":
                light["x"] = 0.5 + 0.3 * math.cos(light["phase"])
                light["y"] = 0.5 + 0.2 * math.sin(light["phase"] * 2)

            elif light["movement_pattern"] == "drift":
                light["x"] += math.cos(light["phase"]) * 0.002
                light["y"] += math.sin(light["phase"] * 0.7) * 0.002
                # Wrap around edges
                light["x"] = light["x"] % 1.0
                light["y"] = light["y"] % 1.0

            elif light["movement_pattern"] == "bounce":
                # Bouncing motion
                bounce_x = abs(math.sin(light["phase"]))
                bounce_y = abs(math.cos(light["phase"] * 0.8))
                light["x"] = 0.1 + 0.8 * bounce_x
                light["y"] = 0.1 + 0.8 * bounce_y

            # Size responds to audio
            base_size = 0.05 + 0.1 * bass
            flicker_size = base_size + 0.03 * math.sin(light["flicker_phase"])
            light["size"] = max(0.02, flicker_size)

            # Intensity flickers with treble
            base_intensity = 0.4 + 0.6 * energy
            flicker = 0.2 * math.sin(light["flicker_phase"] * 2)
            light["intensity"] = max(0.1, base_intensity + flicker)

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render spooky lighting effects"""
        if not self.enabled:
            return None

        # Get audio signals
        bass = frame[FrameSignal.freq_low]
        treble = frame[FrameSignal.freq_high]
        energy = frame[FrameSignal.freq_all]

        # Update lights
        self.update_lights(bass, treble, energy)

        # Create lighting texture (multiplicative blend)
        texture = np.full(
            (self.height, self.width, 4), [128, 128, 128, 255], dtype=np.uint8
        )

        # Draw each light
        for light in self.lights:
            self._draw_light(texture, light)

        return texture

    def _draw_light(self, texture: np.ndarray, light: dict):
        """Draw a single light with falloff"""
        center_x = int(light["x"] * self.width)
        center_y = int(light["y"] * self.height)
        radius = int(light["size"] * min(self.width, self.height))
        color = light["color"]
        intensity = light["intensity"]

        # Draw light with radial falloff
        for y in range(max(0, center_y - radius), min(self.height, center_y + radius)):
            for x in range(
                max(0, center_x - radius), min(self.width, center_x + radius)
            ):
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance <= radius:
                    # Radial falloff
                    falloff = 1.0 - (distance / radius)
                    falloff = falloff * falloff  # Quadratic falloff

                    # Light contribution
                    light_factor = intensity * falloff

                    # Multiplicative blending (lighter areas get more light)
                    current = texture[y, x]
                    for c in range(3):  # RGB channels
                        # Multiplicative: light color affects the result
                        multiplier = 1.0 + light_factor * (color[c] / 255.0 - 0.5)
                        texture[y, x, c] = int(min(255, current[c] * multiplier))


class HalloweenParticles(LayerBase):
    """Floating Halloween particles (bats, skulls, etc.)"""

    def __init__(
        self,
        name: str = "particles",
        z_order: int = 6,
        width: int = 1920,
        height: int = 1080,
        max_particles: int = 20,
    ):
        super().__init__(name, z_order, width, height)
        self.max_particles = max_particles
        self.particles = []
        self.particle_types = ["bat", "skull", "spider", "ghost"]

    def add_particle(self, particle_type: str = None):
        """Add a new particle"""
        if len(self.particles) >= self.max_particles:
            return

        particle_type = particle_type or random.choice(self.particle_types)

        self.particles.append(
            {
                "type": particle_type,
                "x": random.uniform(-0.1, 1.1),  # Can start off-screen
                "y": random.uniform(-0.1, 1.1),
                "vx": random.uniform(-0.01, 0.01),
                "vy": random.uniform(-0.01, 0.01),
                "size": random.uniform(0.02, 0.08),
                "rotation": random.random() * math.pi * 2,
                "rotation_speed": random.uniform(-0.1, 0.1),
                "age": 0,
                "max_age": random.randint(300, 600),
                "alpha": random.uniform(0.3, 0.8),
            }
        )

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render floating Halloween particles"""
        if not self.enabled:
            return None

        # Add new particles based on energy
        energy = frame[FrameSignal.freq_all]
        if random.random() < 0.02 * (1 + energy):  # Higher energy = more particles
            self.add_particle()

        # Update particles
        self._update_particles()

        if not self.particles:
            return None

        # Create particle texture
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Draw each particle
        for particle in self.particles:
            self._draw_particle(texture, particle)

        return texture

    def _update_particles(self):
        """Update particle positions and remove old ones"""
        for particle in self.particles[:]:
            # Age particle
            particle["age"] += 1
            if particle["age"] >= particle["max_age"]:
                self.particles.remove(particle)
                continue

            # Move particle
            particle["x"] += particle["vx"]
            particle["y"] += particle["vy"]
            particle["rotation"] += particle["rotation_speed"]

            # Remove particles that are too far off-screen
            if (
                particle["x"] < -0.2
                or particle["x"] > 1.2
                or particle["y"] < -0.2
                or particle["y"] > 1.2
            ):
                self.particles.remove(particle)

    def _draw_particle(self, texture: np.ndarray, particle: dict):
        """Draw a single particle"""
        x = int(particle["x"] * self.width)
        y = int(particle["y"] * self.height)
        size = int(particle["size"] * min(self.width, self.height))

        if size < 1:
            return

        # Age affects alpha
        age_factor = 1.0 - (particle["age"] / particle["max_age"])
        alpha = int(particle["alpha"] * age_factor * 255)

        # Simple particle shapes
        if particle["type"] == "bat":
            color = [50, 50, 50, alpha]  # Dark gray
            self._draw_bat_shape(texture, x, y, size, color)
        elif particle["type"] == "skull":
            color = [200, 200, 200, alpha]  # Light gray
            self._draw_skull_shape(texture, x, y, size, color)
        elif particle["type"] == "spider":
            color = [80, 40, 40, alpha]  # Dark brown
            self._draw_spider_shape(texture, x, y, size, color)
        elif particle["type"] == "ghost":
            color = [255, 255, 255, alpha // 2]  # Semi-transparent white
            self._draw_ghost_shape(texture, x, y, size, color)

    def _draw_bat_shape(
        self, texture: np.ndarray, x: int, y: int, size: int, color: List[int]
    ):
        """Draw a simple bat shape"""
        # Simple bat silhouette
        for dy in range(-size // 2, size // 2):
            for dx in range(-size, size):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    # Bat wing shape (very simplified)
                    if abs(dy) <= size // 3 and abs(dx) <= size // 2:
                        texture[py, px] = color

    def _draw_skull_shape(
        self, texture: np.ndarray, x: int, y: int, size: int, color: List[int]
    ):
        """Draw a simple skull shape"""
        # Circular skull
        for dy in range(-size // 2, size // 2):
            for dx in range(-size // 2, size // 2):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    if dx * dx + dy * dy <= (size // 2) ** 2:
                        texture[py, px] = color

    def _draw_spider_shape(
        self, texture: np.ndarray, x: int, y: int, size: int, color: List[int]
    ):
        """Draw a simple spider shape"""
        # Spider body and legs
        for dy in range(-size // 4, size // 4):
            for dx in range(-size // 4, size // 4):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    texture[py, px] = color

    def _draw_ghost_shape(
        self, texture: np.ndarray, x: int, y: int, size: int, color: List[int]
    ):
        """Draw a simple ghost shape"""
        # Wavy ghost silhouette
        for dy in range(-size // 2, size // 2):
            for dx in range(-size // 2, size // 2):
                px, py = x + dx, y + dy
                if 0 <= px < self.width and 0 <= py < self.height:
                    # Wavy edges
                    wave = math.sin(dy * 0.3) * size // 4
                    if abs(dx + wave) <= size // 3:
                        texture[py, px] = color


class HorrorColorGrade(LayerBase):
    """Color grading layer for horror atmosphere"""

    def __init__(
        self,
        name: str = "horror_grade",
        z_order: int = 15,
        width: int = 1920,
        height: int = 1080,
    ):
        super().__init__(name, z_order, width, height)
        self.grade_intensity = 0.5
        self.horror_tint = (1.2, 0.8, 0.9)  # Enhance reds, reduce greens, slight blue

    def set_horror_intensity(self, intensity: float):
        """Set the intensity of the horror color grading"""
        self.grade_intensity = max(0.0, min(1.0, intensity))

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render color grading overlay"""
        if not self.enabled or self.grade_intensity < 0.1:
            return None

        # Create color grading overlay
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Horror color tint
        r_mult, g_mult, b_mult = self.horror_tint

        # Create subtle color overlay
        overlay_alpha = int(self.grade_intensity * 30)  # Subtle effect

        # Red-tinted overlay for horror atmosphere
        texture[:, :] = [
            int(255 * r_mult * 0.3),  # Red tint
            int(255 * g_mult * 0.2),  # Reduced green
            int(255 * b_mult * 0.25),  # Slight blue
            overlay_alpha,
        ]

        return texture

    def __str__(self) -> str:
        return f"🩸HorrorColorGrade({self.grade_intensity:.1f})"
