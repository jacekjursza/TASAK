"""Initialize TASAK configuration with templates."""

import sys
from pathlib import Path
import yaml


TEMPLATES = {
    "basic": {
        "description": "Basic configuration for general use",
        "config": {
            "header": "TASAK Configuration",
            "apps_config": {"enabled_apps": ["hello", "list_files", "git_status"]},
            "hello": {
                "name": "Hello World",
                "type": "cmd",
                "meta": {"command": "echo 'Hello from TASAK!'"},
            },
            "list_files": {
                "name": "List Files",
                "type": "cmd",
                "meta": {"command": "ls -la"},
            },
            "git_status": {
                "name": "Git Status",
                "type": "cmd",
                "meta": {"command": "git status -sb"},
            },
        },
    },
    "ai-agent": {
        "description": "Optimized for AI agents (Claude Code, Cursor, Copilot)",
        "config": {
            "header": "AI Agent Toolkit",
            "apps_config": {
                "enabled_apps": ["dev", "test", "build", "format", "check_types"]
            },
            "dev": {
                "name": "Start Development",
                "type": "cmd",
                "meta": {
                    "command": "npm run dev || python manage.py runserver || cargo run"
                },
            },
            "test": {
                "name": "Run Tests",
                "type": "cmd",
                "meta": {"command": "npm test || pytest || cargo test"},
            },
            "build": {
                "name": "Build Project",
                "type": "cmd",
                "meta": {
                    "command": "npm run build || python setup.py build || cargo build --release"
                },
            },
            "format": {
                "name": "Format Code",
                "type": "cmd",
                "meta": {"command": "prettier --write . || black . || cargo fmt"},
            },
            "check_types": {
                "name": "Type Check",
                "type": "cmd",
                "meta": {"command": "tsc --noEmit || mypy . || cargo check"},
            },
            "plugins": {"python": {"auto_enable_all": True, "search_paths": []}},
        },
    },
    "team": {
        "description": "Team configuration with standardized workflows",
        "config": {
            "header": "Team Development Tools",
            "apps_config": {
                "enabled_apps": ["setup", "dev", "test", "lint", "deploy", "docs"]
            },
            "setup": {
                "name": "Setup Environment",
                "type": "cmd",
                "meta": {"command": "npm install && npm run prepare"},
            },
            "dev": {
                "name": "Development Mode",
                "type": "cmd",
                "meta": {"command": "docker-compose up -d && npm run dev"},
            },
            "test": {
                "name": "Test Suite",
                "type": "curated",
                "commands": [
                    {
                        "name": "test",
                        "description": "Run all tests with coverage",
                        "backend": {
                            "type": "composite",
                            "steps": [
                                {"type": "cmd", "command": ["npm", "run", "test:unit"]},
                                {
                                    "type": "cmd",
                                    "command": ["npm", "run", "test:integration"],
                                },
                                {"type": "cmd", "command": ["npm", "run", "test:e2e"]},
                            ],
                        },
                    }
                ],
            },
            "lint": {
                "name": "Lint & Format",
                "type": "cmd",
                "meta": {"command": "npm run lint:fix && npm run format"},
            },
            "deploy": {
                "name": "Deploy",
                "type": "cmd",
                "meta": {"command": "./scripts/deploy.sh staging"},
            },
            "docs": {
                "name": "Generate Docs",
                "type": "cmd",
                "meta": {"command": "npm run docs:build"},
            },
        },
    },
    "devops": {
        "description": "DevOps configuration with infrastructure tools",
        "config": {
            "header": "DevOps Toolkit",
            "apps_config": {
                "enabled_apps": [
                    "status",
                    "logs",
                    "deploy",
                    "rollback",
                    "scale",
                    "backup",
                ]
            },
            "status": {
                "name": "System Status",
                "type": "cmd",
                "meta": {"command": "kubectl get pods -A || docker ps"},
            },
            "logs": {
                "name": "View Logs",
                "type": "cmd",
                "meta": {
                    "command": "kubectl logs -f deployment/app || docker-compose logs -f"
                },
            },
            "deploy": {
                "name": "Deploy Application",
                "type": "curated",
                "commands": [
                    {
                        "name": "deploy",
                        "description": "Deploy with safety checks",
                        "backend": {
                            "type": "composite",
                            "steps": [
                                {
                                    "type": "cmd",
                                    "command": ["./scripts/pre-deploy-check.sh"],
                                },
                                {
                                    "type": "cmd",
                                    "command": ["kubectl", "apply", "-f", "k8s/"],
                                },
                                {
                                    "type": "cmd",
                                    "command": ["./scripts/post-deploy-verify.sh"],
                                },
                            ],
                        },
                    }
                ],
            },
            "rollback": {
                "name": "Rollback Deployment",
                "type": "cmd",
                "meta": {"command": "kubectl rollout undo deployment/app"},
            },
            "scale": {
                "name": "Scale Application",
                "type": "cmd",
                "meta": {"command": "kubectl scale deployment/app --replicas=3"},
            },
            "backup": {
                "name": "Backup Database",
                "type": "cmd",
                "meta": {"command": "./scripts/backup-db.sh"},
            },
        },
    },
}


def init_config(template_name: str = "basic", location: str = "local") -> None:
    """Initialize TASAK configuration from template."""

    # Validate template
    if template_name not in TEMPLATES:
        print(f"❌ Unknown template: {template_name}")
        print(f"Available templates: {', '.join(TEMPLATES.keys())}")
        sys.exit(1)

    template = TEMPLATES[template_name]

    # Determine target path
    if location == "global":
        config_dir = Path.home() / ".tasak"
        config_path = config_dir / "tasak.yaml"
    else:  # local
        config_dir = Path.cwd()
        config_path = config_dir / "tasak.yaml"

    # Check if config already exists
    if config_path.exists():
        response = input(
            f"⚠️  Config already exists at {config_path}. Overwrite? [y/N]: "
        )
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Create directory if needed
    if location == "global":
        config_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    try:
        with open(config_path, "w") as f:
            yaml.safe_dump(
                template["config"],
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        print(f"✅ Created {template_name} configuration at: {config_path}")
        print(f"📝 Template: {template['description']}")

        # Show next steps
        print("\n🚀 Next steps:")
        print("1. Review the configuration: cat " + str(config_path))
        print("2. List available apps: tasak")
        print("3. Run your first app: tasak hello")

        # Additional tips for specific templates
        if template_name == "ai-agent":
            print("\n💡 AI Agent tip: Add this to your AI's system prompt:")
            print(
                "   'You have access to TASAK for running commands. Use `tasak` to see available tools.'"
            )
        elif template_name == "team":
            print(
                "\n💡 Team tip: Commit tasak.yaml to your repository for consistent tooling across the team."
            )
        elif template_name == "devops":
            print(
                "\n💡 DevOps tip: Customize the commands to match your infrastructure setup."
            )

    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        sys.exit(1)


def list_templates() -> None:
    """List available templates with descriptions."""
    print("📋 Available TASAK Templates\n")
    for name, template in TEMPLATES.items():
        print(f"  {name:12} - {template['description']}")
    print("\nUsage: tasak --init <template> [--global]")


def handle_init_command(args) -> None:
    """Handle the --init command from main."""

    # If no template specified, list them
    if not args.init or args.init == "list":
        list_templates()
        return

    # Determine location
    location = "global" if getattr(args, "global", False) else "local"

    # Initialize with template
    init_config(args.init, location)
