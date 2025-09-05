"""Dynamic Client Registration for MCP OAuth."""

import requests
import json
from typing import Dict, Optional, Tuple
import sys


def register_oauth_client(
    registration_endpoint: str,
    app_name: str = "TASAK MCP Client",
    redirect_uris: list = None,
) -> Tuple[Optional[str], Optional[str], Optional[Dict]]:
    """
    Dynamically registers an OAuth client with the authorization server.

    Implements OAuth 2.0 Dynamic Client Registration Protocol (RFC7591).

    Args:
        registration_endpoint: The dynamic registration endpoint URL
        app_name: Name of the client application
        redirect_uris: List of allowed redirect URIs

    Returns:
        Tuple of (client_id, client_secret, full_response)
    """
    if redirect_uris is None:
        # Default to localhost with various ports for flexibility
        redirect_uris = [
            "http://localhost:8080",
            "http://localhost:8989",
            "http://localhost:3000",
            "http://127.0.0.1:8080",
        ]

    # Prepare registration request per RFC7591
    registration_request = {
        "application_type": "native",
        "client_name": app_name,
        "redirect_uris": redirect_uris,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # Public client (no secret)
        "scope": "offline_access read:jira-work write:jira-work read:confluence-content.all write:confluence-content.all",
        "software_statement": "TASAK: The Agent's Swiss Army Knife - MCP Client",
    }

    try:
        print(
            f"Attempting dynamic client registration at {registration_endpoint}",
            file=sys.stderr,
        )

        response = requests.post(
            registration_endpoint,
            json=registration_request,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )

        if response.status_code in [200, 201]:
            registration_response = response.json()
            client_id = registration_response.get("client_id")
            client_secret = registration_response.get("client_secret")

            print("✓ Successfully registered OAuth client", file=sys.stderr)
            print(f"  Client ID: {client_id}", file=sys.stderr)

            # Save registration info for future use
            _save_registration(app_name, registration_response)

            return client_id, client_secret, registration_response

        else:
            print(
                f"Registration failed with status {response.status_code}",
                file=sys.stderr,
            )
            print(f"Response: {response.text}", file=sys.stderr)
            return None, None, None

    except requests.exceptions.RequestException as e:
        print(f"Failed to register client: {e}", file=sys.stderr)
        return None, None, None


def _save_registration(app_name: str, registration_data: Dict):
    """Saves the registration data for future use."""
    from pathlib import Path

    config_dir = Path.home() / ".tasak"
    config_dir.mkdir(parents=True, exist_ok=True)

    registration_file = config_dir / "registrations.json"

    # Load existing registrations
    registrations = {}
    if registration_file.exists():
        with open(registration_file, "r") as f:
            registrations = json.load(f)

    # Add new registration
    registrations[app_name] = registration_data

    # Save back
    with open(registration_file, "w") as f:
        json.dump(registrations, f, indent=2)

    # Set proper permissions
    import os

    os.chmod(registration_file, 0o600)


def get_saved_registration(app_name: str) -> Optional[Dict]:
    """Retrieves saved registration data if available."""
    from pathlib import Path

    registration_file = Path.home() / ".tasak" / "registrations.json"

    if not registration_file.exists():
        return None

    try:
        with open(registration_file, "r") as f:
            registrations = json.load(f)
            return registrations.get(app_name)
    except Exception:
        return None
