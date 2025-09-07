"""
Client for communicating with TASAK daemon.
"""

import sys
import json
from typing import Any, Dict, List, Optional
import requests
from pathlib import Path
import os

from ..mcp_real_client import MCPRealClient


DAEMON_URL = "http://127.0.0.1:8765"
TIMEOUT = 60  # seconds (aligns with server init timeouts)
CLIENT_VERBOSE = (
    os.environ.get("TASAK_DEBUG") == "1" or os.environ.get("TASAK_VERBOSE") == "1"
)
DISABLE_AUTOSTART_FILE = Path.home() / ".tasak" / "daemon.disabled"


class DaemonClient:
    """Client for communicating with TASAK daemon."""

    def __init__(self, app_name: str, config: Dict[str, Any]):
        self.app_name = app_name
        self.config = config
        self.daemon_url = DAEMON_URL

        # Extract MCP config
        if "_mcp_config" in config:
            self.mcp_config = config["_mcp_config"]
        else:
            # Load from file if needed
            config_file = config.get("config")
            if config_file:
                config_path = Path(config_file)
                if not config_path.is_absolute():
                    config_path = Path.home() / ".tasak" / config_path

                if config_path.exists():
                    with open(config_path, "r") as f:
                        self.mcp_config = json.load(f)
                else:
                    self.mcp_config = {}
            else:
                self.mcp_config = {}

    def is_daemon_available(self) -> bool:
        """Check if daemon is running and available."""
        try:
            response = requests.get(f"{self.daemon_url}/health", timeout=1)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        # Attempt autostart unless disabled or in debug
        if os.environ.get("TASAK_DEBUG") == "1":
            return False
        if os.environ.get("TASAK_NO_DAEMON") == "1":
            return False
        if DISABLE_AUTOSTART_FILE.exists():
            return False

        try:
            # Lazy import to avoid cycles
            from .manager import start_daemon

            started = start_daemon()
            if started:
                # Re-check health quickly
                try:
                    response = requests.get(f"{self.daemon_url}/health", timeout=2)
                    return response.status_code == 200
                except Exception:
                    return False
        except Exception:
            return False

        return False

    def get_tool_definitions(self) -> Optional[List[Dict[str, Any]]]:
        """Get tool definitions from daemon."""
        try:
            print(
                f"Daemon: requesting tool list for '{self.app_name}'", file=sys.stderr
            )
            if CLIENT_VERBOSE:
                print(
                    f"Daemon: requesting tool list for '{self.app_name}'",
                    file=sys.stderr,
                )
            response = requests.post(
                f"{self.daemon_url}/tools/list/{self.app_name}",
                json=self.mcp_config,
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("tools", [])
            else:
                print(
                    f"Error fetching tools from daemon: {response.status_code}",
                    file=sys.stderr,
                )
                return None

        except requests.exceptions.Timeout:
            print("Daemon request timed out", file=sys.stderr)
            return None
        except requests.exceptions.ConnectionError:
            print("Could not connect to daemon", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error communicating with daemon: {e}", file=sys.stderr)
            return None

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool through the daemon."""
        try:
            # Prepare request with config in body
            request_data = {
                "tool_name": tool_name,
                "arguments": arguments,
                "config": self.mcp_config,
            }

            if CLIENT_VERBOSE:
                print(
                    f"Daemon: calling tool '{tool_name}' for '{self.app_name}'",
                    file=sys.stderr,
                )
            response = requests.post(
                f"{self.daemon_url}/tools/call/{self.app_name}",
                json=request_data,
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("result")
                else:
                    error = data.get("error", "Unknown error")
                    print(f"Tool execution failed: {error}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(
                    f"Error calling tool through daemon: {response.status_code}",
                    file=sys.stderr,
                )
                sys.exit(1)

        except requests.exceptions.Timeout:
            print("Daemon request timed out", file=sys.stderr)
            sys.exit(1)
        except requests.exceptions.ConnectionError:
            print("Could not connect to daemon", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error communicating with daemon: {e}", file=sys.stderr)
            sys.exit(1)


def get_mcp_client(app_name: str, app_config: Dict[str, Any]) -> Any:
    """
    Get an MCP client - either daemon client or direct client.

    This function checks if the daemon is running and uses it if available,
    otherwise falls back to direct MCP connection.
    """
    import os
    import time

    # Check if debug mode is enabled
    debug_mode = os.environ.get("TASAK_DEBUG") == "1"

    if debug_mode:
        print("🔍 Debug: Bypassing daemon, using direct connection", file=sys.stderr)
        start_time = time.time()
        client = MCPRealClient(app_name, app_config)
        print(
            f"🔍 Debug: Client initialization took {time.time() - start_time:.2f}s",
            file=sys.stderr,
        )
        return client

    # Try daemon first
    daemon_client = DaemonClient(app_name, app_config)

    if daemon_client.is_daemon_available():
        if CLIENT_VERBOSE:
            print("Using daemon for connection pooling", file=sys.stderr)
        return daemon_client
    else:
        # Fall back to direct connection
        print("Daemon not available, using direct connection", file=sys.stderr)
        return MCPRealClient(app_name, app_config)
