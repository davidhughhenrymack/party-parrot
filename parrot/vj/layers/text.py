import os
from typing import Optional, Tuple, Union
import numpy as np
from parrot.vj.base import LayerBase
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.config import CONFIG
from parrot.vj.modern_text_renderer import get_modern_text_system

from PIL import Image, ImageDraw, ImageFont


class TextLayer(LayerBase):
    """A layer that renders text with various effects and alpha masking"""

    def __init__(
        self,
        text: str = "DEAD SEXY",
        name: str = "text",
        font_path: Optional[str] = None,
        font_size: int = None,
        color: Tuple[int, int, int] = (255, 255, 255),
        alpha_mask: bool = True,
        z_order: int = 2,
    ):
        super().__init__(name, z_order)

        self.text = text
        self.font_path = font_path or CONFIG["text_font_path"]
        self.font_size = font_size or CONFIG["default_font_size"]
        self.font_family = "Arial"  # Default font family
        self.color = color
        self.alpha_mask = alpha_mask  # If True, text acts as alpha mask (transparent text, opaque background)

        # Font and rendering properties
        self.font: Optional["ImageFont.FreeTypeFont"] = None
        self.text_image: Optional[np.ndarray] = None
        self.text_dirty = True  # Flag to regenerate text when needed

        # Text positioning and animation
        self.text_x = 0.5  # Relative position (0-1)
        self.text_y = 0.5
        self.text_rotation = 0.0  # Degrees
        self.text_scale = 1.0

        # Effects
        self.outline_width = 0
        self.outline_color = (0, 0, 0)
        self.shadow_offset = (0, 0)
        self.shadow_color = (0, 0, 0, 128)

        # Initialize font
        self._load_font()

        # Get modern text renderer
        self.text_renderer = get_modern_text_system()

        # Generate initial text image
        self._generate_text_image()

    def _load_font(self):
        """Load the font for text rendering"""
        if not True:
            return

        try:
            if self.font_path and os.path.exists(self.font_path):
                self.font = ImageFont.truetype(self.font_path, self.font_size)
            else:
                # Try to load a default system font
                try:
                    # Common font paths to try
                    font_paths = [
                        "/System/Library/Fonts/Helvetica.ttc",  # macOS
                        "/System/Library/Fonts/Arial.ttf",  # macOS
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                        "/Windows/Fonts/arial.ttf",  # Windows
                        "/Windows/Fonts/calibri.ttf",  # Windows
                    ]

                    for font_path in font_paths:
                        if os.path.exists(font_path):
                            self.font = ImageFont.truetype(font_path, self.font_size)
                            break
                    else:
                        # Fall back to default font
                        self.font = ImageFont.load_default()
                        print(
                            f"TextLayer: Using default font (size may not be accurate)"
                        )

                except Exception as e:
                    print(f"TextLayer: Error loading system fonts: {e}")
                    self.font = ImageFont.load_default()

        except Exception as e:
            print(f"TextLayer: Error loading font {self.font_path}: {e}")
            try:
                self.font = ImageFont.load_default()
            except:
                self.font = None

    def _generate_text_image(self):
        """Generate the text image with current settings"""
        # Try enhanced text renderer first
        if hasattr(self, "text_renderer"):
            try:
                # Determine font family - try to extract from font path
                font_family = None
                if self.font_path and os.path.exists(self.font_path):
                    # Extract font family from path
                    font_name = os.path.splitext(os.path.basename(self.font_path))[0]
                    font_family = font_name

                # Use modern renderer
                modern_result = self.text_renderer.render_text(
                    text=self.text,
                    width=self.width,
                    height=self.height,
                    font_family=font_family or self.font_family,
                    font_size=self.font_size,
                    color=self.color,
                    position=(self.text_x, self.text_y),
                    outline_width=self.outline_width,
                    outline_color=self.outline_color,
                    shadow_offset=self.shadow_offset,
                    shadow_color=(
                        self.shadow_color[:3]
                        if len(self.shadow_color) > 3
                        else self.shadow_color
                    ),
                )

                if modern_result is not None:
                    self.text_image = modern_result
                    self.text_dirty = False
                    return
            except Exception as e:
                print(f"Enhanced text rendering failed: {e}")

        # Fallback to original PIL rendering
        if not True or not self.font:
            # Create a simple fallback text image
            self.text_image = self._create_fallback_text()
            return

        try:
            # Create a temporary image to measure text size
            temp_img = Image.new("RGBA", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)

            # Get text bounding box
            bbox = temp_draw.textbbox((0, 0), self.text, font=self.font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Add padding for effects
            padding = (
                max(
                    self.outline_width * 2,
                    abs(self.shadow_offset[0]),
                    abs(self.shadow_offset[1]),
                )
                + 10
            )
            img_width = text_width + padding * 2
            img_height = text_height + padding * 2

            # Create the text image
            img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Calculate text position (centered with padding)
            text_x = padding
            text_y = padding

            # Draw shadow if enabled
            if self.shadow_offset != (0, 0):
                shadow_x = text_x + self.shadow_offset[0]
                shadow_y = text_y + self.shadow_offset[1]
                draw.text(
                    (shadow_x, shadow_y),
                    self.text,
                    font=self.font,
                    fill=self.shadow_color,
                )

            # Draw outline if enabled
            if self.outline_width > 0:
                for dx in range(-self.outline_width, self.outline_width + 1):
                    for dy in range(-self.outline_width, self.outline_width + 1):
                        if dx != 0 or dy != 0:
                            outline_x = text_x + dx
                            outline_y = text_y + dy
                            draw.text(
                                (outline_x, outline_y),
                                self.text,
                                font=self.font,
                                fill=(*self.outline_color, 255),
                            )

            # Draw main text
            text_color = (*self.color, 255)
            draw.text((text_x, text_y), self.text, font=self.font, fill=text_color)

            # Convert to numpy array
            self.text_image = np.array(img)
            self.text_dirty = False

        except Exception as e:
            print(f"TextLayer: Error generating text image: {e}")
            self.text_image = self._create_fallback_text()

    def _create_fallback_text(self) -> np.ndarray:
        """Create a simple fallback text image when PIL is not available"""
        # Create a simple block text representation
        img = np.zeros((200, 800, 4), dtype=np.uint8)

        # Simple block letters for "DEAD SEXY"
        # This is very basic - just colored blocks
        color = (*self.color, 255)

        # Draw some rectangular blocks to represent text
        block_width = 80
        block_height = 150
        spacing = 20
        start_x = 50
        start_y = 25

        for i, char in enumerate(self.text[:8]):  # Limit to 8 characters
            x = start_x + i * (block_width + spacing)
            if x + block_width < img.shape[1]:
                img[start_y : start_y + block_height, x : x + block_width] = color

        return img

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render the text layer"""
        if not self.enabled:
            return None

        # Regenerate text if needed
        if self.text_dirty:
            self._generate_text_image()

        if self.text_image is None:
            return None

        # Create output texture
        output = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Calculate positioning
        text_h, text_w = self.text_image.shape[:2]
        scaled_w = int(text_w * self.text_scale)
        scaled_h = int(text_h * self.text_scale)

        # Position text
        pos_x = int(self.text_x * self.width - scaled_w // 2)
        pos_y = int(self.text_y * self.height - scaled_h // 2)

        # Ensure text fits within bounds
        pos_x = max(0, min(pos_x, self.width - scaled_w))
        pos_y = max(0, min(pos_y, self.height - scaled_h))

        # Scale text if needed
        text_to_render = self.text_image
        if self.text_scale != 1.0:
            from PIL import Image

            pil_img = Image.fromarray(self.text_image)
            pil_img = pil_img.resize((scaled_w, scaled_h), Image.LANCZOS)
            text_to_render = np.array(pil_img)

        # Apply alpha mask effect if enabled
        if self.alpha_mask:
            # Text becomes transparent (alpha = 0), background becomes opaque black
            # First, create a black background
            output[:, :] = (0, 0, 0, 255)  # Opaque black

            # Then, make areas with text transparent
            end_x = min(pos_x + text_to_render.shape[1], self.width)
            end_y = min(pos_y + text_to_render.shape[0], self.height)

            if end_x > pos_x and end_y > pos_y:
                text_region = text_to_render[: end_y - pos_y, : end_x - pos_x]

                # Use text alpha to create inverse alpha mask
                text_alpha = text_region[:, :, 3]
                inverse_alpha = 255 - text_alpha

                # Apply inverse alpha to output
                output[pos_y:end_y, pos_x:end_x, 3] = inverse_alpha
        else:
            # Normal text rendering - just composite the text onto transparent background
            end_x = min(pos_x + text_to_render.shape[1], self.width)
            end_y = min(pos_y + text_to_render.shape[0], self.height)

            if end_x > pos_x and end_y > pos_y:
                text_region = text_to_render[: end_y - pos_y, : end_x - pos_x]
                output[pos_y:end_y, pos_x:end_x] = text_region

        return output

    def set_text(self, text: str):
        """Update the text content"""
        if self.text != text:
            self.text = text
            self.text_dirty = True

    def set_font_size(self, size: int):
        """Update the font size"""
        if self.font_size != size:
            self.font_size = size
            self._load_font()
            self.text_dirty = True

    def set_color(self, color: Tuple[int, int, int]):
        """Update the text color"""
        if self.color != color:
            self.color = color
            self.text_dirty = True

    def set_position(self, x: float, y: float):
        """Set text position (0-1 relative coordinates)"""
        self.text_x = max(0.0, min(1.0, x))
        self.text_y = max(0.0, min(1.0, y))

    def set_scale(self, scale: float):
        """Set text scale factor"""
        self.text_scale = max(0.1, min(5.0, scale))

    def set_alpha_mask(self, alpha_mask: bool):
        """Enable or disable alpha mask mode"""
        self.alpha_mask = alpha_mask

    def set_outline(self, width: int, color: Tuple[int, int, int] = (0, 0, 0)):
        """Set text outline"""
        if self.outline_width != width or self.outline_color != color:
            self.outline_width = max(0, width)
            self.outline_color = color
            self.text_dirty = True

    def set_shadow(
        self, offset: Tuple[int, int], color: Tuple[int, int, int, int] = (0, 0, 0, 128)
    ):
        """Set text shadow"""
        if self.shadow_offset != offset or self.shadow_color != color:
            self.shadow_offset = offset
            self.shadow_color = color
            self.text_dirty = True

    def set_font_family(self, family_name: str):
        """Set font family by name"""
        if hasattr(self, "text_renderer"):
            font_path = self.text_renderer.font_manager.find_font(family_name)
            if font_path:
                self.font_path = font_path
                self._load_font()
                self.text_dirty = True
                print(f"TextLayer: Using font {family_name} from {font_path}")
            else:
                print(f"TextLayer: Font {family_name} not found")

    def use_horror_font(self):
        """Use the best available horror font"""
        if hasattr(self, "text_renderer"):
            horror_fonts = self.text_renderer.horror_fonts
            if horror_fonts:
                self.set_font_family(horror_fonts[0])
                print(f"TextLayer: Using horror font: {horror_fonts[0]}")
            else:
                print("TextLayer: No horror fonts available, using bold font")
                self.use_bold_font()

    def use_bold_font(self):
        """Use the best available bold font"""
        if hasattr(self, "text_renderer"):
            bold_fonts = self.text_renderer.bold_fonts
            if bold_fonts:
                self.set_font_family(bold_fonts[0])
                print(f"TextLayer: Using bold font: {bold_fonts[0]}")
            else:
                # Try Impact as fallback
                self.set_font_family("Impact")

    def get_available_fonts(self) -> dict:
        """Get information about available fonts"""
        if hasattr(self, "text_renderer"):
            return self.text_renderer.get_font_info()
        return {"error": "Text renderer not available"}

    def cleanup(self):
        """Clean up text resources"""
        pass  # No special cleanup needed for text layers


class MockTextLayer(LayerBase):
    """A mock text layer for when PIL is not available"""

    def __init__(
        self,
        text: str = "DEAD SEXY",
        name: str = "mock_text",
        alpha_mask: bool = True,
        z_order: int = 2,
    ):
        super().__init__(name, z_order)
        self.text = text
        self.alpha_mask = alpha_mask

    def render(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render mock text as colored blocks"""
        if not self.enabled:
            return None

        output = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        if self.alpha_mask:
            # Create black background with transparent text area
            output[:, :] = (0, 0, 0, 255)  # Opaque black

            # Create a simple text-shaped transparent area in the center
            center_x, center_y = self.width // 2, self.height // 2
            text_width, text_height = 600, 100

            x1 = center_x - text_width // 2
            x2 = center_x + text_width // 2
            y1 = center_y - text_height // 2
            y2 = center_y + text_height // 2

            # Make text area transparent
            output[y1:y2, x1:x2, 3] = 0
        else:
            # Simple white text blocks
            center_x, center_y = self.width // 2, self.height // 2
            text_width, text_height = 600, 100

            x1 = center_x - text_width // 2
            x2 = center_x + text_width // 2
            y1 = center_y - text_height // 2
            y2 = center_y + text_height // 2

            output[y1:y2, x1:x2] = (255, 255, 255, 255)

        return output

    def set_text(self, text: str):
        """Mock text setting"""
        self.text = text

    def set_alpha_mask(self, alpha_mask: bool):
        """Mock alpha mask setting"""
        self.alpha_mask = alpha_mask

    def set_scale(self, scale: float):
        """Mock scale setting"""
        self.text_scale = scale

    def set_position(self, x: float, y: float):
        """Mock position setting"""
        self.text_x = x
        self.text_y = y

    def set_color(self, color: tuple):
        """Mock color setting"""
        self.color = color

    def cleanup(self):
        """Clean up mock text resources"""
        pass  # No special cleanup needed


# Use MockTextLayer if PIL is not available
if not True:
    TextLayer = MockTextLayer
