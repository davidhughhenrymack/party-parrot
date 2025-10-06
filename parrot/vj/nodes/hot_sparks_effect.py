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
    A hot sparks particle effect that fires white spark particles with gold glow
    from the top corners downward toward the center of the screen on small pulse signals.
    Sparks start as chips then grow into four-pointed starbursts (with one point elongated)
    before suddenly disappearing and respawning. Continuously emits while signal is active.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        num_sparks: int = 600,
        signal: FrameSignal = FrameSignal.pulse,
        spark_lifetime: float = 1.0,
        opacity_multiplier: float = 1.0,
    ):
        """
        Args:
            width: Width of the effect
            height: Height of the effect
            num_sparks: Number of spark particles per emission
            signal: Which frame signal triggers the sparks
            spark_lifetime: How long sparks live before fading out (seconds)
            opacity_multiplier: Overall opacity/intensity multiplier
        """
        super().__init__(width, height)
        self.num_sparks = num_sparks
        self.signal = signal
        self.spark_lifetime = spark_lifetime
        self.mode_opacity_multiplier = opacity_multiplier

        # Track emission state
        self.start_time = time.time()  # Reference time for relative calculations
        self.emission_start_time = (
            -10.0
        )  # When continuous emission started (negative = not emitting)
        self.emission_stop_time = -10.0  # When emission stopped
        self.pulse_seed = random.random()
        self.is_emitting = False  # Track if currently emitting

    def generate(self, vibe: Vibe):
        """Configure spark parameters based on the vibe"""
        pass

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
        uniform float emission_stop_time;
        uniform float pulse_seed;
        uniform int num_sparks;
        uniform float spark_lifetime;
        uniform bool is_emitting;
        uniform float mode_opacity_multiplier;
        
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
        
        // Distance function for a four-pointed star (cross/plus shape, one point longer)
        float starburst(vec2 p, float size, float elongation) {
            vec2 ap = abs(p);
            
            // Create a cross/plus shape using two rectangles
            // Horizontal bar
            float horizontal = max(ap.x - size, ap.y - size * 0.2);
            // Vertical bar (elongated)
            float vertical = max(ap.y - size * elongation, ap.x - size * 0.2);
            
            // Union of the two bars
            return min(horizontal, vertical);
        }
        
        // Calculate spark contribution
        vec3 calculate_spark(vec2 uv, int spark_id, float emission_time, float current_time) {
            float spawn_stagger = 1 / float(num_sparks);
            float spark_birth_time = emission_time + float(spark_id) * spawn_stagger;
            float spark_age = current_time - spark_birth_time;
            
            // Don't render if not yet born
            if (spark_age < 0.0) {
                return vec3(0.0);
            }
            
            // Only loop particles if still emitting
            if (is_emitting) {
                spark_age = mod(spark_age, spark_lifetime);
            } else {
                // Not emitting - don't spawn new particles after emission stopped
                if (spark_birth_time > emission_stop_time) {
                    return vec3(0.0);
                }
                // If past lifetime, don't render
                if (spark_age > spark_lifetime) {
                    return vec3(0.0);
                }
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
                // Fire DOWNWARD (negative Y) and toward center (positive X) with wider random spread - FASTER
                float base_speed = 1.2 + random(seed + vec2(40.0, 0.0)) * 0.6; // 1.2-1.8 (2x faster)
                float angle_spread = (random(seed + vec2(30.0, 0.0)) - 0.5) * 0.8; // -0.4 to 0.4 (doubled width)
                initial_velocity = vec2(0.35 + angle_spread, -base_speed); // Negative Y = downward, wider horizontal
            } else {
                // Right cannon at TOP right corner
                start_pos = vec2(0.90 - random(seed + vec2(10.0, 0.0)) * 0.05, 0.98);
                // Fire DOWNWARD (negative Y) and toward center (negative X) with wider random spread - FASTER
                float base_speed = 1.2 + random(seed + vec2(40.0, 0.0)) * 0.6; // 1.2-1.8 (2x faster)
                float angle_spread = (random(seed + vec2(30.0, 0.0)) - 0.5) * 0.8; // -0.4 to 0.4 (doubled width)
                initial_velocity = vec2(-0.35 + angle_spread, -base_speed); // Negative Y = downward, wider horizontal
            }
            
            float gravity = 0.8; // Positive value pulls toward y=0 (downward)
            vec2 spark_pos = start_pos + initial_velocity * spark_age;
            spark_pos.y += 0.5 * gravity * spark_age * spark_age;
            
            // Add slight horizontal air resistance drift
            float drift = sin(spark_age * 2.0 + float(spark_id)) * 0.01;
            spark_pos.x += drift;
            
            // Spark chip size (small rectangular chips) - 30% smaller
            vec2 spark_size = vec2(
                (0.0005 + random(seed + vec2(40.0, 0.0)) * 0.002) * 0.7,  // 30% smaller
                (0.0003 + random(seed + vec2(50.0, 0.0)) * 0.0017) * 0.7  // 30% smaller
            );
            
            // Transform UV to spark space (no rotation)
            vec2 spark_uv = uv - spark_pos;
            
            // Starburst animation progress
            float age_normalized = spark_age / spark_lifetime;
            float growth = smoothstep(0.0, 0.6, age_normalized); // Grow over first 60% of lifetime
            
            // Start as chip, grow into starburst
            float chip_dist = rounded_rect(spark_uv, spark_size, spark_size.y * 0.3);
            
            // Starburst grows and one point elongates - HALF SIZE
            float star_size = max(spark_size.x, spark_size.y) * (1.0 + growth * 0.25);  // Much smaller max size
            float elongation = 1.0 + growth * 0.6; // One point becomes 1.6x longer (half of previous)
            float star_dist = starburst(spark_uv, star_size, elongation);
            
            // Blend from chip to starburst
            float dist = mix(chip_dist, star_dist, growth);
            
            // Smooth falloff for the core spark
            float core_mask = 1.0 - smoothstep(0.0, spark_size.y * 0.5, dist);
            
            // Gold/amber glow effect - much stronger and more visible
            float glow_radius = star_size * 3.0; // Larger glow radius
            float glow_mask = exp(-dist / (glow_radius * 0.3)); // Exponential falloff for softer glow
            float strong_glow = exp(-dist / (glow_radius * 0.1)); // Tighter bright glow
            
            // NO FADE - sudden disappearance (just check if still alive)
            float alive = (age_normalized < 1.0) ? 1.0 : 0.0;
            
            // Add some brightness variation per spark
            float brightness = 0.7 + random(seed + vec2(70.0, 0.0)) * 0.3; // 0.7-1.0
            
            // Sizzle effect: random white-gold color variation over time
            float sizzle_speed = 15.0 + random(seed + vec2(80.0, 0.0)) * 10.0; // Random flicker rate per spark
            float sizzle = random(vec2(spark_age * sizzle_speed, float(spark_id) * 0.37));
            
            // White spark with gold/amber glow
            vec3 white = vec3(1.0, 1.0, 1.0);
            vec3 gold = vec3(1.0, 0.75, 0.2); // Warm gold/amber color
            
            // Sizzle between white-hot and gold-hot randomly
            float gold_mix = 0.3 + sizzle * 0.7; // Randomly 30%-100% gold
            vec3 sizzle_color = mix(white, gold, gold_mix);
            
            // Core is white-gold sizzle, glow is gold
            vec3 core_color = sizzle_color * core_mask * 1.5;
            vec3 glow_color = gold * (strong_glow * 0.8 + glow_mask * 0.4);
            
            vec3 final = (core_color + glow_color) * alive * brightness;
            
            return final;
        }
        
        void main() {
            vec3 final_color = vec3(0.0);
            
            // Only render sparks if emission has started
            if (emission_start_time >= 0.0) {
                // Render all sparks (they have staggered birth times and individual lifetimes)
                // Limit loop iterations for shader optimization (GLSL doesn't optimize unbounded loops well)
                int max_sparks = min(num_sparks, 1200);  // Hard limit to prevent shader slowdown
                for (int i = 0; i < max_sparks; i++) {
                    if (i >= num_sparks) break;  // Early exit
                    vec3 spark_contribution = calculate_spark(uv, i, emission_start_time, time);
                    // Additive blending
                    final_color += spark_contribution;
                }
            }
            
            color = clamp(final_color * mode_opacity_multiplier, 0.0, 1.0);
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set hot sparks effect uniforms"""
        # Use relative time to avoid float precision issues with large Unix timestamps
        current_time = time.time() - self.start_time  # Relative to start

        # Get signal value
        signal_value = frame[self.signal]
        emission_threshold = 0.5

        # Continuous emission while signal is high
        if signal_value > emission_threshold:
            if not self.is_emitting:
                # Signal just went high - start emitting
                self.emission_start_time = current_time
                self.pulse_seed = (
                    random.random()
                )  # New random seed for this emission cycle
                self.is_emitting = True
            # While signal is high, particles continuously loop/respawn
        else:
            # Signal dropped - stop emitting but keep emission_start_time so particles finish
            if self.is_emitting:
                # Just stopped - record the time
                self.emission_stop_time = current_time
            self.is_emitting = False

        # Set uniforms (using relative time for precision)
        self.shader_program["time"] = current_time
        self.shader_program["emission_start_time"] = self.emission_start_time
        self.shader_program["emission_stop_time"] = self.emission_stop_time
        self.shader_program["pulse_seed"] = self.pulse_seed
        self.shader_program["num_sparks"] = self.num_sparks
        self.shader_program["spark_lifetime"] = self.spark_lifetime
        self.shader_program["is_emitting"] = self.is_emitting
        self.shader_program["mode_opacity_multiplier"] = self.mode_opacity_multiplier
