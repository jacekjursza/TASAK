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


class TestMCPRemotePool:
    """Test MCPRemotePool functionality without unittest async methods."""

    def setup_method(self):
        MCPRemotePool._instance = None

    def teardown_method(self):
        if MCPRemotePool._instance:
            MCPRemotePool._instance._shutdown = True

    def test_singleton_pattern(self):
        pool1 = MCPRemotePool()
        pool2 = MCPRemotePool()
        assert pool1 is pool2

    @patch("asyncio.create_subprocess_exec")
    def test_create_process(self, mock_subprocess):
        # Setup mocks
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_subprocess.return_value = mock_process

        mock_session = AsyncMock()

        async def run():
            class _FakeCtx:
                def __init__(self):
                    self.exited = False

                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    self.exited = True
                    return False

            fake_ctx = _FakeCtx()
            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=mock_session
            ), patch(
                "mcp.client.stdio.stdio_client", return_value=fake_ctx
            ) as mock_stdio:
                pool = MCPRemotePool()
                await pool._create_process("test_app", "http://test.com")
                # Verify stdio_client was invoked
                assert mock_stdio.called
                mock_session.initialize.assert_called_once()
                assert "test_app" in pool._pool
                assert pool._pool["test_app"].app_name == "test_app"

        asyncio.run(run())

    @patch("asyncio.create_subprocess_exec")
    def test_reuse_existing_process(self, mock_subprocess):
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_subprocess.return_value = mock_process

        mock_session = AsyncMock()

        async def run():
            class _FakeCtx:
                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=mock_session
            ), patch(
                "mcp.client.stdio.stdio_client", return_value=_FakeCtx()
            ) as mock_stdio:
                pool = MCPRemotePool()
                session1 = await pool.get_session("test_app", "http://test.com")
                session2 = await pool.get_session("test_app", "http://test.com")
                mock_stdio.assert_called_once()
                assert session1 is session2

        asyncio.run(run())

    @patch("asyncio.create_subprocess_exec")
    def test_remove_dead_process(self, mock_subprocess):
        mock_process1 = AsyncMock()
        mock_process1.returncode = None
        mock_process1.stdout = AsyncMock()
        mock_process1.stdin = AsyncMock()
        mock_process2 = AsyncMock()
        mock_process2.returncode = None
        mock_process2.stdout = AsyncMock()
        mock_process2.stdin = AsyncMock()
        mock_subprocess.side_effect = [mock_process1, mock_process2]

        async def run():
            class _FakeCtx:
                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()
            ), patch(
                "mcp.client.stdio.stdio_client", return_value=_FakeCtx()
            ) as mock_stdio:
                pool = MCPRemotePool()
                await pool.get_session("test_app", "http://test.com")
                # Simulate that we now track a child process that has exited
                from unittest.mock import Mock as _Mock

                pool._pool["test_app"].process = _Mock(returncode=1)
                await pool.get_session("test_app", "http://test.com")
                assert mock_stdio.call_count == 2

        asyncio.run(run())

    @patch("asyncio.create_subprocess_exec")
    def test_max_pool_size(self, mock_subprocess):
        mock_processes = []
        for _ in range(3):
            p = AsyncMock()
            p.returncode = None
            p.stdout = AsyncMock()
            p.stdin = AsyncMock()
            mock_processes.append(p)
        mock_subprocess.side_effect = mock_processes

        async def run():
            class _FakeCtx:
                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()
            ), patch("mcp.client.stdio.stdio_client", return_value=_FakeCtx()):
                pool = MCPRemotePool()
                pool.MAX_POOL_SIZE = 2
                await pool.get_session("app1", "http://test1.com")
                await pool.get_session("app2", "http://test2.com")
                await pool.get_session("app3", "http://test3.com")
                assert len(pool._pool) == 2
                assert "app1" not in pool._pool
                assert "app2" in pool._pool
                assert "app3" in pool._pool

        asyncio.run(run())

    @patch("asyncio.create_subprocess_exec")
    def test_cleanup_idle_processes(self, mock_subprocess):
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.stdout = AsyncMock()
        mock_process.stdin = AsyncMock()
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process

        async def run():
            class _FakeCtx:
                def __init__(self):
                    self.exited = False

                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    self.exited = True
                    return False

            fake_ctx = _FakeCtx()
            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()
            ), patch("mcp.client.stdio.stdio_client", return_value=fake_ctx):
                pool = MCPRemotePool()
                pool.IDLE_TIMEOUT = 0.1
                await pool.get_session("test_app", "http://test.com")
                assert "test_app" in pool._pool
                pool._pool["test_app"].last_used = time.time() - 1
                await pool._cleanup_idle_processes()
                assert "test_app" not in pool._pool
                assert fake_ctx.exited

        asyncio.run(run())

    @patch("asyncio.create_subprocess_exec")
    def test_shutdown(self, mock_subprocess):
        mock_processes = []
        for _ in range(2):
            p = AsyncMock()
            p.returncode = None
            p.stdout = AsyncMock()
            p.stdin = AsyncMock()
            p.terminate = Mock()
            p.wait = AsyncMock()
            mock_processes.append(p)
        mock_subprocess.side_effect = mock_processes

        async def run():
            class _FakeCtx:
                def __init__(self):
                    self.exited = False

                async def __aenter__(self):
                    from unittest.mock import Mock as _Mock

                    return _Mock(), _Mock()

                async def __aexit__(self, exc_type, exc, tb):
                    self.exited = True
                    return False

            fake_ctx = _FakeCtx()
            with patch(
                "tasak.mcp_remote_pool.ClientSession", return_value=AsyncMock()
            ), patch("mcp.client.stdio.stdio_client", return_value=fake_ctx):
                pool = MCPRemotePool()
                await pool.get_session("app1", "http://test1.com")
                await pool.get_session("app2", "http://test2.com")
                await pool.shutdown()
                assert fake_ctx.exited
                assert len(pool._pool) == 0

        asyncio.run(run())

    def test_get_stats(self):
        pool = MCPRemotePool()
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
        assert stats["pool_size"] == 1
        assert stats["max_size"] == pool.MAX_POOL_SIZE
        assert "test_app" in stats["processes"]
        assert stats["processes"]["test_app"]["alive"]
        assert abs(stats["processes"]["test_app"]["idle_time"] - 30) < 2


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
