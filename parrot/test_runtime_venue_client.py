"""Tests for `RuntimeVenueClient`'s VJ-preview upload plumbing.

The GL render loop hands JPEG bytes to ``queue_vj_preview_jpeg`` every ~200ms.
If that call blocked on the network — as the old `push_vj_preview_jpeg` did —
the whole rendering pipeline would stall whenever the cloud service was slow
or unreachable. These tests pin the non-blocking, latest-wins contract.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from parrot.runtime_venue_client import RuntimeVenueClient
from parrot.state import State


def _make_client() -> RuntimeVenueClient:
    state = State()
    return RuntimeVenueClient(state, "http://127.0.0.1:9")


def test_queue_vj_preview_is_non_blocking_even_when_uploader_is_stalled():
    client = _make_client()

    # Replace the uploader's POST with a blocker we control so we can prove the
    # GL-side queue call does not wait for the HTTP round-trip.
    upload_started = threading.Event()
    release_upload = threading.Event()

    def fake_post(*_args, **_kwargs):
        upload_started.set()
        release_upload.wait(timeout=5.0)

        class _FakeResp:
            def raise_for_status(self):
                return None

        return _FakeResp()

    with patch("parrot.runtime_venue_client.requests.post", side_effect=fake_post):
        client.start()
        try:
            t0 = time.perf_counter()
            client.queue_vj_preview_jpeg(b"\xff\xd8\xff\x00first")
            enqueue_elapsed = time.perf_counter() - t0
            # Must return immediately — we budget 100ms for thread scheduling.
            assert enqueue_elapsed < 0.1, enqueue_elapsed

            assert upload_started.wait(timeout=2.0), "uploader thread never started"

            # Enqueuing more frames while the uploader is blocked must also not
            # block the caller, and must coalesce to the most recent payload.
            for i in range(5):
                client.queue_vj_preview_jpeg(f"frame-{i}".encode())
            with client._vj_preview_cond:
                assert client._vj_preview_latest == b"frame-4", (
                    "latest frame must win; intermediate ones are dropped"
                )
        finally:
            release_upload.set()
            client.stop()


def test_queue_vj_preview_is_a_noop_after_stop():
    client = _make_client()
    client.stop()
    # Should not raise, should not wake any thread, should not touch latest.
    client.queue_vj_preview_jpeg(b"\xff\xd8\xff\x00payload")
    assert client._vj_preview_latest is None


def test_queue_vj_preview_posts_to_expected_endpoint():
    client = _make_client()
    seen: list[tuple[str, bytes, dict]] = []
    done = threading.Event()

    def fake_post(url, data=None, headers=None, timeout=None):
        seen.append((url, data, dict(headers or {})))
        done.set()

        class _FakeResp:
            def raise_for_status(self):
                return None

        return _FakeResp()

    with patch("parrot.runtime_venue_client.requests.post", side_effect=fake_post):
        client.start()
        try:
            client.queue_vj_preview_jpeg(b"\xff\xd8\xff\x00abc")
            assert done.wait(timeout=2.0), "uploader never ran"
        finally:
            client.stop()

    assert len(seen) == 1
    url, data, headers = seen[0]
    assert url == "http://127.0.0.1:9/api/runtime/vj-preview"
    assert data == b"\xff\xd8\xff\x00abc"
    assert headers.get("Content-Type") == "image/jpeg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
