#!/usr/bin/env python3
"""
Kawase blur shader for bloom effect.
Implements iterative downsampling blur with diagonal sampling.
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
    """Fragment shader implementing improved Kawase blur with more samples to avoid streaks"""
    return """
    #version 330 core
    in vec2 uv;
    out vec4 fragColor;
    
    uniform sampler2D inputTexture;
    uniform vec2 texelSize;  // 1.0 / texture_dimensions
    uniform float offset;     // Offset multiplier for this pass
    
    void main() {
        // Improved Kawase blur with 9 samples (center + 8 surrounding)
        // This provides better quality and reduces streaking artifacts
        vec2 halfPixel = texelSize * offset;
        
        // Sample center pixel
        vec4 sum = texture(inputTexture, uv);
        
        // Sample 8 surrounding pixels in a square pattern
        sum += texture(inputTexture, uv + vec2(-halfPixel.x, -halfPixel.y));
        sum += texture(inputTexture, uv + vec2(0.0, -halfPixel.y));
        sum += texture(inputTexture, uv + vec2(halfPixel.x, -halfPixel.y));
        sum += texture(inputTexture, uv + vec2(-halfPixel.x, 0.0));
        sum += texture(inputTexture, uv + vec2(halfPixel.x, 0.0));
        sum += texture(inputTexture, uv + vec2(-halfPixel.x, halfPixel.y));
        sum += texture(inputTexture, uv + vec2(0.0, halfPixel.y));
        sum += texture(inputTexture, uv + vec2(halfPixel.x, halfPixel.y));
        
        // Average the 9 samples (center gets double weight effectively)
        fragColor = sum * (1.0 / 9.0);
    }
    """
