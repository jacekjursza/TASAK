# Curated Mode - Complete Redesign as API Composite

## New Vision: API Composite Pattern

Curated mode should be a way to create **composite APIs** that abstract over multiple underlying systems, not just parameter remapping.




## Core Concept

Curated mode creates an **abstraction layer** where one TASAK app can orchestrate multiple underlying tools:

```yaml
my-todo:
  type: curated  # New type! Not cmd with mode:curated
  name: "Unified TODO Manager"

  commands:
    - name: "list"
      description: "List tasks from multiple sources"
      backend:
        type: cmd
        command: ["todo-cli", "list", "--format=json", "--project=${project}"]
      params:
        - name: "--project"
          required: false
          help: "Filter by project name"

    - name: "create"
      description: "Create task in Jira"
      backend:
        type: mcp
        app: "atlassian"
        tool: "jira_create_issue"
        args:
          project: "PAY"  # Hardcoded
          title: "${title}"  # From user
          description: "${description}"
      params:
        - name: "--title"
          required: true
          help: "Task title"
        - name: "--description"
          required: false
          default: ""
          help: "Task description"

    - name: "sync"
      description: "Sync local TODOs to Jira"
      backend:
        type: composite  # Calls multiple backends!
        steps:
          - type: cmd
            command: ["todo-cli", "export", "--format=json"]
            capture: "todos"
          - type: mcp
            app: "atlassian"
            tool: "jira_bulk_create"
            args:
              items: "${todos}"
```

## Key Features

### 1. Single App, Multiple Commands
Instead of `tasak app-name tool args`, curated apps work like:
```bash
tasak my-todo list --project backend
tasak my-todo create --title "Fix bug" --description "Details..."
tasak my-todo sync
```

### 2. Backend Abstraction
One command can call:
- Shell commands (`type: cmd`)
- MCP tools (`type: mcp`)
- Other TASAK apps (`type: tasak`)
- Multiple steps (`type: composite`)

### 3. Parameter Interpolation
```yaml
command: ["git", "commit", "-m", "${message}"]
args:
  project: "${project_name:-DEFAULT}"  # With default
  title: "${title}"  # Required
```

### 4. Data Flow Between Steps
```yaml
steps:
  - command: ["get-config"]
    capture: "config"  # Save output
  - command: ["deploy", "--env=${config.environment}"]  # Use it
```

## Implementation Architecture

### Proposed Solution
**Location:** `app_runner.py` line 53
```python
for param in params_config:
    param_name = param.pop("name")  # DESTRUCTIVE - modifies original dict!
    parser.add_argument(param_name, **param)
```

**Problem:**
- `pop()` removes "name" from the dictionary permanently
- Later code at line 66 tries to access the destroyed config
- Second run would fail completely (no "name" key exists)

### 2. Broken Mapping Logic
**Location:** `app_runner.py` lines 63-76
```python
for arg_name, arg_value in vars(parsed_args).items():
    if arg_value is not None:
        for p_config in params_config:
            if p_config["dest"] == arg_name:  # FAILS - "name" was removed!
                maps_to = p_config.get("maps_to")
```

**Problems:**
- Can't find config because "name" was popped
- `maps_to` is passed to argparse (shouldn't be)
- Logic doesn't handle the actual parameter translation

### 3. No Parameter Remapping for MCP
MCP apps only validate against schema but don't support parameter remapping at all.

## Expected Behavior

### Example Configuration
```yaml
docker-stats:
  type: cmd
  meta:
    mode: curated
    command: ["docker", "stats"]
    params:
      - name: "--output"          # User types this
        dest: "output_format"      # Internal variable name
        maps_to: "--format"        # Actual docker flag
        choices: ["json", "table"]
        help: "Output format"

      - name: "--verbose"          # User types this
        dest: "verbose"
        maps_to: "-v"              # Maps to short flag
        action: "store_true"
        help: "Verbose output"

      - name: "--watch"            # User types this
        dest: "no_stream"
        maps_to: "--no-stream"     # Different flag name
        action: "store_false"      # Inverted logic!
        help: "Watch for changes"
```

### Expected Usage
```bash
# User types:
tasak docker-stats --output json --verbose --watch

# Should execute:
docker stats --format json -v --no-stream
```

## Implementation Fix

### Step 1: Fix Configuration Destruction

```python
def _run_curated_mode(meta: Dict[str, Any], app_args: List[str]):
    """Executes the command in curated mode."""
    base_command = meta.get("command")
    params_config = meta.get("params", [])

    if not base_command:
        print("'command' not specified for curated mode.", file=sys.stderr)
        sys.exit(1)

    # Build parser WITHOUT modifying original config
    parser = argparse.ArgumentParser(
        description=meta.get("description", "Curated command")
    )

    # Create mapping of dest -> param config for later use
    dest_to_config = {}

    for param_orig in params_config:
        # Make a copy to avoid modifying original
        param = param_orig.copy()
        param_name = param.pop("name")

        # Store mapping for later
        param_dest = param.get("dest") or param_name.lstrip("-").replace("-", "_")
        dest_to_config[param_dest] = param_orig

        # Remove maps_to from argparse params (it's for us, not argparse)
        param.pop("maps_to", None)

        # Add to parser
        parser.add_argument(param_name, **param)
```

### Step 2: Fix Mapping Logic

```python
    # Parse arguments
    parsed_args = parser.parse_args(app_args)

    # Build command
    if isinstance(base_command, str):
        command_list = base_command.split()
    else:
        command_list = list(base_command)

    # Map parsed arguments to command flags
    for arg_name, arg_value in vars(parsed_args).items():
        if arg_value is None:
            continue

        # Skip boolean False values (unless it's store_false action)
        if isinstance(arg_value, bool) and not arg_value:
            config = dest_to_config.get(arg_name)
            if config and config.get("action") != "store_false":
                continue

        # Get the configuration for this argument
        if arg_name in dest_to_config:
            config = dest_to_config[arg_name]

            # Get the flag to use (maps_to or original name)
            flag = config.get("maps_to", config["name"])

            # Add flag
            command_list.append(flag)

            # Add value if not boolean or if True
            if not isinstance(arg_value, bool):
                command_list.append(str(arg_value))
            # For store_false, we already added the flag

    _execute_command(command_list)
```

### Step 3: Add Tests

Create `tests/test_curated_mode.py`:
```python
def test_parameter_remapping():
    """Test that parameters are correctly remapped."""
    meta = {
        'command': ['echo'],
        'params': [
            {
                'name': '--my-format',
                'dest': 'format',
                'maps_to': '--original-format'
            }
        ]
    }

    result = build_command(meta, ['--my-format', 'json'])
    assert result == ['echo', '--original-format', 'json']

def test_boolean_flags():
    """Test boolean flag handling."""
    meta = {
        'command': ['echo'],
        'params': [
            {
                'name': '--verbose',
                'dest': 'verbose',
                'maps_to': '-v',
                'action': 'store_true'
            }
        ]
    }

    result = build_command(meta, ['--verbose'])
    assert result == ['echo', '-v']

def test_inverted_boolean():
    """Test store_false action."""
    meta = {
        'command': ['echo'],
        'params': [
            {
                'name': '--watch',
                'dest': 'no_stream',
                'maps_to': '--no-stream',
                'action': 'store_false'
            }
        ]
    }

    result = build_command(meta, ['--watch'])
    assert result == ['echo', '--no-stream']
```

## MCP Curated Mode Extension

For MCP apps, add similar remapping capability:

```python
def _run_mcp_curated_mode(app_name, app_config, app_args):
    """Run MCP app in curated mode with parameter remapping."""
    meta = app_config.get("meta", {})
    remap_config = meta.get("params", {})

    # If remap config exists, translate parameters
    if remap_config:
        tool_name, translated_args = translate_mcp_args(app_args, remap_config)
    else:
        # Fallback to normal validation
        tool_name = app_args[0] if app_args else None
        translated_args = parse_args_with_validation(app_args[1:])

    # Execute with translated arguments
    client.call_tool(tool_name, translated_args)
```

## Configuration Examples

### Example 1: Git Wrapper
```yaml
git-simple:
  type: cmd
  meta:
    mode: curated
    command: ["git"]
    description: "Simplified git interface"
    params:
      - name: "--save"
        dest: "save"
        maps_to: "commit"
        help: "Save changes"

      - name: "--message"
        dest: "message"
        maps_to: "-m"
        help: "Commit message"

      - name: "--everything"
        dest: "all"
        maps_to: "-a"
        action: "store_true"
        help: "Include all changes"
```

Usage: `tasak git-simple --save --message "Fixed bug" --everything`
Executes: `git commit -m "Fixed bug" -a`

### Example 2: Docker Simplified
```yaml
docker-simple:
  type: cmd
  meta:
    mode: curated
    command: ["docker"]
    description: "Simplified docker interface"
    params:
      - name: "action"
        dest: "action"
        choices: ["list", "stop", "remove"]
        help: "Action to perform"
        position: 0  # Positional argument

      - name: "--type"
        dest: "type"
        maps_to: None  # Handled specially
        choices: ["containers", "images"]
        default: "containers"
        help: "Resource type"
```

Usage: `tasak docker-simple list --type images`
Executes: `docker images` (special handling for combined commands)

## Benefits When Fixed

1. **User-Friendly APIs** - Create intuitive interfaces for complex commands
2. **Parameter Translation** - Map verbose names to cryptic flags
3. **Consistent Interface** - Standardize similar tools to use same parameter names
4. **Simplified Options** - Hide complexity, expose only what's needed
5. **Inverted Logic** - Can invert boolean flags for better UX

## Implementation Priority

**HIGH** - This is a core feature that's currently broken. It affects the fundamental value proposition of TASAK as a command proxy that can improve UX.

## Estimated Effort

- Fix implementation: 2-4 hours
- Add tests: 2 hours
- Test with real commands: 1 hour
- Total: ~5-7 hours
