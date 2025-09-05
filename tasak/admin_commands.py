"""Administrative commands for TASAK."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .auth import run_auth_app
from .mcp_real_client import MCPRealClient
from .schema_manager import SchemaManager


def setup_admin_subparsers(subparsers):
    """Set up admin subcommand parsers."""

    # Auth subcommand
    auth_parser = subparsers.add_parser(
        "auth", help="Manage authentication for an application"
    )
    auth_parser.add_argument("app", help="Application name")
    auth_parser.add_argument(
        "--check", action="store_true", help="Check authentication status"
    )
    auth_parser.add_argument(
        "--clear", action="store_true", help="Clear authentication data"
    )
    auth_parser.add_argument(
        "--refresh", action="store_true", help="Refresh authentication token"
    )

    # Refresh subcommand
    refresh_parser = subparsers.add_parser(
        "refresh", help="Refresh tool schemas from server"
    )
    refresh_parser.add_argument(
        "app", nargs="?", help="Application name (or --all for all apps)"
    )
    refresh_parser.add_argument(
        "--all", action="store_true", help="Refresh schemas for all MCP apps"
    )
    refresh_parser.add_argument(
        "--force", action="store_true", help="Force refresh even if cache is fresh"
    )

    # Clear subcommand
    clear_parser = subparsers.add_parser(
        "clear", help="Clear all data for an application"
    )
    clear_parser.add_argument("app", help="Application name")
    clear_parser.add_argument("--cache", action="store_true", help="Clear only cache")
    clear_parser.add_argument(
        "--auth", action="store_true", help="Clear only authentication"
    )
    clear_parser.add_argument("--schema", action="store_true", help="Clear only schema")
    clear_parser.add_argument(
        "--all", action="store_true", help="Clear all data (default)"
    )

    # Info subcommand
    info_parser = subparsers.add_parser(
        "info", help="Show information about an application"
    )
    info_parser.add_argument("app", help="Application name")

    # List subcommand
    list_parser = subparsers.add_parser(
        "list", help="List all configured applications with status"
    )
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )


def handle_admin_command(args: argparse.Namespace, config: Dict[str, Any]):
    """Handle admin subcommand execution."""
    if not hasattr(args, "admin_command") or not args.admin_command:
        print(
            "Error: No admin command specified. Use --help for usage.", file=sys.stderr
        )
        sys.exit(1)

    if args.admin_command == "auth":
        handle_auth(args, config)
    elif args.admin_command == "refresh":
        handle_refresh(args, config)
    elif args.admin_command == "clear":
        handle_clear(args, config)
    elif args.admin_command == "info":
        handle_info(args, config)
    elif args.admin_command == "list":
        handle_list(args, config)
    else:
        print(f"Unknown admin command: {args.admin_command}", file=sys.stderr)
        sys.exit(1)


def handle_auth(args: argparse.Namespace, config: Dict[str, Any]):
    """Handle authentication management."""
    app_name = args.app

    # Check if app exists in config
    app_config = config.get(app_name)
    if not app_config:
        print(
            f"Error: Application '{app_name}' not found in configuration.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.check:
        # Check authentication status
        auth_file = Path.home() / ".tasak" / "auth.json"
        if auth_file.exists():
            with open(auth_file, "r") as f:
                auth_data = json.load(f)
                if app_name in auth_data:
                    token_data = auth_data[app_name]
                    expires_at = token_data.get("expires_at", 0)
                    if expires_at > 0:
                        expiry_time = datetime.fromtimestamp(expires_at)
                        print(f"Authenticated for '{app_name}'")
                        print(f"Token expires at: {expiry_time}")
                    else:
                        print(f"Authenticated for '{app_name}' (no expiry information)")
                else:
                    print(f"Not authenticated for '{app_name}'")
        else:
            print(f"Not authenticated for '{app_name}'")

    elif args.clear:
        # Clear authentication data
        auth_file = Path.home() / ".tasak" / "auth.json"
        if auth_file.exists():
            with open(auth_file, "r") as f:
                auth_data = json.load(f)

            if app_name in auth_data:
                del auth_data[app_name]
                with open(auth_file, "w") as f:
                    json.dump(auth_data, f, indent=2)
                print(f"Authentication data cleared for '{app_name}'")
            else:
                print(f"No authentication data found for '{app_name}'")
        else:
            print(f"No authentication data found for '{app_name}'")

    elif args.refresh:
        # Refresh authentication token
        print(f"Refreshing authentication for '{app_name}'...")
        # This would call the refresh logic from auth.py
        print("Token refresh not yet implemented")

    else:
        # Perform authentication
        print(f"Authenticating with '{app_name}'...")
        # For MCP-remote apps, we need the server URL
        if app_config.get("type") == "mcp-remote":
            server_url = app_config.get("meta", {}).get("server_url")
            run_auth_app(app_name, server_url=server_url)
        else:
            # For regular MCP apps, no auth needed typically
            print(f"App '{app_name}' does not require authentication.", file=sys.stderr)


def handle_refresh(args: argparse.Namespace, config: Dict[str, Any]):
    """Handle schema refresh."""
    # Get list of enabled apps
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if args.all:
        # Refresh all MCP apps
        mcp_apps = [
            name for name in enabled_apps if config.get(name, {}).get("type") == "mcp"
        ]

        if not mcp_apps:
            print("No MCP applications found to refresh.")
            return

        for app_name in mcp_apps:
            refresh_app_schema(app_name, config[app_name], args.force)

    elif args.app:
        # Refresh specific app
        app_config = config.get(args.app)
        if not app_config:
            print(f"Error: Application '{args.app}' not found.", file=sys.stderr)
            sys.exit(1)
        if app_config.get("type") != "mcp":
            print(f"Warning: '{args.app}' is not an MCP application.", file=sys.stderr)
            return

        refresh_app_schema(args.app, app_config, args.force)

    else:
        print("Error: Specify an app name or use --all", file=sys.stderr)
        sys.exit(1)


def refresh_app_schema(app_name: str, app_config: Dict[str, Any], force: bool = False):
    """Refresh schema for a specific app."""
    print(f"Refreshing schema for '{app_name}'...")

    # Clear cache if forcing refresh
    if force:
        client = MCPRealClient(app_name, app_config)
        client.clear_cache()

    # Fetch fresh tool definitions
    client = MCPRealClient(app_name, app_config)
    tools = client.get_tool_definitions()

    if tools:
        # Use SchemaManager to save
        schema_manager = SchemaManager()
        schema_file = schema_manager.save_schema(app_name, tools)
        print(f"Schema refreshed for '{app_name}' ({len(tools)} tools)")
        print(f"Saved to: {schema_file}")
    else:
        print(f"Failed to refresh schema for '{app_name}'")


def handle_clear(args: argparse.Namespace, config: Dict[str, Any]):
    """Handle clearing of app data."""
    app_name = args.app

    app_config = config.get(app_name)
    if not app_config:
        print(f"Error: Application '{app_name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Determine what to clear
    clear_all = args.all or (not args.cache and not args.auth and not args.schema)

    if clear_all or args.cache:
        # Clear cache
        cache_file = Path.home() / ".tasak" / "cache" / f"{app_name}.json"
        if cache_file.exists():
            cache_file.unlink()
            print(f"Cache cleared for '{app_name}'")
        else:
            print(f"No cache found for '{app_name}'")

    if clear_all or args.auth:
        # Clear authentication
        auth_file = Path.home() / ".tasak" / "auth.json"
        if auth_file.exists():
            with open(auth_file, "r") as f:
                auth_data = json.load(f)

            if app_name in auth_data:
                del auth_data[app_name]
                with open(auth_file, "w") as f:
                    json.dump(auth_data, f, indent=2)
                print(f"Authentication cleared for '{app_name}'")
            else:
                print(f"No authentication data found for '{app_name}'")

    if clear_all or args.schema:
        # Clear schema
        schema_file = Path.home() / ".tasak" / "schemas" / f"{app_name}.json"
        if schema_file.exists():
            schema_file.unlink()
            print(f"Schema cleared for '{app_name}'")
        else:
            print(f"No schema found for '{app_name}'")


def handle_info(args: argparse.Namespace, config: Dict[str, Any]):
    """Show information about an application."""
    app_name = args.app

    app_config = config.get(app_name)
    if not app_config:
        print(f"Error: Application '{app_name}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"\nApplication: {app_name}")
    print(f"Type: {app_config.get('type', 'unknown')}")
    print(f"Name: {app_config.get('name', 'No description')}")

    # Check authentication status
    auth_file = Path.home() / ".tasak" / "auth.json"
    if auth_file.exists():
        with open(auth_file, "r") as f:
            auth_data = json.load(f)
            if app_name in auth_data:
                print("Authentication: Yes")
            else:
                print("Authentication: No")
    else:
        print("Authentication: No")

    # Check cache status
    cache_file = Path.home() / ".tasak" / "cache" / f"{app_name}.json"
    if cache_file.exists():
        age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        print(f"Cache: {age.days} days old")
    else:
        print("Cache: Not cached")

    # Check schema status using SchemaManager
    schema_manager = SchemaManager()
    schema_data = schema_manager.load_schema(app_name)
    if schema_data:
        last_updated = schema_data.get("last_updated", "Unknown")
        tool_count = len(schema_data.get("tools", {}))
        age_days = schema_manager.get_schema_age_days(app_name)
        if age_days is not None:
            print(f"Schema: {tool_count} tools ({age_days} days old)")
        else:
            print(f"Schema: {tool_count} tools (updated: {last_updated})")
    else:
        print("Schema: Not available")


def handle_list(args: argparse.Namespace, config: Dict[str, Any]):
    """List all configured applications."""
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if not enabled_apps:
        print("No applications configured.")
        return

    print("\nConfigured Applications:")
    print("-" * 60)

    for app_name in sorted(enabled_apps):
        app_config = config.get(app_name, {})
        app_type = app_config.get("type", "unknown")
        description = app_config.get("name", "No description")

        status_parts = []

        # Check authentication
        auth_file = Path.home() / ".tasak" / "auth.json"
        if auth_file.exists():
            with open(auth_file, "r") as f:
                auth_data = json.load(f)
                if app_name in auth_data:
                    status_parts.append("auth")

        # Check cache
        cache_file = Path.home() / ".tasak" / "cache" / f"{app_name}.json"
        if cache_file.exists():
            status_parts.append("cached")

        # Check schema
        schema_file = Path.home() / ".tasak" / "schemas" / f"{app_name}.json"
        if schema_file.exists():
            status_parts.append("schema")

        status = f"[{', '.join(status_parts)}]" if status_parts else "[no data]"

        print(f"  {app_name:<20} ({app_type:^12}) - {description:<30} {status}")

        if args.verbose:
            # Show more details
            if app_type == "mcp":
                config_file = app_config.get("config", "Not specified")
                print(f"    Config: {config_file}")
            elif app_type == "mcp-remote":
                server_url = app_config.get("meta", {}).get(
                    "server_url", "Not specified"
                )
                print(f"    Server: {server_url}")
            elif app_type == "cmd":
                command = app_config.get("meta", {}).get("command", "Not specified")
                mode = app_config.get("meta", {}).get("mode", "proxy")
                print(f"    Command: {command}")
                print(f"    Mode: {mode}")
