# Argument Handling Architecture

## Core Principle
**Everything after `tasak <app>` goes to the target service**

## Architecture

### Command Structure
```
tasak [global-options] <app> [everything-else-goes-to-app]
```

### Global Options (processed by TASAK)
- `tasak --version` - Show TASAK version
- `tasak --help` - Show TASAK help
- `tasak --config <file>` - Use specific config file

### App-Level Arguments (everything else)
```
tasak <app> [anything] [here] [goes] [to] [app]
```

## Mode Behaviors

### 1. Proxy Mode (pass-through)
**"What you type is what you get"**

```bash
# CMD proxy example:
tasak ls -la /home
→ executes: ls -la /home

tasak ls --help
→ executes: ls --help
→ returns: ls's help, not TASAK's help

# MCP proxy example:
tasak gok note_create --title "Test" --invalid-arg "foo"
→ sends to MCP: {"title": "Test", "invalid-arg": "foo"}
→ MCP server decides if invalid-arg is an error
```

**Implementation:**
```python
def run_proxy_mode(app_config, args):
    # For CMD
    if app_type == "cmd":
        subprocess.run([command] + args)

    # For MCP
    elif app_type == "mcp":
        # No validation, just parse and send
        tool = args[0] if args else None
        tool_args = parse_args_naively(args[1:])
        mcp_client.call_tool(tool, tool_args)
```

### 2. Curated Mode (structured)
**"We validate and help you"**

```bash
# CMD curated example:
tasak docker-stats --format json
→ validates: format must be [json|table|csv]
→ executes: docker stats --format=json

tasak docker-stats --help
→ shows: TASAK's help for docker-stats (not docker's)

# MCP curated example:
tasak gok note_create --title "Test" --invalid-arg "foo"
→ ERROR: Unknown argument: --invalid-arg
→ (checks against cached schema)

tasak gok note_create --help
→ shows: TASAK's generated help from schema
```

**Implementation:**
```python
def run_curated_mode(app_config, args):
    # Build parser from schema/config
    parser = build_parser_from_schema(app_config)

    # Parse and validate
    try:
        parsed = parser.parse_args(args)
    except ArgumentError as e:
        print(f"Error: {e}")
        parser.print_help()
        sys.exit(1)

    # Execute with validated args
    if app_type == "cmd":
        cmd_args = build_command_args(parsed)
        subprocess.run([command] + cmd_args)
    elif app_type == "mcp":
        mcp_client.call_tool(parsed.tool, vars(parsed))
```

## Key Differences Summary

| Aspect | Proxy Mode | Curated Mode |
|--------|------------|--------------|
| Validation | None | Against schema |
| --help | Shows target's help | Shows TASAK's help |
| Unknown args | Passed through | Error |
| Use case | Power users, debugging | Normal usage |
| Speed | Faster (no validation) | Slower (validation) |

## Naive Argument Parsing for Proxy Mode

```python
def parse_args_naively(args: List[str]) -> Dict[str, Any]:
    """
    Convert CLI args to dict without schema knowledge.
    Examples:
    --foo bar → {"foo": "bar"}
    --flag → {"flag": True}
    --count 3 → {"count": "3"}  # Always string in proxy mode
    """
    result = {}
    i = 0
    while i < len(args):
        if args[i].startswith('--'):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith('--'):
                result[key] = args[i + 1]
                i += 2
            else:
                result[key] = True
                i += 1
        else:
            # Positional arguments
            result[f"_arg{i}"] = args[i]
            i += 1
    return result
```

## Curated Mode Configuration

### For CMD Apps
Curated mode requires full argument definition in config:

```yaml
# Example: docker-stats wrapper
docker-stats:
  type: cmd
  mode: curated
  meta:
    command: ["docker", "stats"]
    description: "Display container resource usage statistics"
    args:
      - name: format
        type: choice
        choices: [json, table, csv]
        default: table
        help: "Output format for statistics"
      - name: no-stream
        type: flag
        help: "Disable streaming, show only first result"
      - name: container
        type: string
        required: false
        help: "Container name or ID (optional)"
```

This generates help like:
```
usage: tasak docker-stats [-h] [--format {json,table,csv}] [--no-stream] [--container CONTAINER]

Display container resource usage statistics

options:
  -h, --help            show this help message and exit
  --format {json,table,csv}
                        Output format for statistics
  --no-stream           Disable streaming, show only first result
  --container CONTAINER Container name or ID (optional)
```

### For MCP Apps
Curated mode can either:

1. **Use cached schema** (from server):
```yaml
gok:
  type: mcp
  mode: curated
  # No meta needed - uses ~/.tasak/schemas/gok.yaml
```

2. **Override with custom descriptions**:
```yaml
gok:
  type: mcp
  mode: curated
  meta:
    description: "Knowledge management system"
    tools:
      note_create:
        description: "Create a new note in your knowledge base"
        args:
          title:
            description: "Title of your note (keep it concise)"
          content:
            description: "Note content in Markdown format"
      # Overrides only what's specified, rest from schema
```

## Default Mode Selection

```yaml
# In app config
gok:
  type: mcp
  mode: curated  # default for production apps

ls:
  type: cmd
  mode: proxy    # default for system commands

my-tool:
  type: cmd
  mode: curated  # when we want validation
```

## Override Mode via CLI (future)
```bash
tasak --proxy gok note_create --whatever  # Force proxy mode
tasak --curated ls -la  # Force curated mode (if schema exists)
```
