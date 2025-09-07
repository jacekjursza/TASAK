# Advanced Usage
## Contents

- [MCP-Remote Applications](#mcp-remote-applications)
  - [What is MCP-Remote?](#what-is-mcp-remote)
  - [Why Use MCP-Remote?](#why-use-mcp-remote)
  - [Process Pool Architecture (TASAK Enhancement)](#process-pool-architecture-tasak-enhancement)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [Error Handling](#error-handling)
  - [Response Structure Validation](#response-structure-validation)
  - [Troubleshooting](#troubleshooting)
- [MCP Local Applications](#mcp-local-applications)
  - [Configuration](#configuration-2)
  - [Server Types](#server-types)
  - [Authentication](#authentication)
- [CMD Applications](#cmd-applications)
  - [Curated Mode](#curated-mode)
  - [Proxy Mode](#proxy-mode)
- [Admin Commands](#admin-commands)
  - [Authentication Management](#authentication-management)
  - [Schema Management](#schema-management)
  - [Information Commands](#information-commands)
- [Performance Optimizations](#performance-optimizations)
  - [Process Pool (MCP-Remote)](#process-pool-mcp-remote)
  - [Schema Caching](#schema-caching)
  - [Connection Reuse](#connection-reuse)
- [Security Considerations](#security-considerations)
- [Compatibility Notes](#compatibility-notes)
  - [FastMCP vs Standard SDK](#fastmcp-vs-standard-sdk)
  - [Version Requirements](#version-requirements)
- [Examples](#examples)
  - [Complete Configuration](#complete-configuration)
  - [Workflow Example](#workflow-example)


## MCP-Remote Applications

### What is MCP-Remote?

`mcp-remote` is an official npm package that acts as a **proxy bridge** between local MCP clients and remote MCP servers. It handles OAuth authentication flows and maintains persistent connections to cloud-based MCP servers.

**Key Features:**
- OAuth 2.1 Authentication with PKCE
- Automatic token management and refresh
- SSE (Server-Sent Events) transport
- Dynamic OAuth client registration
- **Process pooling for performance** (TASAK enhancement)

### Why Use MCP-Remote?

Enterprise MCP servers (Atlassian, GitHub, Slack) require:
- OAuth 2.1 flows with PKCE
- Dynamic client registration
- Token refresh handling
- Secure token storage

Instead of implementing this complexity in every client, `mcp-remote` provides a standardized proxy.

### Process Pool Architecture (TASAK Enhancement)

TASAK implements a process pool for MCP-Remote connections to improve performance:

```python
# Configuration (hardcoded in mcp_remote_pool.py)
MAX_POOL_SIZE = 10   # Maximum concurrent processes
IDLE_TIMEOUT = 300   # 5 minutes
```

Benefits:
- Reuses existing connections (avoids OAuth re-authentication)
- Automatic cleanup of idle processes
- Prevents resource exhaustion
- Faster tool execution

### Configuration

#### Basic Setup

```yaml
# In tasak.yaml
atlassian:
  name: "Atlassian (Jira & Confluence)"
  type: "mcp-remote"
  meta:
    server_url: "https://mcp.atlassian.com/v1/sse"
```

#### Supported Servers

| Server | URL | Description |
|--------|-----|-------------|
| Atlassian | `https://mcp.atlassian.com/v1/sse` | Jira, Confluence |
| GitHub | `https://mcp.github.com/v1/sse` | Repositories, issues |
| Slack | `https://mcp.slack.com/v1/sse` | Workspace communication |

### Usage

#### Agent-Friendly CLI Semantics

For both MCP and MCP‑Remote apps, the CLI follows a minimal, predictable contract suitable for AI agents:

- `tasak <app>` → prints only tool names, one per line.
- `tasak <app> <tool>` →
  - Executes immediately if the tool has no required parameters.
  - Otherwise prints focused help for that tool (equivalent to `--help`) with description and parameters, including which are required and their types.
- `tasak <app> <tool> --help` → always prints focused help for that tool.
- `tasak <app> --help` → prints grouped simplified help:
  - "<app> commands:" — tools without required params (run immediately)
  - "<app> sub-apps (use --help to read more):" — tools with required params
  Each line shows `<name> - <description>`.

Additional behavior:
- Tool schemas are cached and refreshed automatically (transparent 1‑day TTL) during listing/help; no extra messages are shown to the agent.
- Transport/debug logs are suppressed by default. Set `TASAK_DEBUG=1` or `TASAK_VERBOSE=1` to see detailed diagnostics.

#### First-Time Authentication

```bash
# Triggers OAuth flow in browser
tasak atlassian

# Or explicitly authenticate
tasak admin auth atlassian
```

Process:
1. Browser opens automatically
2. Log in to service (e.g., Atlassian)
3. Approve permissions
4. Tokens saved in `~/.mcp-auth/mcp-remote-{version}/`

#### Subsequent Uses

```bash
# Uses cached tokens (from pool if available)
tasak atlassian list-projects
```

#### Token Storage

Tokens are managed by `mcp-remote`:
```
~/.mcp-auth/mcp-remote-{version}/
├── {hash}_tokens.json        # Access & refresh tokens
├── {hash}_client_info.json   # OAuth client config
└── {hash}_code_verifier.txt  # PKCE verifier
```

### Error Handling

TASAK properly distinguishes between error types:

```python
# Authentication errors cause exit
if "401" in error_msg or "unauthorized" in error_msg.lower():
    sys.exit(1)  # User needs to re-authenticate

# Other errors are raised for proper handling
raise RuntimeError(f"Failed to call tool: {error_msg}")
```

### Response Structure Validation

TASAK validates response structures to prevent crashes:

```python
# Checks for expected structure
if hasattr(result, "content") and result.content:
    # Extract text or data
elif result:
    # Return as-is if different structure
```

### Troubleshooting

#### Node.js Not Found
```bash
Error: npx not found. Please install Node.js first.
```
**Solution:** Install Node.js from https://nodejs.org/

#### Authentication Issues
```bash
Authentication required. Run: tasak admin auth [app_name]
```
**Solution:** Re-authenticate with `tasak admin auth [app_name]`

#### Token Expired
Tokens should auto-refresh. If not:
```bash
# Clear and re-authenticate
rm -rf ~/.mcp-auth/mcp-remote-*/
tasak admin auth atlassian
```

## MCP Local Applications

### Configuration

MCP apps connect to local MCP servers running as subprocesses:

```yaml
# In tasak.yaml
my_mcp_app:
  name: "Local MCP Server"
  type: "mcp"
  config: "./mcp_config.json"  # Or Python/Node script
```

### Server Types

1. **Python MCP Servers**: Using `fastmcp` or standard SDK
2. **Node.js MCP Servers**: Using `@modelcontextprotocol/sdk`
3. **Binary MCP Servers**: Any executable following MCP protocol

### Authentication

Local MCP apps may handle their own authentication:

```yaml
my_mcp_app:
  type: "mcp"
  config: "./config.json"
  meta:
    requires_auth: true
    auth_type: "api_key"
```

## CMD Applications

### Curated Mode

Curated mode provides structured parameter handling:

```yaml
git_log:
  type: "cmd"
  meta:
    command: "git log"
    mode: "curated"
    parameters:
      - name: "lines"
        type: "int"
        default: 10
        maps_to: "-n"
      - name: "oneline"
        type: "flag"
        maps_to: "--oneline"
```

Usage:
```bash
tasak git_log --lines 5 --oneline
# Executes: git log -n 5 --oneline
```

### Proxy Mode

Direct command pass-through:

```yaml
git:
  type: "cmd"
  meta:
    command: "git"
    mode: "proxy"
```

Usage:
```bash
tasak git status --short
# Executes: git status --short
```

## Admin Commands

### Authentication Management

```bash
# Check authentication status
tasak admin auth [app_name] --check

# Clear authentication
tasak admin auth [app_name] --clear

# Re-authenticate
tasak admin auth [app_name]
```

### Schema Management

```bash
# Refresh tool schemas
tasak admin refresh [app_name]
tasak admin refresh --all

# Clear cached schemas
tasak admin clear [app_name] --schema
```

### Information Commands

```bash
# List all configured apps
tasak admin list
tasak admin list --verbose

# Show app details
tasak admin info [app_name]
```

## Performance Optimizations

### Process Pool (MCP-Remote)

- Maintains up to 10 concurrent processes
- Reuses connections for 5 minutes
- Automatic cleanup of idle processes
- Statistics available via pool.get_stats()

### Schema Caching

- Tool definitions cached locally
- 7-day default cache duration
- Manual refresh: `tasak admin refresh [app_name]`

### Connection Reuse

- SSE connections kept alive
- OAuth tokens refreshed automatically
- Process pooling prevents re-authentication

## Security Considerations

1. **Token Storage**: User-only permissions in `~/.mcp-auth/`
2. **HTTPS Only**: All remote communications use TLS
3. **OAuth 2.1**: Modern security with PKCE
4. **Scoped Access**: Minimal required permissions
5. **No Secrets in Code**: All credentials in secure storage

## Compatibility Notes

### FastMCP vs Standard SDK

Both FastMCP and standard MCP SDK are supported:
- **Protocol compatible**: Same JSON-RPC over SSE/stdio
- **Connection handling**: Unified client code
- **Tool discovery**: Automatic schema detection

### Version Requirements

- **Node.js**: 16+ (for npx and mcp-remote)
- **Python**: 3.11+ (for TASAK)
- **mcp-remote**: Auto-installed via npx

## Examples

### Complete Configuration

```yaml
# ~/.tasak/tasak.yaml
apps_config:
  enabled_apps:
    - jira
    - github
    - git
    - local_tools

# MCP-Remote app
jira:
  name: "Jira Integration"
  type: "mcp-remote"
  meta:
    server_url: "https://mcp.atlassian.com/v1/sse"

# MCP-Remote app
github:
  name: "GitHub Integration"
  type: "mcp-remote"
  meta:
    server_url: "https://mcp.github.com/v1/sse"

# CMD app (curated)
git:
  name: "Git Helper"
  type: "cmd"
  meta:
    command: "git"
    mode: "curated"
    parameters:
      - name: "message"
        type: "str"
        maps_to: "-m"
        help: "Commit message"

# Local MCP app
local_tools:
  name: "Local Python Tools"
  type: "mcp"
  config: "./tools/mcp_server.py"
```

### Workflow Example

```bash
# 1. First-time setup
tasak admin auth jira
tasak admin auth github

# 2. Use tools
tasak jira search-issues --project PROJ --status "In Progress"
tasak github create-pr --title "Feature X" --base main

# 3. Local operations
tasak git commit --message "Add feature X"
tasak local_tools run-analysis --input data.csv

# 4. Maintenance
tasak admin refresh --all  # Update schemas
tasak admin list --verbose  # Check status
```
