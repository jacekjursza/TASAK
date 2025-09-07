"""Create custom commands that use their own config files."""

import os
import platform
import stat
import sys
import yaml
from pathlib import Path
from typing import Any, Dict
import argparse


def handle_create_command(args: argparse.Namespace, config: Dict[str, Any]):
    """Create a custom command that uses its own config file."""
    command_name = args.name
    is_windows = platform.system() == "Windows"

    # Validate command name
    if not command_name.replace("-", "").replace("_", "").isalnum():
        print(f"❌ Invalid command name: {command_name}")
        print(
            "   Command names can only contain letters, numbers, hyphens, and underscores"
        )
        sys.exit(1)

    # Determine installation directory
    if args.install_global:
        install_dir = Path.home() / ".local" / "bin"
    else:
        install_dir = Path.cwd()

    install_dir.mkdir(parents=True, exist_ok=True)
    command_path = install_dir / command_name

    # Check if command already exists
    if command_path.exists() and not args.force:
        print(f"❌ Command '{command_name}' already exists at: {command_path}")
        print("   Use --force to overwrite")
        sys.exit(1)

    if is_windows:
        # For Windows, create both .py and .bat files
        py_path = command_path.with_suffix(".py")
        bat_path = command_path.with_suffix(".bat")

        # Create Python script (import-first with safe fallbacks)
        py_content = f'''"""
Custom TASAK command: {command_name}
This command uses {command_name}.yaml instead of tasak.yaml
"""

import os
import sys
import subprocess
import shutil

# Set environment variables to tell TASAK which config and display name to use
os.environ["TASAK_CONFIG_NAME"] = "{command_name}.yaml"
os.environ["TASAK_BIN_NAME"] = "{command_name}"

def _run():
    try:
        from tasak.main import main as tasak_main
        # Pretend the binary name is this wrapper
        sys.argv[0] = "{command_name}"
        tasak_main()
        return 0
    except Exception:
        # Fallbacks: PATH binary first, then python -m tasak.main
        bin_path = shutil.which("tasak")
        if bin_path:
            return subprocess.call([bin_path] + sys.argv[1:])
        return subprocess.call([sys.executable, "-m", "tasak.main"] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(_run())
'''

        with open(py_path, "w") as f:
            f.write(py_content)

        # Create batch wrapper (.bat launches the Python wrapper)
        bat_content = f"""@echo off
set TASAK_CONFIG_NAME={command_name}.yaml
set TASAK_BIN_NAME={command_name}
python "{py_path}" %*
"""

        with open(bat_path, "w") as f:
            f.write(bat_content)

        # Update command_path to point to the .bat file
        command_path = bat_path

    else:
        # For Unix-like systems (Linux/Mac), create Python script (import-first)
        wrapper_content = f'''#!/usr/bin/env python3
"""
Custom TASAK command: {command_name}
This command uses {command_name}.yaml instead of tasak.yaml
"""

import os
import sys
import subprocess
import shutil

# Set environment variables to tell TASAK which config and display name to use
os.environ["TASAK_CONFIG_NAME"] = "{command_name}.yaml"
os.environ["TASAK_BIN_NAME"] = "{command_name}"

def _run():
    try:
        from tasak.main import main as tasak_main
        # Pretend the binary name is this wrapper
        sys.argv[0] = "{command_name}"
        tasak_main()
        return 0
    except Exception:
        # Fallbacks: PATH binary first, then python -m tasak.main
        bin_path = shutil.which("tasak")
        if bin_path:
            return subprocess.call([bin_path] + sys.argv[1:])
        return subprocess.call([sys.executable, "-m", "tasak.main"] + sys.argv[1:])

if __name__ == "__main__":
    sys.exit(_run())
'''

        # Write the wrapper script
        with open(command_path, "w") as f:
            f.write(wrapper_content)

        # Make it executable (only on Unix-like systems)
        os.chmod(command_path, os.stat(command_path).st_mode | stat.S_IEXEC)

    # Create example config files
    config_locations = _create_example_configs(command_name)

    # Success message
    print(f"✅ Created custom command: {command_name}")
    print(f"📍 Command location: {command_path}")

    if config_locations:
        print("📝 Config files created:")
        for loc in config_locations:
            print(f"   - {loc}")

    print("\n🚀 Usage:")
    print(f"   {command_name}              # List available apps")
    print(f"   {command_name} hello        # Run the hello app")
    print(f"   {command_name} --init       # Initialize config from template")

    if args.install_global:
        if is_windows:
            print("\n💡 Tip: Make sure ~/.local/bin is in your PATH")
            print("   Add to PATH in System Settings")
        else:
            print("\n💡 Tip: Make sure ~/.local/bin is in your PATH")
            print('   export PATH="$HOME/.local/bin:$PATH"')
    else:
        if is_windows:
            print("\n💡 Tip: Run from this directory:")
            print(f"   {command_name}")
        else:
            print("\n💡 Tip: Run from this directory or add to PATH:")
            print(f"   ./{command_name}")


def _create_example_configs(command_name: str) -> list[str]:
    """Create example configuration files for the custom command."""
    config_locations = []

    # Check local directory
    local_config = Path.cwd() / f"{command_name}.yaml"
    if not local_config.exists():
        example_config = {
            "header": f"{command_name.upper()} Command Suite",
            "apps_config": {"enabled_apps": ["hello", "status"]},
            "hello": {
                "name": "Hello World",
                "type": "cmd",
                "meta": {"command": f"echo 'Hello from {command_name}!'"},
            },
            "status": {
                "name": "Status Check",
                "type": "cmd",
                "meta": {"command": "echo 'All systems operational'"},
            },
        }

        with open(local_config, "w") as f:
            yaml.safe_dump(example_config, f, default_flow_style=False, sort_keys=False)
        config_locations.append(str(local_config))

    # Check global directory
    global_config = Path.home() / ".tasak" / f"{command_name}.yaml"
    if not global_config.exists():
        global_config.parent.mkdir(parents=True, exist_ok=True)
        # Create minimal global config
        global_example = {
            "header": f"Global {command_name} configuration",
            "apps_config": {"enabled_apps": []},
        }

        with open(global_config, "w") as f:
            yaml.safe_dump(global_example, f, default_flow_style=False, sort_keys=False)
        config_locations.append(str(global_config))

    return config_locations
