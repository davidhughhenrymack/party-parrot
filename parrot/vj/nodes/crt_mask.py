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
class CRTMask(PostProcessEffectBase):
    """
    A CRT TV mask effect with fisheye distortion.
    Shows the video within a slightly rounded rectangle (like an old TV screen)
    with barrel distortion to simulate the curved glass of a CRT monitor.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        width: float = 0.67,
        height: float = 0.67,
        corner_radius: float = 0.02,
        center_x: float = 0.5,
        center_y: float = 0.5,
        barrel_distortion: float = 0.22,
        vignette_strength: float = 0.3,
        mask_width: int = 1920,
        mask_height: int = 1080,
    ):
        """
        Args:
            input_node: The node that provides the video input
            width: Width of the TV screen (0.0-1.0)
            height: Height of the TV screen (0.0-1.0)
            corner_radius: Radius of the rounded corners (0.0-0.1, less rounded than vintage film)
            center_x: X position of screen center (0.0 = left, 1.0 = right)
            center_y: Y position of screen center (0.0 = bottom, 1.0 = top)
            barrel_distortion: Strength of fisheye/barrel distortion (0.0-0.5)
            vignette_strength: Strength of edge darkening (0.0-1.0)
            mask_width: Width of the generated mask texture
            mask_height: Height of the generated mask texture
        """
        super().__init__(input_node)
        self.width = width
        self.height = height
        self.corner_radius = corner_radius
        self.center_x = center_x
        self.center_y = center_y
        self.barrel_distortion = barrel_distortion
        self.vignette_strength = vignette_strength
        self.mask_width = mask_width
        self.mask_height = mask_height

        # Mask generation state
        self.mask_texture = None
        self.mask_array = None  # Cache the generated mask array
        self.mask_needs_update = True

    def generate(self, vibe: Vibe):
        """Configure CRT mask parameters based on the vibe"""
        # Keep CRT parameters mostly stable with slight variation (max 2/3 of screen)
        self.width = random.uniform(0.64, 0.70)
        self.height = random.uniform(0.64, 0.70)
        self.corner_radius = random.uniform(0.015, 0.025)

        # Keep center mostly centered
        self.center_x = random.uniform(0.49, 0.51)
        self.center_y = random.uniform(0.49, 0.51)

        # Vary distortion slightly for organic feel
        self.barrel_distortion = random.uniform(0.18, 0.26)
        self.vignette_strength = random.uniform(0.25, 0.35)

        # Mark mask for regeneration and clear cache
        self.mask_needs_update = True
        self.mask_array = None  # Clear cached mask array

    def print_self(self) -> str:
        """Return class name with current parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="📺",
            width=self.width,
            height=self.height,
            distortion=self.barrel_distortion,
        )

    def _generate_mask(self) -> np.ndarray:
        """Generate the CRT TV mask with barrel-distorted curved sides"""
        # Calculate TV screen dimensions in pixels
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

        # Create mask array directly using numpy for barrel distortion
        height, width = self.mask_height, self.mask_width
        mask_array = np.zeros((height, width), dtype=np.uint8)

        # Create coordinate grids normalized to -1 to 1
        y_coords, x_coords = np.mgrid[0:height, 0:width]

        # Normalize coordinates to -1 to 1 range centered at CRT center
        x_norm = (x_coords - center_x_px) / (rect_width_px / 2)
        y_norm = (y_coords - center_y_px) / (rect_height_px / 2)

        # Apply inverse barrel distortion to create bowed mask edges
        # This makes the mask bulge outward like a CRT screen
        r_squared = x_norm**2 + y_norm**2
        distortion_factor = 1.0 - self.barrel_distortion * 0.3  # Scale down for mask
        x_distorted = x_norm * distortion_factor
        y_distorted = y_norm * distortion_factor

        # Calculate distance from center in distorted space
        dist_from_center = np.maximum(np.abs(x_distorted), np.abs(y_distorted))

        # Create mask: 1.0 inside the distorted rectangle, 0.0 outside
        # Apply corner rounding
        corner_radius_norm = corner_radius_px / (rect_width_px / 2)

        # Create rounded rectangle mask in distorted space
        x_edge = np.abs(x_distorted) - (1.0 - corner_radius_norm)
        y_edge = np.abs(y_distorted) - (1.0 - corner_radius_norm)

        # Distance to rounded rectangle
        outside_dist = np.sqrt(np.maximum(x_edge, 0) ** 2 + np.maximum(y_edge, 0) ** 2)
        inside_mask = (dist_from_center <= 1.0) & (outside_dist <= corner_radius_norm)

        # Apply smooth edges with anti-aliasing
        edge_width = 0.02  # Smooth edge transition
        smooth_mask = np.clip(
            1.0 - (outside_dist - corner_radius_norm) / edge_width, 0, 1
        )
        smooth_mask = np.where(dist_from_center <= 1.0, smooth_mask, 0)

        mask_array = (smooth_mask * 255).astype(np.uint8)

        # Apply vignette effect for additional CRT glass curvature
        mask_array = self._apply_vignette(mask_array, left, top, right, bottom)

        return mask_array

    def _apply_vignette(
        self, mask_array: np.ndarray, left: int, top: int, right: int, bottom: int
    ) -> np.ndarray:
        """Apply vignette effect to simulate curved CRT glass"""
        height, width = mask_array.shape
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2

        # Calculate maximum distance from center (to the corners of the screen area)
        max_dist = np.sqrt(((right - left) / 2) ** 2 + ((bottom - top) / 2) ** 2)

        # Create coordinate grids
        y_coords, x_coords = np.mgrid[0:height, 0:width]

        # Calculate distance from center for each pixel
        distances = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)

        # Normalize distances
        normalized_distances = np.clip(distances / max_dist, 0, 1)

        # Apply vignette: darker at edges, full brightness at center
        vignette = 1.0 - (normalized_distances**2 * self.vignette_strength)
        vignette = np.clip(vignette, 0, 1)

        # Apply vignette to mask
        mask_array = (mask_array.astype(np.float32) * vignette).astype(np.uint8)

        return mask_array

    def _get_fragment_shader(self) -> str:
        """Fragment shader with barrel distortion and mask"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform sampler2D mask_texture;
        uniform float barrel_distortion;
        
        vec2 barrel_distort(vec2 coord, float strength) {
            // Center the coordinates
            vec2 cc = coord - 0.5;
            
            // Calculate distance from center
            float dist = length(cc);
            
            // Apply barrel distortion
            float distortion_factor = 1.0 + strength * dist * dist;
            vec2 distorted = cc * distortion_factor;
            
            // Return to 0-1 range
            return distorted + 0.5;
        }
        
        void main() {
            // Apply barrel distortion to UV coordinates
            vec2 distorted_uv = barrel_distort(uv, barrel_distortion);
            
            // Check if distorted UV is within bounds
            if (distorted_uv.x < 0.0 || distorted_uv.x > 1.0 || 
                distorted_uv.y < 0.0 || distorted_uv.y > 1.0) {
                color = vec3(0.0);
                return;
            }
            
            // Sample the input texture with distorted coordinates
            vec3 input_color = texture(input_texture, distorted_uv).rgb;
            
            // Sample the mask texture (single channel, so use .r)
            float mask_value = texture(mask_texture, uv).r;
            
            // Apply mask to input color
            color = input_color * mask_value;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set mask texture and barrel distortion uniforms"""
        # Update mask texture only once per generate() call
        if self.mask_needs_update or self.mask_texture is None:
            self._update_mask_texture()

        # Bind mask texture to texture unit 1
        if self.mask_texture:
            self.mask_texture.use(1)
            self.shader_program["mask_texture"] = 1

        # Set barrel distortion strength
        self.shader_program["barrel_distortion"] = self.barrel_distortion

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
