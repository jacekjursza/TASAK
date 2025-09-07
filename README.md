# TASAK: The Agent's Swiss Army Knife

**Transform your AI coding assistant into a productivity powerhouse with custom tools and workflows tailored to YOUR codebase.**

[![PyPI version](https://badge.fury.io/py/tasak.svg)](https://badge.fury.io/py/tasak)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release](https://img.shields.io/github/release/jacekjursza/tasak.svg)](https://github.com/jacekjursza/tasak/releases/latest)

📋 **[See what's new in v0.1.0 →](CHANGELOG.md)**

## 🚀 Why TASAK?

### For AI Agent Power Users (Claude Code, Cursor, Copilot)
**Problem:** Your AI assistant wastes tokens rediscovering your project structure, can't run your custom toolchain, and you're copy-pasting commands back and forth.

**Solution:** TASAK gives your AI agent a curated toolkit that understands YOUR workflow:
- 📦 **Package complex workflows** into simple commands ("deploy staging" instead of 10 manual steps)
- 🧠 **Reduce context usage** by 80% through hierarchical command discovery
- 🔧 **Self-improving:** Let your agent write Python plugins to extend its own capabilities!
- 🎯 **Project-aware:** Different tools for different projects, automatically

### For Development Teams
**Problem:** Every developer has their own way of running tests, deployments, and dev environments. Onboarding is painful.

**Solution:** TASAK standardizes your team's workflow into a unified command palette:
- 🏢 **Company-wide tooling** in global config, project-specific in local
- 📚 **Self-documenting:** Your AI agent can explain and execute any workflow
- 🔒 **Secure by default:** Only expose what you explicitly allow
- 🚄 **Zero friction:** Works with any language, any framework, any toolchain

## 💡 Real-World Magic

```yaml
# Your AI agent can now do THIS with a single command:
tasak deploy_review_app
# Instead of:
# 1. Check git branch
# 2. Build Docker image
# 3. Push to registry
# 4. Update k8s manifests
# 5. Apply to cluster
# 6. Wait for rollout
# 7. Run smoke tests
# 8. Post PR comment with URL
```

## 🎯 Perfect For

### ✨ Claude Code / Cursor / Copilot / Gemini CLI / Codex CLI / Users
- Build a custom toolkit that makes your AI assistant 10x more effective
- Stop wasting time on repetitive commands - let your agent handle them
- Create project-specific "skills" your AI can use intelligently

### 👥 Development Teams
- Standardize workflows across your entire team
- Make complex operations accessible to junior developers
- Document-by-doing: your commands ARE the documentation

### 🔧 DevOps & Platform Engineers
- Expose safe, curated access to production tools
- Build guardrails around dangerous operations
- Create approval workflows for sensitive commands

### 🎨 Open Source Maintainers
- Give contributors a standard way to run your project
- Reduce "works on my machine" issues
- Make your project AI-assistant friendly

## 🌟 Killer Features

### 🧩 **Python Plugins** (NEW!)
Your AI agent can write its own tools! Just ask:
> "Create a plugin that formats all Python files and runs tests"

The agent writes the Python function, TASAK automatically loads it. Mind = blown. 🤯

### 🎭 **Three Modes of Power**

**`cmd` apps** - Quick & dirty commands
```yaml
format_code:
  type: cmd
  meta:
    command: "ruff format . && ruff check --fix"
```

**`mcp` apps** - Stateful AI-native services
```yaml
database:
  type: mcp
  meta:
    command: "uvx mcp-server-sqlite --db ./app.db"
```

**`curated` apps** - Orchestrated workflows
```yaml
full_deploy:
  type: curated
  commands:
    - test
    - build
    - deploy
    - notify_slack
```

### 🔄 **Hierarchical Config**
Global tools + project tools = perfect setup
```
~/.tasak/tasak.yaml       # Your personal toolkit
./project/tasak.yaml      # Project-specific tools
= Your AI has exactly what it needs
```

## ⚡ Quick Start

### 1. Install (30 seconds)
```bash
pipx install git+https://github.com/jacekjursza/TASAK.git
```

### 2. Create Your First Power Tool (1 minute)
```bash
cat > ~/.tasak/tasak.yaml << 'EOF'
header: "My AI Assistant Toolkit"

apps_config:
  enabled_apps:
    - dev
    - test
    - deploy

# One command to rule them all
dev:
  name: "Start Development"
  type: "cmd"
  meta:
    command: "docker-compose up -d && npm run dev"

test:
  name: "Run Tests"
  type: "cmd"
  meta:
    command: "npm test && npm run e2e"

deploy:
  name: "Deploy to Staging"
  type: "cmd"
  meta:
    command: "./scripts/deploy.sh staging"
EOF
```

### 3. Watch Your AI Agent Level Up
```bash
# Your AI can now:
tasak dev      # Start entire dev environment
tasak test     # Run full test suite
tasak deploy   # Deploy to staging
# No more copy-pasting commands!
```

## 🎓 Real Use Cases

### Use Case 1: Supercharge Your Claude Code
```yaml
# .tasak/tasak.yaml in your project
header: "NextJS + Supabase Project"

apps_config:
  enabled_apps:
    - setup_branch
    - check_types
    - preview

setup_branch:
  name: "Setup new feature branch"
  type: "cmd"
  meta:
    command: |
      git checkout -b $1 &&
      npm install &&
      npm run db:migrate &&
      npm run dev

check_types:
  name: "Full type check"
  type: "cmd"
  meta:
    command: "tsc --noEmit && eslint . --fix"

preview:
  name: "Deploy preview"
  type: "cmd"
  meta:
    command: "vercel --prod=false"
```

Now your Claude Code can:
- Create and setup feature branches
- Run comprehensive type checks
- Deploy preview environments
...all without you typing a single command!

### Use Case 2: Team Workflow Standardization
```yaml
# Company-wide ~/.tasak/tasak.yaml
header: "ACME Corp Standard Tools"

apps_config:
  enabled_apps:
    - vpn
    - staging_logs
    - prod_deploy

vpn:
  name: "Connect to VPN"
  type: "cmd"
  meta:
    command: "openvpn --config ~/.acme/vpn.conf"

staging_logs:
  name: "Stream staging logs"
  type: "cmd"
  meta:
    command: "kubectl logs -f -n staging --selector=app"

prod_deploy:
  name: "Production deployment"
  type: "curated"
  commands:
    - name: "deploy"
      description: "Full production deployment with approvals"
      backend:
        type: composite
        steps:
          - type: cmd
            command: ["./scripts/request-approval.sh"]
          - type: cmd
            command: ["./scripts/deploy-prod.sh"]
```

### Use Case 3: Python Plugins - Let AI Extend Itself!
```python
# Your AI agent can write this!
# ~/.tasak/plugins/my_tools.py

def smart_refactor(file_pattern: str, old_name: str, new_name: str):
    """Refactor variable/function names across multiple files"""
    import subprocess
    result = subprocess.run(
        ["rg", "-l", old_name, file_pattern],
        capture_output=True,
        text=True
    )
    files = result.stdout.strip().split("\n")

    for file in files:
        subprocess.run([
            "sed", "-i", f"s/{old_name}/{new_name}/g", file
        ])

    return f"Refactored {len(files)} files"

# Now available as: tasak smart_refactor "*.py" "oldFunc" "newFunc"
```

## 📚 Documentation

**Quick Links:**
- [Why TASAK?](docs/about.md) - See more use cases and benefits
- [Installation & Setup](docs/setup.md) - Get running in 2 minutes
- [Basic Usage](docs/basic_usage.md) - Your first `cmd` apps
- [Advanced Usage](docs/advanced_usage.md) - MCP servers, Python plugins, and workflows
- [Changelog](CHANGELOG.md) - See all releases and changes

## 🤖 CLI Semantics for Agents

For MCP and MCP‑Remote apps, TASAK presents a predictable, agent‑friendly CLI:

- `tasak <app>` → prints only tool names (one per line). No headers or descriptions.
- `tasak <app> <tool>` →
  - If the tool has no required parameters: executes immediately with empty args.
  - If the tool has required parameters: shows focused help for that tool (same as `--help`), including description and parameters with required/type info.
- `tasak <app> <tool> --help` → always shows focused help for that single tool.
- `tasak <app> --help` → prints grouped simplified help:
  - "<app> commands:" — tools without required params (can run immediately) as `<name> - <description>`
  - "<app> sub-apps (use --help to read more):" — tools with required params as `<name> - <description>`

Behavior notes:
- Tool schema listing/help uses a transparent 1‑day cache; when stale or missing, TASAK refreshes quietly and updates the cache.
- Noisy transport logs are suppressed by default; enable with `TASAK_DEBUG=1` or `TASAK_VERBOSE=1` if you need to debug.

## Daemon (Connection Pooling)

TASAK can run a local daemon to pool MCP connections and cache schemas, dramatically reducing per-command startup time. The daemon runs on `127.0.0.1:8765` and the CLI auto-starts it on demand (unless explicitly stopped or disabled).

- Start: `tasak daemon start`
- Stop: `tasak daemon stop` (also disables autostart until next manual start)
- Restart: `tasak daemon restart`
- Status: `tasak daemon status`
- Logs: `tasak daemon logs -f`

### Logging levels

By default the daemon is quiet (warning and errors only). Enable verbose logs when debugging:

- CLI flags:
  - `tasak daemon start -v` or `tasak daemon restart -v` (equivalent to debug)
  - `tasak daemon start --log-level info` (or `debug`, `warning`, `error`)
- Environment variable:
  - `TASAK_DAEMON_LOG_LEVEL=INFO` (or `DEBUG`) before starting the daemon

CLI-side daemon hints ("Using daemon…", "Daemon: …") appear only when `--debug` or `TASAK_VERBOSE=1` is set.

### HTTP endpoints

The daemon exposes a small local API for health checks and diagnostics:

- `GET /health` – basic liveness + uptime
- `GET /connections` – active connections with age/idle and counters
- `GET /apps/{app}/ping?deep=true` – shallow or deep ping (deep performs a quick tool list)
- `GET /metrics` – basic counters (connection creations/reuses, per-app list/call/error counts)

### Autostart behavior

The CLI auto-starts the daemon unless one of the following is true:
- `tasak daemon stop` was called (creates `~/.tasak/daemon.disabled`)
- `TASAK_NO_DAEMON=1` is set in the environment
- `--debug` is used (bypasses daemon for direct connections)

### Tuning

You can tune TTLs via environment variables before starting the daemon:

- `TASAK_DAEMON_CONN_TTL` – connection idle TTL in seconds (default: `300`)
- `TASAK_DAEMON_CACHE_TTL` – tools cache TTL in seconds (default: `900`)

## 🤝 Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/jacekjursza/TASAK/issues)
- **Discussions**: [Share your TASAK configs and workflows](https://github.com/jacekjursza/TASAK/discussions)
- **Examples**: Check out `examples/` folder for real-world configurations

## 🛠️ For Contributors

Built with Python 3.11+, following TDD principles. We welcome contributions!

### Development Setup
```bash
git clone https://github.com/jacekjursza/TASAK.git
cd TASAK
python -m venv .venv
source .venv/bin/activate

# Install in editable mode (includes MCP by default)
pip install -e .

# Run tests
pytest -q

# Optional: if you install pytest-timeout, you can enable
# suite timeouts using the provided CI config
pytest -c pytest-ci.ini -q
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
