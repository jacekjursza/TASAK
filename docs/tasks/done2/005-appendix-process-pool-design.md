# TASAK Service Architecture - Performance Optimization

## Problem
Starting `mcp-remote` proxy for each command is inefficient:
- OAuth handshake each time
- Connection setup overhead
- Process spawn/teardown cost
- Poor user experience (slow)

## Proposed Solution: tasak-service

### Architecture Overview
```
┌──────────┐       ┌────────────────┐       ┌─────────────┐
│  tasak   │ ←───→ │  tasak-service │ ←───→ │ MCP Servers │
│   CLI    │ HTTP  │    (daemon)    │ SSE/  │  (remote)   │
└──────────┘       └────────────────┘ STDIO └─────────────┘
                           ↓
                    Maintains persistent
                    connections to servers
```

### Key Features

1. **Persistent Connections**
   - Keep `mcp-remote` proxies running
   - Reuse connections across commands
   - Instant response times

2. **Connection Pooling**
   ```
   tasak-service
   ├── atlassian-proxy (running)
   ├── github-proxy (idle, will start on demand)
   └── slack-proxy (running)
   ```

3. **Smart Lifecycle**
   - Start on first use
   - Keep alive for X minutes after last command
   - Auto-shutdown idle connections
   - Manual start/stop options

### Usage Patterns

#### Automatic Mode (default)
```bash
$ tasak atlassian jira_search --query "bug"
→ [tasak-service auto-starts if needed]
→ [instant response - connection already open]

$ tasak github repo_list
→ [reuses running service]
→ [instant response]

# After 10 minutes of inactivity
→ [tasak-service auto-stops]
```

#### Manual Mode
```bash
$ tasak service start              # Start service daemon
$ tasak service start atlassian    # Start specific proxy
$ tasak service status              # Show running proxies
$ tasak service stop                # Stop all
$ tasak service logs atlassian     # View proxy logs
```

### Implementation Approaches

#### Option 1: Separate Binary
```
/usr/local/bin/tasak         # CLI tool
/usr/local/bin/tasak-service # Service daemon
```

**Pros:**
- Clean separation
- Can run as systemd service
- Independent lifecycle

**Cons:**
- Two binaries to manage
- IPC complexity

#### Option 2: Integrated Mode
```bash
tasak --daemon              # Run in service mode
tasak --service-port 7890   # Custom service port
```

**Pros:**
- Single binary
- Easier distribution

**Cons:**
- More complex main.py

#### Option 3: Hybrid
```python
# Same codebase, two entry points
bin/tasak         → tasak.main:cli()
bin/tasak-service → tasak.service:daemon()
```

### Communication Protocol

#### REST API
```python
# tasak-service exposes:
GET  /status
GET  /proxies
POST /proxies/{app}/start
POST /proxies/{app}/stop
POST /proxies/{app}/execute
```

#### Example Flow
```python
# In tasak CLI
def run_mcp_remote_app(app_name, args):
    # Try service first
    if service_available():
        response = requests.post(
            f"http://localhost:7890/proxies/{app_name}/execute",
            json={"tool": args[0], "arguments": args[1:]}
        )
        return response.json()
    else:
        # Fallback to direct execution (current behavior)
        return run_mcp_remote_directly(app_name, args)
```

### Service Management

#### Auto-start Logic
```python
def ensure_service_running():
    if not is_service_running():
        # Start in background
        subprocess.Popen([
            sys.executable, "-m", "tasak.service",
            "--daemon", "--auto-shutdown", "600"  # 10 minutes
        ])
        wait_for_service_ready()
```

#### Connection Management
```python
class ProxyManager:
    def __init__(self):
        self.proxies = {}  # app_name -> Popen object
        self.last_used = {}  # app_name -> timestamp

    def get_proxy(self, app_name):
        if app_name not in self.proxies:
            self.start_proxy(app_name)
        self.last_used[app_name] = time.time()
        return self.proxies[app_name]

    def cleanup_idle(self):
        for app_name, last in self.last_used.items():
            if time.time() - last > 300:  # 5 minutes
                self.stop_proxy(app_name)
```

### Benefits

1. **Performance**
   - 10x faster for subsequent commands
   - No connection overhead
   - No repeated OAuth flows

2. **Resource Efficiency**
   - Share connections across terminal sessions
   - Automatic cleanup of idle resources

3. **Better UX**
   - Instant responses after first command
   - Background token refresh
   - Connection status visibility

### Configuration

```yaml
# ~/.tasak/service.yaml
service:
  auto_start: true
  auto_shutdown_minutes: 10
  port: 7890
  log_level: INFO

  proxies:
    atlassian:
      keep_alive_minutes: 30  # Keep longer for frequently used
      auto_start: true

    github:
      keep_alive_minutes: 5
      auto_start: false  # Start on demand
```

### Challenges

1. **Complexity** - Another component to maintain
2. **Debugging** - Harder to troubleshoot daemon issues
3. **Platform differences** - Windows vs Linux service management
4. **Security** - Local HTTP API needs access control

### Alternative: Simple Process Pool

Instead of full service, just keep processes alive briefly:

```python
# In tasak CLI
class ProxyPool:
    _instances = {}  # Singleton per app

    def get_proxy(self, app_name):
        if app_name not in self._instances:
            self._instances[app_name] = start_proxy(app_name)
            # Auto-cleanup after delay
            threading.Timer(300, lambda: self.cleanup(app_name)).start()
        return self._instances[app_name]
```

Simpler but less capable than full service.

## DECISION: Process Pool with Future Hybrid Path

### Architectural Decision (2025-01-05)
We've decided to implement **Process Pool** as the initial solution, with architecture that allows future evolution to Hybrid model if needed.

### Implementation Plan

#### Phase 1: Process Pool (CURRENT TARGET)
- Keep `mcp-remote` proxies alive for 5 minutes after use
- Pool exists within CLI process lifetime
- No daemon, no separate service
- Simple threading-based cleanup

```python
# Implementation in tasak/mcp_remote_runner.py
class MCPRemotePool:
    """Manages pool of mcp-remote proxy processes."""

    _pool = {}  # app_name -> {'process': Popen, 'last_used': timestamp}
    _lock = threading.Lock()

    @classmethod
    def get_proxy(cls, app_name: str, server_url: str):
        with cls._lock:
            if app_name in cls._pool:
                cls._pool[app_name]['last_used'] = time.time()
                return cls._pool[app_name]['process']

            # Start new proxy
            process = cls._start_proxy(app_name, server_url)
            cls._pool[app_name] = {
                'process': process,
                'last_used': time.time()
            }

            # Schedule cleanup
            threading.Timer(300, lambda: cls._cleanup(app_name)).start()
            return process
```

#### Phase 2: Future Hybrid (IF NEEDED)
- Add `tasak service` command to run as daemon
- Same pool code, but persistent across CLI invocations
- REST API for inter-process communication
- Only implement if Process Pool proves insufficient

### Benefits of This Approach
1. **Simple to implement** - Just a class with dictionary
2. **Immediate performance gain** - No reconnection overhead
3. **No extra complexity** - No daemon management
4. **Future-proof** - Pool code reusable in service mode
5. **Gradual migration** - Can evolve without breaking changes

### Success Metrics
- Second command to same service takes <1 second (vs current 3-5 seconds)
- No zombie processes after CLI exits
- Clean shutdown on Ctrl+C

### Migration Path to Hybrid
If Process Pool is not enough (e.g., need sharing across terminal sessions):
1. Extract pool logic to shared module
2. Add service wrapper around pool
3. Add REST API
4. CLI checks for service, falls back to local pool
5. No changes to user experience

This decision balances immediate needs with future flexibility.
