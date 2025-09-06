"""Unit tests for oauth_discovery module."""

from unittest.mock import Mock, patch

import requests

from tasak.oauth_discovery import (
    discover_oauth_endpoints,
    get_oauth_config_for_service,
)


class TestDiscoverOAuthEndpoints:
    """Test discover_oauth_endpoints function."""

    @patch("tasak.oauth_discovery.requests.get")
    def test_successful_oauth_discovery(self, mock_get, capsys):
        """Test successful OAuth endpoint discovery."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "registration_endpoint": "https://auth.example.com/register",
            "issuer": "https://auth.example.com",
        }
        mock_get.return_value = mock_response

        auth_url, token_url, reg_url, metadata = discover_oauth_endpoints(
            "https://example.com/api"
        )

        assert auth_url == "https://auth.example.com/authorize"
        assert token_url == "https://auth.example.com/token"
        assert reg_url == "https://auth.example.com/register"
        assert metadata["issuer"] == "https://auth.example.com"

        captured = capsys.readouterr()
        assert "Discovered OAuth endpoints" in captured.err

        # Verify correct well-known URL was used
        mock_get.assert_called_with(
            "https://example.com/.well-known/oauth-authorization-server",
            headers={"MCP-Protocol-Version": "1.0"},
            timeout=5,
        )

    @patch("tasak.oauth_discovery.requests.get")
    def test_oidc_fallback(self, mock_get, capsys):
        """Test fallback to OpenID Connect discovery."""
        # First call fails (OAuth)
        mock_oauth_response = Mock()
        mock_oauth_response.status_code = 404

        # Second call succeeds (OIDC)
        mock_oidc_response = Mock()
        mock_oidc_response.status_code = 200
        mock_oidc_response.json.return_value = {
            "authorization_endpoint": "https://auth.example.com/oidc/authorize",
            "token_endpoint": "https://auth.example.com/oidc/token",
        }

        mock_get.side_effect = [mock_oauth_response, mock_oidc_response]

        auth_url, token_url, reg_url, metadata = discover_oauth_endpoints(
            "https://example.com"
        )

        assert auth_url == "https://auth.example.com/oidc/authorize"
        assert token_url == "https://auth.example.com/oidc/token"
        assert reg_url is None

        captured = capsys.readouterr()
        assert "Discovered OAuth endpoints" in captured.err
        assert "openid-configuration" in captured.err

    @patch("tasak.oauth_discovery.requests.get")
    def test_default_endpoints_fallback(self, mock_get, capsys):
        """Test fallback to default MCP endpoints."""
        # Both discovery attempts fail
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        auth_url, token_url, reg_url, metadata = discover_oauth_endpoints(
            "https://example.com/api"
        )

        assert auth_url == "https://example.com/authorize"
        assert token_url == "https://example.com/token"
        assert reg_url == "https://example.com/register"
        assert metadata is None

        captured = capsys.readouterr()
        assert "Using default MCP OAuth endpoints" in captured.err

    @patch("tasak.oauth_discovery.requests.get")
    def test_request_exception_handling(self, mock_get, capsys):
        """Test handling of request exceptions."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        auth_url, token_url, reg_url, metadata = discover_oauth_endpoints(
            "https://example.com"
        )

        # Should fall back to defaults
        assert auth_url == "https://example.com/authorize"
        assert token_url == "https://example.com/token"
        assert reg_url == "https://example.com/register"

        captured = capsys.readouterr()
        assert "Failed to fetch OAuth metadata" in captured.err
        assert "Connection failed" in captured.err

    @patch("tasak.oauth_discovery.requests.get")
    def test_incomplete_metadata(self, mock_get, capsys):
        """Test handling of incomplete metadata (missing endpoints)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "issuer": "https://auth.example.com",
            # Missing authorization_endpoint and token_endpoint
        }
        mock_get.return_value = mock_response

        auth_url, token_url, reg_url, metadata = discover_oauth_endpoints(
            "https://example.com"
        )

        # Should fall back to defaults when endpoints are missing
        assert auth_url == "https://example.com/authorize"
        assert token_url == "https://example.com/token"
        assert reg_url == "https://example.com/register"


class TestGetOAuthConfigForService:
    """Test get_oauth_config_for_service function."""

    def test_unknown_service(self):
        """Test getting config for unknown service."""
        config = get_oauth_config_for_service("unknown_service")
        assert config == {}

    @patch("tasak.oauth_discovery.discover_oauth_endpoints")
    def test_atlassian_service(self, mock_discover):
        """Test getting config for Atlassian service."""
        mock_discover.return_value = (
            "https://auth.atlassian.com/authorize",
            "https://auth.atlassian.com/oauth/token",
            "https://auth.atlassian.com/oidc/register",
            {"issuer": "https://auth.atlassian.com"},
        )

        config = get_oauth_config_for_service("atlassian")

        assert config["server_url"] == "https://auth.atlassian.com"
        assert config["mcp_endpoint"] == "https://mcp.atlassian.com/v1/sse"
        assert config["required_port"] == 5598
        assert "offline_access" in config["scopes"]
        assert config["use_main_oauth"] is True
        assert config["auth_url"] == "https://auth.atlassian.com/authorize"
        assert config["token_url"] == "https://auth.atlassian.com/oauth/token"

        mock_discover.assert_called_once_with("https://auth.atlassian.com")

    @patch("tasak.oauth_discovery.discover_oauth_endpoints")
    def test_service_with_metadata(self, mock_discover):
        """Test service config with discovered metadata."""
        mock_discover.return_value = (
            "https://discovered.com/auth",
            "https://discovered.com/token",
            None,
            {
                "issuer": "https://discovered.com",
                "scopes_supported": ["read", "write"],
            },
        )

        config = get_oauth_config_for_service("atlassian")

        assert "metadata" in config
        assert config["metadata"]["issuer"] == "https://discovered.com"
        assert "available_scopes" in config
        assert config["available_scopes"] == ["read", "write"]

    @patch("tasak.oauth_discovery.discover_oauth_endpoints")
    def test_service_fallback_to_static(self, mock_discover):
        """Test fallback to static URLs when discovery returns None."""
        mock_discover.return_value = (None, None, None, None)

        config = get_oauth_config_for_service("atlassian")

        # Should use static URLs
        assert config["auth_url"] == "https://auth.atlassian.com/authorize"
        assert config["token_url"] == "https://auth.atlassian.com/oauth/token"
        assert config.get("registration_url") is None
