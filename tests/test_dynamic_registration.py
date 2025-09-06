"""Unit tests for dynamic_registration module."""

import json
from unittest.mock import Mock, mock_open, patch

import requests

from tasak.dynamic_registration import (
    register_oauth_client,
    _save_registration,
    get_saved_registration,
)


class TestRegisterOAuthClient:
    """Test register_oauth_client function."""

    @patch("tasak.dynamic_registration.requests.post")
    @patch("tasak.dynamic_registration._save_registration")
    def test_successful_registration(self, mock_save, mock_post, capsys):
        """Test successful client registration."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "client_id": "test_client_123",
            "client_secret": "test_secret_456",
            "client_name": "TASAK MCP Client",
        }
        mock_post.return_value = mock_response

        client_id, client_secret, response = register_oauth_client(
            "https://auth.example.com/register", "TestApp"
        )

        assert client_id == "test_client_123"
        assert client_secret == "test_secret_456"
        assert response["client_name"] == "TASAK MCP Client"

        mock_save.assert_called_once_with("TestApp", response)

        captured = capsys.readouterr()
        assert "Successfully registered OAuth client" in captured.err
        assert "Client ID: test_client_123" in captured.err

    @patch("tasak.dynamic_registration.requests.post")
    def test_registration_with_custom_redirect_uris(self, mock_post):
        """Test registration with custom redirect URIs."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"client_id": "test_client"}
        mock_post.return_value = mock_response

        register_oauth_client(
            "https://auth.example.com/register",
            "TestApp",
            redirect_uris=["https://custom.redirect.com"],
        )

        # Check that custom redirect URIs were used
        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["redirect_uris"] == ["https://custom.redirect.com"]

    @patch("tasak.dynamic_registration.requests.post")
    def test_registration_failure_status(self, mock_post, capsys):
        """Test registration failure due to bad status code."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid request"
        mock_post.return_value = mock_response

        client_id, client_secret, response = register_oauth_client(
            "https://auth.example.com/register"
        )

        assert client_id is None
        assert client_secret is None
        assert response is None

        captured = capsys.readouterr()
        assert "Registration failed with status 400" in captured.err
        assert "Invalid request" in captured.err

    @patch("tasak.dynamic_registration.requests.post")
    def test_registration_request_exception(self, mock_post, capsys):
        """Test registration failure due to request exception."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client_id, client_secret, response = register_oauth_client(
            "https://auth.example.com/register"
        )

        assert client_id is None
        assert client_secret is None
        assert response is None

        captured = capsys.readouterr()
        assert "Failed to register client: Connection failed" in captured.err

    @patch("tasak.dynamic_registration.requests.post")
    def test_default_redirect_uris(self, mock_post):
        """Test that default redirect URIs are used when none provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"client_id": "test"}
        mock_post.return_value = mock_response

        register_oauth_client("https://auth.example.com/register")

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert "http://localhost:8080" in request_data["redirect_uris"]
        assert "http://127.0.0.1:8080" in request_data["redirect_uris"]


class TestSaveRegistration:
    """Test _save_registration function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.chmod")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_save_new_registration(
        self, mock_mkdir, mock_exists, mock_chmod, mock_file
    ):
        """Test saving registration when file doesn't exist."""
        mock_exists.return_value = False

        registration_data = {"client_id": "test123", "client_secret": "secret456"}
        _save_registration("TestApp", registration_data)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Check what was written
        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        assert "TestApp" in data
        assert data["TestApp"]["client_id"] == "test123"

        # Check file permissions were set
        mock_chmod.assert_called_once()
        args = mock_chmod.call_args[0]
        assert args[1] == 0o600

    @patch("builtins.open", new_callable=mock_open, read_data='{"ExistingApp": {}}')
    @patch("os.chmod")
    @patch("pathlib.Path.exists")
    def test_save_registration_existing_file(self, mock_exists, mock_chmod, mock_file):
        """Test saving registration when file exists with other registrations."""
        mock_exists.return_value = True

        registration_data = {"client_id": "new123"}
        _save_registration("NewApp", registration_data)

        # Check that existing data was preserved
        handle = mock_file()
        written_data = "".join(call[0][0] for call in handle.write.call_args_list)
        data = json.loads(written_data)
        assert "ExistingApp" in data
        assert "NewApp" in data
        assert data["NewApp"]["client_id"] == "new123"


class TestGetSavedRegistration:
    """Test get_saved_registration function."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"TestApp": {"client_id": "saved123"}}',
    )
    @patch("pathlib.Path.exists")
    def test_get_existing_registration(self, mock_exists, mock_file):
        """Test retrieving existing registration."""
        mock_exists.return_value = True

        registration = get_saved_registration("TestApp")

        assert registration is not None
        assert registration["client_id"] == "saved123"

    @patch("pathlib.Path.exists")
    def test_get_registration_file_not_exists(self, mock_exists):
        """Test retrieving registration when file doesn't exist."""
        mock_exists.return_value = False

        registration = get_saved_registration("TestApp")

        assert registration is None

    @patch("builtins.open", new_callable=mock_open, read_data='{"OtherApp": {}}')
    @patch("pathlib.Path.exists")
    def test_get_registration_app_not_found(self, mock_exists, mock_file):
        """Test retrieving registration for app not in file."""
        mock_exists.return_value = True

        registration = get_saved_registration("TestApp")

        assert registration is None

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("pathlib.Path.exists")
    def test_get_registration_invalid_json(self, mock_exists, mock_file):
        """Test handling of invalid JSON in registration file."""
        mock_exists.return_value = True

        registration = get_saved_registration("TestApp")

        assert registration is None
