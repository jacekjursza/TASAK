import argparse
import sys
from typing import Any, Dict

from .app_runner import run_cmd_app
from .config import load_and_merge_configs
from .mcp_client import run_mcp_app


def main():
    """Main entry point for the TASAK application."""
    parser = argparse.ArgumentParser(
        prog="tasak",
        description="TASAK: The Agent's Swiss Army Knife. A command-line proxy for AI agents.",
        epilog="Run 'tasak <app_name> --help' to see help for a specific application."
    )

    parser.add_argument(
        "app_name",
        nargs='?',
        help="The name of the application to run. If not provided, lists available apps."
    )

    args, unknown_args = parser.parse_known_args()
    config = load_and_merge_configs()

    if not args.app_name:
        _list_available_apps(config)
        return

    app_name = args.app_name
    apps_config = config.get('apps_config', {})
    enabled_apps = apps_config.get('enabled_apps', [])

    if app_name not in enabled_apps:
        print(f"Error: App '{app_name}' is not enabled or does not exist.", file=sys.stderr)
        _list_available_apps(config)
        sys.exit(1)

    app_config = config.get(app_name)
    if not app_config:
        print(f"Error: Configuration for app '{app_name}' not found.", file=sys.stderr)
        sys.exit(1)

    app_type = app_config.get('type')
    if app_type == 'cmd':
        run_cmd_app(app_config, unknown_args)
    elif app_type == 'mcp':
        run_mcp_app(app_name, app_config, unknown_args)
    else:
        print(f"Error: Unknown app type '{app_type}' for app '{app_name}'.", file=sys.stderr)
        sys.exit(1)

def _list_available_apps(config: Dict[str, Any]):
    """Lists all enabled applications from the configuration."""
    print("Available applications:")
    apps_config = config.get('apps_config', {})
    enabled_apps = apps_config.get('enabled_apps', [])
    
    if not enabled_apps:
        print("  (No applications enabled in configuration)")
        return

    for app_name in sorted(enabled_apps):
        app_info = config.get(app_name, {})
        app_type = app_info.get('type', 'N/A')
        app_description = app_info.get('name', 'No description')
        print(f"  - {app_name:<20} (type: {app_type:<5}) - {app_description}")


if __name__ == "__main__":
    main()
