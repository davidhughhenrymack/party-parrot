import os
import random
import time
from typing import Optional, List
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.config import CONFIG

import av


class VideoLayer(LayerBase):
    """A layer that plays video files with optional effects"""

    def __init__(
        self,
        name: str = "video",
        video_dir: Optional[str] = None,
        loop: bool = True,
        z_order: int = 1,
    ):
        super().__init__(name, z_order)

        self.video_dir = video_dir or CONFIG["video_directory"]
        self.loop = loop
        self.current_video_path: Optional[str] = None
        self.container: Optional["av.container.InputContainer"] = None
        self.video_stream: Optional["av.video.VideoStream"] = None
        self.frame_generator = None
        self.current_frame: Optional[np.ndarray] = None
        self.video_fps = 30.0
        self.last_frame_time = 0.0
        self.frame_duration = 1.0 / 30.0  # Default to 30fps

        # Video file management
        self.video_files: List[str] = []
        self.last_video_scan = 0
        self.video_scan_interval = 10.0  # Scan for new videos every 10 seconds

        # Performance tracking
        self.frames_decoded = 0
        self.decode_errors = 0

        # Initialize video list
        self._scan_video_files()

        # Load initial video if available
        if self.video_files:
            self.load_random_video()

    def _scan_video_files(self):
        """Scan the video directory for supported video files"""
        current_time = time.time()

        # Only scan periodically to avoid filesystem overhead
        if current_time - self.last_video_scan < self.video_scan_interval:
            return

        self.last_video_scan = current_time

        if not os.path.exists(self.video_dir):
            print(f"Warning: Video directory does not exist: {self.video_dir}")
            return

        old_count = len(self.video_files)
        self.video_files.clear()

        try:
            for filename in os.listdir(self.video_dir):
                if any(
                    filename.lower().endswith(ext)
                    for ext in CONFIG["supported_video_formats"]
                ):
                    full_path = os.path.join(self.video_dir, filename)
                    if os.path.isfile(full_path):
                        self.video_files.append(full_path)

            if len(self.video_files) != old_count:
                print(
                    f"VideoLayer: Found {len(self.video_files)} video files in {self.video_dir}"
                )

        except OSError as e:
            print(f"Error scanning video directory {self.video_dir}: {e}")

    def load_random_video(self) -> bool:
        """Load a random video from the video directory"""
        if not True:
            return False

        self._scan_video_files()

        if not self.video_files:
            print("No video files found")
            return False

        # Close current video if open
        self._close_current_video()

        # Select random video (avoid repeating the same video if possible)
        available_videos = self.video_files.copy()
        if len(available_videos) > 1 and self.current_video_path:
            try:
                available_videos.remove(self.current_video_path)
            except ValueError:
                pass  # Current video not in list anymore

        new_video_path = random.choice(available_videos)
        return self.load_video(new_video_path)

    def load_video(self, video_path: str) -> bool:
        """Load a specific video file"""
        if not True:
            return False

        try:
            # Close current video
            self._close_current_video()

            # Open new video
            self.container = av.open(video_path)
            self.video_stream = self.container.streams.video[0]

            # Get video properties
            self.video_fps = float(self.video_stream.average_rate)
            self.frame_duration = (
                1.0 / self.video_fps if self.video_fps > 0 else 1.0 / 30.0
            )

            # Create frame generator
            self.frame_generator = self.container.decode(self.video_stream)

            self.current_video_path = video_path
            self.last_frame_time = time.time()
            self.frames_decoded = 0

            print(
                f"VideoLayer: Loaded {os.path.basename(video_path)} ({self.video_fps:.1f} fps)"
            )
            return True

        except Exception as e:
            print(f"Error loading video {video_path}: {e}")
            self.decode_errors += 1
            return False

    def _close_current_video(self):
        """Close the currently open video"""
        if self.container:
            try:
                self.container.close()
            except:
                pass
            self.container = None
            self.video_stream = None
            self.frame_generator = None

    def _get_next_frame(self) -> Optional[np.ndarray]:
        """Get the next frame from the current video"""
        if not self.frame_generator:
            return None

        try:
            frame = next(self.frame_generator)

            # Convert to numpy array
            img = frame.to_ndarray(format="rgba")

            # Resize if necessary
            if img.shape[:2] != (self.height, self.width):
                # Simple nearest-neighbor resize for now
                # TODO: Use proper scaling with interpolation
                from PIL import Image

                pil_img = Image.fromarray(img)
                pil_img = pil_img.resize((self.width, self.height), Image.NEAREST)
                img = np.array(pil_img)

            self.frames_decoded += 1
            return img

        except StopIteration:
            # End of video
            if self.loop:
                # Try to restart the video
                if self.current_video_path and self.load_video(self.current_video_path):
                    return self._get_next_frame()
                else:
                    # If restart fails, try loading a new random video
                    if self.load_random_video():
                        return self._get_next_frame()
            return None

        except Exception as e:
            print(f"Error decoding video frame: {e}")
            self.decode_errors += 1

            # Try to recover by loading a new video
            if self.decode_errors < 5:  # Avoid infinite loops
                if self.load_random_video():
                    return self._get_next_frame()

            return None

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render the current video frame"""
        if not self.enabled or not True:
            return None

        current_time = time.time()

        # Check if it's time for the next frame
        if current_time - self.last_frame_time >= self.frame_duration:
            new_frame = self._get_next_frame()
            if new_frame is not None:
                self.current_frame = new_frame
                self.last_frame_time = current_time

        # Return current frame (may be None if no video loaded)
        return self.current_frame

    def switch_video(self):
        """Switch to a random different video"""
        self.load_random_video()

    def get_video_info(self) -> dict:
        """Get information about the current video"""
        info = {
            "current_video": (
                os.path.basename(self.current_video_path)
                if self.current_video_path
                else None
            ),
            "video_count": len(self.video_files),
            "fps": self.video_fps,
            "frames_decoded": self.frames_decoded,
            "decode_errors": self.decode_errors,
            "has_av": True,
        }
        return info

    def cleanup(self):
        """Clean up video resources"""
        self._close_current_video()

    def __del__(self):
        """Cleanup when the layer is destroyed"""
        self._close_current_video()


class MockVideoLayer(LayerBase):
    """A mock video layer for when PyAV is not available"""

    def __init__(
        self,
        name: str = "mock_video",
        video_dir: str = None,
        loop: bool = True,
        z_order: int = 1,
    ):
        super().__init__(name, z_order)
        self.video_dir = video_dir  # Store for compatibility
        self.loop = loop  # Store for compatibility
        self.frame_count = 0
        self.color = (128, 128, 128)  # Base color for lighting effects
        self.color_cycle = [
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
        ]

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render a mock animated pattern"""
        if not self.enabled:
            return None

        self.frame_count += 1

        # Create a simple animated pattern
        color_index = (self.frame_count // 30) % len(self.color_cycle)
        base_color = self.color_cycle[color_index]

        # Create gradient effect
        texture = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        for y in range(self.height):
            intensity = int(255 * (0.3 + 0.7 * (y / self.height)))
            color = tuple(int(c * intensity / 255) for c in base_color)
            texture[y, :] = (*color, 128)  # Semi-transparent

        return texture

    def switch_video(self):
        """Mock video switching"""
        self.frame_count = 0

    def load_random_video(self) -> bool:
        """Mock video loading"""
        return True

    def get_video_info(self) -> dict:
        """Get mock video info"""
        return {
            "current_video": "mock_video.mp4",
            "video_count": 1,
            "fps": 30.0,
            "frames_decoded": self.frame_count,
            "decode_errors": 0,
            "has_av": False,
        }

    def set_color(self, color: tuple):
        """Set the base color for mock video generation"""
        if len(color) >= 3:
            # Update the color cycle to use variations of the set color
            base_r, base_g, base_b = color[:3]
            self.color_cycle = [
                (base_r, base_g, base_b),
                (min(255, base_r + 30), base_g, base_b),
                (base_r, min(255, base_g + 30), base_b),
                (base_r, base_g, min(255, base_b + 30)),
                (max(0, base_r - 30), max(0, base_g - 30), max(0, base_b - 30)),
                (min(255, base_r + 20), min(255, base_g + 20), min(255, base_b + 20)),
            ]


# Use MockVideoLayer if PyAV is not available
if not True:
    VideoLayer = MockVideoLayer
