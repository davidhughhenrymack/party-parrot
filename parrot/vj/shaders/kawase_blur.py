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
    """Fragment shader implementing Kawase blur with diagonal sampling"""
    return """
    #version 330 core
    in vec2 uv;
    out vec4 fragColor;
    
    uniform sampler2D inputTexture;
    uniform vec2 texelSize;  // 1.0 / texture_dimensions
    uniform float offset;     // Offset multiplier for this pass
    
    void main() {
        // Kawase blur samples 4 diagonal pixels at increasing offsets
        // This creates a nice soft blur with relatively few samples
        vec2 halfPixel = texelSize * offset;
        
        // Sample at 4 diagonal positions
        vec4 sum = vec4(0.0);
        sum += texture(inputTexture, uv + vec2(-halfPixel.x, -halfPixel.y));
        sum += texture(inputTexture, uv + vec2(halfPixel.x, -halfPixel.y));
        sum += texture(inputTexture, uv + vec2(-halfPixel.x, halfPixel.y));
        sum += texture(inputTexture, uv + vec2(halfPixel.x, halfPixel.y));
        
        // Average the samples
        fragColor = sum * 0.25;
    }
    """
