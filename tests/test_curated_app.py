"""Unit tests for curated app functionality."""

import unittest
from unittest.mock import Mock, patch
from io import StringIO

from tasak.curated_app import CuratedApp


class TestVariableInterpolation(unittest.TestCase):
    """Test variable interpolation functionality."""

    def setUp(self):
        self.app = CuratedApp("test", {"name": "Test App"})

    def test_simple_interpolation(self):
        template = "Hello ${name}"
        context = {"name": "World"}
        result, _ = self.app._interpolate(template, context)
        self.assertEqual(result, "Hello World")

    def test_default_value_interpolation(self):
        template = "Hello ${name:-Guest}"
        context = {}
        result, _ = self.app._interpolate(template, context)
        self.assertEqual(result, "Hello Guest")

    def test_existing_value_overrides_default(self):
        template = "Hello ${name:-Guest}"
        context = {"name": "Alice"}
        result, _ = self.app._interpolate(template, context)
        self.assertEqual(result, "Hello Alice")

    def test_list_interpolation(self):
        template = ["echo", "${message}"]
        context = {"message": "Hello"}
        result, _ = self.app._interpolate(template, context)
        self.assertEqual(result, ["echo", "Hello"])

    def test_dict_interpolation(self):
        template = {"project": "${project_name}", "priority": "${priority:-low}"}
        context = {"project_name": "TASAK"}
        result, _ = self.app._interpolate(template, context)
        self.assertEqual(result, {"project": "TASAK", "priority": "low"})

    def test_nested_interpolation(self):
        template = {
            "command": ["echo", "${message}"],
            "args": {"level": "${level:-info}"},
        }
        context = {"message": "Test"}
        result, _ = self.app._interpolate(template, context)
        expected = {"command": ["echo", "Test"], "args": {"level": "info"}}
        self.assertEqual(result, expected)


class TestCommandBuilding(unittest.TestCase):
    """Test command structure building."""

    def test_simple_command_building(self):
        config = {
            "commands": [
                {
                    "name": "test",
                    "description": "Test command",
                    "backend": {"type": "cmd", "command": ["echo", "test"]},
                }
            ]
        }
        app = CuratedApp("test", config)
        self.assertIn("test", app.commands)
        self.assertEqual(app.commands["test"].name, "test")
        self.assertEqual(app.commands["test"].description, "Test command")

    def test_subcommand_building(self):
        config = {
            "commands": [
                {
                    "name": "task",
                    "description": "Task management",
                    "subcommands": [
                        {
                            "name": "list",
                            "description": "List tasks",
                            "backend": {"type": "cmd", "command": ["echo", "list"]},
                        }
                    ],
                }
            ]
        }
        app = CuratedApp("test", config)
        self.assertIn("task", app.commands)
        self.assertEqual(len(app.commands["task"].subcommands), 1)
        self.assertEqual(app.commands["task"].subcommands[0].name, "list")


class TestBackendExecution(unittest.TestCase):
    """Test different backend execution types."""

    @patch("subprocess.run")
    def test_cmd_backend_execution(self, mock_run):
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {"type": "cmd", "command": ["echo", "hello"]},
                }
            ]
        }
        app = CuratedApp("test", config)
        app.run(["test"])

        mock_run.assert_called_once_with(
            ["echo", "hello"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_cmd_backend_with_interpolation(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "greet",
                    "backend": {"type": "cmd", "command": ["echo", "Hello"]},
                    "params": [{"name": "--name", "required": True}],
                }
            ]
        }
        app = CuratedApp("test", config)
        app.run(["greet", "--name", "Alice"])

        mock_run.assert_called_once_with(
            ["echo", "Hello", "--name", "Alice"], capture_output=True, text=True
        )

    @patch("subprocess.run")
    def test_composite_backend_sequential(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "build",
                    "backend": {
                        "type": "composite",
                        "steps": [
                            {"type": "cmd", "command": ["echo", "step1"]},
                            {"type": "cmd", "command": ["echo", "step2"]},
                        ],
                    },
                }
            ]
        }
        app = CuratedApp("test", config)
        app.run(["build"])

        # Should execute both commands in sequence
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(["echo", "step1"], capture_output=True, text=True)
        mock_run.assert_any_call(["echo", "step2"], capture_output=True, text=True)

    @patch("subprocess.run")
    def test_conditional_backend(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "deploy",
                    "backend": {
                        "type": "conditional",
                        "condition": "${env}",
                        "branches": {
                            "dev": {"type": "cmd", "command": ["echo", "dev"]},
                            "prod": {"type": "cmd", "command": ["echo", "prod"]},
                        },
                    },
                    "params": [
                        {"name": "--env", "required": True, "choices": ["dev", "prod"]}
                    ],
                }
            ]
        }
        app = CuratedApp("test", config)

        # Test dev branch
        app.run(["deploy", "--env", "dev"])
        mock_run.assert_called_with(
            ["echo", "dev", "--env", "dev"], capture_output=True, text=True
        )

        # Test prod branch
        mock_run.reset_mock()
        app.run(["deploy", "--env", "prod"])
        mock_run.assert_called_with(
            ["echo", "prod", "--env", "prod"], capture_output=True, text=True
        )

    @patch("subprocess.Popen")
    def test_async_command_execution(self, mock_popen):
        mock_process = Mock()
        mock_popen.return_value = mock_process

        config = {
            "commands": [
                {
                    "name": "start",
                    "backend": {
                        "type": "cmd",
                        "command": ["server", "start"],
                        "async": True,
                    },
                }
            ]
        }
        app = CuratedApp("test", config)
        app.run(["start"])

        # Should use Popen for async execution
        mock_popen.assert_called_once_with(["server", "start"])

    @patch("subprocess.run")
    def test_required_command_failure(self, mock_run):
        mock_run.return_value = Mock(returncode=1)

        config = {
            "commands": [
                {
                    "name": "test",
                    "backend": {"type": "cmd", "command": ["false"], "required": True},
                }
            ]
        }
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            app.run(["test"])
        self.assertEqual(cm.exception.code, 1)


class TestParameterHandling(unittest.TestCase):
    """Test parameter parsing and validation."""

    @patch("subprocess.run")
    def test_required_parameter(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "create",
                    "backend": {"type": "cmd", "command": ["touch"]},
                    "params": [{"name": "--file", "required": True}],
                }
            ]
        }
        app = CuratedApp("test", config)

        # Should fail without required parameter
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["create"])

    @patch("subprocess.run")
    def test_parameter_with_choices(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "set",
                    "backend": {"type": "cmd", "command": ["echo"]},
                    "params": [
                        {
                            "name": "--level",
                            "choices": ["low", "high"],
                            "required": True,
                        }
                    ],
                }
            ]
        }
        app = CuratedApp("test", config)

        # Should accept valid choice
        app.run(["set", "--level", "high"])
        mock_run.assert_called_with(
            ["echo", "--level", "high"], capture_output=True, text=True
        )

        # Should reject invalid choice
        with self.assertRaises(SystemExit):
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["set", "--level", "medium"])

    @patch("subprocess.run")
    def test_parameter_with_default(self, mock_run):
        mock_run.return_value = Mock(returncode=0)

        config = {
            "commands": [
                {
                    "name": "list",
                    "backend": {"type": "cmd", "command": ["ls"]},
                    "params": [{"name": "--path", "default": "/tmp"}],
                }
            ]
        }
        app = CuratedApp("test", config)

        # Should use default when not provided
        app.run(["list"])
        mock_run.assert_called_with(
            ["ls", "--path", "/tmp"], capture_output=True, text=True
        )

        # Should override default when provided
        mock_run.reset_mock()
        app.run(["list", "--path", "/home"])
        mock_run.assert_called_with(
            ["ls", "--path", "/home"], capture_output=True, text=True
        )


class TestHelpDisplay(unittest.TestCase):
    """Test help message generation."""

    def test_app_help(self):
        config = {
            "name": "Test App",
            "description": "A test application",
            "commands": [
                {"name": "cmd1", "description": "First command"},
                {"name": "cmd2", "description": "Second command"},
            ],
        }
        app = CuratedApp("test", config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            app._show_help()
            output = mock_stdout.getvalue()

        self.assertIn("Test App", output)
        self.assertIn("A test application", output)
        self.assertIn("cmd1", output)
        self.assertIn("First command", output)
        self.assertIn("cmd2", output)
        self.assertIn("Second command", output)

    def test_help_with_subcommands(self):
        config = {
            "commands": [
                {
                    "name": "task",
                    "description": "Task management",
                    "subcommands": [
                        {"name": "list", "description": "List tasks"},
                        {"name": "create", "description": "Create task"},
                    ],
                }
            ]
        }
        app = CuratedApp("test", config)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            app._show_help()
            output = mock_stdout.getvalue()

        self.assertIn("task", output)
        self.assertIn("Task management", output)
        self.assertIn("list", output)
        self.assertIn("create", output)


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios."""

    def test_unknown_command(self):
        config = {"commands": []}
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["nonexistent"])
        self.assertEqual(cm.exception.code, 1)

    def test_unknown_backend_type(self):
        config = {"commands": [{"name": "test", "backend": {"type": "unknown"}}]}
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["test"])
        self.assertEqual(cm.exception.code, 1)

    @patch("subprocess.run")
    def test_command_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        config = {
            "commands": [
                {"name": "test", "backend": {"type": "cmd", "command": ["nonexistent"]}}
            ]
        }
        app = CuratedApp("test", config)

        with self.assertRaises(SystemExit) as cm:
            with patch("sys.stderr", new_callable=StringIO):
                app.run(["test"])
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
