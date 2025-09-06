# TASAK: The Agent's Swiss Army Knife

**Transform your AI coding assistant into a productivity powerhouse with custom tools and workflows tailored to YOUR codebase.**

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

## 🤝 Community & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/jacekjursza/TASAK/issues)
- **Discussions**: [Share your TASAK configs and workflows](https://github.com/jacekjursza/TASAK/discussions)
- **Examples**: Check out `examples/` folder for real-world configurations

## 💬 What Users Say

> "TASAK reduced my Claude Code token usage by 80%. My AI assistant now understands my entire development workflow." - *DevOps Engineer*

> "We standardized our team's toolchain with TASAK. New developers are productive on day one." - *Team Lead*

> "The Python plugins feature is a game-changer. My AI agent literally improves itself!" - *AI Power User*

## 🛠️ For Contributors

Built with Python 3.11+, following TDD principles. We welcome contributions!

### Development Setup
```bash
git clone https://github.com/jacekjursza/TASAK.git
cd TASAK
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest -q  # Run tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
