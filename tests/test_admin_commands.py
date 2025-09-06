"""Unit tests for admin_commands module."""

import argparse
from unittest.mock import Mock, mock_open, patch, MagicMock

import pytest

from tasak.admin_commands import (
    handle_admin_command,
    handle_auth,
    handle_clear,
    handle_info,
    handle_list,
    handle_refresh,
    refresh_app_schema,
    setup_admin_subparsers,
)


class TestSetupAdminSubparsers:
    """Test setup_admin_subparsers function."""

    def test_auth_command_structure(self):
        """Test auth command arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="admin_command")
        setup_admin_subparsers(subparsers)

        # Test with all auth flags
        args = parser.parse_args(["auth", "app", "--check"])
        assert args.app == "app"
        assert args.check is True

    def test_refresh_command_structure(self):
        """Test refresh command arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="admin_command")
        setup_admin_subparsers(subparsers)

        # refresh can take app name or --all
        args = parser.parse_args(["refresh", "--all", "--force"])
        assert args.all is True
        assert args.force is True

    def test_list_command_structure(self):
        """Test list command with verbose flag."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="admin_command")
        setup_admin_subparsers(subparsers)

        args = parser.parse_args(["list", "--verbose"])
        assert args.verbose is True

    def test_clear_command_structure(self):
        """Test clear command arguments."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="admin_command")
        setup_admin_subparsers(subparsers)

        args = parser.parse_args(["clear", "app", "--cache", "--auth"])
        assert args.app == "app"
        assert args.cache is True
        assert args.auth is True


class TestHandleAdminCommand:
    """Test handle_admin_command function."""

    @patch("tasak.admin_commands.handle_auth")
    def test_dispatch_auth_command(self, mock_auth):
        """Test dispatching to auth handler."""
        args = Mock(admin_command="auth")
        config = {}

        handle_admin_command(args, config)
        mock_auth.assert_called_once_with(args, config)

    @patch("tasak.admin_commands.handle_refresh")
    def test_dispatch_refresh_command(self, mock_refresh):
        """Test dispatching to refresh handler."""
        args = Mock(admin_command="refresh")
        config = {}

        handle_admin_command(args, config)
        mock_refresh.assert_called_once_with(args, config)

    def test_unknown_command(self, capsys):
        """Test handling unknown admin command."""
        args = Mock(admin_command="unknown")
        config = {}

        with pytest.raises(SystemExit):
            handle_admin_command(args, config)

        captured = capsys.readouterr()
        assert "Unknown admin command: unknown" in captured.err

    def test_no_admin_command(self, capsys):
        """Test handling when no admin command specified."""
        args = Mock(spec=[])  # No admin_command attribute
        config = {}

        with pytest.raises(SystemExit):
            handle_admin_command(args, config)

        captured = capsys.readouterr()
        assert "No admin command specified" in captured.err


class TestHandleAuth:
    """Test handle_auth function."""

    def test_app_not_found(self, capsys):
        """Test when app is not in config."""
        args = Mock(app="nonexistent", check=False, clear=False, refresh=False)
        config = {}

        with pytest.raises(SystemExit) as exc_info:
            handle_auth(args, config)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Application 'nonexistent' not found" in captured.err

    def test_non_mcp_remote_app(self, capsys):
        """Test auth command on non-mcp-remote app."""
        args = Mock(app="test_app", check=False, clear=False, refresh=False)
        config = {"test_app": {"type": "cmd"}}

        handle_auth(args, config)

        captured = capsys.readouterr()
        assert "does not require authentication" in captured.err

    @patch("tasak.admin_commands.Path.exists")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"test_app": {"token": "test", "expires_at": 0}}',
    )
    def test_check_existing_auth(self, mock_file, mock_exists, capsys):
        """Test checking existing auth."""
        mock_exists.return_value = True
        args = Mock(app="test_app", check=True, clear=False, refresh=False)
        config = {
            "test_app": {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
        }

        handle_auth(args, config)

        captured = capsys.readouterr()
        assert "Authenticated for 'test_app'" in captured.out

    @patch("tasak.admin_commands.Path.exists")
    def test_check_no_auth(self, mock_exists, capsys):
        """Test checking when no auth exists."""
        mock_exists.return_value = False
        args = Mock(app="test_app", check=True, clear=False, refresh=False)
        config = {
            "test_app": {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
        }

        handle_auth(args, config)

        captured = capsys.readouterr()
        assert "Not authenticated for 'test_app'" in captured.out

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"test_app": {"token": "test"}}',
    )
    @patch("tasak.admin_commands.Path.exists")
    def test_clear_auth(self, mock_exists, mock_file, capsys):
        """Test clearing authentication."""
        mock_exists.return_value = True
        args = Mock(app="test_app", check=False, clear=True, refresh=False)
        config = {
            "test_app": {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
        }

        handle_auth(args, config)

        captured = capsys.readouterr()
        assert "Authentication data cleared for 'test_app'" in captured.out

    def test_refresh_auth(self, capsys):
        """Test refreshing authentication."""
        args = Mock(app="test_app", check=False, clear=False, refresh=True)
        config = {
            "test_app": {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
        }

        handle_auth(args, config)

        captured = capsys.readouterr()
        assert "Refreshing authentication for 'test_app'" in captured.out
        assert "Token refresh not yet implemented" in captured.out

    @patch("tasak.admin_commands.run_auth_app")
    def test_auth_run(self, mock_run_auth, capsys):
        """Test running authentication for mcp-remote app."""
        args = Mock(app="test_app", check=False, clear=False, refresh=False)
        config = {
            "test_app": {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
        }

        handle_auth(args, config)

        mock_run_auth.assert_called_once_with("test_app", server_url="http://test")
        captured = capsys.readouterr()
        assert "Authenticating with 'test_app'" in captured.out


class TestHandleRefresh:
    """Test handle_refresh function."""

    @patch("tasak.admin_commands.refresh_app_schema")
    def test_refresh_all_apps(self, mock_refresh, capsys):
        """Test refreshing all apps."""
        args = Mock(app=None, all=True, force=False)
        config = {
            "app1": {"type": "mcp"},
            "app2": {"type": "mcp-remote"},
            "apps_config": {"enabled_apps": ["app1", "app2"]},
        }

        handle_refresh(args, config)

        assert mock_refresh.call_count == 2
        mock_refresh.assert_any_call("app1", {"type": "mcp"}, False)
        mock_refresh.assert_any_call("app2", {"type": "mcp-remote"}, False)

    @patch("tasak.admin_commands.refresh_app_schema")
    def test_refresh_specific_app(self, mock_refresh, capsys):
        """Test refreshing specific app."""
        args = Mock(app="test_app", all=False, force=True)
        config = {"test_app": {"type": "mcp"}}

        handle_refresh(args, config)

        mock_refresh.assert_called_once_with("test_app", {"type": "mcp"}, True)

    def test_refresh_nonexistent_app(self, capsys):
        """Test refreshing non-existent app."""
        args = Mock(app="nonexistent", all=False, force=False)
        config = {}

        with pytest.raises(SystemExit) as exc_info:
            handle_refresh(args, config)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Application 'nonexistent' not found" in captured.err

    def test_refresh_no_args(self, capsys):
        """Test refresh with no app or --all."""
        args = Mock(app=None, all=False, force=False)
        config = {}

        with pytest.raises(SystemExit):
            handle_refresh(args, config)

        captured = capsys.readouterr()
        assert "Specify an app name or use --all" in captured.err


class TestRefreshAppSchema:
    """Test refresh_app_schema function."""

    @patch("tasak.admin_commands.SchemaManager")
    @patch("tasak.admin_commands.MCPRealClient")
    def test_refresh_mcp_app(self, mock_client_class, mock_schema_class, capsys):
        """Test refreshing MCP app schema."""
        mock_client = Mock()
        mock_client.get_tool_definitions.return_value = [{"name": "tool1"}]
        mock_client_class.return_value = mock_client

        mock_schema = Mock()
        mock_schema.save_schema.return_value = "/path/to/schema.json"
        mock_schema_class.return_value = mock_schema

        app_config = {"type": "mcp", "meta": {"command": "test_server"}}
        refresh_app_schema("test_app", app_config)

        captured = capsys.readouterr()
        assert "Schema refreshed for 'test_app' (1 tools)" in captured.out

    @patch("tasak.mcp_remote_client.MCPRemoteClient")
    def test_refresh_mcp_remote_app(self, mock_client_class, capsys):
        """Test refreshing MCP-remote app schema."""
        mock_client = Mock()
        mock_client.get_tool_definitions.return_value = []
        mock_client_class.return_value = mock_client

        # Mock the module import
        with patch.dict(
            "sys.modules",
            {"tasak.mcp_remote_client": Mock(MCPRemoteClient=mock_client_class)},
        ):
            app_config = {"type": "mcp-remote", "meta": {"server_url": "http://test"}}
            refresh_app_schema("test_app", app_config)

        captured = capsys.readouterr()
        assert "Failed to refresh schema for 'test_app'" in captured.out

    def test_refresh_unsupported_app_type(self, capsys):
        """Test refreshing schema for unsupported app type."""
        app_config = {"type": "cmd"}
        refresh_app_schema("test_app", app_config)

        captured = capsys.readouterr()
        assert "Unsupported app type: cmd" in captured.out


class TestHandleClear:
    """Test handle_clear function."""

    def test_clear_app_not_found(self, capsys):
        """Test clearing cache for non-existent app."""
        args = Mock(app="nonexistent", all=False, cache=False, auth=False, schema=False)
        config = {}

        with pytest.raises(SystemExit) as exc_info:
            handle_clear(args, config)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Application 'nonexistent' not found" in captured.err

    @patch("tasak.admin_commands.Path.unlink")
    @patch("tasak.admin_commands.Path.exists")
    def test_clear_cache(self, mock_exists, mock_unlink, capsys):
        """Test clearing cache."""
        mock_exists.return_value = True
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        args = Mock(app="test_app", all=False, cache=True, auth=False, schema=False)
        config = {"test_app": {"type": "mcp"}}

        with patch("tasak.admin_commands.Path", return_value=mock_path):
            handle_clear(args, config)

        captured = capsys.readouterr()
        assert "Cache cleared for 'test_app'" in captured.out

    @patch("builtins.open", new_callable=mock_open, read_data='{"test_app": {}}')
    @patch("tasak.admin_commands.Path.exists")
    def test_clear_auth(self, mock_exists, mock_file, capsys):
        """Test clearing auth data."""
        mock_exists.return_value = True
        args = Mock(app="test_app", all=False, cache=False, auth=True, schema=False)
        config = {"test_app": {"type": "mcp-remote"}}

        handle_clear(args, config)

        captured = capsys.readouterr()
        assert "Authentication cleared for 'test_app'" in captured.out

    @patch("tasak.admin_commands.Path.exists")
    def test_clear_all(self, mock_exists, capsys):
        """Test clearing all data."""
        # Return True for auth file, False for cache and schema
        mock_exists.side_effect = [False, True, False]

        args = Mock(app="test_app", all=True, cache=False, auth=False, schema=False)
        config = {"test_app": {"type": "mcp"}}

        with patch("builtins.open", mock_open(read_data='{"test_app": {}}')):
            handle_clear(args, config)

        captured = capsys.readouterr()
        # Should report no cache/schema but clear auth
        assert "No cache found" in captured.out
        assert "Authentication cleared" in captured.out
        assert "No schema found" in captured.out


class TestHandleInfo:
    """Test handle_info function."""

    def test_info_app_not_found(self, capsys):
        """Test info for non-existent app."""
        args = Mock(app="nonexistent")
        config = {}

        with pytest.raises(SystemExit) as exc_info:
            handle_info(args, config)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Application 'nonexistent' not found" in captured.err

    def test_info_basic_app(self, capsys):
        """Test info for basic app."""
        args = Mock(app="test_app")
        config = {
            "test_app": {
                "name": "Test Application",
                "type": "cmd",
                "meta": {"command": "echo test"},
            }
        }

        with patch("tasak.admin_commands.Path.exists", return_value=False):
            handle_info(args, config)

        captured = capsys.readouterr()
        assert "Application: test_app" in captured.out
        assert "Type: cmd" in captured.out
        assert "Name: Test Application" in captured.out

    @patch("tasak.admin_commands.SchemaManager")
    def test_info_with_schema(self, mock_schema_class, capsys):
        """Test info with schema."""
        mock_schema = Mock()
        mock_schema.load_schema.return_value = {
            "tools": [{"name": "tool1"}],
            "last_updated": "2024-01-01",
        }
        mock_schema.get_schema_age_days.return_value = 5
        mock_schema_class.return_value = mock_schema

        args = Mock(app="test_app")
        config = {"test_app": {"type": "mcp", "name": "Test MCP"}}

        with patch("tasak.admin_commands.Path.exists", return_value=False):
            handle_info(args, config)

        captured = capsys.readouterr()
        assert "Application: test_app" in captured.out
        assert "Type: mcp" in captured.out
        assert "Schema: 1 tools (5 days old)" in captured.out


class TestHandleList:
    """Test handle_list function."""

    def test_list_no_apps(self, capsys):
        """Test listing when no apps configured."""
        args = Mock(verbose=False)
        config = {"apps_config": {"enabled_apps": []}}

        handle_list(args, config)

        captured = capsys.readouterr()
        assert "No applications configured" in captured.out

    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("tasak.admin_commands.Path.exists")
    def test_list_apps(self, mock_exists, mock_file, capsys):
        """Test listing configured apps."""
        mock_exists.return_value = False
        args = Mock(verbose=False)
        config = {
            "apps_config": {"enabled_apps": ["app1", "app2"]},
            "app1": {"type": "cmd", "name": "Command App"},
            "app2": {"type": "mcp", "name": "MCP App"},
        }

        handle_list(args, config)

        captured = capsys.readouterr()
        assert "app1" in captured.out
        assert "cmd" in captured.out
        assert "Command App" in captured.out
        assert "app2" in captured.out
        assert "mcp" in captured.out

    @patch("builtins.open", new_callable=mock_open, read_data='{"app1": {}}')
    @patch("tasak.admin_commands.Path.exists")
    def test_list_apps_with_auth(self, mock_exists, mock_file, capsys):
        """Test listing shows auth status."""
        mock_exists.side_effect = [
            True,
            False,
            False,
        ]  # auth exists, no cache, no schema
        args = Mock(verbose=False)
        config = {
            "apps_config": {"enabled_apps": ["app1"]},
            "app1": {"type": "mcp-remote", "name": "Remote App"},
        }

        handle_list(args, config)

        captured = capsys.readouterr()
        assert "[auth]" in captured.out

    def test_list_verbose(self, capsys):
        """Test verbose listing."""
        args = Mock(verbose=True)
        config = {
            "apps_config": {"enabled_apps": ["app1"]},
            "app1": {
                "type": "cmd",
                "name": "Command App",
                "meta": {"command": "echo test", "mode": "proxy"},
            },
        }

        with patch("tasak.admin_commands.Path.exists", return_value=False):
            handle_list(args, config)

        captured = capsys.readouterr()
        assert "Command: echo test" in captured.out
        assert "Mode: proxy" in captured.out
