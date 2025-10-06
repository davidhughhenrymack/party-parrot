import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from parrot.api.web_server import (
    app,
    get_local_ip,
    get_mode,
    set_mode,
    get_vj_mode,
    set_vj_mode,
    deploy_hype,
    get_hype_status,
    get_manual_dimmer,
    set_manual_dimmer,
    set_effect,
    start_web_server,
    state_instance,
    director_instance,
)
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode
from parrot.state import State


class TestWebServer:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Reset global state
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = None
        web_server_module.director_instance = None
        web_server_module.last_hype_time = 0

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

    def test_deploy_hype_no_state(self):
        """Test POST /api/hype when state is not initialized."""
        response = self.client.post("/api/hype")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_deploy_hype_no_director(self):
        """Test POST /api/hype when director is not initialized."""
        import parrot.api.web_server as web_server_module

        web_server_module.state_instance = Mock()
        web_server_module.director_instance = None

        response = self.client.post("/api/hype")
        assert response.status_code == 500

        data = json.loads(response.data)
        assert "error" in data

    def test_deploy_hype_success(self):
        """Test POST /api/hype with valid state and director."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        mock_director = Mock()
        web_server_module.state_instance = mock_state
        web_server_module.director_instance = mock_director

        response = self.client.post("/api/hype")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert "message" in data
        assert "duration" in data
        mock_director.deploy_hype.assert_called_once()

    def test_get_hype_status_inactive(self):
        """Test GET /api/hype/status when hype is inactive."""
        response = self.client.get("/api/hype/status")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["active"] is False
        assert data["remaining"] == 0

    def test_get_hype_status_active(self):
        """Test GET /api/hype/status when hype is active."""
        import parrot.api.web_server as web_server_module

        web_server_module.last_hype_time = time.time() - 2  # 2 seconds ago

        response = self.client.get("/api/hype/status")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["active"] is True
        assert data["remaining"] > 0
        assert data["remaining"] <= 8  # HYPE_DURATION

    def test_get_manual_dimmer_no_state(self):
        """Test GET /api/manual_dimmer when state is not initialized."""
        response = self.client.get("/api/manual_dimmer")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["value"] == 0
        assert data["supported"] is False

    def test_get_manual_dimmer_with_state(self):
        """Test GET /api/manual_dimmer when state is initialized."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        mock_state.manual_dimmer = 0.5
        mock_state.venue = Mock()
        web_server_module.state_instance = mock_state

        with patch("parrot.api.web_server.has_manual_dimmer", return_value=True):
            response = self.client.get("/api/manual_dimmer")
            assert response.status_code == 200

            data = json.loads(response.data)
            assert data["value"] == 0.5
            assert data["supported"] is True

    def test_set_manual_dimmer_no_state(self):
        """Test POST /api/manual_dimmer when state is not initialized."""
        response = self.client.post(
            "/api/manual_dimmer", json={"value": 0.5}, content_type="application/json"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is False

    def test_set_manual_dimmer_valid_value(self):
        """Test POST /api/manual_dimmer with valid value."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        response = self.client.post(
            "/api/manual_dimmer", json={"value": 0.7}, content_type="application/json"
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["value"] == 0.7
        mock_state.set_manual_dimmer.assert_called_once_with(0.7)

    def test_set_manual_dimmer_clamps_value(self):
        """Test POST /api/manual_dimmer clamps values to 0-1 range."""
        import parrot.api.web_server as web_server_module

        mock_state = Mock()
        web_server_module.state_instance = mock_state

        # Test value > 1
        response = self.client.post(
            "/api/manual_dimmer", json={"value": 1.5}, content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["value"] == 1.0

        # Test value < 0
        response = self.client.post(
            "/api/manual_dimmer", json={"value": -0.5}, content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["value"] == 0.0

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
        mock_state.set_effect_thread_safe.assert_called_once_with("strobe")

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

    @patch("threading.Thread")
    @patch("builtins.print")
    def test_start_web_server(self, mock_print, mock_thread):
        """Test start_web_server function."""
        mock_state = Mock()
        mock_director = Mock()

        with patch("parrot.api.web_server.get_local_ip", return_value="192.168.1.100"):
            start_web_server(mock_state, mock_director, port=8080)

        # Check that global instances are set
        import parrot.api.web_server as web_server_module

        assert web_server_module.state_instance == mock_state
        assert web_server_module.director_instance == mock_director

        # Check that thread was started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()

        # Check that IP address was printed
        mock_print.assert_any_call(
            "\n🌐 Web interface available at: http://192.168.1.100:8080/"
        )

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
        mock_state.vj_mode = VJMode.full_rave
        web_server_module.state_instance = mock_state

        response = self.client.get("/api/vj_mode")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["vj_mode"] == "full_rave"
        assert "available_vj_modes" in data

    def test_set_vj_mode_no_state(self):
        """Test POST /api/vj_mode when state is not initialized."""
        response = self.client.post(
            "/api/vj_mode",
            json={"vj_mode": "full_rave"},
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
            json={"vj_mode": "full_rave"},
            content_type="application/json",
        )
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["vj_mode"] == "full_rave"
        mock_state.set_vj_mode_thread_safe.assert_called_once_with(VJMode.full_rave)
