#!/usr/bin/env python3
"""Simple test to debug DMX fixture rendering coordinates"""

import os
import tempfile
import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.vj.nodes.fixture_visualization import FixtureVisualization
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import scheme_halloween
from parrot.patch_bay import venues
from parrot.utils.colour import Color
from parrot.state import State
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.vj.vj_director import VJDirector

# Create temp directory to isolate state.json
temp_dir = tempfile.mkdtemp()
original_cwd = os.getcwd()
os.chdir(temp_dir)

try:
    # Create standalone ModernGL context
    ctx = mgl.create_context(standalone=True)

    # Create state with venue
    state = State()
    state.set_venue(venues.dmack)

    # Create position manager
    position_manager = FixturePositionManager(state)

    # Create VJ director
    vj_director = VJDirector(state)

    # Create renderer
    renderer = FixtureVisualization(
        state=state,
        position_manager=position_manager,
        vj_director=vj_director,
        width=1920,
        height=1080,
    )

    # Setup renderer
    renderer.enter(ctx)

    # Print fixture information
    print(f"Number of fixture renderers: {len(renderer.renderers)}")
    print(f"Canvas size: {renderer.canvas_width}x{renderer.canvas_height}")
    print(f"Render size: {renderer.width}x{renderer.height}")
    print()

    for i, fixture_renderer in enumerate(renderer.renderers[:5]):
        fixture = fixture_renderer.fixture
        pos = position_manager.get_fixture_position(fixture)
        if pos:
            x, y, z = pos
            print(f"Fixture {i} ({fixture.id}): pos=({x},{y},{z})")
        else:
            print(f"Fixture {i} ({fixture.id}): NO POSITION")

    # Set some DMX values on fixtures
    for fixture_renderer in renderer.renderers[:3]:
        fixture = fixture_renderer.fixture
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
        pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))[
            :, :, :3
        ]
    else:
        pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

    # Flip vertically
    pixels = np.flipud(pixels)

    # Save to the original working directory
    img = Image.fromarray(pixels, "RGB")
    output_path = os.path.join(original_cwd, "test_output", "dmx_debug.png")
    img.save(output_path)
    print(f"\nSaved test_output/dmx_debug.png")
    print(
        f"Image stats: min={np.min(pixels)}, max={np.max(pixels)}, mean={np.mean(pixels):.2f}"
    )

    # Cleanup
    renderer.exit()
    ctx.release()
finally:
    # Change back to original directory and clean up temp dir
    os.chdir(original_cwd)
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
