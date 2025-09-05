"""OAuth Discovery module for dynamic endpoint resolution."""

import requests
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin
import sys


def discover_oauth_endpoints(
    server_url: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[Dict]]:
    """
    Discovers OAuth endpoints from a server using well-known URIs.

    Args:
        server_url: The base URL of the MCP server

    Returns:
        Tuple of (authorization_url, token_url, registration_url, full_metadata)
    """
    # Extract base URL (remove path component as per MCP spec)
    parsed = urlparse(server_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Try OAuth 2.0 Authorization Server Metadata (RFC 8414)
    well_known_url = urljoin(base_url, "/.well-known/oauth-authorization-server")

    try:
        response = requests.get(
            well_known_url, headers={"MCP-Protocol-Version": "1.0"}, timeout=5
        )

        if response.status_code == 200:
            metadata = response.json()
            auth_endpoint = metadata.get("authorization_endpoint")
            token_endpoint = metadata.get("token_endpoint")
            registration_endpoint = metadata.get("registration_endpoint")

            if auth_endpoint and token_endpoint:
                print(
                    f"✓ Discovered OAuth endpoints from {well_known_url}",
                    file=sys.stderr,
                )
                return auth_endpoint, token_endpoint, registration_endpoint, metadata

    except requests.exceptions.RequestException as e:
        print(
            f"Failed to fetch OAuth metadata from {well_known_url}: {e}",
            file=sys.stderr,
        )

    # Try OpenID Connect Discovery as fallback
    oidc_url = urljoin(base_url, "/.well-known/openid-configuration")

    try:
        response = requests.get(oidc_url, timeout=5)

        if response.status_code == 200:
            metadata = response.json()
            auth_endpoint = metadata.get("authorization_endpoint")
            token_endpoint = metadata.get("token_endpoint")
            registration_endpoint = metadata.get("registration_endpoint")

            if auth_endpoint and token_endpoint:
                print(f"✓ Discovered OAuth endpoints from {oidc_url}", file=sys.stderr)
                return auth_endpoint, token_endpoint, registration_endpoint, metadata

    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch OIDC metadata from {oidc_url}: {e}", file=sys.stderr)

    # Use default MCP endpoints as fallback (as per spec)
    print(f"Using default MCP OAuth endpoints for {base_url}", file=sys.stderr)
    return (
        urljoin(base_url, "/authorize"),
        urljoin(base_url, "/token"),
        urljoin(base_url, "/register"),
        None,
    )


def get_oauth_config_for_service(service_name: str) -> Dict[str, str]:
    """
    Gets OAuth configuration for known services.

    Args:
        service_name: Name of the service (e.g., 'atlassian')

    Returns:
        Dictionary with OAuth configuration
    """
    known_services = {
        "atlassian": {
            "server_url": "https://auth.atlassian.com",  # Use main Atlassian OAuth
            "mcp_endpoint": "https://mcp.atlassian.com/v1/sse",
            "required_port": 5598,  # Atlassian MCP requires this specific port
            "scopes": [
                "offline_access",
                "read:jira-work",
                "write:jira-work",
                "read:confluence-content.all",
                "write:confluence-content.all",
            ],
            "static_auth_url": "https://auth.atlassian.com/authorize",
            "static_token_url": "https://auth.atlassian.com/oauth/token",
            "static_registration_url": "https://auth.atlassian.com/oidc/register",
            "use_main_oauth": True,  # Flag to use main Atlassian OAuth, not MCP
        }
    }

    config = known_services.get(service_name, {})

    # Try discovery if server_url is provided
    if config.get("server_url"):
        auth_url, token_url, registration_url, metadata = discover_oauth_endpoints(
            config["server_url"]
        )

        # Use discovered endpoints if available, otherwise fall back to static
        config["auth_url"] = auth_url or config.get("static_auth_url")
        config["token_url"] = token_url or config.get("static_token_url")
        config["registration_url"] = registration_url

        # Add metadata if discovered
        if metadata:
            config["metadata"] = metadata

            # Check if our required scopes are supported
            supported_scopes = metadata.get("scopes_supported", [])
            if supported_scopes:
                config["available_scopes"] = supported_scopes

    return config
