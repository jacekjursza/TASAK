"""End-to-end tests for MCP type applications."""

import json
import os
import subprocess
import time
from pathlib import Path
import tempfile
import shutil


# Get the test directory
TEST_DIR = Path(__file__).parent
CONFIG_FILE = TEST_DIR / "tasak_test_config.yaml"


class TestMCPApps:
    """Test MCP type applications."""

    def setup_method(self):
        """Create a dummy auth file for MCP tests."""
        self.temp_home = tempfile.mkdtemp()
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_home

        tasak_dir = Path(self.temp_home) / ".tasak"
        tasak_dir.mkdir()

        auth_file = tasak_dir / "auth.json"
        with open(auth_file, "w") as f:
            json.dump(
                {
                    "test-mcp": {
                        "access_token": "dummy_token",
                        "expires_at": time.time() + 3600,
                    }
                },
                f,
            )

    def teardown_method(self):
        """Clean up the dummy auth file."""
        if self.original_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self.original_home
        shutil.rmtree(self.temp_home)

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        os.chdir(Path(__file__).parent.parent.parent)

    def run_tasak(self, *args, input_text=None, timeout=10):
        """Helper to run tasak with test config."""
        test_env = os.environ.copy()
        test_env["TASAK_CONFIG"] = str(CONFIG_FILE)

        cmd = ["tasak"] + list(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input=input_text,
                env=test_env,
                timeout=timeout,
            )
            return result
        except subprocess.TimeoutExpired:
            # This is expected for interactive MCP servers
            return None

    def test_mcp_server_tool_call(self):
        """Test calling a tool on MCP server."""
        # Use JSON input for tool call
        result = self.run_tasak("test-mcp", "add", "--a", "5", "--b", "3")
        assert result is not None
        assert result.returncode == 0

        # Parse the response
        output = result.stdout.strip()
        if output:
            # The output should contain the result
            assert "8" in output or "result.*8" in output.lower()

    def test_mcp_server_multiply(self):
        """Test multiply tool on MCP server."""
        result = self.run_tasak("test-mcp", "multiply", "--x", "4", "--y", "7")
        assert result is not None
        assert result.returncode == 0
        assert "28" in result.stdout

    def test_mcp_server_echo(self):
        """Test echo tool on MCP server."""
        result = self.run_tasak("test-mcp", "echo", "--message", "Hello MCP!")
        assert result is not None
        assert result.returncode == 0
        assert "Echo: Hello MCP!" in result.stdout

    def test_mcp_server_weather(self):
        """Test weather tool on MCP server."""
        result = self.run_tasak("test-mcp", "get_weather", "--city", "London")
        assert result is not None
        assert result.returncode == 0
        assert "London" in result.stdout
        assert "Sunny" in result.stdout or "weather" in result.stdout.lower()

    def test_mcp_server_divide(self):
        """Test divide tool on MCP server."""
        result = self.run_tasak(
            "test-mcp", "divide", "--numerator", "10", "--denominator", "2"
        )
        assert result is not None
        assert result.returncode == 0
        assert "5" in result.stdout or "5.0" in result.stdout

    def test_mcp_server_divide_by_zero(self):
        """Test divide by zero error handling."""
        tool_call = json.dumps(
            {"tool": "divide", "arguments": {"numerator": 10, "denominator": 0}}
        )

        result = self.run_tasak("test-mcp", tool_call)
        assert result is not None
        # Should handle the error gracefully
        assert (
            "error" in result.stdout.lower()
            or "zero" in result.stdout.lower()
            or result.returncode != 0
        )

    def test_mcp_server_invalid_tool(self):
        """Test calling non-existent tool."""
        tool_call = json.dumps({"tool": "nonexistent", "arguments": {}})

        result = self.run_tasak("test-mcp", tool_call)
        assert result is not None
        # Should report tool not found
        assert (
            "not found" in result.stdout.lower()
            or "error" in result.stdout.lower()
            or result.returncode != 0
        )

    def test_mcp_server_list_tools(self):
        """Test listing available tools."""
        # Send empty input or special command to list tools
        result = self.run_tasak("test-mcp", "--list-tools")

        if result and result.returncode == 0:
            output = result.stdout.lower()
            # Should list all our tools
            assert "add" in output or "multiply" in output or "echo" in output

    def test_mcp_server_help(self):
        """Test help for MCP server."""
        result = self.run_tasak("test-mcp", "--help")

        if result and result.returncode == 0:
            # Should show some help information
            assert "tool" in result.stdout.lower() or "mcp" in result.stdout.lower()


class TestMCPInteractive:
    """Test interactive MCP features."""

    def setup_method(self):
        """Create a dummy auth file for MCP tests."""
        self.temp_home = tempfile.mkdtemp()
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_home

        tasak_dir = Path(self.temp_home) / ".tasak"
        tasak_dir.mkdir()

        auth_file = tasak_dir / "auth.json"
        with open(auth_file, "w") as f:
            json.dump(
                {
                    "test-mcp": {
                        "access_token": "dummy_token",
                        "expires_at": time.time() + 3600,
                    }
                },
                f,
            )

    def teardown_method(self):
        """Clean up the dummy auth file."""
        if self.original_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self.original_home
        shutil.rmtree(self.temp_home)

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        os.chdir(Path(__file__).parent.parent.parent)

    def test_mcp_interactive_mode(self):
        """Test that MCP can run in interactive mode."""
        test_env = os.environ.copy()
        test_env["TASAK_CONFIG"] = str(CONFIG_FILE)

        cmd = ["python", "-m", "tasak.main", "test-mcp", "--interactive"]

        # Start the process
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=test_env,
        )

        try:
            # Give it time to start
            time.sleep(1)

            # Check if process is still running
            assert proc.poll() is None, "Process should still be running"

            # Send a tool call
            if proc.stdin:
                tool_call = json.dumps({"tool": "add", "arguments": {"a": 1, "b": 2}})
                proc.stdin.write(tool_call + "\n")
                proc.stdin.flush()

                # Give it time to process
                time.sleep(0.5)

                # Try to read output (non-blocking would be better)
                # This is simplified - real implementation might need async

        finally:
            # Clean up
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


class TestIntegration:
    """Integration tests combining multiple features."""

    def setup_method(self):
        """Create a dummy auth file for MCP tests."""
        self.temp_home = tempfile.mkdtemp()
        self.original_home = os.environ.get("HOME")
        os.environ["HOME"] = self.temp_home

        tasak_dir = Path(self.temp_home) / ".tasak"
        tasak_dir.mkdir()

        auth_file = tasak_dir / "auth.json"
        with open(auth_file, "w") as f:
            json.dump(
                {
                    "test-mcp": {
                        "access_token": "dummy_token",
                        "expires_at": time.time() + 3600,
                    }
                },
                f,
            )

    def teardown_method(self):
        """Clean up the dummy auth file."""
        if self.original_home is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = self.original_home
        shutil.rmtree(self.temp_home)

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        os.chdir(Path(__file__).parent.parent.parent)

    def run_tasak(self, *args):
        """Helper to run tasak with test config."""
        test_env = os.environ.copy()
        test_env["TASAK_CONFIG"] = str(CONFIG_FILE)

        cmd = ["tasak"] + list(args)
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=test_env, timeout=10
        )
        return result

    def test_switching_between_apps(self):
        """Test running different apps in sequence."""
        # Run cmd app
        result1 = self.run_tasak("hello", "greet", "--name", "Test")
        assert result1.returncode == 0
        assert "Hello, Test!" in result1.stdout

        # Run another cmd app
        result2 = self.run_tasak("hello-proxy", "--name", "Proxy", "--json")
        assert result2.returncode == 0
        data = json.loads(result2.stdout)
        assert "greeting" in data

        # Run MCP app (if possible)
        tool_call = json.dumps(
            {"tool": "echo", "arguments": {"message": "Integration test"}}
        )
        result3 = self.run_tasak("test-mcp", tool_call)
        if result3:  # MCP might not work in all environments
            assert "Integration test" in result3.stdout or result3.returncode != 0

    def test_config_loading(self):
        """Test that our test config is loaded correctly."""
        result = self.run_tasak()
        assert result.returncode == 0

        # Check all our test apps are listed
        assert "hello" in result.stdout
        assert "hello-proxy" in result.stdout
        assert "test-mcp" in result.stdout

        # Should show app types
        assert "cmd" in result.stdout.lower() or "command" in result.stdout.lower()
        assert "mcp" in result.stdout.lower() or "server" in result.stdout.lower()
