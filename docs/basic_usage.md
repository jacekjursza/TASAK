# Basic Usage
## Contents

- [Understanding App Types](#understanding-app-types)
- [Your First App](#your-first-app)
- [Simple Commands with CMD Apps](#simple-commands-with-cmd-apps)
- [Introduction to Curated Apps](#introduction-to-curated-apps)
- [Practical Examples](#practical-examples)
  - [1. File Operations](#1-file-operations)
  - [2. Development Tools](#2-development-tools)
  - [3. System Information](#3-system-information)
  - [4. Data Processing](#4-data-processing)
- [Using Environment Variables](#using-environment-variables)
- [Command Chaining](#command-chaining)
- [Working with Project Configs](#working-with-project-configs)
- [Tips and Best Practices](#tips-and-best-practices)
  - [1. Naming Conventions](#1-naming-conventions)
  - [2. Security](#2-security)
  - [3. Documentation](#3-documentation)
  - [4. Organization](#4-organization)
  - [5. Error Handling](#5-error-handling)
- [Common Patterns](#common-patterns)
  - [Pattern 1: Conditional Execution](#pattern-1-conditional-execution)
  - [Pattern 2: Multi-line Commands](#pattern-2-multi-line-commands)
  - [Pattern 3: Output Redirection](#pattern-3-output-redirection)
- [Troubleshooting Common Issues](#troubleshooting-common-issues)
  - [App not found](#app-not-found)
  - [Command fails silently](#command-fails-silently)
  - [Arguments not working](#arguments-not-working)
- [Next Steps](#next-steps)
 - [Create a Standalone Command](#create-a-standalone-command)


This guide covers creating and using simple `cmd` apps - the foundation of TASAK.

## Understanding App Types

TASAK supports two app types:

- **`cmd`**: Execute shell commands (this guide)
- **`mcp`**: Run persistent MCP servers ([Advanced Usage](advanced_usage.md))

## Your First App

Let's create a simple app that lists files:

```yaml
# ~/.tasak/tasak.yaml
header: "My TASAK Tools"

apps_config:
  enabled_apps:
    - list_files

list_files:
  name: "List Files"
  type: "cmd"
  meta:
    command: "ls -la"
```

Run it:
```bash
tasak list_files

# Output:
# total 24
# drwxr-xr-x  3 user user 4096 Jan 15 10:00 .
# drwxr-xr-x 10 user user 4096 Jan 15 09:00 ..
# -rw-r--r--  1 user user  234 Jan 15 10:00 tasak.yaml
```

## Simple Commands with CMD Apps

CMD apps execute shell commands directly. They're perfect for single-purpose tools:

```yaml
git_status:
  name: "Git Status"
  type: "cmd"
  meta:
    command: "git status"
```

Usage:
```bash
tasak git_status
# Executes: git status

# Arguments are passed through
tasak git_status --short
# Executes: git status --short
```

## Introduction to Curated Apps

**Note**: Curated apps are a new feature that create composite APIs from multiple tools. They're covered in detail in [Advanced Usage](advanced_usage.md).

Unlike simple `cmd` apps, `curated` apps can:
- Orchestrate multiple commands
- Combine different tool types (cmd, mcp)
- Provide structured interfaces with validation
- Execute conditional workflows

Quick example:
```yaml
my-workspace:
  type: curated  # New app type!
  name: "Development Workspace"
  commands:
    - name: "start"
      description: "Start all services"
      backend:
        type: composite
        steps:
          - type: cmd
            command: ["docker-compose", "up", "-d"]
          - type: cmd
            command: ["npm", "run", "dev"]
```

Usage:
```bash
tasak my-workspace start
# Executes multiple commands in sequence
```

For now, let's focus on simple `cmd` apps.

## Practical Examples

### 1. File Operations

```yaml
# File management tools
apps_config:
  enabled_apps:
    - find_large_files
    - backup_current
    - clean_temp

find_large_files:
  name: "Find Large Files"
  type: "cmd"
  meta:
    command: "find . -type f -size +100M -exec ls -lh {} \\;"

backup_current:
  name: "Backup Current Directory"
  type: "cmd"
  meta:
    command: "tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz ."  # Backs up current directory

clean_temp:
  name: "Clean Temp Files"
  type: "cmd"
  meta:
    command: "find /tmp -type f -mtime +7 -delete"
```

### 2. Development Tools

```yaml
# Development workflow
apps_config:
  enabled_apps:
    - run_tests
    - format_code
    - check_types

run_tests:
  name: "Run Tests"
  type: "cmd"
  meta:
    command: "pytest tests/ -v"

format_code:
  name: "Format Code"
  type: "cmd"
  meta:
    command: "black . --line-length 88"  # Use default values

check_types:
  name: "Type Check"
  type: "cmd"
  meta:
    command: "mypy . --strict"
```

### 3. System Information

```yaml
# System monitoring
apps_config:
  enabled_apps:
    - disk_usage
    - memory_info
    - network_status

disk_usage:
  name: "Disk Usage"
  type: "cmd"
  meta:
    command: "df -h"

memory_info:
  name: "Memory Info"
  type: "cmd"
  meta:
    command: "free -h"

network_status:
  name: "Network Status"
  type: "cmd"
  meta:
    command: "ss -tulpn | grep LISTEN"
```

### 4. Data Processing

```yaml
# Data tools
apps_config:
  enabled_apps:
    - count_lines
    - json_format
    - csv_preview

count_lines:
  name: "Count Lines"
  type: "cmd"
  meta:
    command: "wc -l"  # Pass filename as argument

json_format:
  name: "Format JSON"
  type: "cmd"
  meta:
    command: "python -m json.tool"  # Use stdin/stdout redirection

csv_preview:
  name: "Preview CSV"
  type: "cmd"
  meta:
    command: "head -n 10 | column -t -s,"  # Pass file via stdin or as argument
```

## Using Environment Variables

Environment variables are expanded by the shell when the command is executed:

```yaml
deploy:
  name: "Deploy Application"
  type: "cmd"
  meta:
    # Shell will expand $DEPLOY_USER and $DEPLOY_HOST from environment
    command: "rsync -av ./dist/ $DEPLOY_USER@$DEPLOY_HOST:/var/www/app"
```

Set environment variables before running:
```bash
export DEPLOY_USER="admin"
export DEPLOY_HOST="server.example.com"
tasak deploy
```

**Note**: The `env` section is only supported in `mcp` type apps, not in `cmd` apps.

## Command Chaining

Create complex workflows with shell operators:

```yaml
build_and_test:
  name: "Build and Test"
  type: "cmd"
  meta:
    command: "npm run build && npm test && echo 'Build successful!'"

safe_cleanup:
  name: "Safe Cleanup"
  type: "cmd"
  meta:
    command: "rm -rf temp/* || echo 'No temp files to clean'"
```

## Working with Project Configs

Create project-specific tools that complement global ones:

```yaml
# ~/myproject/tasak.yaml
header: "MyProject Tools"

apps_config:
  enabled_apps:
    - start_dev
    - db_migrate
    - generate_docs

start_dev:
  name: "Start Development"
  type: "cmd"
  meta:
    command: "docker-compose up -d && npm run dev"

db_migrate:
  name: "Database Migration"
  type: "cmd"
  meta:
    command: "python manage.py migrate"

generate_docs:
  name: "Generate Documentation"
  type: "cmd"
  meta:
    command: "sphinx-build -b html docs/ docs/_build"
```

## Create a Standalone Command

Turn your TASAK config into its own CLI wrapper (uses `<name>.yaml` instead of `tasak.yaml`).

```bash
# Create wrapper in current directory
tasak admin create_command mytool

# Run locally (current dir is not in PATH)
./mytool --help

# Install globally (~/.local/bin/mytool)
tasak admin create_command mytool --global
# Ensure ~/.local/bin is in PATH (e.g., add to ~/.bashrc)
```

Notes:
- Wrapper sets `TASAK_CONFIG_NAME=mytool.yaml` and `TASAK_BIN_NAME=mytool`.
- Config resolution merges `~/.tasak/mytool.yaml` with local `./mytool.yaml` and `./.tasak/mytool.yaml`.
- See Advanced Usage → “Custom Commands (create_command)” for details.

## Tips and Best Practices

### 1. Naming Conventions
- Use descriptive, action-oriented names
- Use underscores for multi-word names
- Group related apps with prefixes (e.g., `git_status`, `git_log`)

### 2. Security
- Never hardcode passwords or API keys
- Use environment variables for sensitive data
- Be careful with commands that delete or modify files
- Test commands manually before adding to TASAK

### 3. Documentation
- Add comments in your YAML files
- Use descriptive `help` text for curated args
- Keep a README with your custom apps

### 4. Organization
```yaml
# Group related apps together
# === File Operations ===
list_files:
  # ...

find_files:
  # ...

# === Git Commands ===
git_status:
  # ...

git_log:
  # ...
```

### 5. Error Handling
```yaml
safe_command:
  name: "Safe Command"
  type: "cmd"
  meta:
    # Use || to provide fallback
    command: "risky_command || echo 'Command failed, but continuing...'"

required_command:
  name: "Required Command"
  type: "cmd"
  meta:
    # Use && to ensure prerequisites
    command: "test -f config.json && python app.py"
```

## Common Patterns

### Pattern 1: Conditional Execution
```yaml
backup_if_exists:
  name: "Backup If Exists"
  type: "cmd"
  meta:
    command: "[ -f data.db ] && cp data.db data.backup.db || echo 'No database to backup'"
```

### Pattern 2: Multi-line Commands
```yaml
complex_task:
  name: "Complex Task"
  type: "cmd"
  meta:
    command: >
      echo "Starting task..." &&
      python preprocess.py &&
      python main.py &&
      python cleanup.py &&
      echo "Task completed!"
```

### Pattern 3: Output Redirection
```yaml
save_report:
  name: "Save Report"
  type: "cmd"
  meta:
    command: "python generate_report.py > reports/report_$(date +%Y%m%d).txt 2>&1"
```

## Troubleshooting Common Issues

### App not found
```bash
tasak myapp
# Error: App 'myapp' not found

# Fix: Check it's in enabled_apps list
```

### Command fails silently
```yaml
# Add error checking
my_command:
  meta:
    command: "set -e && my_risky_command"  # Exit on error
```

### Arguments not working
```yaml
# For complex parameter handling, use the new curated app type
# See Advanced Usage guide for details on curated apps
my_app:
  type: curated  # New app type for composite APIs
  commands:
    - name: "process"
      params:
        - name: "--file"
          required: true
```

## Next Steps

You've learned the basics of creating and using `cmd` apps. Ready for more?

- Explore [Advanced Usage](advanced_usage.md) - Learn about MCP servers, authentication, and complex workflows
- Check out example configurations in the repository
- Share your custom apps with the community!
