#!/usr/bin/env python3

import math
import time
import random
import numpy as np
import moderngl as mgl
from typing import Optional
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase
from parrot.vj.utils.signal_utils import get_random_frame_signal


@beartype
class OscilloscopeEffect(GenerativeEffectBase):
    """
    Retro oscilloscope waveform effect that draws scrolling waveforms with bloom.
    Creates multiple parallel horizontal lines with sine-based variations based on audio signals.
    Features a retro CRT-style appearance with color scheme-based phosphor glow and bloom effects.
    """

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        line_count: int = 8,
        scroll_speed: float = 2.0,
        waveform_scale: float = 0.3,
        bloom_intensity: float = 1.5,
        signal: FrameSignal = FrameSignal.freq_all,
    ):
        """
        Args:
            width: Width of the generated content
            height: Height of the generated content
            line_count: Number of parallel waveform lines
            scroll_speed: Speed of horizontal scrolling (pixels per second)
            waveform_scale: Scale factor for waveform amplitude
            bloom_intensity: Intensity of the bloom effect
            signal: Audio signal to use for waveform data
        """
        super().__init__(width, height)
        self.line_count = line_count
        self.scroll_speed = scroll_speed
        self.waveform_scale = waveform_scale
        self.bloom_intensity = bloom_intensity
        self.signal = signal

        # Oscilloscope state
        self.start_time = time.time()
        self.waveform_history = []
        self.max_history_length = 200  # Keep enough history for smooth scrolling

        # OpenGL resources for bloom effect
        self.bloom_framebuffer: Optional[mgl.Framebuffer] = None
        self.bloom_texture: Optional[mgl.Texture] = None
        self.blur_program: Optional[mgl.Program] = None
        self.composite_program: Optional[mgl.Program] = None

    @beartype
    def enter(self, context: mgl.Context):
        """Initialize OpenGL resources including bloom effect"""
        self._setup_gl_resources(context, self.width, self.height)
        self._setup_bloom_resources(context)

    @beartype
    def exit(self):
        """Clean up all OpenGL resources"""
        super().exit()
        self._cleanup_bloom_resources()

    def _cleanup_bloom_resources(self):
        """Clean up bloom-specific resources"""
        if self.bloom_framebuffer:
            self.bloom_framebuffer.release()
            self.bloom_framebuffer = None
        if self.bloom_texture:
            self.bloom_texture.release()
            self.bloom_texture = None
        if self.blur_program:
            self.blur_program.release()
            self.blur_program = None
        if self.composite_program:
            self.composite_program.release()
            self.composite_program = None

    def _setup_bloom_resources(self, context: mgl.Context):
        """Setup additional resources for bloom effect"""
        if not self.bloom_texture:
            self.bloom_texture = context.texture((self.width, self.height), 3)
            self.bloom_framebuffer = context.framebuffer(
                color_attachments=[self.bloom_texture]
            )

        if not self.blur_program:
            self.blur_program = context.program(
                vertex_shader=self._get_vertex_shader(),
                fragment_shader=self._get_blur_fragment_shader(),
            )

        if not self.composite_program:
            self.composite_program = context.program(
                vertex_shader=self._get_vertex_shader(),
                fragment_shader=self._get_composite_fragment_shader(),
            )

    @beartype
    def generate(self, vibe: Vibe):
        """Configure oscilloscope parameters based on the vibe"""
        self.signal = get_random_frame_signal()

        # Randomize some parameters based on the vibe
        if random.random() < 0.3:  # 30% chance to change parameters
            self.line_count = random.randint(6, 12)
            self.scroll_speed = random.uniform(1.0, 3.0)
            self.waveform_scale = random.uniform(0.2, 0.5)
            self.bloom_intensity = random.uniform(1.0, 2.0)

    def print_self(self) -> str:
        """Return class name with current signal and oscilloscope parameters"""
        return f"📊 {Fore.GREEN}{self.__class__.__name__}{Style.RESET_ALL} [{Fore.YELLOW}{self.signal.name}{Style.RESET_ALL}, lines:{Fore.WHITE}{self.line_count}{Style.RESET_ALL}, scale:{Fore.WHITE}{self.waveform_scale:.2f}{Style.RESET_ALL}]"

    def _get_fragment_shader(self) -> str:
        """Fragment shader for oscilloscope waveform rendering"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        
        uniform float time;
        uniform float line_count;
        uniform float scroll_speed;
        uniform float waveform_scale;
        uniform vec3 base_color;
        uniform vec3 accent_color;
        uniform sampler2D waveform_data;
        uniform int waveform_length;
        uniform vec2 resolution;
        
        // Smooth distance to line function
        float distanceToLine(vec2 p, vec2 a, vec2 b) {
            vec2 pa = p - a;
            vec2 ba = b - a;
            float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
            return length(pa - ba * h);
        }
        
        // Generate waveform point based on audio data and position
        vec2 getWaveformPoint(float x, float lineIndex) {
            // Calculate which sample to use based on x position and scrolling
            float scrollOffset = time * scroll_speed * 0.1;
            float samplePos = x * 0.5 + scrollOffset;
            
            // Use fractional part for smooth wrapping without discontinuities
            float wrappedPos = fract(samplePos);
            int sampleIndex = int(wrappedPos * float(waveform_length - 1));
            
            // Get audio amplitude from texture (using 2D texture with Y=0.5)
            float amplitude = texture(waveform_data, vec2(float(sampleIndex) / float(waveform_length - 1), 0.5)).r;
            
            // Add sine wave variation based on line index and time for smooth continuity
            float phaseOffset = lineIndex * 0.5 + time * 0.3;
            float sineVariation = sin(samplePos * 8.0 + phaseOffset) * 0.1;
            amplitude += sineVariation;
            
            // Calculate y position for this line
            float lineY = (lineIndex + 0.5) / line_count;
            float waveY = lineY + amplitude * waveform_scale;
            
            return vec2(x, waveY);
        }
        
        void main() {
            vec2 fragCoord = uv * resolution;
            vec2 normalizedCoord = uv;
            
            float minDistance = 1000.0;
            float totalIntensity = 0.0;
            
            // Draw multiple waveform lines
            for (float lineIndex = 0.0; lineIndex < line_count; lineIndex += 1.0) {
                // Sample multiple points along the line for smooth curves
                for (float x = 0.0; x <= 1.0; x += 0.01) {
                    vec2 p1 = getWaveformPoint(x, lineIndex);
                    vec2 p2 = getWaveformPoint(x + 0.01, lineIndex);
                    
                    float dist = distanceToLine(normalizedCoord, p1, p2);
                    minDistance = min(minDistance, dist);
                    
                    // Add intensity based on distance
                    float intensity = 1.0 / (1.0 + dist * 200.0);
                    totalIntensity += intensity;
                }
            }
            
            // Create phosphor-like glow effect with lower alpha
            float glow = 1.0 / (1.0 + minDistance * 100.0) * 0.6;  // Reduced glow intensity
            float coreGlow = 1.0 / (1.0 + minDistance * 500.0) * 0.4;  // Reduced core glow
            
            // Combine base color and accent color
            vec3 finalColor = base_color * glow + accent_color * coreGlow;
            finalColor += base_color * totalIntensity * 0.05;  // Reduced intensity contribution
            
            // Add scanline effect for retro CRT look
            float scanline = sin(fragCoord.y * 0.5) * 0.1 + 0.9;
            finalColor *= scanline;
            
            // Add slight vignette
            vec2 center = normalizedCoord - 0.5;
            float vignette = 1.0 - dot(center, center) * 0.3;
            finalColor *= vignette;
            
            color = finalColor;
        }
        """

    def _get_blur_fragment_shader(self) -> str:
        """Fragment shader for bloom blur pass"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform vec2 blur_direction;
        uniform float blur_strength;
        
        void main() {
            vec3 result = vec3(0.0);
            float totalWeight = 0.0;
            
            // Gaussian blur
            for (int i = -4; i <= 4; i++) {
                vec2 offset = blur_direction * float(i) * blur_strength;
                float weight = exp(-float(i * i) / 8.0);
                result += texture(input_texture, uv + offset).rgb * weight;
                totalWeight += weight;
            }
            
            color = result / totalWeight;
        }
        """

    def _get_composite_fragment_shader(self) -> str:
        """Fragment shader for compositing original with bloom"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D original_texture;
        uniform sampler2D bloom_texture;
        uniform float bloom_intensity;
        
        void main() {
            vec3 original = texture(original_texture, uv).rgb;
            vec3 bloom = texture(bloom_texture, uv).rgb;
            
            // Additive bloom
            color = original + bloom * bloom_intensity;
        }
        """

    @beartype
    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set oscilloscope effect uniforms"""
        current_time = time.time() - self.start_time

        # Update waveform history with current audio data
        self._update_waveform_history(frame)

        # Set basic uniforms
        self.shader_program["time"] = current_time
        self.shader_program["line_count"] = float(self.line_count)
        self.shader_program["scroll_speed"] = self.scroll_speed
        self.shader_program["waveform_scale"] = self.waveform_scale
        self.shader_program["resolution"] = (float(self.width), float(self.height))

        # Set colors from color scheme (already in 0-1 range)
        primary_color = list(scheme.fg.rgb)
        bg_color = list(scheme.bg.rgb)
        secondary_color = list(scheme.bg_contrast.rgb)

        # Use the actual color scheme colors instead of forcing green
        base_color = (
            0.4 * bg_color[0] + 0.6 * primary_color[0],
            0.4 * bg_color[1] + 0.6 * primary_color[1],
            0.4 * bg_color[2] + 0.6 * primary_color[2],
        )
        accent_color = (
            0.3 * primary_color[0] + 0.7 * secondary_color[0],
            0.3 * primary_color[1] + 0.7 * secondary_color[1],
            0.3 * primary_color[2] + 0.7 * secondary_color[2],
        )

        self.shader_program["base_color"] = base_color
        self.shader_program["accent_color"] = accent_color

        # Create and bind waveform data texture
        self._bind_waveform_texture()

    @beartype
    def _update_waveform_history(self, frame: Frame):
        """Update the waveform history buffer with current audio data"""
        # Get audio timeseries data
        signal_name = self.signal.name
        if (
            hasattr(frame, "timeseries")
            and frame.timeseries
            and signal_name in frame.timeseries
        ):
            waveform_data = frame.timeseries[signal_name]
            if isinstance(waveform_data, (list, np.ndarray)) and len(waveform_data) > 0:
                # Normalize the data to -1 to 1 range
                waveform_array = np.array(waveform_data, dtype=np.float32)
                if len(waveform_array) > 0:
                    # Normalize
                    max_val = np.max(np.abs(waveform_array))
                    if max_val > 0:
                        waveform_array = waveform_array / max_val

                    # Add to history
                    self.waveform_history.extend(waveform_array)

                    # Keep history at manageable size
                    if len(self.waveform_history) > self.max_history_length:
                        self.waveform_history = self.waveform_history[
                            -self.max_history_length :
                        ]

        # If no data available, use a simple sine wave as fallback
        if not self.waveform_history:
            current_time = time.time() - self.start_time
            fallback_data = [
                math.sin(current_time * 2.0 + i * 0.1) * 0.5 for i in range(100)
            ]
            self.waveform_history = fallback_data

    def _bind_waveform_texture(self):
        """Create and bind a 1D texture with waveform data"""
        if not self.waveform_history:
            return

        # Prepare waveform data as texture
        waveform_array = np.array(self.waveform_history, dtype=np.float32)

        # Create 1D texture
        if hasattr(self, "_waveform_texture"):
            self._waveform_texture.release()

        # Create 2D texture data (single row, single channel for waveform data)
        texture_data = waveform_array.astype(np.float32)

        context = self.shader_program.ctx
        self._waveform_texture = context.texture(
            (len(waveform_array), 1), 1, texture_data.tobytes(), dtype="f4"
        )
        self._waveform_texture.use(1)

        self.shader_program["waveform_data"] = 1
        self.shader_program["waveform_length"] = len(waveform_array)

    @beartype
    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """
        Render the oscilloscope effect with bloom.
        First renders the basic waveforms, then applies bloom post-processing.
        """
        if not self.framebuffer:
            self._setup_gl_resources(context, self.width, self.height)
        if not self.bloom_framebuffer:
            self._setup_bloom_resources(context)

        # Render main oscilloscope effect to main framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Set effect-specific uniforms
        self._set_effect_uniforms(frame, scheme)

        # Render main effect
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Apply bloom effect
        self._apply_bloom_effect(context, frame, scheme)

        return self.framebuffer

    @beartype
    def _apply_bloom_effect(
        self, context: mgl.Context, frame: Frame, scheme: ColorScheme
    ):
        """Apply bloom post-processing effect"""
        if (
            not self.bloom_framebuffer
            or not self.blur_program
            or not self.composite_program
        ):
            return

        # First blur pass - horizontal
        self.bloom_framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        self.framebuffer.color_attachments[0].use(0)
        self.blur_program["input_texture"] = 0
        self.blur_program["blur_direction"] = (1.0 / self.width, 0.0)
        self.blur_program["blur_strength"] = 2.0

        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Second blur pass - vertical (back to main framebuffer)
        self.framebuffer.use()

        self.bloom_framebuffer.color_attachments[0].use(0)
        self.blur_program["blur_direction"] = (0.0, 1.0 / self.height)

        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Composite original with bloom
        # Store original in bloom buffer temporarily
        self.bloom_framebuffer.use()
        context.clear(0.0, 0.0, 0.0)
        self._set_effect_uniforms(frame, scheme)  # Re-render original
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Final composite
        self.framebuffer.use()

        self.bloom_framebuffer.color_attachments[0].use(0)  # Original
        self.framebuffer.color_attachments[0].use(1)  # Blurred

        self.composite_program["original_texture"] = 0
        self.composite_program["bloom_texture"] = 1
        self.composite_program["bloom_intensity"] = self.bloom_intensity

        self.quad_vao.render(mgl.TRIANGLE_STRIP)
