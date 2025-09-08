"""
Enhanced text rendering system with professional font support
"""

import os
import platform
from typing import Optional, List, Tuple, Union
import numpy as np

try:
    import skia

    HAS_SKIA = True
except ImportError:
    HAS_SKIA = False
    print("Warning: skia-python not available. Using fallback text rendering.")

try:
    from PIL import Image, ImageDraw, ImageFont

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import fontTools.ttLib

    HAS_FONTTOOLS = True
except ImportError:
    HAS_FONTTOOLS = False

# Modern text rendering using Skia (no pygame conflicts)
HAS_PYGAME = False


class FontManager:
    """Manages system fonts and provides font discovery"""

    def __init__(self):
        self.system_fonts = {}
        self.font_cache = {}
        self._discover_system_fonts()

    def _discover_system_fonts(self):
        """Discover available system fonts"""
        font_dirs = self._get_system_font_directories()

        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                self._scan_font_directory(font_dir)

        print(f"FontManager: Found {len(self.system_fonts)} system fonts")

    def _get_system_font_directories(self) -> List[str]:
        """Get system font directories for different platforms"""
        system = platform.system()

        if system == "Darwin":  # macOS
            return [
                "/System/Library/Fonts",
                "/Library/Fonts",
                os.path.expanduser("~/Library/Fonts"),
                "/System/Library/Assets/com_apple_MobileAsset_Font6",
            ]
        elif system == "Windows":
            return [
                "C:/Windows/Fonts",
                os.path.expanduser("~/AppData/Local/Microsoft/Windows/Fonts"),
            ]
        elif system == "Linux":
            return [
                "/usr/share/fonts",
                "/usr/local/share/fonts",
                os.path.expanduser("~/.fonts"),
                os.path.expanduser("~/.local/share/fonts"),
                "/usr/share/fonts/truetype",
                "/usr/share/fonts/opentype",
            ]
        else:
            return []

    def _scan_font_directory(self, font_dir: str):
        """Scan a directory for font files"""
        font_extensions = {".ttf", ".otf", ".ttc", ".woff", ".woff2"}

        try:
            for root, dirs, files in os.walk(font_dir):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in font_extensions):
                        font_path = os.path.join(root, file)
                        font_name = os.path.splitext(file)[0]

                        # Store font info
                        self.system_fonts[font_name.lower()] = {
                            "path": font_path,
                            "name": font_name,
                            "family": self._extract_font_family(font_path),
                            "style": self._extract_font_style(font_path),
                        }
        except (OSError, PermissionError):
            pass  # Skip directories we can't access

    def _extract_font_family(self, font_path: str) -> str:
        """Extract font family name from font file"""
        if HAS_FONTTOOLS:
            try:
                font = fontTools.ttLib.TTFont(font_path)
                name_table = font["name"]

                # Look for family name (ID 1)
                for record in name_table.names:
                    if (
                        record.nameID == 1 and record.platformID == 3
                    ):  # Microsoft platform
                        return record.string.decode("utf-16-be")
                    elif (
                        record.nameID == 1 and record.platformID == 1
                    ):  # Apple platform
                        return record.string.decode("mac-roman")
            except:
                pass

        # Fallback to filename
        return os.path.splitext(os.path.basename(font_path))[0]

    def _extract_font_style(self, font_path: str) -> str:
        """Extract font style from font file"""
        filename = os.path.basename(font_path).lower()

        if "bold" in filename and "italic" in filename:
            return "bold italic"
        elif "bold" in filename:
            return "bold"
        elif "italic" in filename:
            return "italic"
        elif "light" in filename:
            return "light"
        elif "thin" in filename:
            return "thin"
        elif "black" in filename:
            return "black"
        else:
            return "regular"

    def find_font(self, family_name: str, style: str = "regular") -> Optional[str]:
        """Find a font by family name and style"""
        # Exact match
        search_key = f"{family_name.lower()}_{style.lower()}"
        for font_key, font_info in self.system_fonts.items():
            if (
                font_info["family"].lower() == family_name.lower()
                and font_info["style"].lower() == style.lower()
            ):
                return font_info["path"]

        # Family match with any style
        for font_key, font_info in self.system_fonts.items():
            if font_info["family"].lower() == family_name.lower():
                return font_info["path"]

        # Partial name match
        for font_key, font_info in self.system_fonts.items():
            if family_name.lower() in font_info["family"].lower():
                return font_info["path"]

        return None

    def get_font_families(self) -> List[str]:
        """Get list of available font families"""
        families = set()
        for font_info in self.system_fonts.values():
            families.add(font_info["family"])
        return sorted(list(families))

    def get_font_styles(self, family_name: str) -> List[str]:
        """Get available styles for a font family"""
        styles = set()
        for font_info in self.system_fonts.values():
            if font_info["family"].lower() == family_name.lower():
                styles.add(font_info["style"])
        return sorted(list(styles))

    def get_recommended_fonts(self) -> dict:
        """Get recommended fonts for different purposes"""
        recommendations = {
            "horror": ["Chiller", "Creepster", "Nosifer", "Metal Mania", "Butcherman"],
            "bold": ["Impact", "Arial Black", "Bebas Neue", "Oswald", "Anton"],
            "elegant": ["Times New Roman", "Georgia", "Playfair Display", "Lora"],
            "modern": ["Helvetica", "Arial", "Roboto", "Open Sans", "Lato"],
            "decorative": ["Brush Script MT", "Lucida Handwriting", "Papyrus"],
        }

        available_recommendations = {}
        for category, font_list in recommendations.items():
            available_recommendations[category] = []
            for font_name in font_list:
                if self.find_font(font_name):
                    available_recommendations[category].append(font_name)

        return available_recommendations


class EnhancedTextRenderer:
    """Enhanced text renderer with professional font support"""

    def __init__(self, font_manager: FontManager = None):
        self.font_manager = font_manager or FontManager()
        self.font_cache = {}

    def render_text(
        self,
        text: str,
        font_family: str = None,
        font_size: int = 144,
        font_style: str = "regular",
        color: Tuple[int, int, int] = (255, 255, 255),
        width: int = 1920,
        height: int = 1080,
        outline_width: int = 0,
        outline_color: Tuple[int, int, int] = (0, 0, 0),
        shadow_offset: Tuple[int, int] = (0, 0),
        shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 128),
        alignment: str = "center",
    ) -> Optional[np.ndarray]:
        """Render text with enhanced font support"""

        if not HAS_PIL:
            return self._fallback_text_render(text, width, height, color)

        try:
            # Get font
            font = self._get_font(font_family, font_size, font_style)
            if not font:
                return self._fallback_text_render(text, width, height, color)

            # Create temporary image to measure text
            temp_img = Image.new("RGBA", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)

            # Get text bounding box
            bbox = temp_draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Calculate image size with padding for effects
            padding = (
                max(outline_width * 2, abs(shadow_offset[0]), abs(shadow_offset[1]))
                + 20
            )
            img_width = min(width, text_width + padding * 2)
            img_height = min(height, text_height + padding * 2)

            # Create the text image
            img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Calculate text position based on alignment
            if alignment == "center":
                text_x = (img_width - text_width) // 2
                text_y = (img_height - text_height) // 2
            elif alignment == "left":
                text_x = padding
                text_y = (img_height - text_height) // 2
            elif alignment == "right":
                text_x = img_width - text_width - padding
                text_y = (img_height - text_height) // 2
            else:  # Default to center
                text_x = (img_width - text_width) // 2
                text_y = (img_height - text_height) // 2

            # Draw shadow if enabled
            if shadow_offset != (0, 0):
                shadow_x = text_x + shadow_offset[0]
                shadow_y = text_y + shadow_offset[1]
                draw.text((shadow_x, shadow_y), text, font=font, fill=shadow_color)

            # Draw outline if enabled
            if outline_width > 0:
                for dx in range(-outline_width, outline_width + 1):
                    for dy in range(-outline_width, outline_width + 1):
                        if dx != 0 or dy != 0:
                            outline_x = text_x + dx
                            outline_y = text_y + dy
                            draw.text(
                                (outline_x, outline_y),
                                text,
                                font=font,
                                fill=(*outline_color, 255),
                            )

            # Draw main text
            text_color = (*color, 255)
            draw.text((text_x, text_y), text, font=font, fill=text_color)

            # Convert to numpy array and resize to target dimensions
            text_array = np.array(img)

            # Create final image at target size
            final_img = np.zeros((height, width, 4), dtype=np.uint8)

            # Center the text in the final image
            start_x = (width - img_width) // 2
            start_y = (height - img_height) // 2
            end_x = start_x + img_width
            end_y = start_y + img_height

            # Ensure we don't exceed bounds
            end_x = min(end_x, width)
            end_y = min(end_y, height)

            # Copy text to final image
            final_img[start_y:end_y, start_x:end_x] = text_array[
                : end_y - start_y, : end_x - start_x
            ]

            return final_img

        except Exception as e:
            print(f"Enhanced text rendering failed: {e}")
            return self._fallback_text_render(text, width, height, color)

    def _get_font(
        self, font_family: str, font_size: int, font_style: str
    ) -> Optional["ImageFont.FreeTypeFont"]:
        """Get font object with caching"""
        cache_key = f"{font_family}_{font_size}_{font_style}"

        if cache_key in self.font_cache:
            return self.font_cache[cache_key]

        font = None

        # Try to find the specified font
        if font_family:
            font_path = self.font_manager.find_font(font_family, font_style)
            if font_path:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                except Exception as e:
                    print(f"Failed to load font {font_path}: {e}")

        # Fallback to default fonts
        if not font:
            font = self._get_fallback_font(font_size)

        # Cache the font
        if font:
            self.font_cache[cache_key] = font

        return font

    def _get_fallback_font(self, font_size: int) -> Optional["ImageFont.FreeTypeFont"]:
        """Get fallback font when specified font is not available"""
        # Try common fonts in order of preference
        fallback_fonts = [
            # macOS fonts
            "Helvetica Neue",
            "Arial",
            "Helvetica",
            "Times New Roman",
            # Windows fonts
            "Calibri",
            "Segoe UI",
            "Tahoma",
            "Verdana",
            # Linux fonts
            "DejaVu Sans",
            "Liberation Sans",
            "Ubuntu",
            "Roboto",
        ]

        for font_name in fallback_fonts:
            font_path = self.font_manager.find_font(font_name)
            if font_path:
                try:
                    return ImageFont.truetype(font_path, font_size)
                except:
                    continue

        # Last resort - use PIL default
        try:
            return ImageFont.load_default()
        except:
            return None

    def _fallback_text_render(
        self, text: str, width: int, height: int, color: Tuple[int, int, int]
    ) -> np.ndarray:
        """Fallback text rendering when PIL is not available"""
        # Simple block text representation
        img = np.zeros((height, width, 4), dtype=np.uint8)

        # Calculate block dimensions
        char_width = width // max(1, len(text))
        char_height = height // 3

        start_x = (width - len(text) * char_width) // 2
        start_y = (height - char_height) // 2

        # Draw simple blocks for each character
        for i, char in enumerate(text[: width // char_width]):
            if char != " ":  # Don't draw spaces
                x = start_x + i * char_width
                y = start_y

                # Simple character blocks
                img[y : y + char_height, x : x + char_width // 2] = (*color, 255)

        return img

    def get_font_preview(
        self, font_family: str, sample_text: str = "DEAD SEXY"
    ) -> Optional[np.ndarray]:
        """Generate a preview of a font"""
        return self.render_text(
            sample_text, font_family, font_size=72, width=400, height=100
        )

    def list_horror_fonts(self) -> List[str]:
        """List fonts suitable for horror themes"""
        horror_keywords = [
            "chiller",
            "creepy",
            "horror",
            "gothic",
            "metal",
            "death",
            "blood",
            "skull",
            "bone",
            "nightmare",
            "dark",
            "black",
            "evil",
            "demon",
            "witch",
            "zombie",
            "ghost",
        ]

        horror_fonts = []
        for font_name, font_info in self.font_manager.system_fonts.items():
            family_lower = font_info["family"].lower()
            if any(keyword in family_lower for keyword in horror_keywords):
                horror_fonts.append(font_info["family"])

        # Add commonly available bold fonts good for horror
        bold_fonts = ["Impact", "Arial Black", "Bebas Neue", "Oswald"]
        for font in bold_fonts:
            if self.font_manager.find_font(font):
                horror_fonts.append(font)

        return sorted(list(set(horror_fonts)))

    def list_bold_fonts(self) -> List[str]:
        """List fonts suitable for bold text effects"""
        bold_fonts = []

        # Look for fonts with 'bold' in style or name
        for font_name, font_info in self.font_manager.system_fonts.items():
            if (
                "bold" in font_info["style"].lower()
                or "black" in font_info["style"].lower()
                or "heavy" in font_info["style"].lower()
            ):
                bold_fonts.append(font_info["family"])

        # Add known bold fonts
        known_bold = [
            "Impact",
            "Arial Black",
            "Helvetica Bold",
            "Times Bold",
            "Futura Bold",
            "Avenir Heavy",
            "Montserrat Black",
        ]

        for font in known_bold:
            if self.font_manager.find_font(font):
                bold_fonts.append(font)

        return sorted(list(set(bold_fonts)))


class SystemFontRenderer:
    """System font renderer using PIL + FontTools without pygame"""

    def __init__(self):
        self.system_fonts = []
        self._discover_system_fonts()
        print(f"SystemFontRenderer: Found {len(self.system_fonts)} system fonts")

    def _discover_system_fonts(self):
        """Discover system fonts using FontTools and filesystem"""
        import platform
        import glob

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

        # Find all font files
        font_files = []
        for pattern in font_paths:
            font_files.extend(glob.glob(os.path.expanduser(pattern)))

        # Extract font names
        for font_file in font_files:
            try:
                if HAS_FONTTOOLS:
                    from fontTools.ttLib import TTFont

                    font = TTFont(font_file)
                    name_record = font["name"].getDebugName(1)  # Font family name
                    if name_record:
                        self.system_fonts.append(name_record)
                else:
                    # Fallback: use filename
                    font_name = os.path.splitext(os.path.basename(font_file))[0]
                    self.system_fonts.append(font_name)
            except:
                continue

        # Remove duplicates and sort
        self.system_fonts = sorted(list(set(self.system_fonts)))

    def render_text_pygame(
        self,
        text: str,
        font_name: str = None,
        font_size: int = 144,
        color: Tuple[int, int, int] = (255, 255, 255),
        width: int = 1920,
        height: int = 1080,
        bold: bool = False,
        italic: bool = False,
    ) -> Optional[np.ndarray]:
        """Render text using Pygame's font system"""
        if not self.pygame_available:
            return None

        try:
            # Get font
            if font_name and font_name.lower().replace(" ", "") in self.system_fonts:
                font = pygame.font.SysFont(
                    font_name, font_size, bold=bold, italic=italic
                )
            else:
                # Use default font
                font = pygame.font.Font(None, font_size)

            # Render text
            text_surface = font.render(text, True, color)

            # Convert to numpy array
            text_array = pygame.surfarray.array3d(text_surface)
            text_array = np.transpose(text_array, (1, 0, 2))  # Correct orientation

            # Add alpha channel
            alpha_channel = np.full(
                (text_array.shape[0], text_array.shape[1], 1), 255, dtype=np.uint8
            )
            text_rgba = np.concatenate([text_array, alpha_channel], axis=2)

            # Create final image
            final_img = np.zeros((height, width, 4), dtype=np.uint8)

            # Center the text
            text_h, text_w = text_rgba.shape[:2]
            start_x = (width - text_w) // 2
            start_y = (height - text_h) // 2
            end_x = min(start_x + text_w, width)
            end_y = min(start_y + text_h, height)

            # Copy text to final image
            final_img[start_y:end_y, start_x:end_x] = text_rgba[
                : end_y - start_y, : end_x - start_x
            ]

            return final_img

        except Exception as e:
            print(f"Pygame text rendering failed: {e}")
            return None

    def get_available_fonts(self) -> List[str]:
        """Get list of available system fonts"""
        if self.pygame_available:
            return sorted(self.system_fonts)
        return []


class MultiRendererTextSystem:
    """Text system that tries multiple renderers for best results"""

    def __init__(self):
        self.font_manager = FontManager()
        self.enhanced_renderer = EnhancedTextRenderer(self.font_manager)
        self.pygame_renderer = PygameTextRenderer()

        # Get font recommendations
        self.horror_fonts = self.enhanced_renderer.list_horror_fonts()
        self.bold_fonts = self.enhanced_renderer.list_bold_fonts()

        print(f"MultiRendererTextSystem initialized:")
        print(f"  Horror fonts available: {len(self.horror_fonts)}")
        print(f"  Bold fonts available: {len(self.bold_fonts)}")

        if self.horror_fonts:
            print(f"  Best horror fonts: {self.horror_fonts[:3]}")
        if self.bold_fonts:
            print(f"  Best bold fonts: {self.bold_fonts[:3]}")

    def render_dead_sexy_text(
        self, width: int = 1920, height: int = 1080, style: str = "horror"
    ) -> Optional[np.ndarray]:
        """Render 'DEAD SEXY' text with the best available font"""

        # Choose font based on style
        if style == "horror" and self.horror_fonts:
            font_family = self.horror_fonts[0]  # Best horror font
        elif style == "bold" and self.bold_fonts:
            font_family = self.bold_fonts[0]  # Best bold font
        else:
            # Try some common fonts
            font_family = self._find_best_available_font()

        font_size = max(72, min(200, height // 6))  # Scale with height

        # Try enhanced renderer first
        result = self.enhanced_renderer.render_text(
            "DEAD SEXY",
            font_family=font_family,
            font_size=font_size,
            font_style="bold",
            color=(255, 0, 0),  # Blood red
            width=width,
            height=height,
            outline_width=3,
            outline_color=(0, 0, 0),
            shadow_offset=(5, 5),
            shadow_color=(0, 0, 0, 128),
        )

        if result is not None:
            return result

        # Try Pygame renderer
        result = self.pygame_renderer.render_text_pygame(
            "DEAD SEXY",
            font_name=font_family,
            font_size=font_size,
            color=(255, 0, 0),
            width=width,
            height=height,
            bold=True,
        )

        if result is not None:
            return result

        # Final fallback
        return self.enhanced_renderer._fallback_text_render(
            "DEAD SEXY", width, height, (255, 0, 0)
        )

    def _find_best_available_font(self) -> str:
        """Find the best available font for dramatic text"""
        # Priority order of fonts to try
        preferred_fonts = [
            "Impact",  # Very bold, dramatic
            "Arial Black",  # Bold and readable
            "Helvetica Bold",  # Clean and bold
            "Times Bold",  # Classic bold
            "Bebas Neue",  # Modern condensed
            "Oswald",  # Strong and modern
            "Anton",  # Very bold
            "Helvetica",  # Clean fallback
            "Arial",  # Universal fallback
        ]

        for font in preferred_fonts:
            if self.font_manager.find_font(font):
                return font

        # Return any available font
        families = self.font_manager.get_font_families()
        if families:
            return families[0]

        return None

    def get_font_info(self) -> dict:
        """Get information about available fonts"""
        return {
            "total_fonts": len(self.font_manager.system_fonts),
            "font_families": len(self.font_manager.get_font_families()),
            "horror_fonts": len(self.horror_fonts),
            "bold_fonts": len(self.bold_fonts),
            "pygame_available": self.pygame_renderer.pygame_available,
            "pil_available": HAS_PIL,
            "fonttools_available": HAS_FONTTOOLS,
            "recommended": self.font_manager.get_recommended_fonts(),
        }


# Global text renderer instance
_global_text_renderer = None


def get_text_renderer() -> MultiRendererTextSystem:
    """Get the global text renderer instance"""
    global _global_text_renderer
    if _global_text_renderer is None:
        _global_text_renderer = MultiRendererTextSystem()
    return _global_text_renderer
