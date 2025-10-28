#!/usr/bin/env python3
"""Debug test to check if render_emissive is being called"""

import moderngl as mgl
from parrot.vj.nodes.fixture_visualization import FixtureVisualization
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import scheme_halloween
from parrot.patch_bay import venues
from parrot.state import State
from parrot.utils.colour import Color
from parrot.fixtures.position_manager import FixturePositionManager

# Create context
try:
    ctx = mgl.create_context(standalone=True, backend="egl")
except Exception:
    ctx = mgl.create_context(standalone=True)

# Create state and position manager
state = State()
state.set_venue(venues.mtn_lotus)
position_manager = FixturePositionManager(state)

# Create renderer
renderer = FixtureVisualization(
    state=state,
    position_manager=position_manager,
    width=1920,
    height=1080,
    canvas_width=1200,
    canvas_height=1200,
)

renderer.enter(ctx)

# Check internal state
print(f"\nHas _fixtures: {hasattr(renderer, '_fixtures')}")
if hasattr(renderer, "_fixtures"):
    print(f"Number of _fixtures: {len(renderer._fixtures)}")
    if len(renderer._fixtures) > 0:
        print(f"First fixture type: {type(renderer._fixtures[0])}")

print(f"Number of renderers: {len(renderer.renderers)}")
print(f"room_renderer initialized: {renderer.room_renderer is not None}")

# Set first few fixtures bright (on the actual fixture objects)
if hasattr(renderer, "_fixtures") and len(renderer._fixtures) > 0:
    print(f"\nSetting brightness on first 3 fixtures...")
    for i, fixture in enumerate(renderer._fixtures[:3]):
        fixture.set_dimmer(255)
        if hasattr(fixture, "set_color"):
            colors = [Color("red"), Color("green"), Color("blue")]
            fixture.set_color(colors[i % len(colors)])
        print(f"  Set fixture {i}: dimmer=255, color={['red','green','blue'][i % 3]}")

# Render
frame = Frame({})
scheme = scheme_halloween[0]

print("\n=== Before rendering ===")
print(f"Number of renderers to render emissive: {len(renderer.renderers)}")

# Manually call render_emissive on first renderer to debug
canvas_size = (1200.0, 1200.0)
if len(renderer.renderers) > 0:
    print(f"\nManually calling render_emissive on first renderer...")
    try:
        renderer.emissive_framebuffer.use()
        ctx.clear(0.0, 0.0, 0.0)
        ctx.enable(ctx.BLEND)
        ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE

        renderer.renderers[0].render_emissive(ctx, canvas_size, frame)
        print("✓ render_emissive called successfully")

        # Check result immediately
        data = renderer.emissive_texture.read()
        pixels = np.frombuffer(data, dtype=np.uint8)
        non_zero = np.sum(pixels > 0)
        print(f"Emissive pixels after manual call: {non_zero}")

        ctx.disable(ctx.BLEND)
    except Exception as e:
        print(f"✗ Error calling render_emissive: {e}")
        import traceback

        traceback.print_exc()

print("\n=== Full render ===")
fbo = renderer.render(frame, scheme, ctx)

# Check emissive buffer
import numpy as np

data = renderer.emissive_texture.read()
pixels = np.frombuffer(data, dtype=np.uint8)
non_zero = np.sum(pixels > 0)
print(f"\nEmissive pixels > 0: {non_zero}")
print(f"Emissive max value: {np.max(pixels)}")

renderer.exit()
ctx.release()
