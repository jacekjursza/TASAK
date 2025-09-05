# MCP Compatibility Notes

## Current Status
- FastMCP (used by GOK) and standard MCP SDK are protocol-compatible
- Both implement the same MCP standard (JSON-RPC over SSE/stdio)
- Connection works after fixing API usage (sse_client returns tuple)

## Key Differences

### FastMCP
- Higher-level framework (like FastAPI for MCP)
- Decorator-based tool definition
- Automatic SSE endpoint generation
- Simpler server creation

### Standard MCP SDK
- Lower-level, more control
- Manual session management
- Official Anthropic library
- Used by Claude Desktop

## No Action Needed
The current implementation correctly handles both FastMCP and standard MCP servers through the same client code.
