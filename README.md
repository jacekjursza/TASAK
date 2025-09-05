# TASAK: The Agent's Swiss Army Knife

**TASAK is a command-line proxy that allows AI agents to safely and effectively use predefined tools and applications within your local environment.**

It acts as a secure bridge, exposing a curated set of commands (`cmd` apps) and powerful, AI-native servers (`mcp` apps) through a simple configuration file. The primary user of TASAK is an AI agent, which uses it as an interface to perform tasks on your behalf.

## Key Features

*   **AI-First:** Designed from the ground up as a tool for AI agents to interact with a local system.
*   **Declarative Configuration:** Define available applications and their settings in a simple `tasak.yaml` file.
*   **Hierarchical Config:** Merge global (`~/.tasak/`) and local (`./`) configurations for maximum flexibility.
*   **Two App Types:**
    *   `cmd`: Expose simple, one-off shell commands.
    *   `mcp`: Run persistent, AI-native servers using the **Model Context Protocol (MCP)** for advanced, stateful interactions.
*   **Secure:** You have full control over which commands and applications the AI agent can access.

## How It Works

1.  An **AI Agent** needs to perform a task on your machine (e.g., list files, check weather).
2.  It uses TASAK to discover and execute available "apps".
3.  TASAK reads its configuration (`tasak.yaml`) to find the requested app.
4.  It then runs the app, whether it's a simple command or a complex MCP server, and pipes the output back to the agent.

```mermaid
sequenceDiagram
    participant AI Agent
    participant TASAK
    participant App (cmd/mcp)

    AI Agent->>TASAK: Execute 'list_project_files'
    TASAK->>TASAK: Load tasak.yaml
    TASAK->>App: Run command: 'ls -R src'
    App-->>TASAK: Return file list
    TASAK-->>AI Agent: Stream file list
```

## Getting Started

### Installation

*(This is a placeholder, as the installation method is not yet defined)*

```bash
# Recommended: Install via pipx
pipx install git+https://github.com/jacekjursza/TASAK.git

# Alternative: Install directly
pip install git+https://github.com/jacekjursza/TASAK.git
```

### Configuration

1.  Create a global configuration file to define your most-used apps:

    ```bash
    mkdir -p ~/.tasak
    touch ~/.tasak/tasak.yaml
    ```

2.  Add your first app. For example, a simple command to list files:

    ```yaml
    # ~/.tasak/tasak.yaml
    header: "My Global TASAK Apps"

    apps_config:
      enabled_apps:
        - list_files

    list_files:
      name: "List Files"
      type: "cmd"
      meta:
        # This command will be executed when the AI calls 'list_files'
        command: "ls -la"
    ```

## Usage

Once configured, the AI agent can invoke the app by its name:

```bash
tasak list_files
```

TASAK will execute the `ls -la` command and return the output.

## Configuration in Depth

TASAK uses a hierarchical configuration system. It loads and merges YAML files in the following order, with later files overriding previous ones:

1.  **Global Config:** `~/.tasak/tasak.yaml`
2.  **Local Config (Hierarchical):** Searches upwards from the current directory for `.tasak/tasak.yaml` or `tasak.yaml`.

This allows you to define global tools (like a calculator) and project-specific tools (like a build script) separately.

### Example: `cmd` and `mcp` Apps

Here is a more advanced `tasak.yaml` defining both a simple command and an MCP server for weather forecasts.

```yaml
header: "Project-specific apps for MyWebApp"

apps_config:
  enabled_apps:
    - run_server
    - weather_service

# App Type: cmd
# A simple command to run the local development server.
run_server:
  name: "Run Webapp Server"
  type: "cmd"
  meta:
    command: "npm run dev"

# App Type: mcp
# A persistent MCP server providing weather data.
# The AI can interact with this service more intelligently than a simple command.
weather_service:
  name: "Weather MCP Service"
  type: "mcp"
  meta:
    # TASAK will run this command to start the MCP server.
    # This assumes you have a weather_server.py file as defined in docs/MCP_Server_Build_Use.md
    command: "uv run /path/to/your/weather_server.py"
    env:
      # Securely provide API keys to your MCP server
      OPENWEATHER_API_KEY: "${OPENWEATHER_API_KEY}"
```

## For Developers

This project is built with Python and follows Test-Driven Development (TDD).

### Technical Requirements

*   Python 3.11+
*   Code must be clean, modular, and follow DRY principles.
*   All code, documentation, and comments must be in English.
*   Pre-commit hooks are used to enforce code quality (e.g., max 600 lines per file).
