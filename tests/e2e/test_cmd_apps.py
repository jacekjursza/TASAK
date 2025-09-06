"""End-to-end tests for cmd type applications."""

import json
import os
import subprocess
from pathlib import Path


# Get the test directory
TEST_DIR = Path(__file__).parent
CONFIG_FILE = TEST_DIR / "tasak_test_config.yaml"


class TestCmdApps:
    """Test cmd type applications."""

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        # Ensure we're in the right directory
        os.chdir(Path(__file__).parent.parent.parent)

    def run_tasak(self, *args, env=None):
        """Helper to run tasak with test config."""
        test_env = os.environ.copy()
        test_env["TASAK_CONFIG"] = str(CONFIG_FILE)
        if env:
            test_env.update(env)

        cmd = ["tasak"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env)
        return result

    def test_cmd_curated_basic(self):
        """Test basic curated mode command."""
        result = self.run_tasak("hello", "greet")
        assert result.returncode == 0
        assert "Hello, World!" in result.stdout

    def test_cmd_curated_with_args(self):
        """Test curated mode with arguments."""
        result = self.run_tasak("hello", "greet", "--name", "Alice", "--repeat", "2")
        assert result.returncode == 0
        assert result.stdout.count("Hello, Alice!") == 2

    def test_cmd_curated_json_output(self):
        """Test curated mode with JSON output."""
        result = self.run_tasak("hello", "greet", "--name", "Bob", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["greeting"] == "Hello, Bob!"
        assert data["count"] == 1

    def test_cmd_proxy_mode(self):
        """Test proxy mode passing arguments directly."""
        result = self.run_tasak("hello-proxy", "--name", "Charlie")
        assert result.returncode == 0
        assert "Hello, Charlie!" in result.stdout

    def test_cmd_proxy_mode_with_multiple_args(self):
        """Test proxy mode with multiple arguments."""
        result = self.run_tasak(
            "hello-proxy", "--name", "Dave", "--repeat", "3", "--json"
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["messages"]) == 3
        assert all("Hello, Dave!" in msg for msg in data["messages"])

    def test_cmd_error_handling(self):
        """Test error handling in cmd apps."""
        result = self.run_tasak("hello", "greet", "--error")
        assert result.returncode != 0  # The mini app will exit with 2 for unknown arg
        assert "unrecognized arguments" in result.stderr

    def test_cmd_help(self):
        """Test help output for curated cmd."""
        result = self.run_tasak("hello", "greet", "--help")
        assert result.returncode == 0
        assert "Name to greet" in result.stdout
        assert "Number of times to repeat" in result.stdout

    def test_app_not_found(self):
        """Test running non-existent app."""
        result = self.run_tasak("nonexistent")
        assert result.returncode == 1
        assert (
            "not found" in result.stderr.lower() or "not exist" in result.stderr.lower()
        )

    def test_list_apps(self):
        """Test listing available apps."""
        result = self.run_tasak()
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert "hello-proxy" in result.stdout
        assert "test-mcp" in result.stdout


class TestCmdProxyVsCurated:
    """Test differences between proxy and curated modes."""

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        os.chdir(Path(__file__).parent.parent.parent)

    def run_tasak(self, *args):
        """Helper to run tasak with test config."""
        test_env = os.environ.copy()
        test_env["TASAK_CONFIG"] = str(CONFIG_FILE)

        cmd = ["tasak"] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, env=test_env)
        return result

    def test_proxy_preserves_exact_args(self):
        """Test that proxy mode preserves exact argument format."""
        # Proxy mode should pass args exactly as given
        result_proxy = self.run_tasak("hello-proxy", "--name=TestUser", "--repeat=2")
        assert result_proxy.returncode == 0
        assert "Hello, TestUser!" in result_proxy.stdout

    def test_curated_normalizes_args(self):
        """Test that curated mode normalizes arguments."""
        # Curated mode should handle both formats
        result1 = self.run_tasak("hello", "greet", "--name", "User1")
        result2 = self.run_tasak("hello", "greet", "--name=User1")

        assert result1.returncode == 0
        assert result2.returncode == 0
        assert result1.stdout == result2.stdout

    def test_unknown_args_handling(self):
        """Test how unknown arguments are handled."""
        # Proxy mode should pass unknown args to the command
        result_proxy = self.run_tasak("hello-proxy", "--unknown-flag")
        # The hello_cmd script will fail with unknown argument
        assert result_proxy.returncode != 0

        # Curated mode should reject unknown args at tasak level
        result_curated = self.run_tasak("hello", "greet", "--unknown-flag")
        assert result_curated.returncode != 0
