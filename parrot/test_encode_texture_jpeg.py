"""Tests for `_encode_texture_rgb_as_jpeg` in gl_window_app.

The encoder feeds the VJ FBO output to the web preview. Earlier it hard-coded
``RGB`` mode while the VJ pipeline's final framebuffer is RGBA — the 4:3 stride
mismatch sheared every row and produced striped previews. These tests exercise
the encoder over RGB, RGBA, and grayscale textures using a fake moderngl
Texture so we don't need a GL context.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from parrot.gl_window_app import _encode_texture_rgb_as_jpeg


class _FakeTexture:
    """Minimal moderngl.Texture stand-in: `.size`, `.components`, `.read()`."""

    def __init__(self, pixels: np.ndarray):
        assert pixels.ndim == 3
        h, w, c = pixels.shape
        self.size = (w, h)
        self.components = c
        self._pixels = np.ascontiguousarray(pixels.astype(np.uint8))

    def read(self, alignment: int = 1) -> bytes:
        assert alignment == 1, "encoder must request byte-aligned reads"
        return self._pixels.tobytes()


def _make_gradient(width: int, height: int, channels: int) -> np.ndarray:
    xs = np.linspace(0, 255, width, dtype=np.uint8)
    ys = np.linspace(0, 255, height, dtype=np.uint8)
    r = np.broadcast_to(xs, (height, width))
    g = np.broadcast_to(ys[:, None], (height, width))
    b = (r.astype(int) + g.astype(int)) // 2
    stacked = [r, g, b]
    if channels == 4:
        stacked.append(np.full_like(r, 255))
    elif channels == 1:
        stacked = [((r.astype(int) + g.astype(int)) // 2).astype(np.uint8)]
    return np.stack(stacked, axis=-1).astype(np.uint8)


def _decode_jpeg(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def test_encode_rgba_texture_matches_unsheared_source() -> None:
    pixels = _make_gradient(32, 24, 4)
    tex = _FakeTexture(pixels)
    jpeg = _encode_texture_rgb_as_jpeg(tex)
    assert jpeg is not None
    decoded = np.asarray(_decode_jpeg(jpeg))
    # Encoder flips vertically to match GL → screen orientation; compare against
    # the flipped source. JPEG is lossy so we only require rough equality.
    expected = np.flipud(pixels[:, :, :3])
    diff = np.abs(decoded.astype(int) - expected.astype(int)).mean()
    assert diff < 15, f"JPEG RGBA→RGB roundtrip diverged: mean diff {diff:.2f}"


def test_encode_rgb_texture_still_works() -> None:
    pixels = _make_gradient(40, 20, 3)
    tex = _FakeTexture(pixels)
    jpeg = _encode_texture_rgb_as_jpeg(tex)
    assert jpeg is not None
    decoded = np.asarray(_decode_jpeg(jpeg))
    expected = np.flipud(pixels)
    diff = np.abs(decoded.astype(int) - expected.astype(int)).mean()
    assert diff < 15


def test_encode_grayscale_texture_converted_to_rgb() -> None:
    pixels = _make_gradient(16, 16, 1)
    tex = _FakeTexture(pixels)
    jpeg = _encode_texture_rgb_as_jpeg(tex)
    assert jpeg is not None
    decoded = np.asarray(_decode_jpeg(jpeg))
    assert decoded.shape == (16, 16, 3)


def test_encode_unsupported_components_returns_none() -> None:
    pixels = np.zeros((8, 8, 2), dtype=np.uint8)
    tex = _FakeTexture(pixels)
    assert _encode_texture_rgb_as_jpeg(tex) is None


def test_encode_tiny_texture_returns_none() -> None:
    pixels = _make_gradient(1, 8, 4)
    tex = _FakeTexture(pixels)
    assert _encode_texture_rgb_as_jpeg(tex) is None
