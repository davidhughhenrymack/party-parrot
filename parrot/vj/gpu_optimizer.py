"""
GPU Optimization for VJ Shader System
Optimized for Apple Silicon M4 Max with Metal 3 support
"""

import platform
import subprocess
import os
from typing import Dict, Any, Optional, Tuple

import moderngl


class GPUInfo:
    """Detects and provides GPU information"""

    def __init__(self):
        self.gpu_info = self._detect_gpu()
        self.performance_profile = self._determine_performance_profile()

    def _detect_gpu(self) -> Dict[str, Any]:
        """Detect GPU capabilities"""
        gpu_info = {
            "platform": platform.system(),
            "machine": platform.machine(),
            "gpu_type": "unknown",
            "metal_support": False,
            "moderngl_available": True,
            "recommended_resolution": (1920, 1080),
            "max_texture_size": 4096,
            "shader_complexity": "medium",
        }

        if gpu_info["platform"] == "Darwin":  # macOS
            gpu_info.update(self._detect_macos_gpu())
        elif gpu_info["platform"] == "Windows":
            gpu_info.update(self._detect_windows_gpu())
        elif gpu_info["platform"] == "Linux":
            gpu_info.update(self._detect_linux_gpu())

        return gpu_info

    def _detect_macos_gpu(self) -> Dict[str, Any]:
        """Detect macOS GPU using system_profiler"""
        gpu_info = {}

        try:
            # Get display info
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            output = result.stdout

            # Parse GPU information
            if "Apple M" in output:
                # Apple Silicon
                if "M4 Max" in output:
                    gpu_info.update(
                        {
                            "gpu_type": "Apple M4 Max",
                            "metal_support": True,
                            "recommended_resolution": (2560, 1440),
                            "max_texture_size": 8192,
                            "shader_complexity": "ultra",
                            "performance_tier": "flagship",
                        }
                    )
                elif "M4 Pro" in output or "M4" in output:
                    gpu_info.update(
                        {
                            "gpu_type": "Apple M4",
                            "metal_support": True,
                            "recommended_resolution": (1920, 1080),
                            "max_texture_size": 8192,
                            "shader_complexity": "high",
                            "performance_tier": "high",
                        }
                    )
                elif "M3" in output:
                    gpu_info.update(
                        {
                            "gpu_type": "Apple M3",
                            "metal_support": True,
                            "recommended_resolution": (1920, 1080),
                            "max_texture_size": 4096,
                            "shader_complexity": "high",
                            "performance_tier": "high",
                        }
                    )
                elif "M2" in output:
                    gpu_info.update(
                        {
                            "gpu_type": "Apple M2",
                            "metal_support": True,
                            "recommended_resolution": (1920, 1080),
                            "max_texture_size": 4096,
                            "shader_complexity": "medium",
                            "performance_tier": "medium",
                        }
                    )
                elif "M1" in output:
                    gpu_info.update(
                        {
                            "gpu_type": "Apple M1",
                            "metal_support": True,
                            "recommended_resolution": (1680, 1050),
                            "max_texture_size": 4096,
                            "shader_complexity": "medium",
                            "performance_tier": "medium",
                        }
                    )

            # Check for Metal support
            if "Metal" in output:
                gpu_info["metal_support"] = True
                if "Metal 3" in output:
                    gpu_info["metal_version"] = 3
                elif "Metal 2" in output:
                    gpu_info["metal_version"] = 2
                else:
                    gpu_info["metal_version"] = 1

        except Exception as e:
            print(f"GPU detection error: {e}")

        return gpu_info

    def _detect_windows_gpu(self) -> Dict[str, Any]:
        """Detect Windows GPU"""
        # Simplified Windows GPU detection
        return {
            "gpu_type": "Windows GPU",
            "recommended_resolution": (1920, 1080),
            "shader_complexity": "medium",
            "performance_tier": "medium",
        }

    def _detect_linux_gpu(self) -> Dict[str, Any]:
        """Detect Linux GPU"""
        # Simplified Linux GPU detection
        return {
            "gpu_type": "Linux GPU",
            "recommended_resolution": (1920, 1080),
            "shader_complexity": "medium",
            "performance_tier": "medium",
        }

    def _determine_performance_profile(self) -> Dict[str, Any]:
        """Determine optimal performance settings"""
        tier = self.gpu_info.get("performance_tier", "medium")

        profiles = {
            "flagship": {  # M4 Max, RTX 4090, etc.
                "max_concurrent_shaders": 8,
                "shader_resolution": (2560, 1440),
                "target_fps": 60,
                "enable_complex_shaders": True,
                "enable_multi_pass": True,
                "texture_quality": "ultra",
                "anti_aliasing": True,
            },
            "high": {  # M4 Pro, M3, RTX 3080, etc.
                "max_concurrent_shaders": 6,
                "shader_resolution": (1920, 1080),
                "target_fps": 60,
                "enable_complex_shaders": True,
                "enable_multi_pass": True,
                "texture_quality": "high",
                "anti_aliasing": True,
            },
            "medium": {  # M2, M1, GTX 1660, etc.
                "max_concurrent_shaders": 4,
                "shader_resolution": (1680, 1050),
                "target_fps": 60,
                "enable_complex_shaders": True,
                "enable_multi_pass": False,
                "texture_quality": "medium",
                "anti_aliasing": False,
            },
            "low": {  # Integrated graphics, older GPUs
                "max_concurrent_shaders": 2,
                "shader_resolution": (1280, 720),
                "target_fps": 30,
                "enable_complex_shaders": False,
                "enable_multi_pass": False,
                "texture_quality": "low",
                "anti_aliasing": False,
            },
        }

        return profiles.get(tier, profiles["medium"])

    def get_optimal_shader_settings(self) -> Dict[str, Any]:
        """Get optimal shader settings for this GPU"""
        settings = {
            "resolution": self.performance_profile["shader_resolution"],
            "max_concurrent": self.performance_profile["max_concurrent_shaders"],
            "target_fps": self.performance_profile["target_fps"],
            "quality": self.performance_profile["texture_quality"],
            "complex_shaders": self.performance_profile["enable_complex_shaders"],
            "anti_aliasing": self.performance_profile["anti_aliasing"],
        }

        # Apple Silicon optimizations
        if "Apple M" in self.gpu_info.get("gpu_type", ""):
            settings.update(
                {
                    "use_unified_memory": True,
                    "optimize_for_metal": True,
                    "enable_tile_rendering": True,
                    "memory_efficient": True,
                }
            )

        return settings

    def print_gpu_info(self):
        """Print detailed GPU information"""
        print("🖥️ GPU Information:")
        print(f"   Platform: {self.gpu_info['platform']}")
        print(f"   GPU: {self.gpu_info.get('gpu_type', 'Unknown')}")

        if self.gpu_info.get("metal_support"):
            metal_version = self.gpu_info.get("metal_version", "Unknown")
            print(f"   Metal: Version {metal_version}")

        print(
            f"   ModernGL: {'Available' if self.gpu_info['moderngl_available'] else 'Not Available'}"
        )
        print(f"   Performance Tier: {self.gpu_info.get('performance_tier', 'medium')}")

        settings = self.get_optimal_shader_settings()
        print(f"\n⚙️ Optimal Settings:")
        print(f"   Resolution: {settings['resolution'][0]}×{settings['resolution'][1]}")
        print(f"   Max Concurrent Shaders: {settings['max_concurrent']}")
        print(f"   Target FPS: {settings['target_fps']}")
        print(f"   Shader Quality: {settings['quality']}")
        print(
            f"   Complex Shaders: {'Enabled' if settings['complex_shaders'] else 'Disabled'}"
        )

        if settings.get("optimize_for_metal"):
            print(f"   🍎 Apple Silicon Optimizations: Enabled")


class ShaderOptimizer:
    """Optimizes shader performance for the detected GPU"""

    def __init__(self, gpu_info: GPUInfo):
        self.gpu_info = gpu_info
        self.settings = gpu_info.get_optimal_shader_settings()
        self.performance_monitor = PerformanceMonitor()

    def optimize_shader_source(self, shader_source: str) -> str:
        """Optimize shader source for the target GPU"""
        optimized = shader_source

        # Apple Silicon optimizations
        if self.settings.get("optimize_for_metal"):
            optimized = self._optimize_for_metal(optimized)

        # Complexity optimizations
        if not self.settings["complex_shaders"]:
            optimized = self._reduce_complexity(optimized)

        # Performance optimizations
        optimized = self._add_performance_hints(optimized)

        return optimized

    def _optimize_for_metal(self, shader_source: str) -> str:
        """Optimize shader for Apple Metal"""
        # Add precision hints for Metal
        if "#version 330 core" in shader_source:
            # Add precision qualifiers
            optimized = shader_source.replace(
                "#version 330 core", "#version 330 core\nprecision highp float;"
            )
        else:
            optimized = shader_source

        # Metal-specific optimizations
        # Add precision qualifiers and optimization hints
        optimized = optimized.replace(
            "vec2 uv = gl_FragCoord.xy / u_resolution;",
            "highp vec2 uv = gl_FragCoord.xy / u_resolution;",
        )

        return optimized

    def _reduce_complexity(self, shader_source: str) -> str:
        """Reduce shader complexity for lower-end GPUs"""
        optimized = shader_source

        # Reduce iteration counts
        optimized = optimized.replace(
            "for (int i = 0; i < 30", "for (int i = 0; i < 15"
        )
        optimized = optimized.replace(
            "for (int i = 0; i < 20", "for (int i = 0; i < 10"
        )

        # Simplify complex math
        optimized = optimized.replace("* 25.0", "* 15.0")
        optimized = optimized.replace("* 30.0", "* 20.0")

        return optimized

    def _add_performance_hints(self, shader_source: str) -> str:
        """Add performance optimization hints"""
        optimized = shader_source

        # Add early exit conditions
        if "fragColor = vec4(color" in optimized:
            # Add alpha test for early fragment discard
            optimized = optimized.replace(
                "fragColor = vec4(color",
                "if (length(color) < 0.01) discard;\n    fragColor = vec4(color",
            )

        return optimized

    def get_recommended_shader_count(self) -> int:
        """Get recommended number of concurrent shaders"""
        return self.settings["max_concurrent"]

    def get_recommended_resolution(self) -> Tuple[int, int]:
        """Get recommended shader resolution"""
        return self.settings["resolution"]


class PerformanceMonitor:
    """Monitors shader performance and adjusts settings"""

    def __init__(self):
        self.frame_times = []
        self.target_fps = 60
        self.performance_samples = 0
        self.total_render_time = 0.0
        self.dropped_frames = 0

    def record_frame_time(self, frame_time: float):
        """Record a frame render time"""
        self.frame_times.append(frame_time)
        self.total_render_time += frame_time
        self.performance_samples += 1

        # Keep only recent samples
        if len(self.frame_times) > 60:  # Last 60 frames
            old_time = self.frame_times.pop(0)
            self.total_render_time -= old_time

        # Count dropped frames
        if frame_time > (1.0 / self.target_fps) * 1.5:  # 50% over target
            self.dropped_frames += 1

    def get_performance_stats(self) -> Dict[str, float]:
        """Get current performance statistics"""
        if not self.frame_times:
            return {"fps": 0.0, "avg_frame_time": 0.0, "drop_rate": 0.0}

        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        drop_rate = self.dropped_frames / max(1, self.performance_samples)

        return {
            "fps": fps,
            "avg_frame_time": avg_frame_time * 1000,  # ms
            "drop_rate": drop_rate * 100,  # percentage
            "samples": len(self.frame_times),
        }

    def should_reduce_quality(self) -> bool:
        """Check if quality should be reduced"""
        stats = self.get_performance_stats()
        return stats["fps"] < self.target_fps * 0.8 or stats["drop_rate"] > 10.0

    def should_increase_quality(self) -> bool:
        """Check if quality can be increased"""
        stats = self.get_performance_stats()
        return stats["fps"] > self.target_fps * 1.1 and stats["drop_rate"] < 2.0


class AdaptiveShaderManager:
    """Manages shaders with adaptive performance"""

    def __init__(self):
        self.gpu_info = GPUInfo()
        self.optimizer = ShaderOptimizer(self.gpu_info)
        self.performance_monitor = PerformanceMonitor()

        # Adaptive settings
        self.current_shader_count = self.optimizer.get_recommended_shader_count()
        self.current_resolution = self.optimizer.get_recommended_resolution()
        self.quality_level = self.gpu_info.performance_profile["texture_quality"]

        print("🚀 Adaptive Shader Manager initialized:")
        self.gpu_info.print_gpu_info()

    def get_recommended_shader_count(self) -> int:
        """Get recommended number of concurrent shaders"""
        return self.current_shader_count

    def get_recommended_resolution(self) -> Tuple[int, int]:
        """Get recommended shader resolution"""
        return self.current_resolution

    def create_optimized_shader(self, shader_class, name: str, **kwargs) -> Any:
        """Create shader optimized for this GPU"""
        # Remove width/height from kwargs as layers don't take size in constructor
        kwargs.pop("width", None)
        kwargs.pop("height", None)

        # Create shader
        shader = shader_class(name, **kwargs)

        # Optimize shader source if possible
        if hasattr(shader, "shader_source"):
            shader.shader_source = self.optimizer.optimize_shader_source(
                shader.shader_source
            )

        return shader

    def update_performance(self, frame_time: float):
        """Update performance monitoring and adapt if needed"""
        self.performance_monitor.record_frame_time(frame_time)

        # Adaptive quality adjustment
        if self.performance_monitor.performance_samples % 60 == 0:  # Every 60 frames
            if self.performance_monitor.should_reduce_quality():
                self._reduce_quality()
            elif self.performance_monitor.should_increase_quality():
                self._increase_quality()

    def _reduce_quality(self):
        """Reduce quality for better performance"""
        if self.current_shader_count > 2:
            self.current_shader_count -= 1
            print(
                f"🔻 Reducing shader count to {self.current_shader_count} for performance"
            )

        # Reduce resolution if needed
        if self.current_resolution[0] > 1280:
            self.current_resolution = (
                int(self.current_resolution[0] * 0.8),
                int(self.current_resolution[1] * 0.8),
            )
            print(
                f"🔻 Reducing resolution to {self.current_resolution[0]}×{self.current_resolution[1]}"
            )

    def _increase_quality(self):
        """Increase quality when performance allows"""
        max_shaders = self.optimizer.get_recommended_shader_count()

        if self.current_shader_count < max_shaders:
            self.current_shader_count += 1
            print(f"🔺 Increasing shader count to {self.current_shader_count}")

    def get_performance_report(self) -> str:
        """Get performance report"""
        stats = self.performance_monitor.get_performance_stats()

        return f"""
🖥️ GPU Performance Report:
   GPU: {self.gpu_info.gpu_info.get('gpu_type', 'Unknown')}
   Current FPS: {stats['fps']:.1f}
   Avg Frame Time: {stats['avg_frame_time']:.1f}ms
   Drop Rate: {stats['drop_rate']:.1f}%
   Active Shaders: {self.current_shader_count}
   Resolution: {self.current_resolution[0]}×{self.current_resolution[1]}
   Quality: {self.quality_level}
        """


# Apple Silicon specific optimizations
def create_metal_optimized_context():
    """Create ModernGL context optimized for Apple Metal"""
    try:
        # Create context with Apple-specific optimizations
        ctx = moderngl.create_context(standalone=True)

        # Enable optimizations for Apple Silicon
        if hasattr(ctx, "enable"):
            # Enable features that work well with Metal
            pass  # ModernGL handles Metal optimization automatically

        return ctx

    except Exception as e:
        print(f"Failed to create Metal-optimized context: {e}")
        return None


def optimize_for_m4_max():
    """Specific optimizations for Apple M4 Max"""
    return {
        "enable_unified_memory": True,
        "tile_based_rendering": True,
        "max_texture_size": 8192,
        "preferred_format": "RGBA8",
        "enable_compute_shaders": True,
        "memory_bandwidth_gb": 400,  # M4 Max has ~400 GB/s
        "gpu_cores": 40,  # M4 Max has 40 GPU cores
        "recommended_concurrent_shaders": 8,
        "target_resolution": (2560, 1440),
        "enable_hdr": True,
    }


# Global GPU manager instance
_gpu_manager = None


def get_gpu_manager() -> AdaptiveShaderManager:
    """Get the global GPU manager instance"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = AdaptiveShaderManager()
    return _gpu_manager
