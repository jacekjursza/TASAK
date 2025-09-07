"""
Daemon management commands for TASAK.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional
import psutil
import requests


DAEMON_PORT = 8765
DAEMON_HOST = "127.0.0.1"
DAEMON_URL = f"http://{DAEMON_HOST}:{DAEMON_PORT}"
PID_FILE = Path.home() / ".tasak" / "daemon.pid"
LOG_FILE = Path.home() / ".tasak" / "daemon.log"
DISABLE_AUTOSTART_FILE = Path.home() / ".tasak" / "daemon.disabled"


def get_daemon_pid() -> Optional[int]:
    """Get the PID of the running daemon."""
    if not PID_FILE.exists():
        return None

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process is actually running
        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            # Verify it's our daemon
            if "tasak" in " ".join(process.cmdline()).lower():
                return pid
    except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    # PID file exists but process is not running
    PID_FILE.unlink(missing_ok=True)
    return None


def is_daemon_running() -> bool:
    """Check if the daemon is running."""
    pid = get_daemon_pid()
    if not pid:
        return False

    # Also check if it responds to health check
    try:
        response = requests.get(f"{DAEMON_URL}/health", timeout=1)
        return response.status_code == 200
    except:
        return False


def start_daemon(verbose: bool = False, log_level: Optional[str] = None) -> bool:
    """Start the TASAK daemon."""
    if is_daemon_running():
        print("Daemon is already running", file=sys.stderr)
        return True

    # Ensure directories exist
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Start daemon process
    print(f"Starting TASAK daemon on port {DAEMON_PORT}...")

    # Use subprocess to start in background
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent.parent)
    # Determine log level for server and uvicorn
    effective_level = (
        log_level
        or env.get("TASAK_DAEMON_LOG_LEVEL")
        or ("DEBUG" if verbose else "WARNING")
    ).lower()
    env["TASAK_DAEMON_LOG_LEVEL"] = effective_level.upper()

    with open(LOG_FILE, "a") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "tasak.daemon.server:app",
                "--host",
                DAEMON_HOST,
                "--port",
                str(DAEMON_PORT),
                "--log-level",
                effective_level,
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,  # Detach from terminal
        )

    # Save PID
    PID_FILE.write_text(str(process.pid))
    # Ensure autostart is enabled again
    DISABLE_AUTOSTART_FILE.unlink(missing_ok=True)

    # Wait for daemon to start
    for _ in range(10):  # 10 second timeout
        time.sleep(1)
        if is_daemon_running():
            print(f"Daemon started successfully (PID: {process.pid})")
            print(f"Logs: {LOG_FILE}")
            return True

    print("Failed to start daemon", file=sys.stderr)
    stop_daemon()  # Clean up
    return False


def stop_daemon() -> bool:
    """Stop the TASAK daemon."""
    pid = get_daemon_pid()

    if not pid:
        print("Daemon is not running", file=sys.stderr)
        return True

    print(f"Stopping daemon (PID: {pid})...")

    try:
        # Try graceful shutdown first (but verify process actually exits)
        try:
            requests.post(f"{DAEMON_URL}/shutdown", timeout=5)
        except Exception:
            pass

        # Give it a brief moment to exit on its own
        time.sleep(0.5)

        if psutil.pid_exists(pid):
            process = psutil.Process(pid)

            # Try terminate
            process.terminate()

            # Wait for process to terminate
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                # Force kill
                process.kill()
                process.wait(timeout=5)

        print("Daemon stopped")
        PID_FILE.unlink(missing_ok=True)
        # Mark explicit stop to prevent autostart until manual start
        try:
            DISABLE_AUTOSTART_FILE.parent.mkdir(parents=True, exist_ok=True)
            DISABLE_AUTOSTART_FILE.write_text(str(int(time.time())))
        except Exception:
            pass
        return True

    except psutil.NoSuchProcess:
        print("Daemon process not found")
        PID_FILE.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"Error stopping daemon: {e}", file=sys.stderr)
        return False


def restart_daemon(verbose: bool = False, log_level: Optional[str] = None) -> bool:
    """Restart the TASAK daemon."""
    print("Restarting daemon...")
    stop_daemon()
    time.sleep(1)
    return start_daemon(verbose=verbose, log_level=log_level)


def daemon_status():
    """Show daemon status."""
    pid = get_daemon_pid()

    if not pid:
        print("Daemon is not running")
        return

    print(f"Daemon is running (PID: {pid})")

    try:
        # Get health status
        response = requests.get(f"{DAEMON_URL}/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data.get('status', 'unknown')}")
            print(f"Active connections: {data.get('connections', 0)}")

            # Get connection details
            response = requests.get(f"{DAEMON_URL}/connections", timeout=2)
            if response.status_code == 200:
                data = response.json()
                conns = data.get("connections", [])
                if conns:
                    print("\nActive connections:")
                    for conn in conns:
                        print(
                            f"  - {conn['app']}: idle {conn['idle']:.1f}s, age {conn['age']:.1f}s"
                        )
    except Exception as e:
        print(f"Warning: Could not get daemon status: {e}", file=sys.stderr)


def show_daemon_logs(lines: int = 50, follow: bool = False):
    """Show daemon logs."""
    if not LOG_FILE.exists():
        print("No log file found", file=sys.stderr)
        return

    if follow:
        # Use tail -f
        subprocess.run(["tail", "-f", str(LOG_FILE)])
    else:
        # Show last N lines
        subprocess.run(["tail", f"-n{lines}", str(LOG_FILE)])


def handle_daemon_command(args):
    """Handle daemon subcommands."""
    if args.daemon_command == "start":
        start_daemon(
            verbose=getattr(args, "verbose", False),
            log_level=getattr(args, "log_level", None),
        )
    elif args.daemon_command == "stop":
        stop_daemon()
    elif args.daemon_command == "restart":
        restart_daemon(
            verbose=getattr(args, "verbose", False),
            log_level=getattr(args, "log_level", None),
        )
    elif args.daemon_command == "status":
        daemon_status()
    elif args.daemon_command == "logs":
        show_daemon_logs(
            lines=getattr(args, "lines", 50), follow=getattr(args, "follow", False)
        )
    else:
        print(f"Unknown daemon command: {args.daemon_command}", file=sys.stderr)
        sys.exit(1)
