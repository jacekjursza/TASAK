import http.server
import socketserver
import webbrowser
import requests
import json
from pathlib import Path
import os
import sys
import argparse
import time
from urllib.parse import urlparse, parse_qs, unquote
from .oauth_discovery import get_oauth_config_for_service
from .dynamic_registration import register_oauth_client, get_saved_registration
from .pkce import generate_pkce_pair

# --- Constants ---
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"

# --- Global variables for OAuth flow ---
authorization_code = None
code_verifier = None  # For PKCE


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to capture the OAuth 2.1 authorization code."""

    def do_GET(self):
        global authorization_code

        # Log the full request for debugging
        print(
            f"DEBUG: Received callback request: {self.path[:100]}...", file=sys.stderr
        )

        query_components = parse_qs(urlparse(self.path).query)
        if "code" in query_components:
            # Get the raw code first
            raw_code = query_components["code"][0]
            print(f"DEBUG: Raw authorization code: {raw_code[:50]}...", file=sys.stderr)

            # Decode the authorization code (it might be URL-encoded multiple times)
            code = raw_code
            decode_count = 0
            while "%" in code and decode_count < 5:  # Limit decoding attempts
                decoded = unquote(code)
                if decoded == code:
                    break
                code = decoded
                decode_count += 1
                print(
                    f"DEBUG: After decode #{decode_count}: {code[:50]}...",
                    file=sys.stderr,
                )

            authorization_code = code
            print(
                f"DEBUG: Final authorization code format: {code[:50]}...",
                file=sys.stderr,
            )
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authentication successful!</h1><p>You can close this window.</p>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authentication failed.</h1><p>No authorization code found.</p>"
            )


def run_auth_app(app_name: str, server_url: str = None, client_id: str = None):
    """Initiates the OAuth 2.1 flow for a given application."""
    if app_name == "atlassian":
        _do_atlassian_auth()
    else:
        # Try generic OAuth flow with discovery
        if server_url:
            _do_generic_oauth_auth(app_name, server_url, client_id)
        else:
            print(
                f"Authentication for '{app_name}' requires --server-url parameter.",
                file=sys.stderr,
            )
            sys.exit(1)


def _do_generic_oauth_auth(app_name: str, server_url: str, client_id: str):
    """Handles OAuth 2.1 flow for any MCP server with discovery."""
    from .oauth_discovery import discover_oauth_endpoints

    # Discover OAuth endpoints
    auth_endpoint, token_endpoint, metadata = discover_oauth_endpoints(server_url)

    if not auth_endpoint or not token_endpoint:
        print(f"Failed to discover OAuth endpoints for {server_url}", file=sys.stderr)
        sys.exit(1)

    if not client_id:
        print("Client ID is required for generic OAuth flow", file=sys.stderr)
        sys.exit(1)

    print(f"Discovered OAuth endpoints for {app_name}:")
    print(f"  Authorization: {auth_endpoint}")
    print(f"  Token: {token_endpoint}")

    # Get available scopes from metadata
    scopes = []
    if metadata and "scopes_supported" in metadata:
        print(f"  Available scopes: {', '.join(metadata['scopes_supported'][:5])}...")
        # For demo, we'll request some basic scopes
        scopes = metadata["scopes_supported"][:3]

    # Find a free port for the redirect URI
    with socketserver.TCPServer(("localhost", 0), None) as s:
        free_port = s.server_address[1]

    redirect_uri = f"http://localhost:{free_port}"
    scope_str = "%20".join(scopes) if scopes else ""

    auth_url = (
        f"{auth_endpoint}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
    )
    if scope_str:
        auth_url += f"scope={scope_str}&"
    auth_url += "state=tasak-auth-state"

    print("\nYour browser should open for authentication.")
    sys.stdout.flush()
    print(f"If it doesn't, please open this URL manually:\n{auth_url}")
    sys.stdout.flush()
    webbrowser.open(auth_url)

    global authorization_code
    authorization_code = None
    httpd = None
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", free_port), OAuthCallbackHandler) as httpd:
            print(f"\nWaiting for authentication... (Listening on port {free_port})")
            sys.stdout.flush()
            while authorization_code is None:
                httpd.handle_request()

        print("Authorization code received. Exchanging for access token...")
        _exchange_code_for_token(
            authorization_code, redirect_uri, token_endpoint, client_id, code_verifier
        )

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if httpd:
            httpd.server_close()


def _do_atlassian_auth():
    """Handles the full OAuth 2.1 flow for Atlassian."""
    # Get OAuth configuration (with dynamic discovery)
    config = get_oauth_config_for_service("atlassian")

    if not config.get("auth_url") or not config.get("token_url"):
        print("Failed to discover OAuth endpoints for Atlassian", file=sys.stderr)
        sys.exit(1)

    # Try to get saved registration first
    saved_reg = get_saved_registration("atlassian")
    client_id = None
    client_secret = None

    if saved_reg:
        client_id = saved_reg.get("client_id")
        client_secret = saved_reg.get("client_secret")
        print(f"Using saved client registration: {client_id}")

    # If no saved registration and we have a registration endpoint, try dynamic registration
    if not client_id and config.get("registration_url"):
        print("Attempting dynamic client registration with Atlassian...")

        # Use Atlassian required port or find a free port
        required_port = config.get("required_port", 5598)

        redirect_uris = [
            f"http://localhost:{required_port}",
            "http://localhost:5598",  # Atlassian MCP standard port
        ]

        client_id, client_secret, reg_response = register_oauth_client(
            config["registration_url"],
            app_name="TASAK Atlassian Client",
            redirect_uris=redirect_uris,
        )

        if not client_id:
            # Fall back to hardcoded client ID if dynamic registration fails
            print("Dynamic registration failed, using default client ID")
            client_id = config.get("client_id", "5Dzgchq9CCu2EIgv")

    # Use static client ID as last resort
    if not client_id:
        client_id = config.get("client_id", "5Dzgchq9CCu2EIgv")

    auth_endpoint = config.get("auth_url")
    token_endpoint = config.get("token_url")
    scopes = config.get("scopes", [])

    print("Using OAuth endpoints:")
    print(f"  Authorization: {auth_endpoint}")
    print(f"  Token: {token_endpoint}")

    # Check available scopes if metadata was discovered
    if "available_scopes" in config:
        print(f"  Available scopes: {', '.join(config['available_scopes'][:5])}...")

    # Use required port for Atlassian (5598) or find a free port
    free_port = config.get("required_port", None)
    if free_port:
        print(f"Using Atlassian-required port {free_port} for OAuth callback")
    else:
        with socketserver.TCPServer(("localhost", 0), None) as s:
            free_port = s.server_address[1]

    redirect_uri = f"http://localhost:{free_port}"
    scope_str = "%20".join(scopes)

    # Generate PKCE challenge for Atlassian
    global code_verifier, authorization_code
    authorization_code = None
    code_verifier, code_challenge = generate_pkce_pair()
    print("Using PKCE with challenge method S256")

    auth_url = (
        f"{auth_endpoint}?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope_str}&"
        f"state=tasak-auth-state&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )

    print("\nYour browser should open for authentication.")
    sys.stdout.flush()
    print(f"If it doesn't, please open this URL manually:\n{auth_url}")
    sys.stdout.flush()
    webbrowser.open(auth_url)

    httpd = None
    try:
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", free_port), OAuthCallbackHandler) as httpd:
            print(f"\nWaiting for authentication... (Listening on port {free_port})")
            sys.stdout.flush()
            while authorization_code is None:
                httpd.handle_request()

        print("Authorization code received. Exchanging for access token...")
        _exchange_code_for_token(
            authorization_code, redirect_uri, token_endpoint, client_id, code_verifier
        )

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if httpd:
            httpd.server_close()


def _exchange_code_for_token(
    code: str, redirect_uri: str, token_url: str, client_id: str, verifier: str = None
):
    """Exchanges the authorization code for an access token and refresh token."""
    print(f"DEBUG: Exchanging code (first 30 chars): {code[:30]}...")
    print(f"DEBUG: Token URL: {token_url}")
    print(f"DEBUG: Client ID: {client_id}")

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
    }

    # Add PKCE verifier if available
    if verifier:
        payload["code_verifier"] = verifier
        print("DEBUG: Including PKCE code_verifier")

    print("DEBUG: Full payload being sent:")
    for key, value in payload.items():
        if key == "code_verifier":
            print(f"  {key}: {value[:20]}... (truncated)")
        else:
            print(f"  {key}: {value}")

    # MCP servers might require specific headers
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "TASAK/1.0",
        "Origin": "http://localhost:5598",
    }

    # Ensure proper URL encoding for the request
    import urllib.parse

    encoded_payload = urllib.parse.urlencode(payload)

    print(f"DEBUG: Encoded payload: {encoded_payload[:100]}...")

    response = requests.post(token_url, data=encoded_payload, headers=headers)

    if response.status_code != 200:
        print(f"ERROR: Token exchange failed with status {response.status_code}")
        print(f"ERROR Response: {response.text}")

        # Try alternate approach - maybe the code format is different
        if ":" in code:
            # Try extracting just the last part after all colons
            parts = code.split(":")
            if len(parts) > 1:
                alternate_code = parts[-1]
                print(
                    f"DEBUG: Trying with just the token part: {alternate_code[:20]}..."
                )
                payload["code"] = alternate_code
                response = requests.post(token_url, data=payload, headers=headers)

    if response.status_code == 200:
        token_data = response.json()
        # Add timestamp for token expiry calculation
        token_data["obtained_at"] = int(time.time())
        _save_token("atlassian", token_data)
        print("Successfully authenticated and saved tokens.")
        print(
            f"Access token expires in {token_data.get('expires_in', 'unknown')} seconds"
        )
    else:
        print(
            f"Failed to get access token. Status: {response.status_code}",
            file=sys.stderr,
        )
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)


def _save_token(app_name: str, token_data: dict):
    """Saves the token data to the auth file."""
    AUTH_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_tokens = {}
    if AUTH_FILE_PATH.exists():
        with open(AUTH_FILE_PATH, "r") as f:
            all_tokens = json.load(f)

    all_tokens[app_name] = token_data

    with open(AUTH_FILE_PATH, "w") as f:
        json.dump(all_tokens, f, indent=2)

    # Set file permissions (Unix-like systems only)
    try:
        os.chmod(AUTH_FILE_PATH, 0o600)
    except (OSError, AttributeError):
        # Windows doesn't support chmod the same way
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TASAK Authentication Helper")
    parser.add_argument(
        "app_name",
        help="The name of the application to authenticate with (e.g., 'atlassian')",
    )
    parser.add_argument(
        "--server-url",
        help="MCP server URL for OAuth discovery (for non-predefined services)",
    )
    parser.add_argument(
        "--client-id",
        help="OAuth client ID (for non-predefined services)",
    )
    args = parser.parse_args()
    run_auth_app(args.app_name, args.server_url, args.client_id)
