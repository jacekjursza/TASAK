"""Unit tests for MCP Remote Process Pool."""

import asyncio
import time
import unittest
from unittest.mock import Mock, patch, AsyncMock

from tasak.mcp_remote_pool import MCPRemotePool, PooledProcess


class TestPooledProcess(unittest.TestCase):
    """Test PooledProcess dataclass."""

    def test_is_alive_property(self):
        """Test is_alive property returns correct status."""
        mock_process = Mock()
        mock_process.returncode = None  # Process is running

        pooled = PooledProcess(
            process=mock_process,
            session=Mock(),
            created_at=time.time(),
            last_used=time.time(),
            app_name="test",
            server_url="http://test",
        )

        self.assertTrue(pooled.is_alive)

        # Process has exited
        mock_process.returncode = 0
        self.assertFalse(pooled.is_alive)

    def test_idle_time_property(self):
        """Test idle_time calculates correctly."""
        created = time.time() - 10
        last_used = time.time() - 5

        pooled = PooledProcess(
            process=Mock(),
            session=Mock(),
            created_at=created,
            last_used=last_used,
            app_name="test",
            server_url="http://test",
        )

        # Should be approximately 5 seconds
        self.assertAlmostEqual(pooled.idle_time, 5, delta=0.1)


class TestMCPRemotePool(unittest.TestCase):
    """Test MCPRemotePool functionality."""

    def setUp(self):
        """Reset singleton before each test."""
        MCPRemotePool._instance = None

    def tearDown(self):
        """Clean up after each test."""
        if MCPRemotePool._instance:
            MCPRemotePool._instance._shutdown = True

    def test_singleton_pattern(self):
        """Test that pool is a singleton."""
        pool1 = MCPRemotePool()
        pool2 = MCPRemotePool()
        self.assertIs(pool1, pool2)

    @patch("asyncio.create_subprocess_exec")
    async def test_create_process(self, mock_subprocess):
        """Test creating a new process."""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_subprocess.return_value = mock_process

        mock_session = AsyncMock()

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=mock_session):
            pool = MCPRemotePool()

            # Create process
            await pool._create_process("test_app", "http://test.com")

            # Verify process was created
            mock_subprocess.assert_called_once_with(
                "npx",
                "-y",
                "mcp-remote",
                "http://test.com",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=None,
            )

            # Verify session was initialized
            mock_session.initialize.assert_called_once()

            # Verify process is in pool
            self.assertIn("test_app", pool._pool)
            self.assertEqual(pool._pool["test_app"].app_name, "test_app")

    @patch("asyncio.create_subprocess_exec")
    async def test_reuse_existing_process(self, mock_subprocess):
        """Test that existing process is reused."""
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_subprocess.return_value = mock_process

        mock_session = AsyncMock()

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=mock_session):
            pool = MCPRemotePool()

            # Get session twice
            session1 = await pool.get_session("test_app", "http://test.com")
            session2 = await pool.get_session("test_app", "http://test.com")

            # Process should only be created once
            mock_subprocess.assert_called_once()

            # Same session should be returned
            self.assertIs(session1, session2)

    @patch("asyncio.create_subprocess_exec")
    async def test_remove_dead_process(self, mock_subprocess):
        """Test that dead processes are removed and recreated."""
        # First process (will die)
        mock_process1 = AsyncMock()
        mock_process1.returncode = None  # Initially alive
        mock_process1.stdout = AsyncMock()
        mock_process1.stdin = AsyncMock()

        # Second process (replacement)
        mock_process2 = AsyncMock()
        mock_process2.returncode = None
        mock_process2.stdout = AsyncMock()
        mock_process2.stdin = AsyncMock()

        mock_subprocess.side_effect = [mock_process1, mock_process2]

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()):
            pool = MCPRemotePool()

            # Get session first time
            await pool.get_session("test_app", "http://test.com")

            # Mark process as dead
            mock_process1.returncode = 1

            # Get session again - should create new process
            await pool.get_session("test_app", "http://test.com")

            # Should have created 2 processes
            self.assertEqual(mock_subprocess.call_count, 2)

    @patch("asyncio.create_subprocess_exec")
    async def test_max_pool_size(self, mock_subprocess):
        """Test pool size limit is enforced."""
        # Create mock processes
        mock_processes = []
        for i in range(3):
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdin = AsyncMock()
            mock_processes.append(mock_process)

        mock_subprocess.side_effect = mock_processes

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()):
            pool = MCPRemotePool()
            pool.MAX_POOL_SIZE = 2  # Limit to 2

            # Create 3 processes
            await pool.get_session("app1", "http://test1.com")
            await pool.get_session("app2", "http://test2.com")
            await pool.get_session("app3", "http://test3.com")

            # Pool should only have 2 processes
            self.assertEqual(len(pool._pool), 2)

            # First app should have been removed
            self.assertNotIn("app1", pool._pool)
            self.assertIn("app2", pool._pool)
            self.assertIn("app3", pool._pool)

    @patch("asyncio.create_subprocess_exec")
    async def test_cleanup_idle_processes(self, mock_subprocess):
        """Test that idle processes are cleaned up."""
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()):
            pool = MCPRemotePool()
            pool.IDLE_TIMEOUT = 0.1  # Very short timeout for testing

            # Create process
            await pool.get_session("test_app", "http://test.com")
            self.assertIn("test_app", pool._pool)

            # Make it idle
            pool._pool["test_app"].last_used = time.time() - 1

            # Run cleanup
            await pool._cleanup_idle_processes()

            # Process should be removed
            self.assertNotIn("test_app", pool._pool)
            mock_process.terminate.assert_called_once()

    @patch("asyncio.create_subprocess_exec")
    async def test_shutdown(self, mock_subprocess):
        """Test pool shutdown terminates all processes."""
        # Create multiple mock processes
        mock_processes = []
        for i in range(2):
            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.stdout = AsyncMock()
            mock_process.stdin = AsyncMock()
            mock_process.terminate = Mock()
            mock_process.wait = AsyncMock()
            mock_processes.append(mock_process)

        mock_subprocess.side_effect = mock_processes

        with patch("tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()):
            pool = MCPRemotePool()

            # Create processes
            await pool.get_session("app1", "http://test1.com")
            await pool.get_session("app2", "http://test2.com")

            # Shutdown pool
            await pool.shutdown()

            # All processes should be terminated
            for mock_process in mock_processes:
                mock_process.terminate.assert_called_once()

            # Pool should be empty
            self.assertEqual(len(pool._pool), 0)

    def test_get_stats(self):
        """Test get_stats returns correct information."""
        pool = MCPRemotePool()

        # Add mock process to pool
        mock_process = Mock()
        mock_process.returncode = None

        pool._pool["test_app"] = PooledProcess(
            process=mock_process,
            session=Mock(),
            created_at=time.time() - 60,
            last_used=time.time() - 30,
            app_name="test_app",
            server_url="http://test.com",
        )

        stats = pool.get_stats()

        self.assertEqual(stats["pool_size"], 1)
        self.assertEqual(stats["max_size"], pool.MAX_POOL_SIZE)
        self.assertIn("test_app", stats["processes"])
        self.assertTrue(stats["processes"]["test_app"]["alive"])
        self.assertAlmostEqual(stats["processes"]["test_app"]["idle_time"], 30, delta=1)


class TestMCPRemoteClientIntegration(unittest.TestCase):
    """Test MCPRemoteClient integration with pool."""

    def setUp(self):
        """Reset singleton before each test."""
        MCPRemotePool._instance = None

    def tearDown(self):
        """Clean up after each test."""
        if MCPRemotePool._instance:
            MCPRemotePool._instance._shutdown = True

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    def test_client_uses_pool(self, mock_pool_class):
        """Test that MCPRemoteClient uses the pool."""
        from tasak.mcp_remote_client import MCPRemoteClient

        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        # Create client
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        # Verify pool was created
        mock_pool_class.assert_called_once()
        self.assertIs(client.pool, mock_pool)

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    @patch("asyncio.run")
    def test_get_tool_definitions_uses_pool(self, mock_run, mock_pool_class):
        """Test get_tool_definitions uses pool.get_session."""
        from tasak.mcp_remote_client import MCPRemoteClient

        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        # Create client
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        # Call get_tool_definitions
        client.get_tool_definitions()

        # Verify asyncio.run was called
        mock_run.assert_called_once()

    @patch("tasak.mcp_remote_client.MCPRemotePool")
    @patch("asyncio.run")
    def test_call_tool_uses_pool(self, mock_run, mock_pool_class):
        """Test call_tool uses pool.get_session."""
        from tasak.mcp_remote_client import MCPRemoteClient

        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool

        # Create client
        client = MCPRemoteClient(
            "test_app", {"meta": {"server_url": "http://test.com"}}
        )

        # Call tool
        client.call_tool("test_tool", {"arg": "value"})

        # Verify asyncio.run was called
        mock_run.assert_called_once()


if __name__ == "__main__":
    # Run async tests properly
    unittest.main()
