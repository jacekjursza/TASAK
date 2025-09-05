"""Unit tests for MCP integration in curated apps."""

import unittest
from unittest.mock import Mock, patch
from io import StringIO

from tasak.curated_app import CuratedApp


class TestMCPBackendIntegration(unittest.TestCase):
    """Test MCP backend integration in curated apps."""

    @patch("tasak.curated_app.load_and_merge_configs")
    @patch("tasak.curated_app.MCPRealClient")
    def test_mcp_backend_execution(self, mock_mcp_client_class, mock_load_config):
        """Test that MCP backend correctly calls MCP client."""
        # Setup mock configuration
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["test_mcp_app"]},
            "test_mcp_app": {"type": "mcp", "config": "test.json"},
        }

        # Setup mock MCP client
        mock_client = Mock()
        mock_client.call_tool.return_value = {"result": "success"}
        mock_mcp_client_class.return_value = mock_client

        # Create curated app with MCP backend
        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {
                        "type": "mcp",
                        "app": "test_mcp_app",
                        "tool": "test_tool",
                        "args": {"param": "value"},
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        # Execute command
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            app.run(["test"])
            output = mock_stdout.getvalue()

        # Verify MCP client was created and called
        mock_mcp_client_class.assert_called_once_with(
            "test_mcp_app", {"type": "mcp", "config": "test.json"}
        )
        mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})

        # Verify output
        self.assertIn('"result": "success"', output)

    @patch("tasak.curated_app.load_and_merge_configs")
    @patch("tasak.curated_app.MCPRealClient")
    def test_mcp_backend_with_interpolation(
        self, mock_mcp_client_class, mock_load_config
    ):
        """Test MCP backend with variable interpolation."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["test_mcp_app"]},
            "test_mcp_app": {"type": "mcp"},
        }

        mock_client = Mock()
        mock_client.call_tool.return_value = "Task created"
        mock_mcp_client_class.return_value = mock_client

        config = {
            "commands": [
                {
                    "name": "create",
                    "backend": {
                        "type": "mcp",
                        "app": "test_mcp_app",
                        "tool": "create_task",
                        "args": {
                            "title": "${title}",
                            "priority": "${priority:-medium}",
                        },
                    },
                    "params": [{"name": "--title", "required": True}],
                }
            ]
        }
        app = CuratedApp("test", config)

        app.run(["create", "--title", "Fix bug"])

        # Verify interpolation worked
        mock_client.call_tool.assert_called_once_with(
            "create_task", {"title": "Fix bug", "priority": "medium"}
        )

    @patch("tasak.curated_app.load_and_merge_configs")
    @patch("tasak.curated_app.MCPRealClient")
    def test_mcp_backend_with_capture(self, mock_mcp_client_class, mock_load_config):
        """Test MCP backend result capture for use in subsequent steps."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["test_mcp_app"]},
            "test_mcp_app": {"type": "mcp"},
        }

        mock_client = Mock()
        mock_client.call_tool.return_value = {"task_id": "12345"}
        mock_mcp_client_class.return_value = mock_client

        config = {
            "commands": [
                {
                    "name": "workflow",
                    "backend": {
                        "type": "composite",
                        "steps": [
                            {
                                "type": "mcp",
                                "app": "test_mcp_app",
                                "tool": "create_task",
                                "args": {"title": "Test"},
                                "capture": "task_result",
                            },
                            {
                                "type": "cmd",
                                "command": ["echo", "Created task: ${task_result}"],
                            },
                        ],
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            app.run(["workflow"])

            # Verify the captured result was used in the next step
            mock_run.assert_called_with(
                ["echo", "Created task: {'task_id': '12345'}"],
                capture_output=False,
                text=True,
            )

    @patch("tasak.curated_app.load_and_merge_configs")
    @patch("tasak.curated_app.MCPRemoteClient")
    def test_mcp_remote_backend(self, mock_remote_client_class, mock_load_config):
        """Test MCP remote backend uses MCPRemoteClient."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["atlassian"]},
            "atlassian": {
                "type": "mcp-remote",
                "meta": {"server_url": "https://mcp.atlassian.com"},
            },
        }

        mock_client = Mock()
        mock_client.call_tool.return_value = {"issue": "TASK-123"}
        mock_remote_client_class.return_value = mock_client

        config = {
            "commands": [
                {
                    "name": "create-jira",
                    "backend": {
                        "type": "mcp",
                        "app": "atlassian",
                        "tool": "jira_create_issue",
                        "args": {"title": "Test Issue"},
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        app.run(["create-jira"])

        # Verify MCPRemoteClient was used
        mock_remote_client_class.assert_called_once()
        mock_client.call_tool.assert_called_once_with(
            "jira_create_issue", {"title": "Test Issue"}
        )

    @patch("tasak.curated_app.load_and_merge_configs")
    def test_mcp_backend_app_not_found(self, mock_load_config):
        """Test error handling when MCP app is not found."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": []},
        }

        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {
                        "type": "mcp",
                        "app": "nonexistent",
                        "tool": "test_tool",
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                app.run(["test"])

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("not found", mock_stderr.getvalue())

    @patch("tasak.curated_app.load_and_merge_configs")
    @patch("tasak.curated_app.MCPRealClient")
    def test_mcp_backend_tool_error(self, mock_mcp_client_class, mock_load_config):
        """Test error handling when MCP tool call fails."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["test_mcp_app"]},
            "test_mcp_app": {"type": "mcp"},
        }

        mock_client = Mock()
        mock_client.call_tool.side_effect = Exception("Tool not found")
        mock_mcp_client_class.return_value = mock_client

        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {
                        "type": "mcp",
                        "app": "test_mcp_app",
                        "tool": "bad_tool",
                        "required": True,
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["test"])

        self.assertEqual(cm.exception.code, 1)

    @patch("tasak.curated_app.load_and_merge_configs")
    def test_mcp_backend_missing_params(self, mock_load_config):
        """Test error when MCP backend missing required params."""
        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {
                        "type": "mcp",
                        # Missing app and tool
                    },
                }
            ]
        }
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
                app.run(["test"])

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("requires 'app' and 'tool'", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
