"""Unit tests for mcp_remote_auth module."""

import subprocess
from unittest.mock import Mock, patch


from tasak.mcp_remote_auth import authenticate_with_mcp_remote


class TestAuthenticateWithMcpRemote:
    """Test authenticate_with_mcp_remote function."""

    @patch("tasak.mcp_remote_auth.subprocess.run")
    def test_successful_authentication(self, mock_run, capsys):
        """Test successful authentication flow."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = authenticate_with_mcp_remote()

        assert result is True
        captured = capsys.readouterr()
        assert "Using official mcp-remote for authentication" in captured.out
        assert "Authentication successful via mcp-remote" in captured.out

        # Verify subprocess was called correctly
        mock_run.assert_called_once_with(
            [
                "npx",
                "-y",
                "mcp-remote",
                "https://mcp.atlassian.com/v1/sse",
                "--auth-only",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

    @patch("tasak.mcp_remote_auth.subprocess.run")
    def test_failed_authentication(self, mock_run, capsys):
        """Test failed authentication (non-zero return code)."""
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="Auth error")

        result = authenticate_with_mcp_remote()

        assert result is False
        captured = capsys.readouterr()
        assert "Authentication failed: Auth error" in captured.err

    @patch("tasak.mcp_remote_auth.subprocess.run")
    def test_authentication_timeout(self, mock_run, capsys):
        """Test authentication timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["npx"], timeout=120)

        result = authenticate_with_mcp_remote()

        assert result is False
        captured = capsys.readouterr()
        assert "Authentication timed out" in captured.err

    @patch("tasak.mcp_remote_auth.subprocess.run")
    def test_npx_not_found(self, mock_run, capsys):
        """Test when npx is not installed."""
        mock_run.side_effect = FileNotFoundError("npx not found")

        result = authenticate_with_mcp_remote()

        assert result is False
        captured = capsys.readouterr()
        assert "npx not found" in captured.err
        assert "Please install Node.js" in captured.err
        assert "https://nodejs.org/" in captured.err

    @patch("tasak.mcp_remote_auth.subprocess.run")
    def test_generic_exception(self, mock_run, capsys):
        """Test generic exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = authenticate_with_mcp_remote()

        assert result is False
        captured = capsys.readouterr()
        assert "Error running mcp-remote: Unexpected error" in captured.err

    @patch("tasak.mcp_remote_auth.authenticate_with_mcp_remote")
    @patch("tasak.mcp_remote_auth.sys.exit")
    def test_main_success(self, mock_exit, mock_auth):
        """Test main execution with successful auth."""
        mock_auth.return_value = True

        # Import and run the module as main
        import tasak.mcp_remote_auth

        with patch.object(tasak.mcp_remote_auth, "__name__", "__main__"):
            exec(
                compile(
                    open(tasak.mcp_remote_auth.__file__).read(),
                    tasak.mcp_remote_auth.__file__,
                    "exec",
                )
            )

        mock_exit.assert_called_with(0)

    @patch("tasak.mcp_remote_auth.authenticate_with_mcp_remote")
    @patch("tasak.mcp_remote_auth.sys.exit")
    def test_main_failure(self, mock_exit, mock_auth):
        """Test main execution with failed auth."""
        mock_auth.return_value = False

        # Import and run the module as main
        import tasak.mcp_remote_auth

        with patch.object(tasak.mcp_remote_auth, "__name__", "__main__"):
            exec(
                compile(
                    open(tasak.mcp_remote_auth.__file__).read(),
                    tasak.mcp_remote_auth.__file__,
                    "exec",
                )
            )

        mock_exit.assert_called_with(1)
