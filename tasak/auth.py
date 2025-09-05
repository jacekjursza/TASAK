import http.server
import socketserver
import webbrowser
import requests
import json
from pathlib import Path
import os
import sys
import argparse
from urllib.parse import urlparse, parse_qs

# --- Constants ---
ATLASSIAN_CLIENT_ID = "5Dzgchq9CCu2EIgv"
ATLASSIAN_AUTH_URL = "https://mcp.atlassian.com/oauth2/authorize"
ATLASSIAN_TOKEN_URL = "https://mcp.atlassian.com/oauth2/token"
REDIRECT_URI = "http://localhost:8989"
AUTH_FILE_PATH = Path.home() / ".tasak" / "auth.json"

# --- Global variable to hold the authorization code ---
authorization_code = None


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to capture the OAuth 2.1 authorization code."""

    def do_GET(self):
        global authorization_code
        query_components = parse_qs(urlparse(self.path).query)
        if "code" in query_components:
            authorization_code = query_components["code"][0]
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


def run_auth_app(app_name: str):
    """Initiates the OAuth 2.1 flow for a given application."""
    if app_name == "atlassian":
        _do_atlassian_auth()
    else:
        print(f"Authentication for '{app_name}' is not supported.", file=sys.stderr)
        sys.exit(1)


def _do_atlassian_auth():
    """Handles the full OAuth 2.1 flow for Atlassian."""
    # TODO: Check for existing valid token

    auth_url = (
        f"{ATLASSIAN_AUTH_URL}?"
        f"client_id={ATLASSIAN_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=offline_access%20read%3Ajira-work%20write%3Ajira-work&"
        f"state=tasak-auth-state"
    )

    print("Your browser should open for authentication.")
    print(f"If it doesn't, please open this URL manually:\n{auth_url}")
    webbrowser.open(auth_url)

    httpd = None
    try:
        with socketserver.TCPServer(("", 8989), OAuthCallbackHandler) as httpd:
            print("\nWaiting for authentication... (Listening on port 8989)")
            while authorization_code is None:
                httpd.handle_request()

        print("Authorization code received. Exchanging for access token...")
        _exchange_code_for_token(authorization_code)

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        if httpd:
            httpd.server_close()


def _exchange_code_for_token(code: str):
    """Exchanges the authorization code for an access token and refresh token."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": ATLASSIAN_CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(ATLASSIAN_TOKEN_URL, data=payload)

    if response.status_code == 200:
        token_data = response.json()
        _save_token("atlassian", token_data)
        print("Successfully authenticated and saved tokens.")
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
    os.chmod(
        AUTH_FILE_PATH, 0o600
    )  # Set file permissions to be readable/writable only by the user


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TASAK Authentication Helper")
    parser.add_argument(
        "app_name",
        help="The name of the application to authenticate with (e.g., 'atlassian')",
    )
    args = parser.parse_args()
    run_auth_app(args.app_name)
