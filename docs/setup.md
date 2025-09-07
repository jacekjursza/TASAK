# Get TASAK Running in 2 Minutes
## Contents

- [🚀 Quick Start (30 seconds)](#-quick-start-30-seconds)
- [🎯 Your First Power Tool (1 minute)](#-your-first-power-tool-1-minute)
- [📦 Installation Options](#-installation-options)
- [🏛️ Configuration Magic](#-configuration-magic)
- [🔧 Troubleshooting](#-troubleshooting)
- [🚀 What's Next?](#-whats-next)

## 🚀 Quick Start (30 seconds)

### Prerequisites
- Python 3.11+ (check with `python --version`)
- That's it! 🎉

### One-Line Install

```bash
pipx install tasak
```

No pipx? No problem:
```bash
python -m pip install --user pipx && python -m pipx ensurepath
# Then run: pipx install tasak
```

### Verify It Works

```bash
tasak
# You'll see: "TASAK - The Agent's Swiss Army Knife"
```

## 🎯 Your First Power Tool (1 minute)

Let's create your first AI-accessible command in 3 steps:

### Step 1: Create Config Directory
```bash
mkdir -p ~/.tasak
```

### Step 2: Add Your First Tool
```bash
cat > ~/.tasak/tasak.yaml << 'EOF'
header: "My AI Toolkit"

apps_config:
  enabled_apps:
    - hello
    - dev
    - test

# Simple greeting
hello:
  name: "Hello World"
  type: "cmd"
  meta:
    command: "echo 'Hello from TASAK! Your AI assistant can now run commands!'"

# Start your dev environment
dev:
  name: "Start Development"
  type: "cmd"
  meta:
    command: "echo 'Starting dev server...' && npm run dev"

# Run tests
test:
  name: "Run Tests"
  type: "cmd"
  meta:
    command: "npm test"
EOF
```

### Step 3: Test It!
```bash
tasak hello
# Output: Hello from TASAK! Your AI assistant can now run commands!

tasak
# Now shows your available commands!
```

🎆 **Congratulations!** Your AI assistant can now use these commands!

## 📦 Installation Options

### Best Option: pipx (Isolated & Clean)
```bash
pipx install tasak
```

### Alternative: Direct pip
```bash
pip install -U tasak
```

### For Contributors: Development Mode
```bash
git clone https://github.com/jacekjursza/TASAK.git
cd TASAK
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 🏛️ Configuration Magic

### The Power of Hierarchical Config

TASAK's secret sauce is its **smart configuration system**:

```
~/.tasak/tasak.yaml          ← Your personal toolkit (global)
    +
./project/tasak.yaml         ← Project-specific tools (local)
    =
Your AI's Complete Toolkit   ← Best of both worlds!
```

### How It Works

1. **Global Config** (`~/.tasak/tasak.yaml`)
   - Your personal command palette
   - Tools you use everywhere
   - Examples: format code, check weather, system info

2. **Project Config** (in any parent directory)
   - Project-specific commands
   - Overrides global settings
   - Can be `tasak.yaml` or `.tasak/tasak.yaml`
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

→ Learn [Basic Usage](basic_usage.md) - Create your first apps
→ Explore [Advanced Usage](advanced_usage.md) - MCP servers and complex workflows
