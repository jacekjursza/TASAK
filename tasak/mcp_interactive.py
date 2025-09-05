#!/usr/bin/env python3
"""Interactive client for MCP servers via mcp-remote."""

import json
import sys
import subprocess
import threading
import queue
import time


class MCPInteractiveClient:
    """Interactive client for communicating with MCP servers."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.process = None
        self.output_queue = queue.Queue()
        self.running = False

    def start(self):
        """Start the mcp-remote process."""
        cmd = ["npx", "-y", "mcp-remote", self.server_url]

        print(f"Starting MCP connection to {self.server_url}...", file=sys.stderr)

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        self.running = True

        # Start threads to read output
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

        # Wait for connection
        time.sleep(3)
        print(
            "\n✓ Connected! You can now interact with the MCP server.", file=sys.stderr
        )
        print("Commands:", file=sys.stderr)
        print("  list    - List available tools", file=sys.stderr)
        print("  call <tool> <args> - Call a tool", file=sys.stderr)
        print("  info    - Get server info", file=sys.stderr)
        print("  quit    - Exit", file=sys.stderr)
        print("-" * 50, file=sys.stderr)

    def _read_stdout(self):
        """Read stdout from the process."""
        while self.running and self.process:
            line = self.process.stdout.readline()
            if line:
                self.output_queue.put(("stdout", line.strip()))

    def _read_stderr(self):
        """Read stderr from the process."""
        while self.running and self.process:
            line = self.process.stderr.readline()
            if line:
                # Only show non-debug messages
                if not line.startswith("["):
                    self.output_queue.put(("stderr", line.strip()))

    def send_command(self, command: dict):
        """Send a JSON-RPC command to the MCP server."""
        if not self.process:
            print("Error: Not connected", file=sys.stderr)
            return

        json_cmd = json.dumps(command) + "\n"
        self.process.stdin.write(json_cmd)
        self.process.stdin.flush()

    def list_tools(self):
        """Request list of available tools."""
        self.send_command({"jsonrpc": "2.0", "method": "tools/list", "id": 1})

    def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool."""
        self.send_command(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": 2,
            }
        )

    def get_server_info(self):
        """Get server information."""
        self.send_command(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "tasak", "version": "0.1.0"},
                },
                "id": 0,
            }
        )

    def interactive_loop(self):
        """Run interactive command loop."""
        try:
            while self.running:
                # Print any queued output
                while not self.output_queue.empty():
                    source, line = self.output_queue.get()
                    if source == "stdout":
                        print(f"< {line}")
                    else:
                        print(f"! {line}", file=sys.stderr)

                # Get user input
                try:
                    cmd = input("> ").strip()
                except EOFError:
                    break

                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command == "quit" or command == "exit":
                    break
                elif command == "list":
                    self.list_tools()
                elif command == "info":
                    self.get_server_info()
                elif command == "call" and len(parts) >= 2:
                    tool_name = parts[1]
                    args = {}
                    if len(parts) > 2:
                        try:
                            # Try to parse remaining as JSON
                            args = json.loads(" ".join(parts[2:]))
                        except json.JSONDecodeError:
                            # Treat as simple string argument
                            args = {"query": " ".join(parts[2:])}
                    self.call_tool(tool_name, args)
                else:
                    print(
                        "Unknown command. Use: list, call <tool> <args>, info, quit",
                        file=sys.stderr,
                    )

        except KeyboardInterrupt:
            print("\nInterrupted", file=sys.stderr)
        finally:
            self.stop()

    def stop(self):
        """Stop the MCP process."""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("Disconnected", file=sys.stderr)


def main():
    """Main entry point for interactive MCP client."""
    if len(sys.argv) < 2:
        print("Usage: python -m tasak.mcp_interactive <server_url>", file=sys.stderr)
        print(
            "Example: python -m tasak.mcp_interactive https://mcp.atlassian.com/v1/sse",
            file=sys.stderr,
        )
        sys.exit(1)

    server_url = sys.argv[1]

    client = MCPInteractiveClient(server_url)
    client.start()
    client.interactive_loop()


if __name__ == "__main__":
    main()
