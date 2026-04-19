from __future__ import annotations

from unittest.mock import MagicMock, patch

from parrot.launch_stack import _active_venue_editor_url


def _mock_response(json_payload, ok=True):
    response = MagicMock()
    response.ok = ok
    response.json.return_value = json_payload
    return response


def test_active_venue_editor_url_uses_control_state_id():
    payload = {
        "control_state": {"active_venue_id": "venue-xyz"},
        "active_venue": {"summary": {"id": "other-id"}},
    }
    with patch("parrot.launch_stack.requests.get", return_value=_mock_response(payload)):
        url = _active_venue_editor_url("http://127.0.0.1:4041")
    assert url == "http://127.0.0.1:4041/venues/venue-xyz"


def test_active_venue_editor_url_falls_back_to_active_venue_summary():
    payload = {
        "control_state": {},
        "active_venue": {"summary": {"id": "fallback-id"}},
    }
    with patch("parrot.launch_stack.requests.get", return_value=_mock_response(payload)):
        url = _active_venue_editor_url("http://127.0.0.1:4041")
    assert url == "http://127.0.0.1:4041/venues/fallback-id"


def test_active_venue_editor_url_returns_base_when_no_venue_found():
    payload = {"control_state": {}, "active_venue": None}
    with patch("parrot.launch_stack.requests.get", return_value=_mock_response(payload)):
        url = _active_venue_editor_url("http://127.0.0.1:4041")
    assert url == "http://127.0.0.1:4041"


def test_active_venue_editor_url_returns_base_on_request_error():
    with patch(
        "parrot.launch_stack.requests.get",
        side_effect=RuntimeError("network down"),
    ):
        url = _active_venue_editor_url("http://127.0.0.1:4041")
    assert url == "http://127.0.0.1:4041"


def test_active_venue_editor_url_returns_base_on_non_ok_response():
    response = MagicMock()
    response.ok = False
    with patch("parrot.launch_stack.requests.get", return_value=response):
        url = _active_venue_editor_url("http://127.0.0.1:4041")
    assert url == "http://127.0.0.1:4041"
