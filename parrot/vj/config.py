"""VJ System Configuration"""

import os

# Default VJ configuration
VJ_CONFIG = {
    # Video settings
    "video_directory": os.path.join(
        os.path.dirname(__file__), "..", "..", "media", "videos"
    ),
    "supported_video_formats": [".mp4", ".avi", ".mov", ".mkv", ".webm"],
    "video_loop": True,
    "video_preload": True,
    # Display settings
    "default_resolution": (1920, 1080),
    "target_fps": 60,
    "enable_vsync": True,
    # Memory settings
    "max_video_memory_mb": 512,
    "max_cached_videos": 3,
    # Text settings
    "text_font_path": None,  # Will use system default
    "default_font_size": 144,
    "text_quality": "high",  # 'low', 'medium', 'high'
    # Performance settings
    "use_gpu_acceleration": True,
    "texture_compression": True,
    "async_video_loading": True,
    # Debug settings
    "debug_layers": False,
    "show_fps": False,
    "log_performance": False,
}


# Override with environment variables if set
def load_config():
    """Load configuration with environment variable overrides"""
    config = VJ_CONFIG.copy()

    # Video directory
    if "VJ_VIDEO_DIR" in os.environ:
        config["video_directory"] = os.environ["VJ_VIDEO_DIR"]

    # Resolution
    if "VJ_WIDTH" in os.environ and "VJ_HEIGHT" in os.environ:
        try:
            width = int(os.environ["VJ_WIDTH"])
            height = int(os.environ["VJ_HEIGHT"])
            config["default_resolution"] = (width, height)
        except ValueError:
            pass

    # FPS
    if "VJ_FPS" in os.environ:
        try:
            config["target_fps"] = int(os.environ["VJ_FPS"])
        except ValueError:
            pass

    # Debug mode
    if "VJ_DEBUG" in os.environ:
        debug = os.environ["VJ_DEBUG"].lower() in ("1", "true", "yes")
        config["debug_layers"] = debug
        config["show_fps"] = debug
        config["log_performance"] = debug

    return config


# Global config instance
CONFIG = load_config()
