# Handle Server Unavailable Gracefully

## Problem
When user executes an actual command (not just --help), we need graceful handling of server being offline.

## Current Behavior
- Ugly stack traces
- Unclear error messages
- No retry logic
- Repeated failed attempts

## Proposed Solution

### 1. Graceful Error Handling

```python
# In mcp_real_client.py call_tool()
async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
    try:
        # Attempt connection with retry
        result = await self._call_with_retry(tool_name, arguments)
        self._mark_server_online(self.app_name)
        return result
    except (ConnectionError, TimeoutError, SSEError) as e:
        if self._is_cached_offline(self.app_name):
            print(f"Service '{self.app_name}' is not available currently.")
        else:
            print(f"Connecting to '{self.app_name}'...", end='', flush=True)
            # One retry
            try:
                result = await self._call_tool_async(tool_name, arguments)
                print(" connected!")
                self._mark_server_online(self.app_name)
                return result
            except:
                print(" failed.")
                print(f"Service '{self.app_name}' is not available currently.")
                self._mark_server_offline(self.app_name)
        sys.exit(1)
```

### 2. Offline Cache

```python
# ~/.tasak/status/<app_name>.json
{
    "status": "offline",
    "last_check": "2024-01-20T10:30:00Z",
    "last_online": "2024-01-20T10:00:00Z",
    "error": "Connection refused"
}
```

### 3. ~~Cache Logic~~ (SKIP IN V1)

**SIMPLIFICATION:** Skip the 5-minute cache in first version. Just show clean errors.

```python
# V1: Simple approach - just clean errors
async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
    try:
        result = await self._call_tool_async(tool_name, arguments, headers)
        return result
    except (ConnectionError, TimeoutError) as e:
        print(f"Error: Cannot connect to '{self.app_name}' server.", file=sys.stderr)
        print(f"Is the server running?", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error executing tool '{tool_name}': {e}", file=sys.stderr)
        sys.exit(1)
```

### 4. User Experience

#### First failure:
```bash
$ tasak gok note_create --title "Test"
Connecting to 'gok'... failed.
Service 'gok' is not available currently.
```

#### Subsequent failures (within 5 minutes):
```bash
$ tasak gok note_create --title "Test"
Service 'gok' is not available currently.
```

#### After 5 minutes:
```bash
$ tasak gok note_create --title "Test"
Connecting to 'gok'... failed.  [tries again]
Service 'gok' is not available currently.
```

#### When server comes back:
```bash
$ tasak gok note_create --title "Test"
Connecting to 'gok'... connected!
[executes command]
```

### 5. Different Behavior for Different Operations

| Operation | Server Required? | Behavior if Offline |
|-----------|-----------------|---------------------|
| `--help` | No | Use cached schema |
| `list tools` | No | Use cached schema |
| `execute tool` | Yes | Error with nice message |
| `admin refresh` | Yes | Error with nice message |

### 6. Implementation Notes

- **SSE servers**: Connection errors are immediate
- **STDIO servers**: May timeout (need proper timeout handling)
- **MCP-remote**: OAuth failures vs server failures (different messages)

### 7. Benefits

1. **No stack traces** - Clean error messages
2. **Faster feedback** - Don't retry if recently failed
3. **Clear communication** - User knows service is down
4. **Automatic recovery** - Works again when server is back

### 8. Edge Cases

- **Partial failure**: Server responds to some tools but not others
- **Slow server**: Distinguish timeout from offline
- **Auth failure**: Different from server offline
- **Network issues**: User's network vs server down

### 9. Future Enhancements

- `tasak admin status` - Show all services status
- `tasak admin ping <app>` - Manual health check
- Exponential backoff for retries
- Different cache durations per app type
