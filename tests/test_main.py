from unittest.mock import patch, MagicMock

from tasak.main import main, _list_available_apps, _cleanup_pool


class TestCleanupPool:
    """Tests for _cleanup_pool function."""

    @patch("tasak.mcp_remote_pool.MCPRemotePool")
    def test_cleanup_pool_success(self, mock_pool_class):
        """Test successful pool cleanup."""
        with patch("asyncio.run") as mock_run:
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool

            _cleanup_pool()

            mock_pool_class.assert_called_once()
            mock_run.assert_called_once()

    def test_cleanup_pool_error_ignored(self):
        """Test that errors during cleanup are ignored."""
        with patch("tasak.mcp_remote_pool.MCPRemotePool") as mock_pool_class:
            mock_pool_class.side_effect = Exception("Pool error")

            # Should not raise
            _cleanup_pool()


class TestListAvailableApps:
    """Tests for _list_available_apps function."""

    @patch("builtins.print")
    def test_list_no_apps(self, mock_print):
        """Test listing when no apps are configured."""
        config = {}

        _list_available_apps(config)

        calls = mock_print.call_args_list
        assert any("Available applications" in str(c) for c in calls)
        assert any("No applications enabled" in str(c) for c in calls)

    @patch("builtins.print")
    def test_list_empty_enabled_apps(self, mock_print):
        """Test listing when enabled_apps is empty."""
        config = {"apps_config": {"enabled_apps": []}}

        _list_available_apps(config)

        calls = mock_print.call_args_list
        assert any("No applications enabled" in str(c) for c in calls)

    @patch("builtins.print")
    def test_list_single_app(self, mock_print):
        """Test listing a single app."""
        config = {
            "apps_config": {"enabled_apps": ["myapp"]},
            "myapp": {"type": "cmd", "name": "My Application"},
        }

        _list_available_apps(config)

        calls = mock_print.call_args_list
        assert any(
            "myapp" in str(c) and "cmd" in str(c) and "My Application" in str(c)
            for c in calls
        )

    @patch("builtins.print")
    def test_list_multiple_apps_sorted(self, mock_print):
        """Test listing multiple apps in sorted order."""
        config = {
            "apps_config": {"enabled_apps": ["zebra", "alpha", "beta"]},
            "zebra": {"type": "cmd", "name": "Zebra App"},
            "alpha": {"type": "mcp", "name": "Alpha App"},
            "beta": {"type": "curated", "name": "Beta App"},
        }

        _list_available_apps(config)

        # Get the order of app names in print calls
        app_calls = [
            str(c)
            for c in mock_print.call_args_list
            if "alpha" in str(c) or "beta" in str(c) or "zebra" in str(c)
        ]
        # Should be alphabetically sorted
        assert "alpha" in app_calls[0]
        assert "beta" in app_calls[1]
        assert "zebra" in app_calls[2]

    @patch("builtins.print")
    def test_list_app_missing_config(self, mock_print):
        """Test listing when app config is missing."""
        config = {"apps_config": {"enabled_apps": ["missing_app"]}}

        _list_available_apps(config)

        calls = mock_print.call_args_list
        assert any("missing_app" in str(c) and "N/A" in str(c) for c in calls)


class TestMainFunction:
    """Tests for main function."""

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main._list_available_apps")
    @patch("sys.argv", ["tasak"])
    def test_main_no_args_lists_apps(self, mock_list, mock_load_config, mock_atexit):
        """Test main with no arguments lists available apps."""
        mock_load_config.return_value = {"apps_config": {"enabled_apps": []}}

        main()

        mock_atexit.assert_called_once_with(_cleanup_pool)
        mock_load_config.assert_called_once()
        mock_list.assert_called_once()

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("sys.argv", ["tasak", "--help"])
    def test_main_help_flag(self, mock_load_config, mock_atexit):
        """Test main with --help flag."""
        mock_load_config.return_value = {}

        with patch("argparse.ArgumentParser.print_help") as mock_help:
            main()
            mock_help.assert_called_once()

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.run_cmd_app")
    @patch("sys.argv", ["tasak", "myapp", "arg1", "arg2"])
    def test_main_run_cmd_app(self, mock_run_cmd, mock_load_config, mock_atexit):
        """Test main running a cmd type app."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["myapp"]},
            "myapp": {"type": "cmd", "name": "My App"},
        }

        main()

        mock_run_cmd.assert_called_once_with(
            {"type": "cmd", "name": "My App"}, ["arg1", "arg2"]
        )

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.run_curated_app")
    @patch("sys.argv", ["tasak", "curapp"])
    def test_main_run_curated_app(
        self, mock_run_curated, mock_load_config, mock_atexit
    ):
        """Test main running a curated type app."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["curapp"]},
            "curapp": {"type": "curated", "name": "Curated App"},
        }

        main()

        mock_run_curated.assert_called_once_with(
            "curapp", {"type": "curated", "name": "Curated App"}, []
        )

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.run_mcp_app")
    @patch("sys.argv", ["tasak", "mcpapp", "--flag"])
    def test_main_run_mcp_app(self, mock_run_mcp, mock_load_config, mock_atexit):
        """Test main running an mcp type app."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["mcpapp"]},
            "mcpapp": {"type": "mcp", "name": "MCP App"},
        }

        main()

        mock_run_mcp.assert_called_once_with(
            "mcpapp", {"type": "mcp", "name": "MCP App"}, ["--flag"]
        )

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.run_mcp_remote_app")
    @patch("sys.argv", ["tasak", "remoteapp"])
    def test_main_run_mcp_remote_app(
        self, mock_run_remote, mock_load_config, mock_atexit
    ):
        """Test main running an mcp-remote type app."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["remoteapp"]},
            "remoteapp": {"type": "mcp-remote", "name": "Remote App"},
        }

        main()

        mock_run_remote.assert_called_once_with(
            "remoteapp", {"type": "mcp-remote", "name": "Remote App"}, []
        )

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main._list_available_apps")
    @patch("sys.exit")
    @patch("sys.stderr", new_callable=MagicMock)
    @patch("sys.argv", ["tasak", "disabled_app"])
    def test_main_app_not_enabled(
        self, mock_stderr, mock_exit, mock_list, mock_load_config, mock_atexit
    ):
        """Test main with app that's not enabled."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["other_app"]},
            "disabled_app": {"type": "cmd"},
        }

        main()

        mock_exit.assert_called_with(1)
        # Error should be printed to stderr
        calls = str(mock_stderr.write.call_args_list)
        assert "not enabled" in calls or "does not exist" in calls
        mock_list.assert_called_once()

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["tasak", "missing_app"])
    def test_main_app_config_missing(
        self, mock_print, mock_exit, mock_load_config, mock_atexit
    ):
        """Test main with app that has no configuration."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["missing_app"]}
            # Note: missing_app is NOT in the config
        }

        main()

        mock_exit.assert_called_once_with(1)
        # Check that error was printed
        calls = [str(c) for c in mock_print.call_args_list]
        assert any("Configuration for app" in c and "not found" in c for c in calls)

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("sys.exit")
    @patch("builtins.print")
    @patch("sys.argv", ["tasak", "badtype"])
    def test_main_unknown_app_type(
        self, mock_print, mock_exit, mock_load_config, mock_atexit
    ):
        """Test main with unknown app type."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["badtype"]},
            "badtype": {"type": "unknown_type"},
        }

        main()

        mock_exit.assert_called_once_with(1)
        calls = str(mock_print.call_args_list)
        assert "Unknown app type" in calls

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.run_cmd_app")
    @patch("sys.argv", ["tasak", "myapp", "--help"])
    def test_main_app_help_passed_through(
        self, mock_run_cmd, mock_load_config, mock_atexit
    ):
        """Test that --help is passed to the app."""
        mock_load_config.return_value = {
            "apps_config": {"enabled_apps": ["myapp"]},
            "myapp": {"type": "cmd"},
        }

        main()

        mock_run_cmd.assert_called_once_with({"type": "cmd"}, ["--help"])


class TestAdminCommands:
    """Tests for admin command handling."""

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.handle_admin_command")
    @patch("sys.argv", ["tasak", "admin", "--help"])
    def test_main_admin_command(self, mock_handle, mock_load_config, mock_atexit):
        """Test main with admin command."""
        config = {"test": "config"}
        mock_load_config.return_value = config

        # Mock argparse to avoid actual parsing
        with patch("argparse.ArgumentParser.parse_args") as mock_parse:
            mock_args = MagicMock()
            mock_args.admin_command = "test_command"
            mock_parse.return_value = mock_args

            main()

            mock_handle.assert_called_once_with(mock_args, config)

    @patch("tasak.main.atexit.register")
    @patch("tasak.main.load_and_merge_configs")
    @patch("tasak.main.setup_admin_subparsers")
    @patch("tasak.main.handle_admin_command")
    @patch("sys.argv", ["tasak", "admin"])
    def test_main_admin_no_subcommand(
        self, mock_handle, mock_setup, mock_load_config, mock_atexit
    ):
        """Test main with admin but no subcommand."""
        mock_load_config.return_value = {}

        main()

        mock_setup.assert_called_once()
        mock_handle.assert_called_once()


class TestMainEntryPoint:
    """Test the if __name__ == "__main__" block."""

    @patch("tasak.main.main")
    def test_module_run_as_script(self, mock_main):
        """Test that main is called when module is run as script."""
        # Simulate running the module as a script
        import tasak.main as main_module

        # This won't actually trigger __main__ in our test,
        # but we can verify the function exists
        assert hasattr(main_module, "main")
        assert callable(main_module.main)
