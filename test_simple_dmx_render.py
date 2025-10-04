#!/usr/bin/env python3
"""Simple test to debug DMX fixture rendering coordinates"""

import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.vj.nodes.dmx_fixture_renderer import DMXFixtureRenderer
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import scheme_halloween
from parrot.patch_bay import venues
from parrot.utils.colour import Color

# Create standalone ModernGL context
ctx = mgl.create_context(standalone=True)

# Create renderer
renderer = DMXFixtureRenderer(
    width=1920,
    height=1080,
    venue=venues.dmack,
)

# Setup renderer
renderer.enter(ctx)

# Print fixture information
print(f"Number of fixtures: {len(renderer.fixtures)}")
print(f"Canvas size: {renderer.canvas_width}x{renderer.canvas_height}")
print(f"Render size: {renderer.width}x{renderer.height}")
print()

for i, fixture in enumerate(renderer.fixtures[:5]):
    if fixture.id in renderer.fixture_positions:
        x, y, w, h = renderer.fixture_positions[fixture.id]
        print(f"Fixture {i} ({fixture.id}): pos=({x},{y}) size=({w}x{h})")
    else:
        print(f"Fixture {i} ({fixture.id}): NO POSITION")

# Set some DMX values on fixtures
for fixture in renderer.fixtures[:3]:
    try:
        fixture.set_dimmer(255)
        if hasattr(fixture, "set_color"):
            fixture.set_color(Color("red"))
    except:
        pass

# Create test frame
frame = Frame({})
scheme = scheme_halloween[0]

# Render
fbo = renderer.render(frame, scheme, ctx)

# Read pixels
texture = fbo.color_attachments[0]
width, height = texture.size
data = texture.read()

# Reshape
bytes_per_pixel = len(data) // (width * height)
if bytes_per_pixel == 4:
    pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))[:, :, :3]
else:
    pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

# Flip vertically
pixels = np.flipud(pixels)

# Save
img = Image.fromarray(pixels, "RGB")
img.save("test_output/dmx_debug.png")
print(f"\nSaved test_output/dmx_debug.png")
print(
    f"Image stats: min={np.min(pixels)}, max={np.max(pixels)}, mean={np.mean(pixels):.2f}"
)

# Cleanup
renderer.exit()
ctx.release()
