import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from parrot.api.web_server import (
    app,
    get_local_ip,
    get_mode,
    set_mode,
    get_vj_mode,
    set_vj_mode,
    set_effect,
    start_web_server,
    state_instance,
)
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode
from parrot.state import State


class TestWebServer:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        app.config["TESTING"] = True
        self.client = app.test_client()

        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = None

    def test_get_local_ip_success(self):
        """Test get_local_ip returns valid IP address."""
        with patch("socket.socket") as mock_socket:
            mock_sock = Mock()
            mock_sock.getsockname.return_value = ("192.168.1.100", 0)
            mock_socket.return_value = mock_sock

            ip = get_local_ip()
            assert ip == "192.168.1.100"
            mock_sock.connect.assert_called_once_with(("8.8.8.8", 1))
            mock_sock.close.assert_called_once()

    def test_get_local_ip_exception(self):
        """Test get_local_ip falls back to localhost on exception."""
        with patch("socket.socket") as mock_socket:
            mock_socket.side_effect = Exception("Network error")

            ip = get_local_ip()
            assert ip == "127.0.0.1"

    def test_get_mode_no_state(self):
        """Test GET /api/mode when state is not initialized."""
        response = self.client.get("/api/mode")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["mode"] is None
        assert "available_modes" in data
        assert isinstance(data["available_modes"], list)

    def test_get_mode_with_state(self):
        """Test GET /api/mode when state is initialized."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        mock_state.mode = Mode.rave
        web_server_module.state_instance = mock_state

        response = self.client.get("/api/mode")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["mode"] == "rave"
        assert "available_modes" in data

    def test_set_mode_no_state(self):
        """Test POST /api/mode when state is not initialized."""
        response = self.client.post(
            "/api/mode", json={"mode": "rave"}, content_type="application/json"
        )
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_set_mode_missing_parameter(self):
        """Test POST /api/mode with missing mode parameter."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()

        response = self.client.post(
            "/api/mode", json={}, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_set_mode_invalid_mode(self):
        """Test POST /api/mode with invalid mode."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()

        response = self.client.post(
            "/api/mode", json={"mode": "invalid_mode"}, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_set_mode_valid_mode(self):
        """Test POST /api/mode with valid mode."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/mode", json={"mode": "rave"}, content_type="application/json"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["mode"] == "rave"
        mock_state.set_mode_thread_safe.assert_called_once_with(Mode.rave)

    def test_set_effect_no_state(self):
        """Test POST /api/effect when state is not initialized."""
        response = self.client.post(
            "/api/effect", json={"effect": "strobe"}, content_type="application/json"
        )
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_set_effect_missing_parameter(self):
        """Test POST /api/effect with missing effect parameter."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()

        response = self.client.post(
            "/api/effect", json={}, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_set_effect_valid_effect(self):
        """Test POST /api/effect with valid effect."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/effect", json={"effect": "strobe"}, content_type="application/json"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["effect"] == "strobe"
        mock_state.set_effect_thread_safe.assert_called_once_with("strobe", value=None)

    def test_set_effect_explicit_value(self):
        """POST body may include ``value`` for hold / release (mobile remote)."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/effect",
            json={"effect": "pulse", "value": 0},
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        mock_state.set_effect_thread_safe.assert_called_once_with("pulse", value=0.0)

    def test_set_effect_exception(self):
        """Test POST /api/effect when set_effect_thread_safe raises exception."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        mock_state.set_effect_thread_safe.side_effect = Exception("Effect error")
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/effect", json={"effect": "strobe"}, content_type="application/json"
        )
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_index_route(self):
        """Test GET / serves index.html."""
        with patch("parrot.api.web_server.send_from_directory") as mock_send:
            mock_send.return_value = "HTML content"

            response = self.client.get("/")
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_static_files_route(self):
        """Test GET /<path> serves static files."""
        with patch("parrot.api.web_server.send_from_directory") as mock_send:
            mock_send.return_value = "CSS content"

            response = self.client.get("/styles.css")
            assert response.status_code == 200
            mock_send.assert_called_once()

    def test_config_route(self):
        response = self.client.get("/api/config")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["editor_port"] == 4041

    @patch("threading.Thread")
    def test_start_web_server(self, mock_thread):
        """Test start_web_server function."""
        mock_state = Mock()

        start_web_server(mock_state, port=8080)

        import parrot.api.web_server as web_server_module

        assert web_server_module.state_instance == mock_state

        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

    def test_app_configuration(self):
        """Test Flask app configuration."""
        assert isinstance(app, Flask)
        assert app.name == "parrot.api.web_server"

    def test_get_vj_mode_no_state(self):
        """Test GET /api/vj_mode when state is not initialized."""
        response = self.client.get("/api/vj_mode")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["vj_mode"] is None
        assert "available_vj_modes" in data
        assert isinstance(data["available_vj_modes"], list)

    def test_get_vj_mode_with_state(self):
        """Test GET /api/vj_mode when state is initialized."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        mock_state.vj_mode = VJMode.prom_thunderbunny
        web_server_module.state_instance = mock_state

        response = self.client.get("/api/vj_mode")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["vj_mode"] == "prom_thunderbunny"
        assert "available_vj_modes" in data

    def test_set_vj_mode_no_state(self):
        """Test POST /api/vj_mode when state is not initialized."""
        response = self.client.post(
            "/api/vj_mode",
            json={"vj_mode": "prom_wufky"},
            content_type="application/json",
        )
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_set_vj_mode_missing_parameter(self):
        """Test POST /api/vj_mode with missing vj_mode parameter."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()

        response = self.client.post(
            "/api/vj_mode", json={}, content_type="application/json"
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_set_vj_mode_invalid_mode(self):
        """Test POST /api/vj_mode with invalid vj_mode."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()

        response = self.client.post(
            "/api/vj_mode",
            json={"vj_mode": "invalid_mode"},
            content_type="application/json",
        )
        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_set_vj_mode_valid_mode(self):
        """Test POST /api/vj_mode with valid vj_mode."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/vj_mode",
            json={"vj_mode": "prom_mayhem"},
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["vj_mode"] == "prom_mayhem"
        mock_state.set_vj_mode_thread_safe.assert_called_once_with(VJMode.prom_mayhem)
