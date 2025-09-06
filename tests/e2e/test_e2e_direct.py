"""Direct E2E tests using tasak API instead of subprocess."""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import yaml


# Add tasak to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import tasak.main
import tasak.config
import tasak.app_runner


class TestDirectCmdApps:
    """Test cmd apps directly using the API."""

    def setup_method(self):
        """Setup test config for each test."""
        self.test_config = {
            "apps_config": {
                "enabled_apps": ["test-hello", "test-hello-proxy"],
            },
            "test-hello": {
                "type": "curated",
                "name": "Test Hello App",
                "commands": [
                    {
                        "name": "greet",
                        "backend": {
                            "type": "cmd",
                            "command": f"python {Path(__file__).parent / 'mini-apps' / 'hello_cmd.py'}",
                        },
                        "params": [
                            {
                                "name": "--name",
                                "type": "str",
                                "default": "World",
                                "help": "Name to greet",
                            },
                            {
                                "name": "--repeat",
                                "type": "int",
                                "default": 1,
                                "help": "Number of times",
                            },
                            {
                                "name": "--json",
                                "type": "bool",
                                "action": "store_true",
                                "help": "Output as JSON",
                            },
                        ],
                    }
                ],
            },
            "test-hello-proxy": {
                "type": "cmd",
                "command": f"python {Path(__file__).parent / 'mini-apps' / 'hello_cmd.py'}",
            },
        }

    @patch("sys.argv", ["tasak", "test-hello", "greet"])
    @patch("tasak.main.load_and_merge_configs")
    def test_run_cmd_curated_basic(self, mock_config, capsys):
        """Test running a curated cmd app."""
        mock_config.return_value = self.test_config

        try:
            tasak.main.main()
        except SystemExit as e:
            assert e.code == 0

        captured = capsys.readouterr()
        assert "Hello, World!" in captured.out

    def test_run_cmd_curated_with_args(self, capsys):
        """Test running curated cmd with arguments."""
        with patch("tasak.main.load_and_merge_configs", return_value=self.test_config):
            with patch(
                "sys.argv",
                ["tasak", "test-hello", "greet", "--name", "Alice", "--repeat", "2"],
            ):
                try:
                    tasak.main.main()
                except SystemExit as e:
                    assert e.code == 0

                captured = capsys.readouterr()
                assert captured.out.count("Hello, Alice!") == 2

    def test_run_cmd_proxy(self, capsys):
        """Test running proxy mode cmd."""
        with patch("tasak.main.load_and_merge_configs", return_value=self.test_config):
            with patch("sys.argv", ["tasak", "test-hello-proxy", "--name", "Bob"]):
                try:
                    tasak.main.main()
                except SystemExit as e:
                    assert e.code == 0

                captured = capsys.readouterr()
                assert "Hello, Bob!" in captured.out

    def test_list_apps(self, capsys):
        """Test listing available apps."""
        with patch("tasak.main.load_and_merge_configs", return_value=self.test_config):
            with patch("sys.argv", ["tasak"]):
                try:
                    tasak.main.main()
                except SystemExit as e:
                    assert e.code == 0

                captured = capsys.readouterr()
                assert "test-hello" in captured.out
                assert "test-hello-proxy" in captured.out

    def test_app_not_found(self, capsys):
        """Test running non-existent app."""
        with patch("tasak.main.load_and_merge_configs", return_value=self.test_config):
            with patch("sys.argv", ["tasak", "nonexistent"]):
                try:
                    tasak.main.main()
                except SystemExit as e:
                    assert e.code == 1

                captured = capsys.readouterr()
                assert (
                    "not found" in captured.err.lower()
                    or "not exist" in captured.err.lower()
                )

    def test_cmd_with_json_output(self, capsys):
        """Test cmd with JSON output."""
        with patch("tasak.main.load_and_merge_configs", return_value=self.test_config):
            with patch(
                "sys.argv",
                ["tasak", "test-hello", "greet", "--json", "--name", "Charlie"],
            ):
                try:
                    tasak.main.main()
                except SystemExit as e:
                    assert e.code == 0

                captured = capsys.readouterr()
                data = json.loads(captured.out)
                assert data["greeting"] == "Hello, Charlie!"
                assert data["count"] == 1


"""
Note: A previous test class (TestDirectMCPApps) attempted to spin up an MCP
server directly here. That scenario is already covered by
tests/e2e/test_mcp_apps.py via the tasak CLI, so we removed the duplicate,
environment-sensitive direct test for stability.
"""


class TestRealApps:
    """Test with real existing apps from user's config."""

    def test_list_real_apps(self, capsys):
        """Test listing real configured apps."""
        # This uses the actual user config
        with patch("sys.argv", ["tasak"]):
            try:
                tasak.main.main()
            except SystemExit as e:
                assert e.code == 0

            captured = capsys.readouterr()
            # Should list at least some apps
            assert "Available applications:" in captured.out
            # Check for some known apps from user's config
            assert "auth" in captured.out or "atlassian" in captured.out

    def test_auth_help(self, capsys):
        """Test help for auth app."""
        with patch("sys.argv", ["tasak", "auth", "--help"]):
            try:
                tasak.main.main()
            except SystemExit as e:
                # Help exits with 0
                assert e.code == 0

            captured = capsys.readouterr()
            assert "help" in captured.out.lower() or "usage" in captured.out.lower()


class TestConfigMerging:
    """Test configuration merging logic."""

    def test_config_merge_order(self):
        """Test that configs are merged in correct order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a test config structure
            (tmppath / ".tasak").mkdir()

            config1 = {
                "apps": {
                    "app1": {"type": "cmd", "command": "echo", "value": "from_parent"}
                }
            }

            config2 = {
                "apps": {
                    "app1": {"type": "cmd", "command": "echo", "value": "from_child"},
                    "app2": {"type": "cmd", "command": "ls"},
                }
            }

            with open(tmppath / "tasak.yaml", "w") as f:
                yaml.dump(config1, f)

            with open(tmppath / ".tasak" / "tasak.yaml", "w") as f:
                yaml.dump(config2, f)

            # Change to test directory
            original_cwd = os.getcwd()
            try:
                os.chdir(tmppath)

                # Load configs
                merged = tasak.config.load_and_merge_configs()

                # Later configs should override earlier ones
                assert merged["apps"]["app1"]["value"] == "from_child"
                assert "app2" in merged["apps"]

            finally:
                os.chdir(original_cwd)
