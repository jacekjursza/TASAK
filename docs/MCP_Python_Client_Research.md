# MCP Python Client - Complete Implementation Guide

## Executive Summary

**TAK, jest gotowa biblioteka!** Oficjalne MCP Python SDK (`mcp`) zawiera pełne wsparcie dla klientów. Możesz łatwo połączyć się z dowolnym serwerem MCP, wywoływać tools, pobierać resources i obsługiwać responses. SDK jest production-ready i aktywnie rozwijane.

---

## Instalacja

### Podstawowa instalacja
```bash
# Preferowana metoda (z uv)
uv add "mcp[cli]"

# Alternatywnie pip
pip install "mcp[cli]"

# Dla pełnej funkcjonalności
pip install mcp anthropic python-dotenv
```

### Wymagania
- Python 3.10+
- `uv` (zalecane) lub `pip`
- Async/await support

---

## Architektura Klienta MCP

```
┌──────────────┐     JSON-RPC      ┌──────────────┐
│  MCP Client  │ ←────────────────→ │  MCP Server  │
│              │                    │              │
│ ClientSession│     Transport      │   Tools      │
│              │  (stdio/SSE/HTTP)  │   Resources  │
│              │                    │   Prompts    │
└──────────────┘                    └──────────────┘
```

---

## Podstawowa Implementacja Klienta

### 1. Minimalny Przykład - Połączenie i Wywołanie Tool

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

async def basic_client():
    # Konfiguracja serwera
    server_params = StdioServerParameters(
        command="python",
        args=["path/to/server.py"],
        env=None  # lub dict ze zmiennymi środowiskowymi
    )
    
    # Połączenie z serwerem
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Inicjalizacja sesji
            await session.initialize()
            
            # Lista dostępnych tools
            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])
            
            # Wywołanie tool
            result = await session.call_tool(
                'tool_name',
                {'param1': 'value1', 'param2': 'value2'}
            )
            
            # Obsługa wyniku
            print("Result:", result.content[0].text)

# Uruchomienie
asyncio.run(basic_client())
```

### 2. Kompletny Klient z Error Handling

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import asyncio
import logging

class MCPClient:
    def __init__(self, server_script: str):
        self.server_script = server_script
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Establish connection to MCP server"""
        try:
            # Przygotuj parametry serwera
            server_params = StdioServerParameters(
                command="python" if self.server_script.endswith('.py') else "node",
                args=[self.server_script],
                env=None
            )
            
            # Utwórz transport
            self.read, self.write = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # Utwórz sesję
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.read, self.write)
            )
            
            # Inicjalizuj
            await self.session.initialize()
            
            self.logger.info(f"Connected to server: {self.server_script}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def list_tools(self):
        """Get available tools from server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        response = await self.session.list_tools()
        return [
            {
                'name': tool.name,
                'description': tool.description,
                'schema': tool.inputSchema
            }
            for tool in response.tools
        ]
    
    async def call_tool(self, tool_name: str, arguments: dict = None):
        """Call a specific tool with arguments"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        try:
            result = await self.session.call_tool(
                tool_name, 
                arguments or {}
            )
            
            # Parse response
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return content.text
                elif hasattr(content, 'data'):
                    return content.data
            return None
            
        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            raise
    
    async def list_resources(self):
        """Get available resources from server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        response = await self.session.list_resources()
        return [
            {
                'uri': resource.uri,
                'name': resource.name,
                'mimeType': resource.mimeType
            }
            for resource in response.resources
        ]
    
    async def read_resource(self, uri: str):
        """Read a specific resource"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        result = await self.session.read_resource(uri)
        if result.content and len(result.content) > 0:
            return result.content[0].text
        return None
    
    async def list_prompts(self):
        """Get available prompts from server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        response = await self.session.list_prompts()
        return [
            {
                'name': prompt.name,
                'description': prompt.description,
                'arguments': prompt.arguments
            }
            for prompt in response.prompts
        ]
    
    async def get_prompt(self, prompt_name: str, arguments: dict = None):
        """Get a specific prompt with arguments"""
        if not self.session:
            raise RuntimeError("Not connected to server")
            
        result = await self.session.get_prompt(
            prompt_name,
            arguments or {}
        )
        
        if result.messages:
            return result.messages
        return None
    
    async def disconnect(self):
        """Close connection to server"""
        await self.exit_stack.aclose()
        self.logger.info("Disconnected from server")

# Użycie
async def main():
    client = MCPClient("path/to/weather_server.py")
    
    # Połącz
    if await client.connect():
        # Lista tools
        tools = await client.list_tools()
        print(f"Available tools: {tools}")
        
        # Wywołaj tool
        weather = await client.call_tool(
            'get_weather',
            {'city': 'Warsaw', 'units': 'metric'}
        )
        print(f"Weather: {weather}")
        
        # Lista resources
        resources = await client.list_resources()
        print(f"Resources: {resources}")
        
        # Rozłącz
        await client.disconnect()

asyncio.run(main())
```

---

## Integracja z LLM (Claude/OpenAI)

### Przykład z Claude API

```python
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json

class MCPWithClaude:
    def __init__(self, mcp_server: str, anthropic_api_key: str):
        self.mcp_server = mcp_server
        self.anthropic = Anthropic(api_key=anthropic_api_key)
        self.session = None
        
    async def connect_mcp(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command="python",
            args=[self.mcp_server]
        )
        
        self.read, self.write = await stdio_client(server_params).__aenter__()
        self.session = await ClientSession(self.read, self.write).__aenter__()
        await self.session.initialize()
        
    async def query_with_tools(self, user_query: str):
        """Process query using Claude and MCP tools"""
        
        # Get available tools
        tools_response = await self.session.list_tools()
        
        # Convert MCP tools to Claude format
        claude_tools = []
        for tool in tools_response.tools:
            claude_tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            })
        
        # Send query to Claude
        messages = [{"role": "user", "content": user_query}]
        
        response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            tools=claude_tools,
            max_tokens=1000
        )
        
        # Process tool calls
        final_response = []
        
        for block in response.content:
            if block.type == "tool_use":
                # Execute tool via MCP
                tool_result = await self.session.call_tool(
                    block.name,
                    block.input
                )
                
                # Add to response
                final_response.append({
                    "tool": block.name,
                    "result": tool_result.content[0].text
                })
                
                # Continue conversation with tool results
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result.content[0].text
                    }]
                })
                
        # Get final response from Claude
        final_claude_response = self.anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            messages=messages,
            max_tokens=1000
        )
        
        return final_claude_response.content[0].text

# Użycie
async def main():
    client = MCPWithClaude(
        "weather_server.py",
        "your-anthropic-api-key"
    )
    
    await client.connect_mcp()
    
    response = await client.query_with_tools(
        "What's the weather like in Warsaw and London?"
    )
    
    print(response)

asyncio.run(main())
```

---

## Transport Types

### 1. STDIO (Local)
```python
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["server.py"]
)
```

### 2. SSE (Server-Sent Events)
```python
from mcp.client.sse import sse_client

async with sse_client("http://localhost:8080/sse") as client:
    async with ClientSession(client.read, client.write) as session:
        await session.initialize()
```

### 3. HTTP (Streamable)
```python
from mcp.client.http import http_client

async with http_client("http://localhost:8080") as client:
    async with ClientSession(client.read, client.write) as session:
        await session.initialize()
```

---

## Advanced Features

### 1. Progress Tracking
```python
# Obsługa progress updates z serwera
async def handle_progress():
    async for progress in session.progress_notifications():
        print(f"Progress: {progress.progress}/{progress.total}")
```

### 2. Logging
```python
# Obsługa logów z serwera
async def handle_logs():
    async for log_message in session.log_messages():
        print(f"[{log_message.level}] {log_message.data}")
```

### 3. Custom Request Handling
```python
# Wysyłanie custom requests
result = await session.send_request(
    method="custom/method",
    params={"key": "value"}
)
```

---

## Testing

### Unit Test Example
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_mcp_client():
    # Mock session
    mock_session = AsyncMock()
    mock_session.list_tools.return_value = MagicMock(
        tools=[
            MagicMock(name="test_tool", description="Test")
        ]
    )
    
    # Test
    client = MCPClient("dummy.py")
    client.session = mock_session
    
    tools = await client.list_tools()
    assert len(tools) == 1
    assert tools[0]['name'] == 'test_tool'
```

---

## Best Practices

### 1. Resource Management
```python
# Zawsze używaj context managers
async with stdio_client(params) as (r, w):
    async with ClientSession(r, w) as session:
        # Twój kod
```

### 2. Error Handling
```python
try:
    result = await session.call_tool("tool", {})
except MCPError as e:
    logger.error(f"MCP error: {e}")
except TimeoutError:
    logger.error("Request timeout")
```

### 3. Connection Pooling
```python
# Dla wielu równoległych połączeń
class MCPPool:
    def __init__(self, server: str, pool_size: int = 5):
        self.clients = []
        for _ in range(pool_size):
            self.clients.append(MCPClient(server))
    
    async def get_client(self):
        # Round-robin lub inna strategia
        return self.clients[self.index % len(self.clients)]
```

---

## Przykładowe Use Cases

### 1. Database Query Client
```python
client = MCPClient("database_server.py")
await client.connect()

# Query database via MCP
result = await client.call_tool(
    'sql_query',
    {'query': 'SELECT * FROM users LIMIT 10'}
)
```

### 2. File System Client
```python
client = MCPClient("filesystem_server.py")
await client.connect()

# List files
files = await client.call_tool(
    'list_files',
    {'path': '/home/user/documents'}
)
```

### 3. API Gateway Client
```python
client = MCPClient("api_gateway_server.py")
await client.connect()

# Call external API via MCP
weather = await client.call_tool(
    'external_api',
    {
        'service': 'weather',
        'endpoint': '/forecast',
        'params': {'city': 'Warsaw'}
    }
)
```

---

## Podsumowanie

### Co mamy?
✅ **Oficjalne SDK** - `mcp` package z pełnym wsparciem
✅ **ClientSession** - wysokopoziomowe API
✅ **Multiple transports** - stdio, SSE, HTTP
✅ **Type safety** - pełne wsparcie dla typów
✅ **Async/await** - nowoczesne async API
✅ **Production ready** - używane w Claude Desktop

### Kluczowe komponenty:
- `mcp.ClientSession` - główna klasa klienta
- `mcp.client.stdio.stdio_client` - dla lokalnych serwerów
- `StdioServerParameters` - konfiguracja serwera
- Metody: `initialize()`, `list_tools()`, `call_tool()`, `list_resources()`

### Quick Start:
```bash
pip install mcp
# Done! Możesz budować klienty MCP
```

---

*Research Date: 2025-09-05*
*MCP Python SDK Version: Latest (2025)*
*Status: Production Ready*