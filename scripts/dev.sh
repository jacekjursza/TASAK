#!/bin/bash
# Development helper script for TASAK

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${2}${1}${NC}"
}

# Function to show help
show_help() {
    cat << EOF
TASAK Development Helper

Usage: ./scripts/dev.sh [COMMAND]

Commands:
    setup       Set up development environment
    test        Run tests (optionally with coverage)
    lint        Run linters and formatters
    watch       Watch for changes and run tests
    clean       Clean up build artifacts and caches
    install     Install in editable mode
    shell       Start IPython with TASAK imported
    example     Create example configurations
    help        Show this help message

Examples:
    ./scripts/dev.sh setup      # First-time setup
    ./scripts/dev.sh test       # Run all tests
    ./scripts/dev.sh lint       # Check code quality
    ./scripts/dev.sh watch      # Dev mode with auto-testing
EOF
}

# Setup development environment
setup_env() {
    print_color "🔧 Setting up TASAK development environment..." "$BLUE"

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        print_color "Creating virtual environment..." "$YELLOW"
        python3 -m venv .venv
    fi

    # Activate virtual environment
    source .venv/bin/activate

    # Upgrade pip
    print_color "Upgrading pip..." "$YELLOW"
    pip install --upgrade pip

    # Install development dependencies
    print_color "Installing dependencies..." "$YELLOW"
    pip install -e ".[mcp]"
    pip install pytest pytest-cov pytest-watch pre-commit ruff ipython

    # Install pre-commit hooks
    print_color "Installing pre-commit hooks..." "$YELLOW"
    pre-commit install

    # Create default config directories
    print_color "Creating config directories..." "$YELLOW"
    mkdir -p ~/.tasak/plugins/python
    mkdir -p .tasak/plugins/python

    print_color "✅ Development environment ready!" "$GREEN"
    print_color "Activate with: source .venv/bin/activate" "$BLUE"
}

# Run tests
run_tests() {
    print_color "🧪 Running tests..." "$BLUE"

    if [ "$1" == "coverage" ]; then
        pytest --cov=tasak --cov-report=term-missing --cov-report=html
        print_color "Coverage report generated in htmlcov/" "$GREEN"
    else
        pytest -v
    fi
}

# Run linters
run_lint() {
    print_color "🔍 Running code quality checks..." "$BLUE"

    # Run ruff
    print_color "Running ruff..." "$YELLOW"
    ruff check . --fix
    ruff format .

    # Run pre-commit
    print_color "Running pre-commit hooks..." "$YELLOW"
    pre-commit run --all-files

    print_color "✅ Code quality checks passed!" "$GREEN"
}

# Watch for changes
watch_mode() {
    print_color "👁️  Starting watch mode..." "$BLUE"
    print_color "Tests will run automatically on file changes" "$YELLOW"
    pytest-watch -- -v
}

# Clean artifacts
clean_artifacts() {
    print_color "🧹 Cleaning build artifacts..." "$BLUE"

    # Remove Python artifacts
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*.pyd" -delete
    find . -type f -name ".coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

    # Remove build artifacts
    rm -rf build/ dist/ .pytest_cache/ .ruff_cache/

    print_color "✅ Cleaned!" "$GREEN"
}

# Install in editable mode
install_editable() {
    print_color "📦 Installing TASAK in editable mode..." "$BLUE"
    pip install -e ".[mcp]"
    print_color "✅ TASAK installed!" "$GREEN"
}

# Start interactive shell
start_shell() {
    print_color "🐍 Starting IPython with TASAK loaded..." "$BLUE"
    ipython -i -c "
import tasak
from tasak.config import load_and_merge_configs
from tasak.python_plugins import discover_python_plugins

print('TASAK modules loaded!')
print('Available: tasak, load_and_merge_configs, discover_python_plugins')
print()
config = load_and_merge_configs()
print(f'Config loaded with {len(config)} keys')
"
}

# Create example configurations
create_examples() {
    print_color "📝 Creating example configurations..." "$BLUE"

    # Create example global config
    cat > ~/.tasak/tasak.yaml.example << 'EOF'
header: "My Global TASAK Tools"

apps_config:
  enabled_apps:
    - git_status
    - format_code
    - run_tests

# Simple git status command
git_status:
  name: "Git Status"
  type: "cmd"
  meta:
    command: "git status -sb"

# Format code with ruff
format_code:
  name: "Format Python Code"
  type: "cmd"
  meta:
    command: "ruff format . && ruff check --fix"

# Run project tests
run_tests:
  name: "Run Tests"
  type: "cmd"
  meta:
    command: "pytest -v"

# Enable Python plugins
plugins:
  python:
    auto_enable_all: true
    search_paths: []
EOF

    # Create example project config
    cat > tasak.yaml.example << 'EOF'
header: "Project-Specific Tools"

apps_config:
  enabled_apps:
    - dev
    - build
    - deploy

# Start development server
dev:
  name: "Start Dev Server"
  type: "cmd"
  meta:
    command: "npm run dev"

# Build project
build:
  name: "Build Project"
  type: "cmd"
  meta:
    command: "npm run build"

# Deploy to staging
deploy:
  name: "Deploy Staging"
  type: "curated"
  commands:
    - name: "deploy"
      description: "Deploy to staging environment"
      backend:
        type: cmd
        command: ["./scripts/deploy.sh", "staging"]
EOF

    # Create example Python plugin
    mkdir -p ~/.tasak/plugins/python
    cat > ~/.tasak/plugins/python/example_plugin.py << 'EOF'
#!/usr/bin/env python3
"""Example TASAK Python plugin"""

DESCRIPTION = "Example plugin showing argument parsing"

import argparse
import sys

def main():
    parser = argparse.ArgumentParser(
        prog="example_plugin",
        description=DESCRIPTION
    )
    parser.add_argument(
        "action",
        choices=["hello", "info", "test"],
        help="Action to perform"
    )
    parser.add_argument(
        "--name",
        default="World",
        help="Name to greet"
    )

    args = parser.parse_args()

    if args.action == "hello":
        print(f"Hello, {args.name}!")
    elif args.action == "info":
        print("This is an example TASAK Python plugin")
        print(f"Running from: {__file__}")
    elif args.action == "test":
        print("✅ Plugin is working correctly!")
        sys.exit(0)

if __name__ == "__main__":
    main()
EOF

    chmod +x ~/.tasak/plugins/python/example_plugin.py

    print_color "✅ Example files created:" "$GREEN"
    print_color "  - ~/.tasak/tasak.yaml.example" "$YELLOW"
    print_color "  - ./tasak.yaml.example" "$YELLOW"
    print_color "  - ~/.tasak/plugins/python/example_plugin.py" "$YELLOW"
}

# Main script logic
case "${1:-help}" in
    setup)
        setup_env
        ;;
    test)
        run_tests "${2:-}"
        ;;
    lint)
        run_lint
        ;;
    watch)
        watch_mode
        ;;
    clean)
        clean_artifacts
        ;;
    install)
        install_editable
        ;;
    shell)
        start_shell
        ;;
    example)
        create_examples
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_color "Unknown command: $1" "$RED"
        show_help
        exit 1
        ;;
esac
