import time
from typing import Optional
import numpy as np
from colorama import Fore, Style

from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.vj.renderer import ModernGLRenderer
from parrot.vj.vj_interpretations import create_vj_renderer, get_vj_setup
from parrot.vj.config import CONFIG
from parrot.state import State


class VJDirector:
    """Director for the VJ (Video Jockey) system that runs parallel to the lighting system"""

    def __init__(self, state: State, width: int = None, height: int = None):
        self.state = state

        # Use config defaults if not specified
        if width is None or height is None:
            width, height = CONFIG["default_resolution"]

        self.width = width
        self.height = height

        # VJ renderer and components
        self.vj_renderer: Optional[ModernGLRenderer] = None
        self.current_frame: Optional[np.ndarray] = None

        # Performance tracking
        self.last_render_time = 0.0
        self.render_count = 0
        self.total_render_time = 0.0

        # Initialize VJ system
        self.setup_vj_system()

        # Register event handlers
        self.state.events.on_mode_change += self.on_mode_change

    def setup_vj_system(self):
        """Initialize or reinitialize the VJ system"""
        try:
            # Create interpreter args (similar to main director)
            args = InterpreterArgs(
                hype=50,  # Default hype level for VJ
                allow_rainbows=(
                    self.state.theme.allow_rainbows if self.state.theme else True
                ),
                min_hype=0,
                max_hype=100,
            )

            # Create VJ renderer for current mode
            self.vj_renderer = create_vj_renderer(
                self.state.mode, args, self.width, self.height
            )

            print(
                f"{Fore.MAGENTA}VJ System initialized for {self.state.mode.name} mode{Style.RESET_ALL}"
            )
            self._print_vj_setup()

        except Exception as e:
            print(f"{Fore.RED}Error initializing VJ system: {e}{Style.RESET_ALL}")
            self.vj_renderer = None

    def _print_vj_setup(self):
        """Print the current VJ setup (similar to fixture setup printing)"""
        if not self.vj_renderer or not hasattr(self.vj_renderer, "interpreters"):
            return

        print(f"{Fore.MAGENTA}VJ Setup ({self.width}x{self.height}):{Style.RESET_ALL}")

        # Print layers
        for layer in self.vj_renderer.layers:
            layer_info = f"  Layer {layer.z_order}: {layer}"
            if hasattr(layer, "get_video_info"):
                video_info = layer.get_video_info()
                if video_info.get("current_video"):
                    layer_info += f" [{video_info['current_video']}]"
            print(f"{Fore.CYAN}{layer_info}{Style.RESET_ALL}")

        # Print interpreters
        for interpreter in self.vj_renderer.interpreters:
            print(f"{Fore.YELLOW}  {interpreter}{Style.RESET_ALL}")

        print()

    def on_mode_change(self, mode):
        """Handle mode changes and update VJ system"""
        print(f"{Fore.MAGENTA}VJ mode changed to: {mode.name}{Style.RESET_ALL}")
        self.setup_vj_system()

    def step(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Update the VJ system and render a frame

        Args:
            frame: Audio frame data
            scheme: Current color scheme

        Returns:
            np.ndarray: Rendered VJ frame as RGBA data, or None if VJ is disabled
        """
        if not self.vj_renderer:
            return None

        start_time = time.time()

        try:
            # Update all VJ interpreters
            if hasattr(self.vj_renderer, "interpreters"):
                for interpreter in self.vj_renderer.interpreters:
                    interpreter.step(frame, scheme)

            # Render the frame
            self.current_frame = self.vj_renderer.render_frame(frame, scheme)

            # Update performance metrics
            render_time = time.time() - start_time
            self.total_render_time += render_time
            self.render_count += 1
            self.last_render_time = render_time

            # Log performance if enabled
            if (
                CONFIG["log_performance"] and self.render_count % 60 == 0
            ):  # Log every 60 frames
                avg_time = self.total_render_time / self.render_count
                fps = 1.0 / avg_time if avg_time > 0 else 0
                print(f"VJ Performance: {fps:.1f} fps (avg: {avg_time*1000:.1f}ms)")

            return self.current_frame

        except Exception as e:
            print(f"{Fore.RED}Error in VJ step: {e}{Style.RESET_ALL}")
            return None

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the most recently rendered VJ frame"""
        return self.current_frame

    def resize(self, width: int, height: int):
        """Resize the VJ system"""
        if self.width != width or self.height != height:
            self.width = width
            self.height = height

            if self.vj_renderer:
                self.vj_renderer.resize(width, height)
                print(
                    f"{Fore.MAGENTA}VJ System resized to {width}x{height}{Style.RESET_ALL}"
                )

    def shift_vj_interpreters(self):
        """Shift to new random VJ interpreters and trigger video changes"""
        if not self.vj_renderer:
            return

        try:
            # First, switch videos on all video layers
            self._switch_video_layers()

            # Create new interpreter args
            args = InterpreterArgs(
                hype=50,
                allow_rainbows=(
                    self.state.theme.allow_rainbows if self.state.theme else True
                ),
                min_hype=0,
                max_hype=100,
            )

            # Get new interpreters for current layers
            if hasattr(self.vj_renderer, "layers"):
                layers = self.vj_renderer.layers
                from parrot.vj.vj_interpretations import vj_mode_interpretations

                if self.state.mode in vj_mode_interpretations:
                    mode_config = vj_mode_interpretations[self.state.mode]
                    new_interpreters = mode_config["interpreters"](layers, args)
                    self.vj_renderer.interpreters = new_interpreters

                    print(f"{Fore.MAGENTA}🎬 VJ Scene Shift{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.RED}Error shifting VJ interpreters: {e}{Style.RESET_ALL}")

    def _switch_video_layers(self):
        """Switch to random videos on all video layers"""
        if not self.vj_renderer or not hasattr(self.vj_renderer, "layers"):
            return

        video_layers_switched = 0

        for layer in self.vj_renderer.layers:
            # Check if this is a video layer (either VideoLayer or MockVideoLayer)
            if hasattr(layer, "load_random_video"):
                try:
                    # Try to switch to a different video
                    if layer.load_random_video():
                        video_layers_switched += 1
                        print(
                            f"{Fore.CYAN}  📹 {layer.name}: Switched to new video{Style.RESET_ALL}"
                        )
                    else:
                        print(
                            f"{Fore.YELLOW}  📹 {layer.name}: No new video available{Style.RESET_ALL}"
                        )
                except Exception as e:
                    print(
                        f"{Fore.RED}  📹 {layer.name}: Error switching video - {e}{Style.RESET_ALL}"
                    )

            # Also handle MockVideoLayer switch_video method if it exists
            elif hasattr(layer, "switch_video"):
                try:
                    layer.switch_video()
                    video_layers_switched += 1
                    print(
                        f"{Fore.CYAN}  📹 {layer.name}: Mock video switched{Style.RESET_ALL}"
                    )
                except Exception as e:
                    print(
                        f"{Fore.RED}  📹 {layer.name}: Error switching mock video - {e}{Style.RESET_ALL}"
                    )

        if video_layers_switched > 0:
            print(f"{Fore.GREEN}📹 Video switched{Style.RESET_ALL}")
        # Don't log if no videos to switch

    def get_performance_info(self) -> dict:
        """Get VJ system performance information"""
        if self.render_count == 0:
            return {
                "fps": 0.0,
                "avg_render_time_ms": 0.0,
                "last_render_time_ms": 0.0,
                "frames_rendered": 0,
            }

        avg_time = self.total_render_time / self.render_count
        fps = 1.0 / avg_time if avg_time > 0 else 0

        return {
            "fps": fps,
            "avg_render_time_ms": avg_time * 1000,
            "last_render_time_ms": self.last_render_time * 1000,
            "frames_rendered": self.render_count,
        }

    def get_layer_info(self) -> list:
        """Get information about current VJ layers"""
        if not self.vj_renderer:
            return []

        layer_info = []
        for layer in self.vj_renderer.layers:
            info = {
                "name": layer.name,
                "type": layer.__class__.__name__,
                "z_order": layer.z_order,
                "alpha": layer.get_alpha(),
                "enabled": layer.is_enabled(),
                "size": layer.get_size(),
            }

            # Add layer-specific info
            if hasattr(layer, "get_video_info"):
                info["video_info"] = layer.get_video_info()
            elif hasattr(layer, "text"):
                info["text"] = layer.text
                info["alpha_mask"] = getattr(layer, "alpha_mask", False)
            elif hasattr(layer, "color"):
                info["color"] = layer.color

            layer_info.append(info)

        return layer_info

    def is_enabled(self) -> bool:
        """Check if VJ system is enabled and functional"""
        return self.vj_renderer is not None

    def cleanup(self):
        """Cleanup VJ system resources"""
        if self.vj_renderer:
            # Clean up video layers
            for layer in self.vj_renderer.layers:
                if hasattr(layer, "__del__"):
                    try:
                        layer.__del__()
                    except:
                        pass

            self.vj_renderer = None
            print(f"{Fore.MAGENTA}VJ System cleaned up{Style.RESET_ALL}")

    def __del__(self):
        """Cleanup when director is destroyed"""
        self.cleanup()
