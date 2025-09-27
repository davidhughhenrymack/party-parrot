#!/usr/bin/env python3

import random
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class CircularMask(PostProcessEffectBase):
    """
    A circular mask effect that shows the video only within a circle in the center.
    Everything outside the circle is black. Perfect for chill mode aesthetic.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        radius: float = 0.4,
        softness: float = 0.05,
        center_x: float = 0.5,
        center_y: float = 0.5,
    ):
        """
        Args:
            input_node: The node that provides the video input
            radius: Radius of the circular mask (0.0 = point, 0.5 = full width/height)
            softness: How soft the edge of the circle is (0.0 = hard edge, 0.1 = very soft)
            center_x: X position of circle center (0.0 = left, 1.0 = right)
            center_y: Y position of circle center (0.0 = bottom, 1.0 = top)
        """
        super().__init__(input_node)
        self.radius = radius
        self.softness = softness
        self.center_x = center_x
        self.center_y = center_y

    def generate(self, vibe: Vibe):
        """Configure circular mask parameters based on the vibe"""
        # For chill mode, keep parameters stable and gentle
        # Slight variations for organic feel
        self.radius = random.uniform(0.35, 0.45)  # Keep circle reasonably sized
        self.softness = random.uniform(0.03, 0.08)  # Gentle soft edges

        # Keep center mostly centered with slight variation
        self.center_x = random.uniform(0.48, 0.52)
        self.center_y = random.uniform(0.48, 0.52)

    def print_self(self) -> str:
        """Return class name with current parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="⚪️",
            radius=self.radius,
            softness=self.softness,
        )

    def _get_fragment_shader(self) -> str:
        """Fragment shader for circular mask effect"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float mask_radius;
        uniform float mask_softness;
        uniform vec2 mask_center;
        
        void main() {
            // Sample the input texture
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Calculate distance from current pixel to mask center
            vec2 center_offset = uv - mask_center;
            
            // Adjust for aspect ratio to make a perfect circle
            // Assume 16:9 aspect ratio (adjust center_offset.x)
            center_offset.x *= (16.0 / 9.0);
            
            float distance_from_center = length(center_offset);
            
            // Create smooth circular mask
            float mask_value = 1.0 - smoothstep(
                mask_radius - mask_softness,
                mask_radius + mask_softness,
                distance_from_center
            );
            
            // Apply mask to input color
            color = input_color * mask_value;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set circular mask uniforms"""
        self.shader_program["mask_radius"] = self.radius
        self.shader_program["mask_softness"] = self.softness
        self.shader_program["mask_center"] = (self.center_x, self.center_y)
