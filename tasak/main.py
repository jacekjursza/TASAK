import argparse
import sys
from typing import Any, Dict

from .admin_commands import setup_admin_subparsers, handle_admin_command
from .app_runner import run_cmd_app
from .config import load_and_merge_configs
from .mcp_client import run_mcp_app
from .mcp_remote_runner import run_mcp_remote_app


def main():
    """Main entry point for the TASAK application."""
    config = load_and_merge_configs()

    # Check if first argument is 'admin'
    if len(sys.argv) > 1 and sys.argv[1] == "admin":
        # Handle admin commands with a dedicated parser
        parser = argparse.ArgumentParser(
            prog="tasak admin", description="Administrative commands for TASAK"
        )
        subparsers = parser.add_subparsers(
            dest="admin_command", help="Admin command to execute"
        )

        # Set up admin subcommands
        setup_admin_subparsers(subparsers)

        # Parse admin args (skip 'tasak' and 'admin')
        args = parser.parse_args(sys.argv[2:])
        handle_admin_command(args, config)
        return

    # Regular app handling (backward compatible)
    parser = argparse.ArgumentParser(
        prog="tasak",
        description="TASAK: The Agent's Swiss Army Knife. A command-line proxy for AI agents.",
        epilog="Run 'tasak <app_name> --help' to see help for a specific application.",
        add_help=False,  # Disable default help to allow sub-app help handling
    )

    parser.add_argument(
        "app_name",
        nargs="?",
        help="The name of the application to run. If not provided, lists available apps.",
    )
    # Add a custom help argument
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit."
    )

    args, unknown_args = parser.parse_known_args()

    # Manual help handling
    if args.help and not args.app_name:
        parser.print_help()
        return

    if not args.app_name:
        _list_available_apps(config)
        return

    # If help is requested for a specific app, pass it on
    if args.help:
        unknown_args.append("--help")

    app_name = args.app_name
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if app_name not in enabled_apps:
        print(
            f"Error: App '{app_name}' is not enabled or does not exist.",
            file=sys.stderr,
        )
        _list_available_apps(config)
        sys.exit(1)

    app_config = config.get(app_name)
    if not app_config:
        print(f"Error: Configuration for app '{app_name}' not found.", file=sys.stderr)
        sys.exit(1)

    app_type = app_config.get("type")
    if app_type == "cmd":
        run_cmd_app(app_config, unknown_args)
    elif app_type == "mcp":
        run_mcp_app(app_name, app_config, unknown_args)
    elif app_type == "mcp-remote":
        run_mcp_remote_app(app_name, app_config, unknown_args)
    else:
        print(
            f"Error: Unknown app type '{app_type}' for app '{app_name}'.",
            file=sys.stderr,
        )
        sys.exit(1)


def _list_available_apps(config: Dict[str, Any]):
    """Lists all enabled applications from the configuration."""
    print("Available applications:")
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if not enabled_apps:
        print("  (No applications enabled in configuration)")
        return

    for app_name in sorted(enabled_apps):
        app_info = config.get(app_name, {})
        app_type = app_info.get("type", "N/A")
        app_description = app_info.get("name", "No description")
        print(f"  - {app_name:<20} (type: {app_type:<10}) - {app_description}")


if __name__ == "__main__":
    main()
