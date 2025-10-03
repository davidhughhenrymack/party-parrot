#!/usr/bin/env python3

import time
import random
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase


@beartype
class HotSparksEffect(GenerativeEffectBase):
    """
    A hot sparks particle effect that fires glowing spark particles from the top
    corners downward toward the center of the screen on small pulse signals.
    Sparks fade over time and have a glow effect.
    Emits for 1/3 of spark lifetime when triggered.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        num_sparks: int = 200,
        spark_lifetime: float = 1.0,
        spark_speed: float = 0.5,
        signal: FrameSignal = FrameSignal.small_blinder,
    ):
        """
        Args:
            width: Width of the effect
            height: Height of the effect
            num_sparks: Number of spark particles per emission
            spark_lifetime: How long sparks live before fading out (seconds)
            spark_speed: Speed of spark movement
            signal: Which frame signal triggers the sparks
        """
        super().__init__(width, height)
        self.num_sparks = num_sparks
        self.spark_lifetime = spark_lifetime
        self.spark_speed = spark_speed
        self.signal = signal

        # Track emission state
        self.start_time = time.time()  # Reference time for relative calculations
        self.emission_start_time = (
            -10.0
        )  # When continuous emission started (negative = not emitting)
        self.pulse_seed = random.random()
        self.is_emitting = False  # Track if currently emitting
        self.signal_went_high_time = (
            -10.0
        )  # When signal went high (for emission duration)

    def generate(self, vibe: Vibe):
        """Configure spark parameters based on the vibe"""
        from parrot.director.mode import Mode

        if vibe.mode == Mode.rave:
            self.num_sparks = 600  # Even more for rave mode
            self.spark_speed = 1.2
        elif vibe.mode == Mode.chill:
            self.num_sparks = 200  # Fewer for chill mode
            self.spark_speed = 0.5

    def print_self(self) -> str:
        return format_node_status(
            self.__class__.__name__,
            emoji="✨",
            signal=self.signal,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for hot sparks particle rendering"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        
        uniform float time;
        uniform float emission_start_time;
        uniform float pulse_seed;
        uniform int num_sparks;
        uniform float spark_lifetime;
        uniform vec3 spark_color;
        
        // High-quality pseudo-random function
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        // 2D rotation matrix
        mat2 rotate2d(float angle) {
            float c = cos(angle);
            float s = sin(angle);
            return mat2(c, -s, s, c);
        }
        
        // Smooth distance function for rounded rectangle (chip shape)
        float rounded_rect(vec2 p, vec2 size, float radius) {
            vec2 d = abs(p) - size + radius;
            return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
        }
        
        // Calculate spark contribution
        vec3 calculate_spark(vec2 uv, int spark_id, float emission_time, float current_time) {
            // Calculate when this specific spark was emitted (staggered emission)
            float spark_birth_time = emission_time + float(spark_id) * 0.001; // 5ms stagger between sparks (shorter emission period)
            float spark_age = current_time - spark_birth_time;
            
            // Don't render if not yet born or past lifetime
            if (spark_age < 0.0 || spark_age > spark_lifetime) {
                return vec3(0.0);
            }
            
            // Use spark_id and pulse_seed for random values
            vec2 seed = vec2(float(spark_id) * 17.3 + pulse_seed * 100.0, pulse_seed * 50.0);
            
            // Randomly choose left or right corner
            bool from_left = random(seed) > 0.5;
            
            // Start position: top left or top right (spark cannon positions)
            vec2 start_pos;
            vec2 initial_velocity;
            
            if (from_left) {
                // Left cannon at TOP left corner
                // In OpenGL/UV space: y=0.0 is BOTTOM, y=1.0 is TOP (standard OpenGL convention)
                start_pos = vec2(0.10 + random(seed + vec2(10.0, 0.0)) * 0.05, 0.98);
                // Fire DOWNWARD (negative Y) and toward center (positive X) with random spread
                float base_speed = 0.6 + random(seed + vec2(40.0, 0.0)) * 0.3; // 0.6-0.9
                float angle_spread = (random(seed + vec2(30.0, 0.0)) - 0.5) * 0.4; // -0.2 to 0.2
                initial_velocity = vec2(0.25 + angle_spread, -base_speed); // Negative Y = downward
            } else {
                // Right cannon at TOP right corner
                start_pos = vec2(0.90 - random(seed + vec2(10.0, 0.0)) * 0.05, 0.98);
                // Fire DOWNWARD (negative Y) and toward center (negative X) with random spread
                float base_speed = 0.6 + random(seed + vec2(40.0, 0.0)) * 0.3; // 0.6-0.9
                float angle_spread = (random(seed + vec2(30.0, 0.0)) - 0.5) * 0.4; // -0.2 to 0.2
                initial_velocity = vec2(-0.25 + angle_spread, -base_speed); // Negative Y = downward
            }
            
            // Physics simulation: position = start + velocity*t + 0.5*gravity*t^2
            // Gravity pulls UP (positive Y in UV space where y=1 is top)
            float gravity = -0.25; // Upward acceleration (positive Y = up in UV coords)
            vec2 spark_pos = start_pos + initial_velocity * spark_age;
            spark_pos.y += 0.5 * gravity * spark_age * spark_age;
            
            // Add slight horizontal air resistance drift
            float drift = sin(spark_age * 2.0 + float(spark_id)) * 0.01;
            spark_pos.x += drift;
            
            // Spark chip size (small rectangular chips) - 1/3 original size
            vec2 spark_size = vec2(
                0.001 + random(seed + vec2(40.0, 0.0)) * 0.0013,  // width: 0.001-0.0023 (1/3 of 0.003-0.007)
                0.0007 + random(seed + vec2(50.0, 0.0)) * 0.001   // height: 0.0007-0.0017 (1/3 of 0.002-0.005)
            );
            
            // Random rotation that evolves over time
            float base_rotation = random(seed + vec2(60.0, 0.0)) * 6.28318; // 0 to 2π
            float rotation = base_rotation + spark_age * 3.0; // Spin during flight
            
            // Transform UV to spark space
            vec2 spark_uv = uv - spark_pos;
            spark_uv = rotate2d(rotation) * spark_uv;
            
            // Calculate distance to chip shape
            float dist = rounded_rect(spark_uv, spark_size, spark_size.y * 0.3);
            
            // Smooth falloff for the core spark
            float core_mask = 1.0 - smoothstep(0.0, spark_size.y * 0.5, dist);
            
            // Glow effect - much subtler (100x less intense)
            float glow_mask = 1.0 / (1.0 + dist * 80000.0);
            float strong_glow = 1.0 / (1.0 + dist * 20000.0);
            
            // Fade over lifetime (3 seconds)
            float fade = 1.0 - (spark_age / spark_lifetime);
            fade = smoothstep(0.0, 0.15, fade); // Gradual fade at end
            
            // Add some brightness variation per spark
            float brightness = 0.7 + random(seed + vec2(70.0, 0.0)) * 0.3; // 0.7-1.0
            
            // Combine core and subtle glow
            float intensity = (core_mask * 1.2 + strong_glow * 0.008 + glow_mask * 0.003) * fade * brightness;
            
            // Apply color with slight warmth variation
            vec3 spark_col = spark_color;
            // Add slight orange/yellow tint for "hot" look
            spark_col.r *= 1.1;
            spark_col.g *= 1.05;
            
            return spark_col * intensity;
        }
        
        void main() {
            vec3 final_color = vec3(0.0);
            
            // Only render sparks if emission has started
            if (emission_start_time >= 0.0) {
                // Render all sparks (they have staggered birth times and individual lifetimes)
                // Limit loop iterations for shader optimization (GLSL doesn't optimize unbounded loops well)
                int max_sparks = min(num_sparks, 500);  // Hard limit to prevent shader slowdown
                for (int i = 0; i < max_sparks; i++) {
                    if (i >= num_sparks) break;  // Early exit
                    vec3 spark_contribution = calculate_spark(uv, i, emission_start_time, time);
                    // Additive blending
                    final_color += spark_contribution;
                }
            }
            
            color = clamp(final_color, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set hot sparks effect uniforms"""
        # Use relative time to avoid float precision issues with large Unix timestamps
        current_time = time.time() - self.start_time  # Relative to start

        # Get signal value
        signal_value = frame[self.signal]
        emission_threshold = 0.5
        emission_duration = self.spark_lifetime / 3.0  # Emit for 1/3 of spark lifetime

        # Check if we should be emitting
        if signal_value > emission_threshold:
            if not self.is_emitting:
                # Signal just went high - start tracking and emitting
                self.signal_went_high_time = current_time
                self.emission_start_time = current_time
                self.pulse_seed = random.random()  # New random seed for new emission
                self.is_emitting = True
            else:
                # Signal is still high - check if we've emitted for 1/3 of the time
                time_since_signal_high = current_time - self.signal_went_high_time
                if time_since_signal_high > emission_duration:
                    # Stop emitting but let existing sparks finish their lifetime
                    self.is_emitting = False
        else:
            # Signal dropped - stop emitting but let existing sparks finish their lifetime
            self.is_emitting = False

        # Set uniforms (using relative time for precision)
        self.shader_program["time"] = current_time
        self.shader_program["emission_start_time"] = self.emission_start_time
        self.shader_program["pulse_seed"] = self.pulse_seed
        self.shader_program["num_sparks"] = self.num_sparks
        self.shader_program["spark_lifetime"] = self.spark_lifetime
        self.shader_program["spark_color"] = scheme.fg.rgb
