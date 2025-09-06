"""Tests for MCPRemoteClient bug fixes."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tasak.mcp_remote_client import MCPRemoteClient


class TestMCPRemoteClientErrorHandling:
    """Test error handling improvements in MCPRemoteClient."""

    @pytest.mark.asyncio
    async def test_auth_error_exits(self):
        """Test that authentication errors still cause sys.exit(1)."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_session.call_tool.side_effect = Exception("401 Unauthorized")

        with patch.object(client.pool, "get_session", return_value=mock_session):
            with pytest.raises(SystemExit) as exc_info:
                await client._call_tool_async("test_tool", {})

            assert exc_info.value.code == 1

    @pytest.mark.asyncio
    async def test_non_auth_error_raises(self):
        """Test that non-authentication errors raise RuntimeError instead of exiting."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_session.call_tool.side_effect = Exception("Network timeout")

        with patch.object(client.pool, "get_session", return_value=mock_session):
            with pytest.raises(RuntimeError) as exc_info:
                await client._call_tool_async("test_tool", {})

            assert "Failed to call tool test_tool" in str(exc_info.value)
            assert "Network timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_response_with_proper_structure(self):
        """Test handling of response with expected structure."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.content = [Mock(text="Success message")]
        mock_session.call_tool.return_value = mock_result

        with patch.object(client.pool, "get_session", return_value=mock_session):
            result = await client._call_tool_async("test_tool", {})

        assert result == "Success message"

    @pytest.mark.asyncio
    async def test_response_with_data_attribute(self):
        """Test handling of response with data attribute."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_content = Mock(spec=[])  # No text attribute
        mock_content.data = {"key": "value"}
        mock_result.content = [mock_content]
        mock_session.call_tool.return_value = mock_result

        with patch.object(client.pool, "get_session", return_value=mock_session):
            result = await client._call_tool_async("test_tool", {})

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_response_without_content_attribute(self):
        """Test handling of response without content attribute (like a dict)."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        # Return a plain dict instead of object with content
        mock_session.call_tool.return_value = {"result": "direct_value"}

        with patch.object(client.pool, "get_session", return_value=mock_session):
            result = await client._call_tool_async("test_tool", {})

        # Should return the dict as-is
        assert result == {"result": "direct_value"}

    @pytest.mark.asyncio
    async def test_response_with_empty_content(self):
        """Test handling of response with empty content list."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.content = []  # Empty content list
        mock_session.call_tool.return_value = mock_result

        with patch.object(client.pool, "get_session", return_value=mock_session):
            result = await client._call_tool_async("test_tool", {})

        # Should return the mock_result object itself since it's truthy
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_response_none(self):
        """Test handling of None response."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        mock_session = AsyncMock()
        mock_session.call_tool.return_value = None

        with patch.object(client.pool, "get_session", return_value=mock_session):
            result = await client._call_tool_async("test_tool", {})

        # Should return default success message
        assert result == {
            "status": "success",
            "content": "Tool test_tool executed",
        }

    def test_call_tool_sync_wrapper(self):
        """Test that sync call_tool properly handles RuntimeError from async function."""
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        with patch.object(
            client, "_call_tool_async", side_effect=RuntimeError("Test error")
        ):
            with pytest.raises(RuntimeError) as exc_info:
                client.call_tool("test_tool", {})

            assert "Test error" in str(exc_info.value)
