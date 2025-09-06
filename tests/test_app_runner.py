import subprocess
from unittest.mock import patch, MagicMock, call

from tasak.app_runner import run_cmd_app, _run_proxy_mode, _execute_command


class TestRunCmdApp:
    """Tests for run_cmd_app function."""

    @patch("tasak.app_runner._run_proxy_mode")
    def test_run_cmd_app_calls_proxy_mode(self, mock_run_proxy):
        """Test that run_cmd_app calls _run_proxy_mode with correct args."""
        app_config = {
            "name": "test_app",
            "type": "cmd",
            "meta": {"command": "echo hello"},
        }
        app_args = ["--flag", "value"]

        run_cmd_app(app_config, app_args)

        mock_run_proxy.assert_called_once_with(
            {"command": "echo hello"}, ["--flag", "value"]
        )

    @patch("tasak.app_runner._run_proxy_mode")
    def test_run_cmd_app_with_missing_meta(self, mock_run_proxy):
        """Test run_cmd_app with missing meta section."""
        app_config = {"name": "test_app", "type": "cmd"}
        app_args = []

        run_cmd_app(app_config, app_args)

        mock_run_proxy.assert_called_once_with({}, [])


class TestRunProxyMode:
    """Tests for _run_proxy_mode function."""

    @patch("tasak.app_runner._execute_command")
    def test_proxy_mode_with_string_command(self, mock_execute):
        """Test proxy mode with command as string."""
        meta = {"command": "git status"}
        app_args = ["--short"]

        _run_proxy_mode(meta, app_args)

        mock_execute.assert_called_once_with(["git", "status", "--short"])

    @patch("tasak.app_runner._execute_command")
    def test_proxy_mode_with_list_command(self, mock_execute):
        """Test proxy mode with command as list."""
        meta = {"command": ["docker", "run", "ubuntu"]}
        app_args = ["--rm", "-it"]

        _run_proxy_mode(meta, app_args)

        mock_execute.assert_called_once_with(["docker", "run", "ubuntu", "--rm", "-it"])

    @patch("tasak.app_runner._execute_command")
    def test_proxy_mode_with_no_args(self, mock_execute):
        """Test proxy mode with no additional arguments."""
        meta = {"command": "ls"}
        app_args = []

        _run_proxy_mode(meta, app_args)

        mock_execute.assert_called_once_with(["ls"])

    def test_proxy_mode_missing_command(self):
        """Test proxy mode when command is missing."""
        meta = {}
        app_args = ["--flag"]

        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                _run_proxy_mode(meta, app_args)

                # Check error message was printed and exit was called
                mock_print.assert_called_once()
                assert "'command' not specified" in str(mock_print.call_args)
                mock_exit.assert_called_once_with(1)

    def test_proxy_mode_empty_command(self):
        """Test proxy mode when command is empty string."""
        meta = {"command": ""}
        app_args = []

        with patch("sys.exit") as mock_exit:
            with patch("builtins.print") as mock_print:
                _run_proxy_mode(meta, app_args)

                # Empty string is falsy, so should print error and exit
                mock_print.assert_called_once()
                assert "'command' not specified" in str(mock_print.call_args)
                mock_exit.assert_called_once_with(1)


class TestExecuteCommand:
    """Tests for _execute_command function."""

    @patch("subprocess.Popen")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_success(self, mock_stderr, mock_popen):
        """Test successful command execution."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdout = ["Line 1\n", "Line 2\n"]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        _execute_command(["echo", "hello"])

        mock_popen.assert_called_once_with(
            ["echo", "hello"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        mock_process.wait.assert_called_once()

    @patch("subprocess.Popen")
    @patch("sys.exit")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_non_zero_exit(self, mock_stderr, mock_exit, mock_popen):
        """Test command execution with non-zero exit code."""
        mock_process = MagicMock()
        mock_process.stdout = ["Error output\n"]
        mock_process.returncode = 2
        mock_popen.return_value = mock_process

        _execute_command(["false"])

        mock_exit.assert_called_once_with(2)

    @patch("subprocess.Popen")
    @patch("sys.exit")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_file_not_found(self, mock_stderr, mock_exit, mock_popen):
        """Test command execution when command not found."""
        mock_popen.side_effect = FileNotFoundError()

        _execute_command(["nonexistent_command"])

        mock_stderr.write.assert_called()
        mock_exit.assert_called_once_with(1)

    @patch("subprocess.Popen")
    @patch("sys.exit")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_keyboard_interrupt(
        self, mock_stderr, mock_exit, mock_popen
    ):
        """Test command execution interrupted by user."""
        mock_process = MagicMock()
        mock_process.stdout = MagicMock()
        mock_process.stdout.__iter__.side_effect = KeyboardInterrupt()
        mock_popen.return_value = mock_process

        _execute_command(["sleep", "10"])

        mock_exit.assert_called_once_with(130)

    @patch("subprocess.Popen")
    @patch("sys.exit")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_generic_exception(
        self, mock_stderr, mock_exit, mock_popen
    ):
        """Test command execution with unexpected exception."""
        mock_popen.side_effect = Exception("Unexpected error")

        _execute_command(["some_command"])

        mock_stderr.write.assert_called()
        mock_exit.assert_called_once_with(1)

    @patch("subprocess.Popen")
    @patch("builtins.print")
    def test_execute_command_output_streaming(self, mock_print, mock_popen):
        """Test that command output is streamed line by line."""
        mock_process = MagicMock()
        mock_process.stdout = ["Line 1\n", "Line 2\n", "Line 3\n"]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        _execute_command(["cat", "file.txt"])

        # Check that each line was printed
        expected_calls = [
            call("Line 1\n", end=""),
            call("Line 2\n", end=""),
            call("Line 3\n", end=""),
        ]
        # Filter only the output print calls (not the debug message)
        output_calls = [c for c in mock_print.call_args_list if c[1].get("end") == ""]
        assert output_calls == expected_calls

    @patch("subprocess.Popen")
    @patch("sys.stderr", new_callable=MagicMock)
    def test_execute_command_debug_message(self, mock_stderr, mock_popen):
        """Test that debug message is printed to stderr."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        _execute_command(["ls", "-la", "/tmp"])

        # Check that debug message was written to stderr
        calls = mock_stderr.write.call_args_list
        debug_message_found = any(
            "Running command: ls -la /tmp" in str(call) for call in calls
        )
        assert debug_message_found


class TestIntegration:
    """Integration tests for the app_runner module."""

    @patch("subprocess.Popen")
    @patch("builtins.print")
    def test_full_flow_success(self, mock_print, mock_popen):
        """Test complete flow from run_cmd_app to successful execution."""
        mock_process = MagicMock()
        mock_process.stdout = ["Hello, World!\n"]
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        app_config = {"meta": {"command": "echo Hello, World!"}}

        run_cmd_app(app_config, [])

        mock_popen.assert_called_once()
        # Check the command was split correctly
        assert mock_popen.call_args[0][0] == ["echo", "Hello,", "World!"]

    @patch("subprocess.Popen")
    @patch("sys.exit")
    def test_full_flow_failure(self, mock_exit, mock_popen):
        """Test complete flow from run_cmd_app to failed execution."""
        mock_process = MagicMock()
        mock_process.stdout = ["Error!\n"]
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        app_config = {"meta": {"command": ["false"]}}

        run_cmd_app(app_config, [])

        mock_exit.assert_called_once_with(1)
