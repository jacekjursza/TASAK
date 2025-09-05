# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TASAK (The Agent's Swiss Army Knife) is a command-line proxy that enables AI agents to safely execute predefined tools and applications. It provides two types of applications:
- `cmd`: Simple shell command execution
- `mcp`: Persistent MCP (Model Context Protocol) servers for stateful interactions

## Common Development Commands

### Setup and Dependencies
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

### Code Quality
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Run Ruff linter with auto-fix
ruff check . --fix

# Format code with Ruff
ruff format .
```

### Testing the Application
```bash
# Run TASAK to list available apps
tasak

# Test a specific app
tasak <app_name>

# Get help for an app
tasak <app_name> --help
```

## Architecture

### Core Components

1. **main.py**: Entry point that handles argument parsing and routes to appropriate app runners
2. **config.py**: Hierarchical configuration loading system (global → local)
3. **app_runner.py**: Executes `cmd` type applications in proxy or curated modes
4. **mcp_client.py**: Handles MCP server lifecycle and communication
5. **auth.py**: OAuth 2.1 authentication flow implementation

### Configuration Hierarchy

Configs are loaded and merged in order:
1. Global: `~/.tasak/tasak.yaml`
2. Local: Searches upward from CWD for `tasak.yaml` or `.tasak/tasak.yaml`
3. Later configs override earlier ones

### App Types

**cmd apps**: Direct command execution
- `proxy` mode: Passes arguments directly to command
- `curated` mode: Uses argparse for structured parameter handling

**mcp apps**: Local MCP server management
- Spawns server process from config file
- Manages authentication if required
- Proxies tool calls between agent and server

**mcp-remote apps**: Remote MCP servers via official proxy
- Uses `npx mcp-remote` for OAuth-protected servers
- Handles authentication flow automatically
- Ideal for cloud services like Atlassian, GitHub, Slack

### Key Design Patterns

- Configuration-driven application registry
- Hierarchical config merging for flexibility
- Process management for MCP servers
- OAuth 2.1 flow for secure authentication

## Important Constraints

- Python 3.11+ required
- Max 600 lines per file (enforced by pre-commit)
- All code, documentation, and comments must be in English
- Follow DRY principles and maintain modular structure
