"""
Trippy GLSL shader layers for rave visuals
"""

import math
import time
from typing import Optional, Dict, Any
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.gpu_optimizer import get_gpu_manager, create_metal_optimized_context

import moderngl


class ShaderLayer(LayerBase):
    """Base class for GLSL shader-based layers"""

    def __init__(
        self,
        name: str,
        shader_source: str,
        z_order: int = 5,
    ):
        super().__init__(name, z_order)
        self.shader_source = shader_source
        self.time_uniform = 0.0
        self.start_time = time.time()

        # Audio uniforms
        self.bass_uniform = 0.0
        self.treble_uniform = 0.0
        self.energy_uniform = 0.0

        # Color scheme uniforms
        self.color1_uniform = (1.0, 0.0, 0.0)  # Red
        self.color2_uniform = (0.0, 1.0, 0.0)  # Green
        self.color3_uniform = (0.0, 0.0, 1.0)  # Blue

        # ModernGL resources
        self.ctx = None
        self.program = None
        self.vao = None
        self.texture = None
        self.fbo = None

        # Shader will be initialized when size is set by renderer
        self._shader_initialized = False

    def set_size(self, width: int, height: int):
        """Set the size and initialize shader if not already done"""
        super().set_size(width, height)
        if not self._shader_initialized:
            self._init_shader_optimized()
            self._shader_initialized = True

    def _init_shader_optimized(self):
        """Initialize optimized ModernGL shader resources"""
        try:
            # Get GPU manager for optimization
            gpu_manager = get_gpu_manager()

            # Use optimized context for Apple Silicon
            self.ctx = create_metal_optimized_context()
            if not self.ctx:
                self.ctx = moderngl.create_context(standalone=True)

            # Get optimal resolution for this GPU
            optimal_width, optimal_height = gpu_manager.get_recommended_resolution()
            if optimal_width < self.width or optimal_height < self.height:
                print(
                    f"ShaderLayer '{self.name}': Using optimal resolution {optimal_width}×{optimal_height}"
                )
                self.width = optimal_width
                self.height = optimal_height

            # Vertex shader for fullscreen quad
            vertex_shader = """
            #version 330 core
            in vec2 in_position;
            out vec2 v_texcoord;
            
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
                v_texcoord = (in_position + 1.0) * 0.5;
            }
            """

            # Optimize shader source for this GPU
            optimized_shader = gpu_manager.optimizer.optimize_shader_source(
                self.shader_source
            )

            # Create shader program
            self.program = self.ctx.program(
                vertex_shader=vertex_shader, fragment_shader=optimized_shader
            )

            # Create fullscreen quad
            vertices = np.array(
                [
                    -1.0,
                    -1.0,  # Bottom-left
                    1.0,
                    -1.0,  # Bottom-right
                    1.0,
                    1.0,  # Top-right
                    -1.0,
                    1.0,  # Top-left
                ],
                dtype=np.float32,
            )

            indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

            vbo = self.ctx.buffer(vertices.tobytes())
            ibo = self.ctx.buffer(indices.tobytes())

            self.vao = self.ctx.vertex_array(
                self.program, [(vbo, "2f", "in_position")], ibo
            )

            # Create texture and framebuffer
            self.texture = self.ctx.texture((self.width, self.height), 4)
            self.fbo = self.ctx.framebuffer(self.texture)

            print(f"ShaderLayer '{self.name}' initialized with ModernGL")

        except Exception as e:
            print(f"Failed to initialize shader '{self.name}': {e}")
            self.ctx = None

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render shader effect"""
        if not self.enabled:
            return None

        # Update uniforms from audio and color scheme
        self._update_uniforms(frame, scheme)

        if self.ctx and self.program:
            return self._render_shader()
        else:
            return self._render_fallback()

    def _update_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Update shader uniforms"""
        # Time uniform
        self.time_uniform = time.time() - self.start_time

        # Audio uniforms
        self.bass_uniform = frame[FrameSignal.freq_low]
        self.treble_uniform = frame[FrameSignal.freq_high]
        self.energy_uniform = frame[FrameSignal.freq_all]

        # Color scheme uniforms
        self.color1_uniform = scheme.fg.rgb
        self.color2_uniform = scheme.bg.rgb
        self.color3_uniform = scheme.bg_contrast.rgb

    def _render_shader(self) -> Optional[np.ndarray]:
        """Render using ModernGL shader"""
        try:
            import time

            start_time = time.time()
            # Set uniforms
            if "u_time" in self.program:
                self.program["u_time"] = self.time_uniform
            if "u_bass" in self.program:
                self.program["u_bass"] = self.bass_uniform
            if "u_treble" in self.program:
                self.program["u_treble"] = self.treble_uniform
            if "u_energy" in self.program:
                self.program["u_energy"] = self.energy_uniform
            if "u_resolution" in self.program:
                self.program["u_resolution"] = (float(self.width), float(self.height))
            if "u_color1" in self.program:
                self.program["u_color1"] = self.color1_uniform
            if "u_color2" in self.program:
                self.program["u_color2"] = self.color2_uniform
            if "u_color3" in self.program:
                self.program["u_color3"] = self.color3_uniform

            # Render to framebuffer
            self.fbo.use()
            self.ctx.clear(0.0, 0.0, 0.0, 0.0)
            self.vao.render()

            # Read back result
            data = self.fbo.read(components=4)
            result = np.frombuffer(data, dtype=np.uint8)
            result = result.reshape((self.height, self.width, 4))

            # Flip vertically (OpenGL coordinate system)
            result = np.flipud(result)

            # Record performance
            render_time = time.time() - start_time
            gpu_manager = get_gpu_manager()
            gpu_manager.update_performance(render_time)

            return result

        except Exception as e:
            print(f"Shader rendering error: {e}")
            return self._render_fallback()

    def _render_fallback(self) -> Optional[np.ndarray]:
        """CPU fallback rendering when shader fails"""
        # Simple animated pattern as fallback
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Create simple wave pattern
        for y in range(self.height):
            for x in range(self.width):
                # Normalized coordinates
                nx = x / self.width
                ny = y / self.height

                # Simple wave based on time and audio
                wave = math.sin(
                    nx * 10 + self.time_uniform * 2 + self.bass_uniform * 5
                ) * math.cos(ny * 8 + self.time_uniform * 1.5 + self.treble_uniform * 3)

                intensity = int((wave + 1.0) * 0.5 * 255 * self.energy_uniform)

                # Use color scheme
                r = int(self.color1_uniform[0] * intensity)
                g = int(self.color2_uniform[1] * intensity)
                b = int(self.color3_uniform[2] * intensity)

                texture[y, x] = [r, g, b, intensity]

        return texture

    def cleanup(self):
        """Clean up shader resources"""
        if self.ctx:
            try:
                if self.fbo:
                    self.fbo.release()
                if self.texture:
                    self.texture.release()
                if self.vao:
                    self.vao.release()
                if self.program:
                    self.program.release()
            except:
                pass
        self.ctx = None

    def __del__(self):
        self.cleanup()


class TunnelShader(ShaderLayer):
    """Trippy tunnel effect shader"""

    def __init__(
        self,
        name: str = "tunnel",
        z_order: int = 5,
    ):
        tunnel_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord;
            vec2 center = vec2(0.5, 0.5);
            
            // Distance from center
            float dist = distance(uv, center);
            
            // Tunnel effect
            float tunnel_speed = u_time * 0.5 + u_bass * 2.0;
            float tunnel_radius = 0.3 + u_energy * 0.4;
            
            // Create tunnel rings
            float rings = sin(dist * 20.0 - tunnel_speed * 3.0) * 0.5 + 0.5;
            rings *= smoothstep(tunnel_radius, 0.0, dist);
            
            // Rotation effect
            float angle = atan(uv.y - center.y, uv.x - center.x);
            float rotation = u_time * 0.3 + u_treble * 1.5;
            angle += rotation;
            
            // Spiral pattern
            float spiral = sin(angle * 8.0 + dist * 15.0 - tunnel_speed * 2.0) * 0.5 + 0.5;
            
            // Combine effects
            float intensity = rings * spiral * (0.5 + u_energy * 0.5);
            
            // Color mixing
            vec3 color = mix(u_color1, u_color2, sin(u_time * 0.5) * 0.5 + 0.5);
            color = mix(color, u_color3, u_bass);
            
            fragColor = vec4(color * intensity, intensity);
        }
        """
        super().__init__(name, tunnel_shader, z_order)


class PlasmaShader(ShaderLayer):
    """Trippy plasma effect shader"""

    def __init__(
        self,
        name: str = "plasma",
        z_order: int = 4,
    ):
        plasma_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord * 2.0 - 1.0;  // -1 to 1 range
            uv.x *= u_resolution.x / u_resolution.y;  // Aspect ratio correction
            
            float time_factor = u_time * 0.5 + u_energy * 2.0;
            
            // Multiple plasma waves
            float plasma1 = sin(uv.x * 8.0 + time_factor);
            float plasma2 = sin(uv.y * 6.0 + time_factor * 1.3);
            float plasma3 = sin((uv.x + uv.y) * 4.0 + time_factor * 0.8);
            float plasma4 = sin(sqrt(uv.x*uv.x + uv.y*uv.y) * 10.0 + time_factor * 2.0);
            
            // Bass affects wave amplitude
            plasma1 *= (1.0 + u_bass * 2.0);
            plasma2 *= (1.0 + u_bass * 1.5);
            
            // Treble affects frequency
            plasma3 += sin(uv.x * 12.0 * (1.0 + u_treble * 3.0) + time_factor * 2.0);
            plasma4 += cos(uv.y * 10.0 * (1.0 + u_treble * 2.0) + time_factor * 1.5);
            
            // Combine plasma waves
            float combined = (plasma1 + plasma2 + plasma3 + plasma4) * 0.25;
            combined = combined * 0.5 + 0.5;  // Normalize to 0-1
            
            // Color cycling
            vec3 color1 = u_color1 * (sin(combined * 3.14159 + time_factor) * 0.5 + 0.5);
            vec3 color2 = u_color2 * (cos(combined * 3.14159 + time_factor * 1.2) * 0.5 + 0.5);
            vec3 color3 = u_color3 * (sin(combined * 6.28318 + time_factor * 0.8) * 0.5 + 0.5);
            
            vec3 final_color = color1 + color2 + color3;
            final_color *= (0.3 + u_energy * 0.7);
            
            fragColor = vec4(final_color, 0.8);
        }
        """
        super().__init__(name, plasma_shader, z_order)


class FractalShader(ShaderLayer):
    """Trippy fractal effect shader"""

    def __init__(
        self,
        name: str = "fractal",
        z_order: int = 6,
    ):
        fractal_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        vec2 complex_mul(vec2 a, vec2 b) {
            return vec2(a.x*b.x - a.y*b.y, a.x*b.y + a.y*b.x);
        }
        
        float mandelbrot(vec2 c, int max_iter) {
            vec2 z = vec2(0.0);
            for (int i = 0; i < max_iter; i++) {
                if (dot(z, z) > 4.0) return float(i) / float(max_iter);
                z = complex_mul(z, z) + c;
            }
            return 0.0;
        }
        
        void main() {
            vec2 uv = v_texcoord * 4.0 - 2.0;  // -2 to 2 range
            
            // Zoom and movement based on audio
            float zoom = 1.0 + u_energy * 2.0 + u_bass * 0.5;
            vec2 offset = vec2(
                sin(u_time * 0.3 + u_bass) * 0.5,
                cos(u_time * 0.2 + u_treble) * 0.3
            );
            
            uv = uv / zoom + offset;
            
            // Fractal calculation
            int iterations = int(20.0 + u_treble * 30.0);
            float fractal_val = mandelbrot(uv, iterations);
            
            // Color based on fractal value and audio
            float color_shift = u_time * 0.5 + u_energy * 3.0;
            
            vec3 color = vec3(0.0);
            if (fractal_val > 0.0) {
                color.r = sin(fractal_val * 6.28318 + color_shift) * 0.5 + 0.5;
                color.g = sin(fractal_val * 6.28318 + color_shift + 2.094) * 0.5 + 0.5;
                color.b = sin(fractal_val * 6.28318 + color_shift + 4.188) * 0.5 + 0.5;
                
                // Mix with color scheme
                color = mix(color, u_color1, 0.3);
                color = mix(color, u_color2, fractal_val * 0.5);
                color = mix(color, u_color3, u_bass * 0.4);
            }
            
            color *= (0.4 + u_energy * 0.6);
            
            fragColor = vec4(color, 0.7);
        }
        """
        super().__init__(name, fractal_shader, z_order)


class KaleidoscopeShader(ShaderLayer):
    """Trippy kaleidoscope effect shader"""

    def __init__(
        self,
        name: str = "kaleidoscope",
        z_order: int = 7,
    ):
        kaleidoscope_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord - 0.5;
            uv.x *= u_resolution.x / u_resolution.y;
            
            // Polar coordinates
            float radius = length(uv);
            float angle = atan(uv.y, uv.x);
            
            // Kaleidoscope segments
            float segments = 6.0 + u_treble * 6.0;  // 6-12 segments based on treble
            angle = mod(angle, 6.28318 / segments);
            if (mod(floor(angle / (6.28318 / segments)), 2.0) == 1.0) {
                angle = (6.28318 / segments) - angle;
            }
            
            // Convert back to cartesian
            vec2 kaleid_uv = vec2(cos(angle), sin(angle)) * radius;
            
            // Time-based movement
            float time_factor = u_time * 0.8 + u_bass * 2.0;
            kaleid_uv += vec2(sin(time_factor), cos(time_factor * 1.3)) * 0.1;
            
            // Pattern generation
            float pattern1 = sin(kaleid_uv.x * 15.0 + time_factor) * 0.5 + 0.5;
            float pattern2 = cos(kaleid_uv.y * 12.0 + time_factor * 1.2) * 0.5 + 0.5;
            float pattern3 = sin(radius * 20.0 - time_factor * 3.0) * 0.5 + 0.5;
            
            // Bass affects pattern intensity
            pattern1 *= (0.5 + u_bass * 1.5);
            pattern2 *= (0.7 + u_bass * 1.0);
            
            // Combine patterns
            float combined = pattern1 * pattern2 * pattern3;
            combined *= (0.3 + u_energy * 0.7);
            
            // Color cycling
            vec3 color = u_color1 * pattern1 + u_color2 * pattern2 + u_color3 * pattern3;
            color = normalize(color) * combined;
            
            fragColor = vec4(color, combined * 0.8);
        }
        """
        super().__init__(name, kaleidoscope_shader, z_order)


class WaveDistortionShader(ShaderLayer):
    """Trippy wave distortion shader"""

    def __init__(
        self,
        name: str = "wave_distort",
        z_order: int = 8,
    ):
        wave_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord;
            
            // Multiple wave distortions
            float time_bass = u_time + u_bass * 3.0;
            float time_treble = u_time + u_treble * 2.0;
            
            // Horizontal waves
            uv.y += sin(uv.x * 10.0 + time_bass * 2.0) * 0.1 * (1.0 + u_bass);
            uv.x += cos(uv.y * 8.0 + time_treble * 1.5) * 0.08 * (1.0 + u_treble);
            
            // Circular waves
            vec2 center = vec2(0.5 + sin(time_bass * 0.5) * 0.2, 
                              0.5 + cos(time_treble * 0.3) * 0.2);
            float dist = distance(uv, center);
            
            // Ripple effect
            float ripple = sin(dist * 25.0 - time_bass * 4.0) * 0.5 + 0.5;
            ripple *= exp(-dist * 3.0);  // Fade with distance
            
            // Energy affects wave amplitude
            ripple *= (0.3 + u_energy * 1.5);
            
            // Color based on wave patterns
            float color_wave1 = sin(uv.x * 12.0 + time_bass) * 0.5 + 0.5;
            float color_wave2 = cos(uv.y * 10.0 + time_treble) * 0.5 + 0.5;
            float color_wave3 = sin((uv.x + uv.y) * 8.0 + time_bass * 0.7) * 0.5 + 0.5;
            
            vec3 color = u_color1 * color_wave1 + 
                        u_color2 * color_wave2 + 
                        u_color3 * color_wave3;
            
            color *= ripple;
            color *= (0.4 + u_energy * 0.6);
            
            fragColor = vec4(color, ripple * 0.7);
        }
        """
        super().__init__(name, wave_shader, z_order)


class PsychedelicShader(ShaderLayer):
    """Trippy psychedelic pattern shader"""

    def __init__(
        self,
        name: str = "psychedelic",
        z_order: int = 9,
    ):
        psychedelic_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord;
            vec2 center = vec2(0.5, 0.5);
            
            // Multiple time scales
            float fast_time = u_time * 2.0 + u_treble * 5.0;
            float slow_time = u_time * 0.3 + u_bass * 1.0;
            
            // Psychedelic patterns
            float pattern1 = sin(uv.x * 20.0 + fast_time) * 
                            cos(uv.y * 15.0 + slow_time);
            
            float pattern2 = sin(distance(uv, center) * 30.0 - fast_time * 2.0) *
                            cos(atan(uv.y - center.y, uv.x - center.x) * 8.0 + slow_time);
            
            // Interference patterns
            float interference = sin(uv.x * 25.0 + uv.y * 20.0 + fast_time) *
                               cos(uv.x * 18.0 - uv.y * 22.0 + slow_time * 1.5);
            
            // Energy affects complexity
            float complexity = 1.0 + u_energy * 3.0;
            pattern1 *= complexity;
            pattern2 *= complexity;
            
            // Combine patterns
            float combined = (pattern1 + pattern2 + interference) / 3.0;
            combined = combined * 0.5 + 0.5;  // Normalize
            
            // Trippy color mixing
            float color_phase = combined * 6.28318 + fast_time;
            
            vec3 color = vec3(
                sin(color_phase) * 0.5 + 0.5,
                sin(color_phase + 2.094) * 0.5 + 0.5,  // 120 degrees
                sin(color_phase + 4.188) * 0.5 + 0.5   // 240 degrees
            );
            
            // Mix with color scheme
            color = mix(color, u_color1, 0.3);
            color = mix(color, u_color2, sin(slow_time) * 0.5 + 0.5);
            color = mix(color, u_color3, u_bass * 0.4);
            
            // Final intensity
            float intensity = combined * (0.4 + u_energy * 0.6);
            
            fragColor = vec4(color * intensity, intensity * 0.9);
        }
        """
        super().__init__(name, psychedelic_shader, z_order)


class VortexShader(ShaderLayer):
    """Trippy vortex/spiral shader"""

    def __init__(
        self,
        name: str = "vortex",
        z_order: int = 10,
    ):
        vortex_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord - 0.5;
            uv.x *= u_resolution.x / u_resolution.y;
            
            // Polar coordinates
            float radius = length(uv);
            float angle = atan(uv.y, uv.x);
            
            // Vortex parameters
            float vortex_speed = u_time * 1.5 + u_energy * 3.0;
            float vortex_strength = 0.5 + u_bass * 1.5;
            
            // Spiral distortion
            angle += sin(radius * 10.0 - vortex_speed) * vortex_strength;
            angle += radius * 3.0;  // Spiral effect
            
            // Multiple spiral arms
            float arms = 5.0 + u_treble * 3.0;  // 5-8 arms based on treble
            float spiral = sin(angle * arms + radius * 15.0 - vortex_speed * 2.0);
            spiral *= exp(-radius * 2.0);  // Fade with distance
            
            // Radial waves
            float radial_waves = sin(radius * 20.0 - vortex_speed * 3.0) * 0.5 + 0.5;
            radial_waves *= (1.0 - radius);  // Stronger in center
            
            // Combine effects
            float intensity = (spiral * 0.7 + radial_waves * 0.3) * (0.3 + u_energy * 0.7);
            intensity = max(0.0, intensity);
            
            // Color based on angle and radius
            vec3 color = u_color1 * sin(angle + vortex_speed * 0.5) +
                        u_color2 * cos(radius * 8.0 + vortex_speed) +
                        u_color3 * sin(angle * 2.0 + radius * 5.0);
            
            color = normalize(color) * intensity;
            
            fragColor = vec4(color, intensity * 0.8);
        }
        """
        super().__init__(name, vortex_shader, z_order)


class NoiseShader(ShaderLayer):
    """Trippy noise-based shader"""

    def __init__(
        self,
        name: str = "noise",
        z_order: int = 3,
    ):
        noise_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        // Simple noise function
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
        }
        
        float noise(vec2 st) {
            vec2 i = floor(st);
            vec2 f = fract(st);
            
            float a = random(i);
            float b = random(i + vec2(1.0, 0.0));
            float c = random(i + vec2(0.0, 1.0));
            float d = random(i + vec2(1.0, 1.0));
            
            vec2 u = f * f * (3.0 - 2.0 * f);
            
            return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
        }
        
        float fbm(vec2 st) {
            float value = 0.0;
            float amplitude = 0.5;
            float frequency = 0.0;
            
            for (int i = 0; i < 4; i++) {
                value += amplitude * noise(st);
                st *= 2.0;
                amplitude *= 0.5;
            }
            return value;
        }
        
        void main() {
            vec2 uv = v_texcoord;
            
            // Animated noise
            float time_factor = u_time * 0.5;
            vec2 noise_uv = uv * (5.0 + u_energy * 10.0);
            
            // Multiple noise layers
            float noise1 = fbm(noise_uv + vec2(time_factor, 0.0));
            float noise2 = fbm(noise_uv * 1.5 + vec2(0.0, time_factor * 1.3));
            float noise3 = fbm(noise_uv * 2.0 + vec2(time_factor * 0.8, time_factor * 0.6));
            
            // Bass affects noise characteristics
            noise1 = pow(noise1, 1.0 / (1.0 + u_bass * 2.0));
            noise2 *= (0.5 + u_bass * 1.5);
            
            // Treble affects detail
            noise3 *= (0.3 + u_treble * 1.2);
            
            // Combine noise layers
            float combined_noise = (noise1 + noise2 + noise3) / 3.0;
            combined_noise *= (0.2 + u_energy * 0.8);
            
            // Color based on noise
            vec3 color = vec3(0.0);
            color.r = u_color1.r * sin(combined_noise * 6.28318 + time_factor);
            color.g = u_color2.g * cos(combined_noise * 6.28318 + time_factor * 1.2);
            color.b = u_color3.b * sin(combined_noise * 12.56636 + time_factor * 0.8);
            
            color = abs(color);  // Ensure positive values
            color *= (0.5 + u_energy * 0.5);
            
            fragColor = vec4(color, combined_noise * 0.6);
        }
        """
        super().__init__(name, noise_shader, z_order)


class HypnoticShader(ShaderLayer):
    """Hypnotic spiral shader for trance effects"""

    def __init__(
        self,
        name: str = "hypnotic",
        z_order: int = 11,
    ):
        hypnotic_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord - 0.5;
            uv.x *= u_resolution.x / u_resolution.y;
            
            float radius = length(uv);
            float angle = atan(uv.y, uv.x);
            
            // Hypnotic spiral
            float spiral_speed = u_time * 1.0 + u_energy * 2.0;
            float spiral_tightness = 3.0 + u_treble * 5.0;
            
            float hypno = sin(angle * spiral_tightness + radius * 20.0 - spiral_speed * 3.0);
            hypno *= sin(radius * 15.0 - spiral_speed * 2.0);
            hypno = hypno * 0.5 + 0.5;
            
            // Concentric circles
            float circles = sin(radius * 30.0 - spiral_speed * 4.0) * 0.5 + 0.5;
            circles *= (1.0 - radius * 0.8);  // Fade toward edges
            
            // Bass affects the hypnotic intensity
            hypno *= (0.5 + u_bass * 1.5);
            circles *= (0.7 + u_bass * 1.0);
            
            // Combine patterns
            float combined = max(hypno, circles * 0.6);
            combined *= (0.3 + u_energy * 0.7);
            
            // Hypnotic color cycling
            float color_cycle = u_time * 2.0 + combined * 10.0;
            
            vec3 color = vec3(
                sin(color_cycle) * 0.5 + 0.5,
                sin(color_cycle + 2.094) * 0.5 + 0.5,
                sin(color_cycle + 4.188) * 0.5 + 0.5
            );
            
            // Mix with color scheme for theming
            color = mix(color, u_color1, 0.2);
            color = mix(color, u_color2, sin(spiral_speed * 0.3) * 0.5 + 0.5);
            color = mix(color, u_color3, u_treble * 0.3);
            
            fragColor = vec4(color * combined, combined * 0.85);
        }
        """
        super().__init__(name, hypnotic_shader, z_order)


class GlitchShader(ShaderLayer):
    """Digital glitch shader for cyber effects"""

    def __init__(
        self,
        name: str = "glitch",
        z_order: int = 12,
    ):
        glitch_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
        }
        
        void main() {
            vec2 uv = v_texcoord;
            
            // Glitch intensity based on audio
            float glitch_intensity = u_energy * 0.8 + u_treble * 0.5;
            
            // Horizontal glitch lines
            float line_noise = random(vec2(floor(uv.y * 100.0), floor(u_time * 10.0)));
            if (line_noise < glitch_intensity * 0.1) {
                uv.x += (random(vec2(uv.y, u_time)) - 0.5) * 0.1 * glitch_intensity;
            }
            
            // RGB channel separation
            vec2 r_offset = vec2(sin(u_time * 20.0 + u_bass * 30.0) * 0.01 * glitch_intensity, 0.0);
            vec2 g_offset = vec2(0.0, 0.0);
            vec2 b_offset = vec2(-sin(u_time * 25.0 + u_treble * 20.0) * 0.01 * glitch_intensity, 0.0);
            
            // Sample colors with offsets
            float r = step(0.3, random(uv + r_offset + vec2(u_time * 0.1, 0.0)));
            float g = step(0.3, random(uv + g_offset + vec2(0.0, u_time * 0.15)));
            float b = step(0.3, random(uv + b_offset + vec2(u_time * 0.08, u_time * 0.12)));
            
            vec3 glitch_color = vec3(r, g, b);
            
            // Digital blocks
            vec2 block_uv = floor(uv * (10.0 + u_energy * 20.0)) / (10.0 + u_energy * 20.0);
            float block_noise = random(block_uv + vec2(floor(u_time * 5.0), 0.0));
            
            if (block_noise < glitch_intensity * 0.2) {
                glitch_color = vec3(1.0) - glitch_color;  // Invert
            }
            
            // Mix with color scheme
            glitch_color = mix(glitch_color, u_color1, 0.3);
            glitch_color = mix(glitch_color, u_color2, u_bass * 0.4);
            glitch_color = mix(glitch_color, u_color3, u_treble * 0.3);
            
            // Scanlines
            float scanlines = sin(uv.y * u_resolution.y * 0.5) * 0.1 + 0.9;
            glitch_color *= scanlines;
            
            float alpha = glitch_intensity * 0.7;
            fragColor = vec4(glitch_color * alpha, alpha);
        }
        """
        super().__init__(name, glitch_shader, z_order)


class GeometricShader(ShaderLayer):
    """Trippy geometric pattern shader"""

    def __init__(
        self,
        name: str = "geometric",
        z_order: int = 4,
    ):
        geometric_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec2 uv = v_texcoord;
            
            // Grid parameters
            float grid_size = 8.0 + u_treble * 12.0;
            float time_factor = u_time * 0.8 + u_bass * 2.0;
            
            // Create grid
            vec2 grid_uv = uv * grid_size;
            vec2 grid_id = floor(grid_uv);
            vec2 grid_pos = fract(grid_uv);
            
            // Geometric shapes in each cell
            float shape = 0.0;
            
            // Triangle
            float triangle = step(grid_pos.x + grid_pos.y, 1.0 + sin(time_factor + grid_id.x + grid_id.y) * 0.3);
            
            // Circle
            float circle = 1.0 - smoothstep(0.2, 0.4 + u_energy * 0.3, 
                                          distance(grid_pos, vec2(0.5)));
            
            // Square rotation
            vec2 rotated_pos = grid_pos - 0.5;
            float rotation = time_factor + (grid_id.x + grid_id.y) * 0.5;
            mat2 rot = mat2(cos(rotation), -sin(rotation), sin(rotation), cos(rotation));
            rotated_pos = rot * rotated_pos + 0.5;
            
            float square = step(0.3, max(abs(rotated_pos.x - 0.5), abs(rotated_pos.y - 0.5)));
            square = 1.0 - square;
            
            // Select shape based on grid position
            float grid_hash = fract(sin(dot(grid_id, vec2(12.9898, 78.233))) * 43758.5453);
            
            if (grid_hash < 0.33) {
                shape = triangle;
            } else if (grid_hash < 0.66) {
                shape = circle;
            } else {
                shape = square;
            }
            
            // Audio affects shape intensity
            shape *= (0.4 + u_energy * 0.6);
            shape *= (0.7 + u_bass * 0.8);
            
            // Color based on grid position and time
            vec3 color = u_color1 * sin(grid_id.x * 0.5 + time_factor) +
                        u_color2 * cos(grid_id.y * 0.7 + time_factor * 1.2) +
                        u_color3 * sin((grid_id.x + grid_id.y) * 0.3 + time_factor * 0.8);
            
            color = normalize(color) * shape;
            
            fragColor = vec4(color, shape * 0.8);
        }
        """
        super().__init__(name, geometric_shader, z_order)


class RainbowShader(ShaderLayer):
    """Trippy rainbow wave shader"""

    def __init__(
        self,
        name: str = "rainbow",
        z_order: int = 2,
    ):
        rainbow_shader = """
        #version 330 core
        uniform float u_time;
        uniform float u_bass;
        uniform float u_treble;
        uniform float u_energy;
        uniform vec2 u_resolution;
        uniform vec3 u_color1;
        uniform vec3 u_color2;
        uniform vec3 u_color3;
        
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        vec3 hsv2rgb(vec3 c) {
            vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
            vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
            return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
        }
        
        void main() {
            vec2 uv = v_texcoord;
            
            // Wave parameters
            float wave_speed = u_time * 1.5 + u_energy * 3.0;
            float wave_frequency = 8.0 + u_treble * 12.0;
            
            // Multiple rainbow waves
            float wave1 = sin(uv.x * wave_frequency + wave_speed) * 0.5 + 0.5;
            float wave2 = cos(uv.y * wave_frequency * 0.8 + wave_speed * 1.3) * 0.5 + 0.5;
            float wave3 = sin((uv.x + uv.y) * wave_frequency * 0.6 + wave_speed * 0.7) * 0.5 + 0.5;
            
            // Bass affects wave amplitude
            wave1 *= (0.5 + u_bass * 1.5);
            wave2 *= (0.7 + u_bass * 1.0);
            
            // Combine waves for hue
            float hue = (wave1 + wave2 + wave3) / 3.0;
            hue += u_time * 0.2;  // Slow hue rotation
            hue = fract(hue);  // Keep in 0-1 range
            
            // Saturation and value based on audio
            float saturation = 0.8 + u_treble * 0.2;
            float value = 0.6 + u_energy * 0.4;
            
            // Convert HSV to RGB
            vec3 rainbow_color = hsv2rgb(vec3(hue, saturation, value));
            
            // Mix with color scheme for theming
            rainbow_color = mix(rainbow_color, u_color1, 0.1);
            rainbow_color = mix(rainbow_color, u_color2, sin(wave_speed * 0.2) * 0.1);
            rainbow_color = mix(rainbow_color, u_color3, u_bass * 0.1);
            
            // Final intensity
            float intensity = (wave1 * wave2 * wave3) * (0.3 + u_energy * 0.7);
            
            fragColor = vec4(rainbow_color * intensity, intensity * 0.9);
        }
        """
        super().__init__(name, rainbow_shader, z_order)
