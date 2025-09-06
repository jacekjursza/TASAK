"""Unit tests for auth module."""

import json
from unittest.mock import Mock, mock_open, patch

import pytest

from tasak.auth import (
    OAuthCallbackHandler,
    run_auth_app,
    _do_generic_oauth_auth,
    _do_atlassian_auth,
    _save_token,
)


class TestOAuthCallbackHandler:
    """Test OAuthCallbackHandler class."""

    def test_do_get_with_code(self):
        """Test handling GET request with authorization code."""
        handler = OAuthCallbackHandler(Mock(), ("127.0.0.1", 8080), Mock())
        handler.path = "/callback?code=test_auth_code&state=test_state"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Import to access global variable
        import tasak.auth

        handler.do_GET()

        # Check that authorization code was captured
        assert tasak.auth.authorization_code == "test_auth_code"
        handler.send_response.assert_called_with(200)
        handler.wfile.write.assert_called()

    def test_do_get_without_code(self):
        """Test handling GET request without authorization code."""
        handler = OAuthCallbackHandler(Mock(), ("127.0.0.1", 8080), Mock())
        handler.path = "/callback?error=access_denied"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        handler.do_GET()

        handler.send_response.assert_called_with(400)
        handler.wfile.write.assert_called()

    def test_do_get_with_encoded_code(self):
        """Test handling GET request with URL-encoded authorization code."""
        handler = OAuthCallbackHandler(Mock(), ("127.0.0.1", 8080), Mock())
        handler.path = "/callback?code=test%2Bauth%2Bcode"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        import tasak.auth

        handler.do_GET()

        # Check that code was properly decoded
        assert tasak.auth.authorization_code == "test+auth+code"


class TestRunAuthApp:
    """Test run_auth_app function."""

    @patch("tasak.auth._do_atlassian_auth")
    def test_run_auth_app_atlassian(self, mock_atlassian_auth):
        """Test authentication for Atlassian."""
        run_auth_app("atlassian")
        mock_atlassian_auth.assert_called_once()

    @patch("tasak.auth._do_generic_oauth_auth")
    def test_run_auth_app_generic_with_server_url(self, mock_generic_auth):
        """Test generic OAuth with server URL."""
        run_auth_app("test_app", server_url="http://test.com", client_id="test_client")
        mock_generic_auth.assert_called_once_with(
            "test_app", "http://test.com", "test_client"
        )

    def test_run_auth_app_generic_without_server_url(self, capsys):
        """Test generic OAuth without server URL."""
        with pytest.raises(SystemExit) as exc_info:
            run_auth_app("test_app")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "requires --server-url parameter" in captured.err


class TestDoGenericOAuthAuth:
    """Test _do_generic_oauth_auth function."""

    @patch("tasak.auth.discover_oauth_endpoints")
    def test_discovery_failure(self, mock_discover, capsys):
        """Test when OAuth endpoint discovery fails."""
        mock_discover.return_value = (None, None, {})

        with pytest.raises(SystemExit) as exc_info:
            _do_generic_oauth_auth("test_app", "http://test.com", None)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to discover OAuth endpoints" in captured.err

    @patch("tasak.auth.webbrowser.open")
    @patch("tasak.auth.socketserver.TCPServer")
    @patch("tasak.auth.requests.post")
    @patch("tasak.auth.register_oauth_client")
    @patch("tasak.auth.discover_oauth_endpoints")
    def test_successful_oauth_flow(
        self, mock_discover, mock_register, mock_post, mock_server, mock_browser
    ):
        """Test successful OAuth flow."""
        # Setup mocks
        mock_discover.return_value = (
            "http://auth.test/authorize",
            "http://auth.test/token",
            {"issuer": "http://auth.test"},
        )
        mock_register.return_value = {
            "client_id": "dynamic_client",
            "client_secret": "secret",
        }

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Mock server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        # Set authorization code before server shutdown
        import tasak.auth

        tasak.auth.authorization_code = "test_code"

        with patch("tasak.auth._save_token") as mock_save:
            _do_generic_oauth_auth("test_app", "http://test.com", None)

            mock_save.assert_called_once()
            mock_browser.assert_called_once()


class TestSaveToken:
    """Test _save_token function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("tasak.auth.AUTH_FILE_PATH.parent.mkdir")
    @patch("tasak.auth.AUTH_FILE_PATH.exists")
    def test_save_token_new_file(self, mock_exists, mock_mkdir, mock_file):
        """Test saving tokens to new file."""
        mock_exists.return_value = False

        _save_token("test_app", {"access_token": "token123"})

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called()

        # Check what was written
        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        assert "test_app" in data
        assert data["test_app"]["access_token"] == "token123"

    @patch("builtins.open", new_callable=mock_open, read_data='{"existing_app": {}}')
    @patch("tasak.auth.AUTH_FILE_PATH.exists")
    def test_save_token_existing_file(self, mock_exists, mock_file):
        """Test saving tokens to existing file."""
        mock_exists.return_value = True

        _save_token("test_app", {"access_token": "token123"})

        # Check that existing data was preserved
        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        assert "existing_app" in data
        assert "test_app" in data


class TestDoAtlassianAuth:
    """Test _do_atlassian_auth function."""

    @patch("tasak.auth.webbrowser.open")
    @patch("tasak.auth.socketserver.TCPServer")
    @patch("tasak.auth.requests.post")
    @patch("tasak.auth.get_oauth_config_for_service")
    def test_atlassian_auth_flow(
        self, mock_config, mock_post, mock_server, mock_browser
    ):
        """Test Atlassian-specific auth flow."""
        # Setup mocks
        mock_config.return_value = {
            "auth_url": "https://auth.atlassian.com/authorize",
            "token_url": "https://auth.atlassian.com/oauth/token",
            "scopes": ["offline_access"],
            "required_port": 5598,
        }

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "atlassian_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Mock server
        mock_server_instance = Mock()
        mock_server.return_value = mock_server_instance

        # Set authorization code
        import tasak.auth

        tasak.auth.authorization_code = "atlassian_code"

        with patch("tasak.auth._save_token") as mock_save:
            _do_atlassian_auth()

            # Should use Atlassian-specific port
            mock_server.assert_called_once()
            call_args = mock_server.call_args[0]
            assert call_args[0][1] == 5598  # Atlassian required port

            mock_browser.assert_called_once()
            mock_save.assert_called_once()
