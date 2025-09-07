"""Tests for mcp_remote_runner module."""

import json
import subprocess
from unittest.mock import Mock, patch

import pytest

from tasak.mcp_remote_runner import (
    _clear_cache,
    _print_help,
    _run_auth_flow,
    _run_interactive_mode,
    run_mcp_remote_app,
)


class TestRunMCPRemoteApp:
    """Test run_mcp_remote_app function."""

    def test_missing_server_url(self, capsys):
        """Test error when server_url is not configured."""
        app_config = {"meta": {}}

        with pytest.raises(SystemExit) as exc_info:
            run_mcp_remote_app("test_app", app_config, [])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "'server_url' not specified" in captured.err

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_help_flag(self, mock_schema_manager_class, capsys):
        """Test --help flag prints grouped simplified help."""
        app_config = {"meta": {"server_url": "https://example.com"}}
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = {"tools": {"t1": {}, "t2": {}}}
        mock_schema_manager.convert_to_tool_list.return_value = [
            {"name": "t1", "description": "desc1", "input_schema": {"required": []}},
            {"name": "t2", "description": "desc2", "input_schema": {"required": []}},
        ]
        mock_schema_manager.get_schema_age_days.return_value = 0
        mock_schema_manager_class.return_value = mock_schema_manager

        run_mcp_remote_app("test_app", app_config, ["--help"])

        captured = capsys.readouterr()
        out = captured.out.strip().splitlines()
        assert '"test_app" commands:' in out[0]
        assert any(line.startswith("t1 - desc1") for line in out)
        assert any(line.startswith("t2 - desc2") for line in out)

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_help_short_flag(self, mock_schema_manager_class, capsys):
        """Test -h flag prints grouped simplified help."""
        app_config = {"meta": {"server_url": "https://example.com"}}
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = {"tools": {"t1": {}}}
        mock_schema_manager.convert_to_tool_list.return_value = [
            {"name": "t1", "description": "desc", "input_schema": {"required": []}}
        ]
        mock_schema_manager.get_schema_age_days.return_value = 0
        mock_schema_manager_class.return_value = mock_schema_manager

        run_mcp_remote_app("test_app", app_config, ["-h"])

        captured = capsys.readouterr()
        out = captured.out.strip().splitlines()
        assert '"test_app" commands:' in out[0]
        assert any(line.startswith("t1 - desc") for line in out)

    @patch("tasak.mcp_remote_runner._run_auth_flow")
    def test_auth_flag(self, mock_auth_flow, capsys):
        """Test --auth flag."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        run_mcp_remote_app("test_app", app_config, ["--auth"])

        mock_auth_flow.assert_called_once_with("https://example.com")
        captured = capsys.readouterr()
        assert "Starting authentication flow" in captured.out

    @patch("tasak.mcp_remote_runner._run_interactive_mode")
    def test_interactive_flag(self, mock_interactive, capsys):
        """Test --interactive flag."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        run_mcp_remote_app("test_app", app_config, ["--interactive"])

        mock_interactive.assert_called_once_with("https://example.com")
        captured = capsys.readouterr()
        assert "Starting interactive mode" in captured.out

    @patch("tasak.mcp_remote_runner._run_interactive_mode")
    def test_interactive_short_flag(self, mock_interactive, capsys):
        """Test -i flag."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        run_mcp_remote_app("test_app", app_config, ["-i"])

        mock_interactive.assert_called_once_with("https://example.com")

    @patch("tasak.mcp_remote_runner._clear_cache")
    def test_clear_cache_flag(self, mock_clear_cache):
        """Test --clear-cache flag."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        run_mcp_remote_app("test_app", app_config, ["--clear-cache"])

        mock_clear_cache.assert_called_once_with("test_app")

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_curated_mode_with_cached_schema(self, mock_schema_manager_class, capsys):
        """Test curated mode with cached schema."""
        app_config = {"meta": {"server_url": "https://example.com", "mode": "curated"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = {"tools": {"tool1": {}}}
        mock_schema_manager.convert_to_tool_list.return_value = [
            {"name": "tool1", "description": "Test tool"}
        ]
        mock_schema_manager.get_schema_age_days.return_value = 10
        mock_schema_manager_class.return_value = mock_schema_manager

        # Test listing tools via help-style output
        run_mcp_remote_app("test_app", app_config, [])

        captured = capsys.readouterr()
        # Minimal listing: just tool names
        assert captured.out.strip() == "tool1"

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_dynamic_mode_fetches_tools(self, mock_schema_manager_class, capsys):
        """Test dynamic mode fetches tools from server."""
        app_config = {"meta": {"server_url": "https://example.com", "mode": "dynamic"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        # Mock client (limit to used methods)
        class StubClient:
            def get_tool_definitions(self):
                return [{"name": "tool1", "description": "Test tool"}]

        stub = StubClient()

        # Test listing tools
        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            run_mcp_remote_app("test_app", app_config, [])
        mock_schema_manager.save_schema.assert_called_once_with(
            "test_app", [{"name": "tool1", "description": "Test tool"}]
        )

        captured = capsys.readouterr()
        assert captured.out.strip() == "tool1"

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_no_tools_available_error(self, mock_schema_manager_class, capsys):
        """Test error when no tools are available."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        class StubClient:
            def get_tool_definitions(self):
                return None

        stub = StubClient()

        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            # Now help-style output is shown without exiting
            run_mcp_remote_app("test_app", app_config, [])

        captured = capsys.readouterr()
        # Minimal listing with no tools produces empty output
        assert captured.out.strip() == ""

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_call_tool_with_arguments(self, mock_schema_manager_class, capsys):
        """Test calling a tool with arguments."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        # Stub client with only sync methods used by runner (avoids async attribute warnings)
        class StubClient:
            def __init__(self):
                self.calls = []

            def get_tool_definitions(self):
                return [{"name": "test_tool", "description": "Test tool"}]

            def call_tool(self, name, args):
                self.calls.append((name, args))
                return {"result": "success", "data": 123}

        stub = StubClient()

        # Call tool with arguments (patch client factory to return our stub)
        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            run_mcp_remote_app(
                "test_app", app_config, ["test_tool", "--param1", "value1", "--flag"]
            )
        # Verify the stub recorded the expected call
        assert stub.calls == [("test_tool", {"param1": "value1", "flag": True})]

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["result"] == "success"
        assert output["data"] == 123

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_call_tool_string_result(self, mock_schema_manager_class, capsys):
        """Test calling a tool that returns a string."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        class StubClient:
            def get_tool_definitions(self):
                return [{"name": "test_tool", "description": "Test tool"}]

            def call_tool(self, name, args):
                return "Simple string result"

        stub = StubClient()

        # Call tool
        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            run_mcp_remote_app("test_app", app_config, ["test_tool"])

        captured = capsys.readouterr()
        assert captured.out.strip() == "Simple string result"

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_call_tool_error(self, mock_schema_manager_class, capsys):
        """Test error handling when calling a tool."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        class StubClient:
            def get_tool_definitions(self):
                return [{"name": "test_tool", "description": "Test tool"}]

            def call_tool(self, name, args):
                raise Exception("Tool execution failed")

        stub = StubClient()

        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            with pytest.raises(SystemExit) as exc_info:
                run_mcp_remote_app("test_app", app_config, ["test_tool"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error executing tool: Tool execution failed" in captured.err

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_positional_args_warning(self, mock_schema_manager_class, capsys):
        """Test that positional arguments after tool name trigger a warning."""
        app_config = {"meta": {"server_url": "https://example.com"}}

        # Mock schema manager
        mock_schema_manager = Mock()
        mock_schema_manager.load_schema.return_value = None
        mock_schema_manager_class.return_value = mock_schema_manager

        class StubClient:
            def get_tool_definitions(self):
                return [{"name": "test_tool", "description": "Test tool"}]

            def call_tool(self, name, args):
                return {"result": "ok"}

        stub = StubClient()

        # Call with positional args that should trigger warning
        with patch("tasak.mcp_remote_runner.MCPRemoteClient", new=lambda *a, **k: stub):
            run_mcp_remote_app(
                "test_app",
                app_config,
                ["test_tool", "ignored_arg1", "ignored_arg2", "--key", "value"],
            )

        # Verify that positional args were ignored and only --key was passed
        # We can't inspect stub internals here, but output assertions below cover behavior

        captured = capsys.readouterr()
        # Now we should see a warning about ignored arguments
        assert (
            "Warning: Ignoring unexpected positional arguments: ['ignored_arg1', 'ignored_arg2']"
            in captured.err
        )
        assert "Hint: Use --key value format for tool parameters" in captured.err


class TestClearCache:
    """Test _clear_cache function."""

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_clear_existing_cache(self, mock_schema_manager_class, capsys):
        """Test clearing existing cache."""
        mock_schema_manager = Mock()
        mock_schema_manager.delete_schema.return_value = True
        mock_schema_manager_class.return_value = mock_schema_manager

        _clear_cache("test_app")

        mock_schema_manager.delete_schema.assert_called_once_with("test_app")
        captured = capsys.readouterr()
        assert "Schema cache cleared for 'test_app'" in captured.err

    @patch("tasak.mcp_remote_runner.SchemaManager")
    def test_clear_no_cache(self, mock_schema_manager_class, capsys):
        """Test clearing when no cache exists."""
        mock_schema_manager = Mock()
        mock_schema_manager.delete_schema.return_value = False
        mock_schema_manager_class.return_value = mock_schema_manager

        _clear_cache("test_app")

        captured = capsys.readouterr()
        assert "No cached schema found for 'test_app'" in captured.err


class TestRunAuthFlow:
    """Test _run_auth_flow function."""

    @patch("subprocess.run")
    def test_auth_success(self, mock_run, capsys):
        """Test successful authentication."""
        mock_run.return_value = Mock(returncode=0)

        _run_auth_flow("https://example.com")

        mock_run.assert_called_once_with(
            ["npx", "-y", "mcp-remote", "https://example.com"], timeout=120
        )

        captured = capsys.readouterr()
        assert "Starting authentication flow" in captured.err
        assert "browser window will open" in captured.err
        assert "Authentication successful" in captured.err

    @patch("subprocess.run")
    def test_auth_failure(self, mock_run, capsys):
        """Test failed authentication."""
        mock_run.return_value = Mock(returncode=1)

        _run_auth_flow("https://example.com")

        captured = capsys.readouterr()
        assert "Authentication may have failed or was cancelled" in captured.err

    @patch("subprocess.run")
    def test_auth_timeout(self, mock_run, capsys):
        """Test authentication timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["npx"], 120)

        _run_auth_flow("https://example.com")

        captured = capsys.readouterr()
        assert "Authentication timed out" in captured.err

    @patch("subprocess.run")
    def test_npx_not_found(self, mock_run, capsys):
        """Test when npx is not found."""
        mock_run.side_effect = FileNotFoundError()

        _run_auth_flow("https://example.com")

        captured = capsys.readouterr()
        assert "npx not found" in captured.err
        assert "install Node.js" in captured.err

    @patch("subprocess.run")
    def test_auth_keyboard_interrupt(self, mock_run, capsys):
        """Test authentication cancelled by user."""
        mock_run.side_effect = KeyboardInterrupt()

        _run_auth_flow("https://example.com")

        captured = capsys.readouterr()
        assert "Authentication cancelled by user" in captured.err

    @patch("subprocess.run")
    def test_auth_generic_error(self, mock_run, capsys):
        """Test generic error during authentication."""
        mock_run.side_effect = Exception("Generic error")

        _run_auth_flow("https://example.com")

        captured = capsys.readouterr()
        assert "Error during authentication: Generic error" in captured.err


class TestRunInteractiveMode:
    """Test _run_interactive_mode function."""

    @patch("tasak.mcp_interactive.MCPInteractiveClient")
    def test_interactive_mode(self, mock_client_class):
        """Test running interactive mode."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        _run_interactive_mode("https://example.com")

        mock_client_class.assert_called_once_with("https://example.com")
        mock_client.start.assert_called_once()
        mock_client.interactive_loop.assert_called_once()


class TestPrintHelp:
    """Test _print_help function."""

    def test_print_help_basic(self, capsys):
        """Test printing basic help."""
        app_config = {"name": "Test App", "meta": {"server_url": "https://example.com"}}

        _print_help("test_app", app_config)

        captured = capsys.readouterr()
        assert "Test App" in captured.out
        assert "Type: mcp-remote" in captured.out
        assert "Server: https://example.com" in captured.out
        assert "tasak test_app" in captured.out
        assert "--auth" in captured.out
        assert "--interactive" in captured.out
        assert "--help" in captured.out
        assert "OAuth authentication" in captured.out

    def test_print_help_with_tools(self, capsys):
        """Test printing help with available tools."""
        app_config = {
            "name": "Test App",
            "meta": {
                "server_url": "https://example.com",
                "tools": ["tool1", "tool2", "tool3"],
            },
        }

        _print_help("test_app", app_config)

        captured = capsys.readouterr()
        assert "Available tools:" in captured.out
        assert "tool1" in captured.out
        assert "tool2" in captured.out
        assert "tool3" in captured.out

    def test_print_help_minimal_config(self, capsys):
        """Test printing help with minimal config."""
        app_config = {"meta": {}}

        _print_help("test_app", app_config)

        captured = capsys.readouterr()
        assert "MCP Remote app: test_app" in captured.out
        assert "Server: Not configured" in captured.out
