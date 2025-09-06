# Installation & Setup

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (for installation from repository)

## Installation Methods

### Option 1: Install via pipx (Recommended)

The cleanest way to install TASAK is using `pipx`, which creates an isolated environment:

```bash
# Install pipx if you don't have it
python -m pip install --user pipx
python -m pipx ensurepath

# Install TASAK
pipx install git+https://github.com/jacekjursza/TASAK.git
```

### Option 2: Install via pip

For direct installation into your Python environment:

```bash
pip install git+https://github.com/jacekjursza/TASAK.git
```

### Option 3: Development Installation

For contributors or local development:

```bash
# Clone the repository
git clone https://github.com/jacekjursza/TASAK.git
cd TASAK

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Verify Installation

After installation, verify TASAK is working:

```bash
# Check version and list available apps
tasak

# Should display something like:
# TASAK - The Agent's Swiss Army Knife
# Available apps: (none configured yet)
```

## Configuration System

TASAK uses a **hierarchical configuration system** that provides flexibility and organization for your tools.

### Configuration Hierarchy

Configurations are loaded and merged in the following order, with later configs overriding earlier ones:

1. **Global Configuration**: `~/.tasak/tasak.yaml`
   - Shared across all projects
   - Perfect for common tools you use everywhere
   - Examples: calculator, weather, system utilities

2. **Local Configuration**: Project-specific settings
   - TASAK searches upward from current directory to root
   - Looks for BOTH: `tasak.yaml` AND `.tasak/tasak.yaml` in each directory
   - Collects ALL configs found in the hierarchy
   - Merges them in order: root → current directory
   - Ideal for project-specific tools

### How Config Merging Works

```
Load Order (example from /projects/myapp):

1. ~/.tasak/tasak.yaml (Global)
2. /projects/tasak.yaml (if exists)
3. /projects/myapp/tasak.yaml (if exists)
4. /projects/myapp/.tasak/tasak.yaml (if exists)

Each later config overrides previous ones (last-wins strategy)
```

**Example scenario:**
- Global config defines `calculator` and `weather` apps
- Project root has `tasak.yaml` defining `build` and `test` apps
- Current dir has `.tasak/tasak.yaml` overriding `build` with different command
- Final result: `calculator`, `weather`, modified `build`, and `test` are all available

### Initial Setup

1. **Create global configuration directory:**
   ```bash
   mkdir -p ~/.tasak
   ```

2. **Create your first global configuration:**
   ```bash
   cat > ~/.tasak/tasak.yaml << 'EOF'
   header: "Global TASAK Tools"

   apps_config:
     enabled_apps:
       - hello

   hello:
     name: "Hello World"
     type: "cmd"
     meta:
       command: "echo 'Hello from TASAK!'"
   EOF
   ```

3. **Test your configuration:**
   ```bash
   tasak hello
   # Output: Hello from TASAK!
   ```

### Project-Specific Configuration

For any project, create a local `tasak.yaml`:

```bash
# In your project directory
cd /path/to/your/project

# Create local config
cat > tasak.yaml << 'EOF'
header: "Project Tools"

apps_config:
  enabled_apps:
    - build
    - test

build:
  name: "Build Project"
  type: "cmd"
  meta:
    command: "npm run build"

test:
  name: "Run Tests"
  type: "cmd"
  meta:
    command: "npm test"
EOF
```

Now both global and local apps are available:
```bash
tasak         # Lists: hello, build, test
tasak hello   # Runs global app
tasak build   # Runs local app
```

### Configuration Priority Rules

1. **App definitions**: Local overrides global if same name exists
2. **Enabled apps**: Lists are merged (both global and local apps available)
3. **Headers**: Local header is displayed if present
4. **Environment variables**: Can be used in configs with `${VAR_NAME}` syntax

### Best Practices

✅ **DO:**
- Keep sensitive data in environment variables
- Use global config for universal tools
- Use local config for project-specific commands
- Version control your local `tasak.yaml` files
- Document complex configurations with comments

❌ **DON'T:**
- Store API keys or passwords directly in configs
- Create overly complex nested configurations
- Use absolute paths in global configs (reduces portability)

## Environment Variables

TASAK supports environment variable expansion in configurations:

```yaml
weather:
  name: "Weather Service"
  type: "mcp"
  meta:
    command: "python weather_server.py"
    env:
      API_KEY: "${OPENWEATHER_API_KEY}"  # Reads from environment
```

Set environment variables before running TASAK:
```bash
export OPENWEATHER_API_KEY="your-key-here"
tasak weather
```

## Directory Structure

After setup, your TASAK configuration structure should look like:

```
~/
├── .tasak/
│   └── tasak.yaml          # Global configuration
│
└── projects/
    ├── project-a/
    │   └── tasak.yaml      # Project A specific tools
    │
    └── project-b/
        └── .tasak/
            └── tasak.yaml  # Project B specific tools (hidden)
```

## Troubleshooting

### Command not found
- Ensure TASAK is in your PATH
- Try: `python -m tasak` instead of `tasak`

### Configuration not loading
- Check file exists: `ls -la ~/.tasak/tasak.yaml`
- Validate YAML syntax: `python -m yaml tasak.yaml`
- Run with verbose mode: `tasak --debug`

### Apps not appearing
- Verify app is in `enabled_apps` list
- Check YAML indentation (must use spaces, not tabs)
- Ensure no syntax errors in configuration

## Next Steps

Now that TASAK is installed and configured, you're ready to:

→ Learn [Basic Usage](02_basic_usage.md) - Create your first apps
→ Explore [Advanced Usage](03_advanced_usage.md) - MCP servers and complex workflows
