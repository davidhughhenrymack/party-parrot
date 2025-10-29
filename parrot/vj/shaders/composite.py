#!/usr/bin/env python3
"""
Composite shader for combining opaque, emissive, and bloom layers.
Final output = opaque + emissive + (bloom * bloom_alpha)
"""

from beartype import beartype


@beartype
def get_vertex_shader() -> str:
    """Vertex shader for fullscreen quad"""
    return """
    #version 330 core
    in vec2 in_position;
    in vec2 in_texcoord;
    out vec2 uv;
    
    void main() {
        gl_Position = vec4(in_position, 0.0, 1.0);
        uv = in_texcoord;
    }
    """


@beartype
def get_fragment_shader() -> str:
    """Fragment shader for compositing three layers"""
    return """
    #version 330 core
    in vec2 uv;
    out vec4 fragColor;
    
    uniform sampler2D opaqueTexture;   // Blinn-Phong lit geometry
    uniform sampler2D emissiveTexture; // Emissive materials (beams, bulbs)
    uniform sampler2D bloomTexture;    // Blurred emissive for glow
    uniform float bloomAlpha;          // Intensity of bloom effect (0.2-0.3)
    
    void main() {
        vec3 opaque = texture(opaqueTexture, uv).rgb;
        vec3 bloom = texture(bloomTexture, uv).rgb;
        
        // Composite: opaque + bloom contribution (no emissive - only bloom makes it to final)
        vec3 final = opaque + (bloom * bloomAlpha);
        
        fragColor = vec4(final, 1.0);
    }
    """
