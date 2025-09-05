# MCP Remote Communication Issue

## Problem Statement
MCP Remote applications (Atlassian, GitHub, Slack) start the proxy correctly but TASAK doesn't communicate with it.

## Current Behavior
1. User runs: `tasak atlassian`
2. TASAK executes: `npx mcp-remote https://mcp.atlassian.com/v1/sse`
3. Proxy starts successfully and establishes connection:
   - Local STDIO server running
   - Connected to remote SSE server
   - Proxy established between local STDIO and remote SSE
4. **PROBLEM**: TASAK just waits (subprocess.run) instead of communicating
5. User has to Ctrl+C to exit

## Expected Behavior
1. Start `mcp-remote` proxy as subprocess
2. Connect to proxy via STDIO (like with local MCP servers)
3. Send commands through the proxy
4. Proxy forwards to remote server and returns responses

## Root Cause
`mcp_remote_runner.py` line 69:
```python
result = subprocess.run(cmd, check=False)  # Just waits for process to end
```

## Solution Approach
Treat `mcp-remote` like a local MCP server with stdio transport:
1. Start `mcp-remote` as subprocess with `subprocess.Popen`
2. Use `MCPRealClient` with stdio transport to communicate
3. Pass stdin/stdout pipes to MCP ClientSession
4. Keep proxy running in background while communicating

## Implementation Notes
- Similar to how we handle local MCP servers (stdio transport)
- The proxy is just a bridge: TASAK ↔ (stdio) ↔ mcp-remote ↔ (SSE) ↔ Remote Server
- Need to manage proxy lifecycle (start, communicate, cleanup)

## Files to Modify
- `tasak/mcp_remote_runner.py` - change how proxy is started
- Possibly create new transport type or reuse stdio with special handling

## Testing
- Test with Atlassian MCP server
- Verify OAuth flow works
- Ensure tools can be listed and called through proxy
