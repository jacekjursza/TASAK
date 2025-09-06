from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _expand_path(p: str | os.PathLike[str]) -> Path:
    """Expand user and env variables and return a Path."""
    return Path(os.path.expandvars(os.path.expanduser(str(p)))).resolve()


def _iter_ancestor_dirs(start: Path) -> Iterable[Path]:
    """Yield ancestor directories from root to the start path (inclusive)."""
    parts = start.resolve().parts
    for i in range(1, len(parts) + 1):
        yield Path(*parts[:i])


def _plugin_dirs_ladder() -> list[Path]:
    """Build the search ladder for plugin directories.

    Includes:
    - Global: ~/.tasak/plugins/python
    - Local: for every ancestor from filesystem root to CWD,
      include <dir>/.tasak/plugins/python if it exists
    """
    dirs: list[Path] = []

    # Global
    home = Path.home()
    global_dir = home / ".tasak" / "plugins" / "python"
    if global_dir.is_dir():
        dirs.append(global_dir)

    # Ancestors ladder from root -> cwd
    for anc in _iter_ancestor_dirs(Path.cwd()):
        candidate = anc / ".tasak" / "plugins" / "python"
        if candidate.is_dir():
            dirs.append(candidate)

    return dirs


def _extract_description_from_file(path: Path) -> str | None:
    """Extract DESCRIPTION (str) or module docstring first line from Python file.

    Never executes plugin code; uses AST for safety.
    """
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    try:
        mod = ast.parse(source)
    except Exception:
        return None

    # Try DESCRIPTION constant
    for node in mod.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DESCRIPTION":
                    value = node.value
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        return value.value.strip()

    # Fallback: module docstring
    doc = ast.get_docstring(mod)
    if isinstance(doc, str) and doc.strip():
        return doc.strip().splitlines()[0].strip()
    return None


def _scan_plugin_dir(directory: Path) -> dict[str, dict[str, Any]]:
    """Scan a directory for plugin files and build a mapping by name.

    Precedence is handled by the caller by merge order.
    """
    found: dict[str, dict[str, Any]] = {}
    try:
        for entry in directory.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix != ".py":
                continue
            name = entry.stem
            desc = _extract_description_from_file(entry) or f"Python plugin '{name}'"
            found[name] = {
                "name": name,
                "path": str(entry),
                "description": desc,
            }
    except FileNotFoundError:
        pass
    return found


def _resolve_plugin_settings(config: Dict[str, Any]) -> dict[str, Any]:
    """Return effective plugin settings from config.

    Supports config structure:
    plugins:
      python:
        auto_enable_all: bool | str (path)
        search_paths: [str]
        python_executable: str
    """
    plugins_cfg = config.get("plugins", {}) or {}
    py_cfg = plugins_cfg.get("python", {}) or {}

    auto_enable_all = py_cfg.get("auto_enable_all", False)
    extra_paths = py_cfg.get("search_paths", []) or []
    python_executable = py_cfg.get("python_executable")

    # Back-compat: if auto_enable_all is a string, treat as an extra path and enable
    if isinstance(auto_enable_all, str):
        extra_paths = list(extra_paths) + [auto_enable_all]
        auto_enable_all = True

    # Normalize
    extra_paths = [_expand_path(p) for p in extra_paths]

    return {
        "auto_enable_all": bool(auto_enable_all),
        "search_paths": extra_paths,
        "python_executable": python_executable,
    }


def get_plugin_search_dirs(config: Dict[str, Any]) -> List[Path]:
    """Return search directories in effective precedence order.

    The order is: ladder dirs first (global -> ancestors -> cwd), then
    config-provided search_paths (highest precedence at the end).
    """
    settings = _resolve_plugin_settings(config)
    search_dirs: list[Path] = []
    search_dirs.extend(_plugin_dirs_ladder())
    search_dirs.extend(p for p in settings["search_paths"] if p.is_dir())
    return search_dirs


def discover_python_plugins(config: Dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Discover python plugins using ladder + optional config search_paths.

    Returns mapping: name -> { name, path, description }
    Later directories in the list take precedence.
    """
    search_dirs = get_plugin_search_dirs(config)

    plugins: dict[str, dict[str, Any]] = {}
    for d in search_dirs:
        scanned = _scan_plugin_dir(d)
        # merge with precedence to later dirs
        plugins.update(scanned)

    return plugins


def integrate_plugins_into_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Augment config with discovered plugins.

    - Inject a top-level app config for each plugin if not already present.
    - Optionally auto-enable plugins in apps_config.enabled_apps.
    - Populate human-friendly name from DESCRIPTION/docstring if available.
    - Resolve and store python_executable for runner convenience.
    """
    updated = dict(config)
    apps_cfg = updated.setdefault("apps_config", {})
    enabled_apps: list[str] = list(apps_cfg.get("enabled_apps", []) or [])

    settings = _resolve_plugin_settings(updated)
    plugins = discover_python_plugins(updated)

    for name, info in plugins.items():
        # Do not override explicit app configs
        if name not in updated:
            updated[name] = {
                "type": "python-plugin",
                "name": info.get("description") or name,
                "meta": {
                    "plugin_path": info["path"],
                },
            }
        # Ensure plugin_path is set even if user pre-defined minimal stub
        updated.setdefault(name, {}).setdefault("meta", {}).setdefault(
            "plugin_path", info["path"]
        )

        # Resolve and set python executable at app level for runner
        if settings.get("python_executable") and not updated[name].get(
            "python_executable"
        ):
            updated[name]["python_executable"] = settings["python_executable"]

        # Auto-enable
        if settings["auto_enable_all"] and name not in enabled_apps:
            enabled_apps.append(name)

    # Persist enabled_apps updates
    apps_cfg["enabled_apps"] = enabled_apps

    return updated


def run_python_plugin(app_name: str, app_config: Dict[str, Any], app_args: list[str]):
    """Run a discovered python plugin via subprocess.

    Respects optional 'python_executable' in app_config or global default.
    """
    meta = app_config.get("meta", {}) or {}
    plugin_path = meta.get("plugin_path") or app_config.get("plugin_path")
    if not plugin_path:
        print(
            f"Error: Plugin path not specified for app '{app_name}'.",
            file=sys.stderr,
        )
        sys.exit(1)
        return

    # Determine interpreter
    python_exec = (
        app_config.get("python_executable")
        or sys.executable  # default to current interpreter
    )

    command = [python_exec, plugin_path, *app_args]
    _execute_command(command)


def _execute_command(command: list[str]):
    """Executes a command and streams its output (mirrors app_runner)."""
    print(f"Running command: {' '.join(command)}", file=sys.stderr)
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")

        process.wait()
        if process.returncode != 0:
            print(f"\nCommand exited with code {process.returncode}", file=sys.stderr)
            sys.exit(process.returncode)
    except FileNotFoundError:
        print(f"Error: Command not found: {command[0]}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:  # noqa: BLE001
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)
