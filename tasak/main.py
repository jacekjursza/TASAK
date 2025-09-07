import argparse
import atexit
import sys
from typing import Any, Dict

from tasak.admin_commands import setup_admin_subparsers, handle_admin_command
from tasak.app_runner import run_cmd_app
from tasak.config import load_and_merge_configs
from tasak.python_plugins import integrate_plugins_into_config, run_python_plugin
from tasak.curated_app import run_curated_app
from tasak.mcp_client import run_mcp_app
from tasak.mcp_remote_runner import run_mcp_remote_app
from tasak.init_command import handle_init_command


def _cleanup_pool():
    """Best-effort cleanup of MCPRemotePool without creating it at exit.

    Avoids instantiating the pool during interpreter shutdown and avoids
    blocking the process with a long await. Mirrors the pool's internal
    atexit logic with bounded waits.
    """
    try:
        from tasak.mcp_remote_pool import MCPRemotePool
        import logging
        import concurrent.futures as _f

        # Suppress noisy asyncio generator-close logs during shutdown
        try:
            logging.getLogger("asyncio").setLevel(logging.CRITICAL)
        except Exception:
            pass

        inst = getattr(MCPRemotePool, "_instance", None)
        if not inst or getattr(inst, "_shutdown", False):
            return

        # Submit shutdown to the pool's own loop and wait briefly.
        try:
            fut: _f.Future = inst._submit(inst.shutdown())  # type: ignore[attr-defined]
            fut.result(timeout=2.0)
        except Exception:
            # As a fallback, try to stop the loop and join the thread briefly.
            try:
                inst._loop.call_soon_threadsafe(inst._loop.stop)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                inst._thread.join(timeout=0.5)  # type: ignore[attr-defined]
            except Exception:
                pass
    except Exception:
        # Never raise during interpreter shutdown
        pass


def main():
    """Main entry point for the TASAK application."""
    # Register cleanup on exit
    atexit.register(_cleanup_pool)

    # Handle special commands that don't need config
    if len(sys.argv) > 1:
        # Handle --init command
        if sys.argv[1] == "--init" or sys.argv[1] == "-i":
            parser = argparse.ArgumentParser(prog="tasak")
            parser.add_argument(
                "--init",
                "-i",
                nargs="?",
                const="list",
                help="Initialize TASAK configuration from template",
            )
            parser.add_argument(
                "--global",
                "-g",
                action="store_true",
                help="Create global configuration instead of local",
            )
            args = parser.parse_args()
            handle_init_command(args)
            return

        # Handle --version
        if sys.argv[1] == "--version" or sys.argv[1] == "-v":
            from importlib.metadata import version

            try:
                print(f"TASAK version {version('tasak')}")
            except Exception:
                print("TASAK version: development")
            return

    config = load_and_merge_configs()

    # Check if first argument is 'daemon'
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        # Handle daemon commands
        from .daemon.manager import handle_daemon_command

        parser = argparse.ArgumentParser(
            prog="tasak daemon", description="Manage TASAK background daemon"
        )
        subparsers = parser.add_subparsers(
            dest="daemon_command", help="Daemon command to execute"
        )

        # Add daemon subcommands
        start_parser = subparsers.add_parser("start", help="Start the daemon")
        start_parser.add_argument(
            "-v", "--verbose", action="store_true", help="Verbose logging (debug)"
        )
        start_parser.add_argument(
            "--log-level",
            choices=["debug", "info", "warning", "error"],
            help="Set daemon log level",
        )

        subparsers.add_parser("stop", help="Stop the daemon")

        restart_parser = subparsers.add_parser("restart", help="Restart the daemon")
        restart_parser.add_argument(
            "-v", "--verbose", action="store_true", help="Verbose logging (debug)"
        )
        restart_parser.add_argument(
            "--log-level",
            choices=["debug", "info", "warning", "error"],
            help="Set daemon log level",
        )
        subparsers.add_parser("status", help="Show daemon status")

        logs_parser = subparsers.add_parser("logs", help="Show daemon logs")
        logs_parser.add_argument(
            "-n", "--lines", type=int, default=50, help="Number of lines to show"
        )
        logs_parser.add_argument(
            "-f", "--follow", action="store_true", help="Follow log output"
        )

        # Parse and handle (skip 'daemon' from argv)
        args = parser.parse_args(sys.argv[2:])
        handle_daemon_command(args)
        return

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
    # Add --list-apps for scripting/completions
    parser.add_argument(
        "--list-apps", "-l", action="store_true", help="List available applications"
    )
    # Add --debug flag for testing
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: bypass daemon, show detailed logs and timing",
    )

    args, unknown_args = parser.parse_known_args()

    # Set debug mode globally
    if args.debug:
        import os

        os.environ["TASAK_DEBUG"] = "1"
        print("🔍 Debug mode enabled", file=sys.stderr)

    # Manual help handling
    if args.help and not args.app_name:
        parser.print_help()
        print("\n💡 Quick start: Run 'tasak --init' to create a configuration")
        return

    # Augment with discovered python plugins (ladder-based) for regular app flow
    config = integrate_plugins_into_config(config)

    # Handle --list-apps
    if args.list_apps or (not args.app_name):
        _list_available_apps(config, simple=args.list_apps)
        return

    # If help is requested for a specific app, pass it on
    if args.help:
        unknown_args.append("--help")

    app_name = args.app_name
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if app_name not in enabled_apps:
        print(
            f"❌ Error: App '{app_name}' is not enabled or does not exist.",
            file=sys.stderr,
        )
        print("\n💡 Hint: Did you mean one of these?", file=sys.stderr)
        # Find similar app names
        from difflib import get_close_matches

        similar = get_close_matches(app_name, enabled_apps, n=3, cutoff=0.6)
        if similar:
            for name in similar:
                print(f"  - {name}", file=sys.stderr)
        else:
            print("  Run 'tasak' to see all available apps", file=sys.stderr)
        sys.exit(1)

    app_config = config.get(app_name)
    if not app_config:
        print(f"Error: Configuration for app '{app_name}' not found.", file=sys.stderr)
        sys.exit(1)
        return  # Ensure function stops here even if sys.exit is mocked

    app_type = app_config.get("type")
    if app_type == "cmd":
        run_cmd_app(app_config, unknown_args)
    elif app_type == "curated":
        run_curated_app(app_name, app_config, unknown_args)
    elif app_type == "mcp":
        run_mcp_app(app_name, app_config, unknown_args)
    elif app_type == "mcp-remote":
        run_mcp_remote_app(app_name, app_config, unknown_args)
    elif app_type == "python-plugin":
        run_python_plugin(app_name, app_config, unknown_args)
    else:
        print(
            f"Error: Unknown app type '{app_type}' for app '{app_name}'.",
            file=sys.stderr,
        )
        sys.exit(1)


def _list_available_apps(config: Dict[str, Any], simple: bool = False):
    """Lists all enabled applications from the configuration."""
    apps_config = config.get("apps_config", {})
    enabled_apps = apps_config.get("enabled_apps", [])

    if simple:
        # Simple mode for shell completions
        for app_name in sorted(enabled_apps):
            print(f"  {app_name}")
        return

    # Full display mode
    print("🚀 TASAK - The Agent's Swiss Army Knife")
    print("=" * 50)

    if not enabled_apps:
        print("\n📭 No applications configured yet!")
        print("\n💡 Get started:")
        print("  1. Run 'tasak --init' to create a configuration")
        print("  2. Or create ~/.tasak/tasak.yaml manually")
        print("\nExample configuration:")
        print("  apps_config:")
        print("    enabled_apps: [hello]")
        print("  hello:")
        print("    type: cmd")
        print("    meta:")
        print("      command: 'echo Hello World'")
        return

    print("\n📦 Available applications:")
    for app_name in sorted(enabled_apps):
        app_info = config.get(app_name, {})
        app_type = app_info.get("type", "N/A")
        app_description = app_info.get("name", "No description")
        type_icon = {
            "cmd": "⚡",
            "mcp": "🔌",
            "mcp-remote": "☁️",
            "curated": "🎯",
            "python-plugin": "🐍",
        }.get(app_type, "📋")
        print(f"  {type_icon} {app_name:<20} ({app_type}) - {app_description}")

    print("\n💡 Usage: tasak <app_name> [arguments]")
    print("   Help:  tasak <app_name> --help")


if __name__ == "__main__":
    main()
