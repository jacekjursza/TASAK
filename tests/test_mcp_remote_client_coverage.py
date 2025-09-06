"""Additional tests to improve MCPRemoteClient coverage."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tasak.mcp_remote_client import MCPRemoteClient


class TestMCPRemoteClientCoverage:
    """Test cases to improve coverage for MCPRemoteClient."""

    def test_init_without_server_url(self):
        """Test initialization fails without server_url."""
        with pytest.raises(ValueError) as exc_info:
            MCPRemoteClient("test_app", {})  # Empty config without server_url

        assert "No server_url specified for test_app" in str(exc_info.value)

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_fetch_tools_async_success(self, mock_pool_class):
        """Test successful async tools fetching."""
        # Setup
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_session = AsyncMock()
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.inputSchema = {"type": "object"}

        mock_tools_result = Mock()
        mock_tools_result.tools = [mock_tool]

        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_pool.get_session = AsyncMock(return_value=mock_session)

        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.server"}}
        )

        # Execute
        async def run_test():
            return await client._fetch_tools_async()

        tools = asyncio.run(run_test())

        # Verify
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"
        assert tools[0]["description"] == "Test tool description"
        assert tools[0]["input_schema"] == {"type": "object"}

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_fetch_tools_async_general_error(self, mock_pool_class, capsys):
        """Test async tools fetching with general error."""
        # Setup
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_pool.get_session = AsyncMock(side_effect=Exception("Connection failed"))

        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.server"}}
        )

        # Execute
        async def run_test():
            return await client._fetch_tools_async()

        tools = asyncio.run(run_test())

        # Verify
        assert tools == []
        captured = capsys.readouterr()
        assert (
            "Error fetching tools through mcp-remote: Connection failed" in captured.err
        )

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_fetch_tools_async_401_error(self, mock_pool_class, capsys):
        """Test async tools fetching with 401 authentication error."""
        # Setup
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_pool.get_session = AsyncMock(
            side_effect=Exception("Error: 401 Unauthorized")
        )

        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.server"}}
        )

        # Execute
        async def run_test():
            return await client._fetch_tools_async()

        tools = asyncio.run(run_test())

        # Verify
        assert tools == []
        captured = capsys.readouterr()
        assert (
            "Error fetching tools through mcp-remote: Error: 401 Unauthorized"
            in captured.err
        )
        assert "Authentication required. Run: tasak admin auth test_app" in captured.err

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_fetch_tools_async_unauthorized_error(self, mock_pool_class, capsys):
        """Test async tools fetching with unauthorized error."""
        # Setup
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_pool.get_session = AsyncMock(side_effect=Exception("Request unauthorized"))

        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.server"}}
        )

        # Execute
        async def run_test():
            return await client._fetch_tools_async()

        tools = asyncio.run(run_test())

        # Verify
        assert tools == []
        captured = capsys.readouterr()
        assert (
            "Error fetching tools through mcp-remote: Request unauthorized"
            in captured.err
        )
        assert "Authentication required. Run: tasak admin auth test_app" in captured.err

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_fetch_tools_async_multiple_tools(self, mock_pool_class):
        """Test fetching multiple tools."""
        # Setup
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        mock_session = AsyncMock()

        # Create multiple tools
        tools_list = []
        for i in range(3):
            mock_tool = Mock()
            mock_tool.name = f"tool_{i}"
            mock_tool.description = f"Tool {i} description"
            mock_tool.inputSchema = {"type": "object", "id": i}
            tools_list.append(mock_tool)

        mock_tools_result = Mock()
        mock_tools_result.tools = tools_list

        mock_session.list_tools = AsyncMock(return_value=mock_tools_result)
        mock_pool.get_session = AsyncMock(return_value=mock_session)

        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.server"}}
        )

        # Execute
        async def run_test():
            return await client._fetch_tools_async()

        tools = asyncio.run(run_test())

        # Verify
        assert len(tools) == 3
        for i in range(3):
            assert tools[i]["name"] == f"tool_{i}"
            assert tools[i]["description"] == f"Tool {i} description"
            assert tools[i]["input_schema"]["id"] == i
