"""
Modern text rendering system using Skia
High-performance font rendering with excellent system font support
No pygame conflicts with Tkinter
"""

import os
import platform
import glob
from typing import Optional, Tuple, Dict, Any, List
import numpy as np

try:
    import skia

    HAS_SKIA = True
except ImportError:
    HAS_SKIA = False

try:
    from fontTools.ttLib import TTFont

    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

# Fallback to PIL if Skia unavailable
try:
    from PIL import Image, ImageDraw, ImageFont

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ModernFontManager:
    """Modern font manager using Skia font discovery"""

    def __init__(self):
        self.system_fonts = []
        self.font_paths = {}
        self._discover_fonts()

    def _discover_fonts(self):
        """Discover system fonts using Skia or filesystem"""
        if HAS_SKIA:
            self._discover_with_skia()
        else:
            self._discover_filesystem()

    def _discover_with_skia(self):
        """Use Skia font manager for font discovery"""
        try:
            font_mgr = skia.FontMgr()

            for i in range(font_mgr.countFamilies()):
                family_name = font_mgr.getFamilyName(i)
                if family_name:
                    self.system_fonts.append(family_name)

                    # Try to get font path
                    style_set = font_mgr.createStyleSet(i)
                    if style_set.count() > 0:
                        style = style_set.createTypeface(0)
                        if style:
                            # Store font info for later use
                            self.font_paths[family_name] = style

            self.system_fonts = sorted(list(set(self.system_fonts)))
            print(
                f"ModernFontManager: Discovered {len(self.system_fonts)} fonts with Skia"
            )

        except Exception as e:
            print(f"Skia font discovery error: {e}")
            self._discover_filesystem()

    def _discover_filesystem(self):
        """Fallback filesystem font discovery"""
        font_paths = []

        if platform.system() == "Darwin":  # macOS
            font_paths.extend(
                [
                    "/System/Library/Fonts/*.ttf",
                    "/System/Library/Fonts/*.otf",
                    "/Library/Fonts/*.ttf",
                    "/Library/Fonts/*.otf",
                    "~/Library/Fonts/*.ttf",
                    "~/Library/Fonts/*.otf",
                ]
            )
        elif platform.system() == "Windows":
            font_paths.extend(
                [
                    "C:/Windows/Fonts/*.ttf",
                    "C:/Windows/Fonts/*.otf",
                ]
            )
        else:  # Linux
            font_paths.extend(
                [
                    "/usr/share/fonts/*/*.ttf",
                    "/usr/share/fonts/*/*.otf",
                    "~/.fonts/*.ttf",
                    "~/.fonts/*.otf",
                ]
            )

        # Find font files
        font_files = []
        for pattern in font_paths:
            font_files.extend(glob.glob(os.path.expanduser(pattern)))

        # Extract names
        for font_file in font_files:
            try:
                if HAS_FONTTOOLS:
                    font = TTFont(font_file)
                    name = font["name"].getDebugName(1)
                    if name:
                        self.system_fonts.append(name)
                        self.font_paths[name] = font_file
                else:
                    name = os.path.splitext(os.path.basename(font_file))[0]
                    self.system_fonts.append(name)
                    self.font_paths[name] = font_file
            except:
                continue

        self.system_fonts = sorted(list(set(self.system_fonts)))
        print(
            f"ModernFontManager: Discovered {len(self.system_fonts)} fonts from filesystem"
        )

    def get_fonts(self) -> List[str]:
        """Get list of available font names"""
        return self.system_fonts.copy()

    def find_horror_fonts(self) -> List[str]:
        """Find fonts suitable for horror themes"""
        horror_keywords = [
            "gothic",
            "black",
            "bold",
            "heavy",
            "impact",
            "condensed",
            "horror",
            "scary",
            "creepy",
            "death",
            "blood",
        ]

        horror_fonts = []
        for font in self.system_fonts:
            font_lower = font.lower()
            if any(keyword in font_lower for keyword in horror_keywords):
                horror_fonts.append(font)

        return horror_fonts


class SkiaTextRenderer:
    """High-performance text renderer using Skia"""

    def __init__(self):
        if not HAS_SKIA:
            raise ImportError("Skia not available")

        self.font_manager = ModernFontManager()
        self.typeface_cache = {}

    def _get_typeface(self, font_family: str) -> Optional[skia.Typeface]:
        """Get or create Skia typeface for font family"""
        if font_family in self.typeface_cache:
            return self.typeface_cache[font_family]

        try:
            # Try to create typeface by family name
            typeface = skia.Typeface(font_family)
            if typeface:
                self.typeface_cache[font_family] = typeface
                return typeface
        except:
            pass

        # Try default font
        try:
            typeface = skia.Typeface()
            self.typeface_cache[font_family] = typeface
            return typeface
        except:
            return None

    def render_text(
        self,
        text: str,
        width: int,
        height: int,
        font_family: str = "Arial",
        font_size: int = 72,
        color: Tuple[int, int, int] = (255, 255, 255),
        position: Tuple[float, float] = (0.5, 0.5),
        outline_width: int = 0,
        outline_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_offset: Tuple[int, int] = (0, 0),
        shadow_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> np.ndarray:
        """Render text using Skia"""
        try:
            # Create Skia surface
            surface = skia.Surface(width, height)
            canvas = surface.getCanvas()

            # Clear background
            canvas.clear(skia.Color(0, 0, 0, 0))  # Transparent

            # Get typeface
            typeface = self._get_typeface(font_family)
            if not typeface:
                typeface = skia.Typeface()  # Default font

            # Create font
            font = skia.Font(typeface, font_size)

            # Create paint
            paint = skia.Paint(
                AntiAlias=True, Color=skia.Color(color[0], color[1], color[2], 255)
            )

            # Calculate text position
            text_bounds = font.measureText(text)
            # text_bounds is a tuple (width, height), not an object
            text_width = (
                text_bounds[0] if isinstance(text_bounds, tuple) else text_bounds
            )
            text_height = font_size  # Use font size as height estimate

            x = position[0] * width - text_width / 2
            y = position[1] * height + text_height / 2

            # Draw shadow if specified
            if shadow_offset != (0, 0):
                shadow_paint = skia.Paint(
                    AntiAlias=True,
                    Color=skia.Color(
                        shadow_color[0], shadow_color[1], shadow_color[2], 255
                    ),
                )
                canvas.drawString(
                    text, x + shadow_offset[0], y + shadow_offset[1], font, shadow_paint
                )

            # Draw outline if specified
            if outline_width > 0:
                outline_paint = skia.Paint(
                    AntiAlias=True,
                    Style=skia.Paint.kStroke_Style,
                    StrokeWidth=outline_width,
                    Color=skia.Color(
                        outline_color[0], outline_color[1], outline_color[2], 255
                    ),
                )
                canvas.drawString(text, x, y, font, outline_paint)

            # Draw main text
            canvas.drawString(text, x, y, font, paint)

            # Convert to numpy array
            image = surface.makeImageSnapshot()
            array = np.array(image, copy=False)

            return array

        except Exception as e:
            print(f"Skia text rendering error: {e}")
            return self._fallback_render(
                text, width, height, font_family, font_size, color
            )

    def _fallback_render(
        self,
        text: str,
        width: int,
        height: int,
        font_family: str,
        font_size: int,
        color: Tuple[int, int, int],
    ) -> np.ndarray:
        """Fallback text rendering using PIL"""
        if not HAS_PIL:
            # Create simple colored rectangle as last resort
            texture = np.zeros((height, width, 4), dtype=np.uint8)
            texture[:, :] = [color[0], color[1], color[2], 255]
            return texture

        try:
            # Use PIL fallback
            image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            try:
                font = ImageFont.truetype(font_family, font_size)
            except:
                font = ImageFont.load_default()

            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Center text
            x = (width - text_width) // 2
            y = (height - text_height) // 2

            # Draw text
            draw.text((x, y), text, fill=(*color, 255), font=font)

            return np.array(image)

        except Exception as e:
            print(f"PIL fallback error: {e}")
            # Last resort: solid color
            texture = np.zeros((height, width, 4), dtype=np.uint8)
            texture[height // 3 : 2 * height // 3, width // 4 : 3 * width // 4] = [
                color[0],
                color[1],
                color[2],
                255,
            ]
            return texture

    def get_available_fonts(self) -> List[str]:
        """Get list of available fonts"""
        return self.font_manager.get_fonts()

    def get_horror_fonts(self) -> List[str]:
        """Get fonts suitable for horror themes"""
        return self.font_manager.find_horror_fonts()


class ModernTextSystem:
    """Modern text system using Skia or PIL fallback"""

    def __init__(self):
        self.renderer = None

        if HAS_SKIA:
            try:
                self.renderer = SkiaTextRenderer()
                print("ModernTextSystem: Using Skia renderer")
            except Exception as e:
                print(f"Skia renderer failed: {e}")

        if not self.renderer and HAS_PIL:
            # Create PIL-only renderer
            self.renderer = self._create_pil_renderer()
            print("ModernTextSystem: Using PIL renderer")

        if not self.renderer:
            print("Warning: No text renderer available")

    def _create_pil_renderer(self):
        """Create PIL-only renderer"""

        class PILTextRenderer:
            def __init__(self):
                self.font_manager = ModernFontManager()

            def render_text(self, text: str, width: int, height: int, **kwargs):
                """Simple PIL text rendering"""
                font_family = kwargs.get("font_family", "Arial")
                font_size = kwargs.get("font_size", 72)
                color = kwargs.get("color", (255, 255, 255))

                image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                draw = ImageDraw.Draw(image)

                try:
                    font = ImageFont.truetype(font_family, font_size)
                except:
                    try:
                        font = ImageFont.load_default()
                    except:
                        # Create basic text block
                        texture = np.zeros((height, width, 4), dtype=np.uint8)
                        texture[
                            height // 3 : 2 * height // 3, width // 4 : 3 * width // 4
                        ] = [*color, 255]
                        return texture

                # Get text bounds and center
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (width - text_width) // 2
                y = (height - text_height) // 2

                draw.text((x, y), text, fill=(*color, 255), font=font)
                return np.array(image)

            def get_available_fonts(self):
                return self.font_manager.get_fonts()

            def get_horror_fonts(self):
                return self.font_manager.find_horror_fonts()

        return PILTextRenderer()

    def render_text(self, *args, **kwargs) -> np.ndarray:
        """Render text using available renderer"""
        if self.renderer:
            return self.renderer.render_text(*args, **kwargs)

        # Last resort fallback
        width = kwargs.get("width", 800)
        height = kwargs.get("height", 600)
        color = kwargs.get("color", (255, 255, 255))

        texture = np.zeros((height, width, 4), dtype=np.uint8)
        texture[height // 3 : 2 * height // 3, width // 4 : 3 * width // 4] = [
            *color,
            255,
        ]
        return texture

    def get_available_fonts(self) -> List[str]:
        """Get available fonts"""
        if self.renderer:
            return self.renderer.get_available_fonts()
        return ["Arial", "Helvetica", "Times"]

    def get_horror_fonts(self) -> List[str]:
        """Get horror-themed fonts"""
        if self.renderer:
            return self.renderer.get_horror_fonts()
        return ["Arial Black", "Impact"]


# Global text system instance
_text_system = None


def get_modern_text_system() -> ModernTextSystem:
    """Get the global modern text system instance"""
    global _text_system
    if _text_system is None:
        _text_system = ModernTextSystem()
    return _text_system
