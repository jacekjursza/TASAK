# Curated Mode - Complete Redesign as API Composite

## New Vision: API Composite Pattern

Curated mode should be a way to create **composite APIs** that abstract over multiple underlying systems, not just parameter remapping.

## Core Concept

Create unified command-line interfaces that orchestrate multiple tools:

```yaml
my-workspace:
  type: curated  # New app type!
  name: "My Development Workspace"
  description: "Unified interface for my dev workflow"

  commands:
    - name: "start"
      description: "Start development environment"
      backend:
        type: composite
        steps:
          - name: "Start Docker containers"
            type: cmd
            command: ["docker-compose", "up", "-d"]
          - name: "Start local server"
            type: cmd
            command: ["npm", "run", "dev"]
            async: true  # Don't wait
          - name: "Open IDE"
            type: cmd
            command: ["code", "."]

    - name: "task"
      description: "Manage tasks across systems"
      subcommands:
        - name: "create"
          description: "Create task in Jira"
          backend:
            type: mcp
            app: "atlassian"
            tool: "jira_create_issue"
            args:
              project: "${project:-MAIN}"
              title: "${title}"
              type: "${type:-Task}"
          params:
            - name: "--title"
              required: true
              help: "Task title"
            - name: "--project"
              help: "Jira project key"
            - name: "--type"
              choices: ["Task", "Bug", "Story"]
              help: "Issue type"

        - name: "list"
          description: "List tasks from multiple sources"
          backend:
            type: composite
            parallel: true  # Run in parallel
            steps:
              - name: "Local TODOs"
                type: cmd
                command: ["grep", "-r", "TODO", ".", "--include=*.py"]
                capture: "local_todos"
              - name: "Jira tasks"
                type: mcp
                app: "atlassian"
                tool: "jira_search"
                args:
                  jql: "assignee = currentUser() AND status != Done"
                capture: "jira_tasks"
            output:
              format: "merged_json"  # Combine results

    - name: "deploy"
      description: "Deploy to environment"
      backend:
        type: conditional  # New: conditional execution
        condition: "${env}"
        branches:
          dev:
            type: cmd
            command: ["./deploy.sh", "development"]
          prod:
            type: composite
            steps:
              - type: cmd
                command: ["npm", "test"]
                required: true  # Must succeed
              - type: cmd
                command: ["./deploy.sh", "production"]
      params:
        - name: "--env"
          required: true
          choices: ["dev", "prod"]
          help: "Target environment"
```

## Key Design Principles

### 1. Composability
Build complex workflows from simple building blocks:
- Shell commands
- MCP tools
- Other TASAK apps
- HTTP APIs (future)

### 2. Abstraction
Hide implementation details:
```bash
# User doesn't need to know this uses Jira via MCP
tasak my-workspace task create --title "Fix login bug"

# Or that this orchestrates multiple tools
tasak my-workspace start
```

### 3. Reusability
Define once, use everywhere:
```yaml
# Define reusable command groups
templates:
  git-flow:
    - name: "feature"
      backend:
        type: composite
        steps:
          - {type: cmd, command: ["git", "checkout", "-b", "feature/${name}"]}
          - {type: cmd, command: ["git", "push", "-u", "origin", "feature/${name}"]}

# Use in multiple curated apps
my-project:
  type: curated
  include:
    - templates.git-flow
```

## Implementation Approach

### Phase 1: New App Type
Create `type: curated` as distinct from `type: cmd` with `mode: curated`:

```python
# tasak/curated_app.py
class CuratedApp:
    """Orchestrates multiple backends as a composite API."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.commands = self._build_commands(config.get("commands", []))

    def execute(self, args: List[str]):
        """Route to appropriate command."""
        if not args:
            self._show_help()
            return

        command_name = args[0]
        command_args = args[1:]

        if command_name in self.commands:
            self.commands[command_name].execute(command_args)
        else:
            print(f"Unknown command: {command_name}")
            self._show_help()
```

### Phase 2: Backend Executors

```python
# tasak/backends/cmd_backend.py
class CmdBackend:
    """Executes shell commands with variable interpolation."""

    def execute(self, config: Dict, context: Dict):
        command = self._interpolate(config["command"], context)
        subprocess.run(command)

# tasak/backends/mcp_backend.py
class McpBackend:
    """Calls MCP tools."""

    def execute(self, config: Dict, context: Dict):
        app = config["app"]
        tool = config["tool"]
        args = self._interpolate(config.get("args", {}), context)

        # Use existing MCP client
        client = MCPClient(app)
        return client.call_tool(tool, args)

# tasak/backends/composite_backend.py
class CompositeBackend:
    """Orchestrates multiple steps."""

    def execute(self, config: Dict, context: Dict):
        results = {}

        for step in config["steps"]:
            backend = create_backend(step["type"])
            result = backend.execute(step, context)

            if step.get("capture"):
                results[step["capture"]] = result
                context.update(results)

        return results
```

### Phase 3: Variable Interpolation

```python
def interpolate(template: Any, context: Dict) -> Any:
    """Replace ${var} with values from context."""
    if isinstance(template, str):
        # Handle ${var:-default} syntax
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            expr = match.group(1)
            if ":-" in expr:
                var, default = expr.split(":-", 1)
                return str(context.get(var, default))
            return str(context.get(expr, ""))

        return re.sub(pattern, replacer, template)

    elif isinstance(template, dict):
        return {k: interpolate(v, context) for k, v in template.items()}

    elif isinstance(template, list):
        return [interpolate(item, context) for item in template]

    return template
```

## Examples of Composite Power

### Example 1: Multi-Step Deployment
```yaml
deploy-all:
  type: curated
  commands:
    - name: "release"
      backend:
        type: composite
        steps:
          # 1. Run tests
          - type: cmd
            command: ["npm", "test"]
            required: true

          # 2. Build
          - type: cmd
            command: ["npm", "run", "build"]

          # 3. Create GitHub release
          - type: mcp
            app: "github"
            tool: "create_release"
            args:
              version: "${version}"

          # 4. Deploy to cloud
          - type: cmd
            command: ["terraform", "apply", "-auto-approve"]

          # 5. Notify team
          - type: mcp
            app: "slack"
            tool: "send_message"
            args:
              channel: "#releases"
              message: "Version ${version} deployed!"
```

### Example 2: Cross-System Search
```yaml
search-everywhere:
  type: curated
  commands:
    - name: "find"
      backend:
        type: composite
        parallel: true
        steps:
          - type: cmd
            command: ["rg", "${query}"]
            capture: "code_results"

          - type: mcp
            app: "atlassian"
            tool: "confluence_search"
            args: {query: "${query}"}
            capture: "docs_results"

          - type: mcp
            app: "github"
            tool: "search_issues"
            args: {query: "${query}"}
            capture: "issue_results"

        output:
          type: "formatted_report"
```

## Benefits

1. **Unified Interface** - One command to rule them all
2. **Workflow Automation** - Complex multi-step processes simplified
3. **Cross-System Integration** - Combine any tools TASAK can access
4. **Maintainability** - Change implementation without changing interface
5. **Shareability** - Export and share curated app definitions

## Migration Path

1. Keep existing `mode: curated` for simple parameter remapping (fix bugs first)
2. Introduce `type: curated` as new app type
3. Gradually migrate complex use cases to new format
4. Eventually deprecate `mode: curated` in favor of `type: curated`

## Success Metrics

- Reduce 10-step manual workflows to single commands
- Enable non-technical users to execute complex operations
- Share and reuse workflow definitions across teams

## Estimated Effort

- Phase 1 (Basic curated app type): 2 days
- Phase 2 (Backend executors): 3 days
- Phase 3 (Full features): 1 week
- Total: ~2 weeks for full implementation

## Priority

**MEDIUM-HIGH** - This transforms TASAK from a simple proxy into a powerful workflow orchestration tool. However, Process Pool should be done first for performance.
