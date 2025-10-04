#!/usr/bin/env python3

import random
import numpy as np
from PIL import Image, ImageDraw
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class RoundedRectMask(PostProcessEffectBase):
    """
    A rounded rectangle mask effect with decayed film edges.
    Shows the video only within a rounded rectangle with hard noise/decay on the edges
    like old film that has deteriorated over time.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        width: float = 0.7,
        height: float = 0.6,
        corner_radius: float = 0.08,
        center_x: float = 0.5,
        center_y: float = 0.5,
        edge_decay_width: float = 0.03,
        decay_intensity: float = 0.8,
        mask_width: int = 1920,
        mask_height: int = 1080,
    ):
        """
        Args:
            input_node: The node that provides the video input
            width: Width of the rounded rectangle (0.0-1.0)
            height: Height of the rounded rectangle (0.0-1.0)
            corner_radius: Radius of the rounded corners (0.0-0.2)
            center_x: X position of rectangle center (0.0 = left, 1.0 = right)
            center_y: Y position of rectangle center (0.0 = bottom, 1.0 = top)
            edge_decay_width: Width of the decayed edge zone
            decay_intensity: Intensity of the film decay noise (0.0-1.0)
            mask_width: Width of the generated mask texture
            mask_height: Height of the generated mask texture
        """
        super().__init__(input_node)
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.center_x = center_x
        self.center_y = center_y
        self.edge_decay_width = edge_decay_width
        self.decay_intensity = decay_intensity
        self.mask_width = mask_width
        self.mask_height = mask_height

        # Mask generation state
        self.mask_texture = None
        self.mask_array = None  # Cache the generated mask array
        self.mask_needs_update = True

    def generate(self, vibe: Vibe):
        """Configure rounded rectangle mask parameters based on the vibe"""
        # For chill mode, keep parameters stable with slight organic variation
        self.width = random.uniform(0.65, 0.75)
        self.height = random.uniform(0.55, 0.65)
        self.corner_radius = random.uniform(0.06, 0.1)

        # Keep center mostly centered with slight variation
        self.center_x = random.uniform(0.48, 0.52)
        self.center_y = random.uniform(0.48, 0.52)

        # Vary decay parameters for organic film deterioration
        self.edge_decay_width = random.uniform(0.02, 0.04)
        self.decay_intensity = random.uniform(0.7, 0.9)

        # Mark mask for regeneration and clear cache
        self.mask_needs_update = True
        self.mask_array = None  # Clear cached mask array

    def print_self(self) -> str:
        """Return class name with current parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="🧿",
            width=self.width,
            height=self.height,
            radius=self.corner_radius,
        )

    def _generate_mask(self) -> np.ndarray:
        """Generate the confetti mask as a numpy array"""
        # Create a white image (mask starts as all visible)
        mask = Image.new("L", (self.mask_width, self.mask_height), 255)
        draw = ImageDraw.Draw(mask)

        # Calculate rounded rectangle dimensions in pixels
        rect_width_px = int(self.width * self.mask_width)
        rect_height_px = int(self.height * self.mask_height)
        center_x_px = int(self.center_x * self.mask_width)
        center_y_px = int(self.center_y * self.mask_height)
        corner_radius_px = int(
            self.corner_radius * min(self.mask_width, self.mask_height)
        )

        # Calculate rectangle bounds
        left = center_x_px - rect_width_px // 2
        top = center_y_px - rect_height_px // 2
        right = center_x_px + rect_width_px // 2
        bottom = center_y_px + rect_height_px // 2

        # Draw the base rounded rectangle (black = invisible, white = visible)
        # First fill everything with black (invisible)
        draw.rectangle([0, 0, self.mask_width, self.mask_height], fill=0)

        # Then draw the white rounded rectangle (visible area)
        draw.rounded_rectangle(
            [left, top, right, bottom], radius=corner_radius_px, fill=255
        )

        # Convert to numpy array for scanline processing
        mask_array = np.array(mask, dtype=np.uint8)

        # Apply confetti effect using scanline algorithm
        mask_array = self._apply_confetti_scanlines(
            mask_array, left, top, right, bottom
        )

        # Add film sprocket holes along the left edge
        mask_array = self._add_film_sprocket_holes(mask_array, left, top, right, bottom)

        return mask_array

    def _apply_confetti_scanlines(
        self, mask_array: np.ndarray, left: int, top: int, right: int, bottom: int
    ) -> np.ndarray:
        """Apply exactly 100 confetti shapes (circles and rounded rectangles) touching the edge of the rounded rectangle"""
        height, width = mask_array.shape
        corner_radius_px = int(self.corner_radius * min(width, height))

        # Create a stable random seed based on current parameters
        seed = (
            hash(
                (
                    self.width,
                    self.height,
                    self.center_x,
                    self.center_y,
                    self.corner_radius,
                )
            )
            % 2**32
        )
        rng = np.random.RandomState(seed)

        # Find all edge pixels of the rounded rectangle
        edge_pixels = self._find_rounded_rect_edge_pixels(
            mask_array, left, top, right, bottom, corner_radius_px
        )

        if len(edge_pixels) == 0:
            return mask_array

        # Place exactly 100 confetti shapes (mix of circles and rounded rectangles)
        num_confetti = 100
        for i in range(num_confetti):
            # Use deterministic random based on confetti index
            confetti_rng = np.random.RandomState(seed + i)

            # Pick a random edge pixel
            edge_idx = confetti_rng.randint(0, len(edge_pixels))
            edge_x, edge_y = edge_pixels[edge_idx]

            # Calculate normal direction (pointing outward from rectangle)
            normal_x, normal_y = self._calculate_outward_normal(
                edge_x, edge_y, left, top, right, bottom, corner_radius_px
            )

            # Randomly choose between circle and rounded rectangle (50/50 split)
            is_circle = confetti_rng.random() < 0.5

            if is_circle:
                # Random circle size
                size_rand = confetti_rng.random()
                if size_rand > 0.8:
                    radius = confetti_rng.randint(8, 20)  # 20% large
                elif size_rand > 0.5:
                    radius = confetti_rng.randint(4, 12)  # 30% medium
                else:
                    radius = confetti_rng.randint(2, 8)  # 50% small

                # Position circle to touch the edge from outside
                # Place center at radius distance along the outward normal
                circle_x = int(edge_x + normal_x * radius)
                circle_y = int(edge_y + normal_y * radius)

                # Draw the confetti circle (black = invisible)
                self._draw_circle(mask_array, circle_x, circle_y, radius, 0)
            else:
                # Random rounded rectangle size
                size_rand = confetti_rng.random()
                if size_rand > 0.8:
                    # 20% large rectangles
                    rect_width = confetti_rng.randint(12, 24)
                    rect_height = confetti_rng.randint(8, 16)
                elif size_rand > 0.5:
                    # 30% medium rectangles
                    rect_width = confetti_rng.randint(8, 16)
                    rect_height = confetti_rng.randint(6, 12)
                else:
                    # 50% small rectangles
                    rect_width = confetti_rng.randint(4, 12)
                    rect_height = confetti_rng.randint(3, 8)

                # Corner radius proportional to size (but smaller than circle radius)
                corner_radius = min(rect_width, rect_height) // 4

                # Position rectangle to touch the edge from outside
                # Use the larger dimension as the "radius" for positioning
                positioning_radius = max(rect_width, rect_height) // 2
                rect_x = int(edge_x + normal_x * positioning_radius)
                rect_y = int(edge_y + normal_y * positioning_radius)

                # Draw the confetti rounded rectangle (black = invisible)
                self._draw_rounded_rect(
                    mask_array,
                    rect_x,
                    rect_y,
                    rect_width,
                    rect_height,
                    corner_radius,
                    0,
                )

        return mask_array

    def _find_rounded_rect_edge_pixels(
        self,
        mask_array: np.ndarray,
        left: int,
        top: int,
        right: int,
        bottom: int,
        corner_radius: int,
    ) -> list[tuple[int, int]]:
        """Find all pixels on the edge of the rounded rectangle"""
        edge_pixels = []
        height, width = mask_array.shape

        # Sample edge pixels by checking transitions from white to black
        # We'll sample every few pixels to get a good distribution
        sample_step = max(
            1, min(width, height) // 200
        )  # Sample ~200 points around perimeter

        # Top edge (including rounded corners)
        for x in range(left, right + 1, sample_step):
            for y in range(
                max(0, top - corner_radius), min(height, bottom + corner_radius)
            ):
                if 0 <= x < width and 0 <= y < height:
                    if mask_array[y, x] == 255:  # White pixel (inside)
                        # Check if it's on the edge (has black neighbor)
                        if self._is_edge_pixel(mask_array, x, y):
                            edge_pixels.append((x, y))
                        break

        # Bottom edge
        for x in range(left, right + 1, sample_step):
            for y in range(
                min(height - 1, bottom + corner_radius),
                max(-1, top - corner_radius),
                -1,
            ):
                if 0 <= x < width and 0 <= y < height:
                    if mask_array[y, x] == 255:  # White pixel (inside)
                        if self._is_edge_pixel(mask_array, x, y):
                            edge_pixels.append((x, y))
                        break

        # Left edge
        for y in range(top, bottom + 1, sample_step):
            for x in range(
                max(0, left - corner_radius), min(width, right + corner_radius)
            ):
                if 0 <= x < width and 0 <= y < height:
                    if mask_array[y, x] == 255:  # White pixel (inside)
                        if self._is_edge_pixel(mask_array, x, y):
                            edge_pixels.append((x, y))
                        break

        # Right edge
        for y in range(top, bottom + 1, sample_step):
            for x in range(
                min(width - 1, right + corner_radius), max(-1, left - corner_radius), -1
            ):
                if 0 <= x < width and 0 <= y < height:
                    if mask_array[y, x] == 255:  # White pixel (inside)
                        if self._is_edge_pixel(mask_array, x, y):
                            edge_pixels.append((x, y))
                        break

        return edge_pixels

    def _is_edge_pixel(self, mask_array: np.ndarray, x: int, y: int) -> bool:
        """Check if a white pixel is on the edge (has at least one black neighbor)"""
        height, width = mask_array.shape

        # Check 8-connected neighbors
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if mask_array[ny, nx] == 0:  # Black neighbor
                        return True
        return False

    def _calculate_outward_normal(
        self,
        x: int,
        y: int,
        left: int,
        top: int,
        right: int,
        bottom: int,
        corner_radius: int,
    ) -> tuple[float, float]:
        """Calculate the outward normal direction from an edge pixel"""
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2

        # Simple approach: normal points away from rectangle center
        dx = x - center_x
        dy = y - center_y

        # Normalize
        length = (dx * dx + dy * dy) ** 0.5
        if length > 0:
            return dx / length, dy / length
        else:
            return 1.0, 0.0  # Default to right if at center

    def _draw_circle(
        self,
        mask_array: np.ndarray,
        center_x: int,
        center_y: int,
        radius: int,
        value: int,
    ):
        """Draw a circle on the mask array"""
        height, width = mask_array.shape

        # Use circle equation to draw
        for y in range(max(0, center_y - radius), min(height, center_y + radius + 1)):
            for x in range(
                max(0, center_x - radius), min(width, center_x + radius + 1)
            ):
                distance_sq = (x - center_x) ** 2 + (y - center_y) ** 2
                if distance_sq <= radius**2:
                    mask_array[y, x] = value

    def _draw_rounded_rect(
        self,
        mask_array: np.ndarray,
        center_x: int,
        center_y: int,
        width: int,
        height: int,
        corner_radius: int,
        value: int,
    ):
        """Draw a rounded rectangle on the mask array"""
        array_height, array_width = mask_array.shape

        # Calculate bounds
        left = center_x - width // 2
        right = center_x + width // 2
        top = center_y - height // 2
        bottom = center_y + height // 2

        # Clamp corner radius to be reasonable
        max_radius = min(width, height) // 2
        corner_radius = min(corner_radius, max_radius)

        # Draw the rounded rectangle
        for y in range(max(0, top), min(array_height, bottom + 1)):
            for x in range(max(0, left), min(array_width, right + 1)):
                # Check if we're in a corner region
                in_corner = False
                corner_center_x = corner_center_y = 0

                # Top-left corner
                if x < left + corner_radius and y < top + corner_radius:
                    corner_center_x = left + corner_radius
                    corner_center_y = top + corner_radius
                    in_corner = True
                # Top-right corner
                elif x > right - corner_radius and y < top + corner_radius:
                    corner_center_x = right - corner_radius
                    corner_center_y = top + corner_radius
                    in_corner = True
                # Bottom-left corner
                elif x < left + corner_radius and y > bottom - corner_radius:
                    corner_center_x = left + corner_radius
                    corner_center_y = bottom - corner_radius
                    in_corner = True
                # Bottom-right corner
                elif x > right - corner_radius and y > bottom - corner_radius:
                    corner_center_x = right - corner_radius
                    corner_center_y = bottom - corner_radius
                    in_corner = True

                if in_corner:
                    # Check if we're inside the corner circle
                    distance_sq = (x - corner_center_x) ** 2 + (
                        y - corner_center_y
                    ) ** 2
                    if distance_sq <= corner_radius**2:
                        mask_array[y, x] = value
                else:
                    # We're in the main rectangle area (not in corners)
                    mask_array[y, x] = value

    def _add_film_sprocket_holes(
        self, mask_array: np.ndarray, left: int, top: int, right: int, bottom: int
    ) -> np.ndarray:
        """Add a vertical line of small black circles along the left inside edge to simulate film sprocket holes"""
        height = bottom - top

        # Sprocket hole parameters
        hole_radius = 4  # Small circles
        hole_spacing = 30  # Vertical spacing between holes
        left_offset = 15  # Distance from left edge (inside the mask)

        # Calculate number of holes that fit vertically
        num_holes = height // hole_spacing

        # Calculate starting y position to center the holes vertically
        start_y = top + (height - (num_holes - 1) * hole_spacing) // 2

        # Draw each sprocket hole
        hole_x = left + left_offset
        for i in range(num_holes):
            hole_y = start_y + i * hole_spacing
            self._draw_circle(mask_array, hole_x, hole_y, hole_radius, 0)

        return mask_array

    def _get_fragment_shader(self) -> str:
        """Simple fragment shader that uses the pre-generated mask texture"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform sampler2D mask_texture;
        
        void main() {
            // Sample the input texture
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Sample the mask texture (single channel, so use .r)
            float mask_value = texture(mask_texture, uv).r;
            
            // Apply mask to input color
            color = input_color * mask_value;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set mask texture uniform and update mask if needed"""
        # Update mask texture only once per generate() call
        # The mask is generated and cached until the next generate() call
        if self.mask_needs_update or self.mask_texture is None:
            self._update_mask_texture()

        # Bind mask texture to texture unit 1
        if self.mask_texture:
            self.mask_texture.use(1)
            self.shader_program["mask_texture"] = 1

    def _update_mask_texture(self):
        """Generate and upload the mask texture to OpenGL"""
        # Generate the mask as numpy array only if not cached
        if self.mask_array is None:
            self.mask_array = self._generate_mask()

        # Get OpenGL context from shader program
        context = self.shader_program.ctx

        # Create or update the mask texture
        if self.mask_texture:
            self.mask_texture.release()

        # Create single-channel texture (grayscale mask)
        # Normalize to 0.0-1.0 range for OpenGL
        mask_normalized = self.mask_array.astype(np.float32) / 255.0

        self.mask_texture = context.texture(
            (self.mask_width, self.mask_height),
            1,  # Single channel
            mask_normalized.tobytes(),
            dtype="f4",
        )

        self.mask_needs_update = False
