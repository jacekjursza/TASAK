"""
Docs App Type

Provides a filesystem-backed, read-only navigator for Markdown documentation.

Behavior:
- Without arguments: list root-level Markdown files as "commands" and
  immediate subdirectories as "sub-apps".
- With path segments: navigate into subdirectories recursively.
- When a Markdown file is selected (with or without .md extension): print its
  content to stdout.

Configuration (in app_config):
- type: "docs"
- meta:
    directory (str): Absolute or relative path to the docs root directory

Examples:
- tasak docsapp                 # list root-level docs and subfolders
- tasak docsapp guides         # list docs in ./guides
- tasak docsapp guides intro   # print ./guides/intro.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Dict, List, Tuple


def run_docs_app(app_name: str, app_config: Dict[str, any], app_args: List[str]):
    """Run a docs app with recursive navigation.

    Path traversal is based on tokens after the app name. The final target may
    be a directory (list) or a Markdown file (print content). The root directory
    is defined by meta.directory (or meta.dir as a fallback).
    """
    meta = app_config.get("meta", {}) or {}
    base_dir_str = meta.get("directory") or meta.get("dir")
    respect_include = meta.get("respect_include", True)
    exclude_patterns = _normalize_exclude_patterns(meta.get("exclude"))
    if not base_dir_str:
        print("Error: 'meta.directory' not specified for docs app.", file=sys.stderr)
        sys.exit(1)
    base_dir = Path(base_dir_str).expanduser().resolve()
    if not base_dir.exists() or not base_dir.is_dir():
        print(
            f"Error: docs directory does not exist or is not a directory: {base_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Special: explicit help
    if any(a in ("--help", "-h") for a in app_args):
        _print_help(app_name, base_dir)
        return

    # Build target path from non-flag args. Support colon-joined shorthand
    # like "folder:sub1:sub2" in addition to space-separated segments.
    segments: List[str] = []
    for raw in app_args:
        if raw.startswith("-"):
            continue
        if ":" in raw:
            parts = [p for p in raw.split(":") if p]
            segments.extend(parts)
        else:
            segments.append(raw)
    target_path = (base_dir.joinpath(*segments)).resolve() if segments else base_dir

    # Prevent path escape outside base_dir
    try:
        target_path.relative_to(base_dir)
    except Exception:
        print("Error: Path escapes the configured docs directory.", file=sys.stderr)
        sys.exit(1)

    # If directory -> list entries; if file (with or without .md) -> print contents
    if target_path.is_dir():
        # Exclusion: silently fall back to parent listing (agent-friendly)
        if _is_excluded(target_path, base_dir, exclude_patterns):
            parent = target_path.parent if target_path != base_dir else base_dir
            _list_dir(app_name, base_dir, parent, exclude_patterns=exclude_patterns)
            return
        _list_dir(app_name, base_dir, target_path, exclude_patterns=exclude_patterns)
        return

    # Handle file selection: allow implicit .md extension
    if target_path.is_file() and target_path.suffix.lower() == ".md":
        if _is_excluded(target_path, base_dir, exclude_patterns):
            _list_dir(
                app_name,
                base_dir,
                target_path.parent,
                exclude_patterns=exclude_patterns,
            )
            return
        _print_file(
            target_path,
            base_dir,
            respect_include=respect_include,
            exclude_patterns=exclude_patterns,
        )
        return
    md_candidate = target_path.with_suffix(".md")
    if md_candidate.is_file():
        if _is_excluded(md_candidate, base_dir, exclude_patterns):
            _list_dir(
                app_name,
                base_dir,
                md_candidate.parent,
                exclude_patterns=exclude_patterns,
            )
            return
        _print_file(
            md_candidate,
            base_dir,
            respect_include=respect_include,
            exclude_patterns=exclude_patterns,
        )
        return

    # Not found (agent-friendly note)
    print("Path not found — listing parent.", file=sys.stderr)
    # Provide a hint with a listing of the nearest existing parent
    existing_parent = target_path
    while not existing_parent.exists() and existing_parent != existing_parent.parent:
        existing_parent = existing_parent.parent
    if existing_parent.exists() and existing_parent.is_dir():
        _list_dir(app_name, base_dir, existing_parent)
    sys.exit(1)


def _list_dir(
    app_name: str,
    base_dir: Path,
    path: Path,
    *,
    exclude_patterns: List[str] | None = None,
):
    """List Markdown files (commands) and subdirectories (sub-apps)."""
    # Gather immediate children
    try:
        entries = list(path.iterdir())
    except PermissionError:
        print("Error: Permission denied while listing directory.", file=sys.stderr)
        sys.exit(1)

    exclude_patterns = exclude_patterns or []
    md_files = []
    raw_subdirs = []
    for p in entries:
        if _is_excluded(p, base_dir, exclude_patterns):
            continue
        if p.is_file() and p.suffix.lower() == ".md":
            md_files.append(p)
        elif p.is_dir():
            raw_subdirs.append(p)
    md_files.sort(key=lambda p: p.name.lower())
    raw_subdirs.sort(key=lambda p: p.name.lower())

    # Compute flattened sub-apps: hide empty dirs; if a dir contains only dirs
    # (recursively), present as colon-joined paths pointing to deeper nodes
    subapps: List[Tuple[str, Path]] = []  # (display_name, real_path)
    for d in raw_subdirs:
        subapps.extend(_flatten_dir_for_listing(d, base_dir, exclude_patterns))

    # Pretty header based on relative path
    rel = path.relative_to(base_dir)
    where = "/" if str(rel) == "." else f"/{rel.as_posix()}"
    print(f'"{app_name}" at {where}')

    # Commands
    print(f'"{app_name}" commands:')
    if md_files:
        for f in md_files:
            name = f.stem
            print(f"  {name}")
    else:
        print("  (none)")

    # Sub-apps
    print(f'\n"{app_name}" sub-apps:')
    if subapps:
        names = ", ".join(n for n, _ in subapps)
        print(f"  {names}")
    else:
        print("  (none)")

    # Usage hint
    bin_name = _get_binary_name()
    print(
        f"\nUse: {bin_name} {app_name} <subdir> [subdir...]        # Navigate",
    )
    print(
        f"     {bin_name} {app_name} <a:b[:c]>               # Navigate (shorthand)",
    )
    print(
        f"     {bin_name} {app_name} <sub-app...> <command>  # Open Markdown",
    )


def _print_file(
    path: Path,
    base_dir: Path,
    *,
    respect_include: bool = True,
    exclude_patterns: List[str] | None = None,
):
    """Print the contents of a Markdown file to stdout.

    Ensures a trailing newline and optionally expands include directives of the
    form '@relative/path/to/file.md' placed on a single line.
    """
    text = _read_markdown_with_includes(
        path,
        base_dir,
        respect_include=respect_include,
        exclude_patterns=exclude_patterns or [],
    )
    if not text.endswith("\n"):
        text += "\n"
    sys.stdout.write(text)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1", errors="replace")


def _read_markdown_with_includes(
    path: Path,
    base_dir: Path,
    *,
    respect_include: bool = True,
    exclude_patterns: List[str] = None,
    _depth: int = 0,
    _max_depth: int = 20,
) -> str:
    """Read Markdown and expand '@<relpath>' include directives line-by-line.

    - Paths are resolved relative to the current file's directory, falling back
      to base_dir, and must remain within base_dir. Only .md files are included.
    - Recursion depth is limited to prevent cycles.
    """
    text = _read_text(path)
    if not respect_include:
        return text
    if _depth >= _max_depth:
        return text

    lines = text.splitlines()
    out_lines: List[str] = []
    cur_dir = path.parent
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("@") and (" " not in stripped and "\t" not in stripped):
            inc_rel = stripped[1:]
            inc_path = (cur_dir / inc_rel).resolve()

            # Constrain to base_dir
            def _within_base(p: Path) -> bool:
                try:
                    p.relative_to(base_dir)
                    return True
                except Exception:
                    return False

            if not _within_base(inc_path):
                inc_path = (base_dir / inc_rel).resolve()
            if (
                _within_base(inc_path)
                and not _is_excluded(inc_path, base_dir, exclude_patterns or [])
                and inc_path.is_file()
                and inc_path.suffix.lower() == ".md"
            ):
                included = _read_markdown_with_includes(
                    inc_path,
                    base_dir,
                    respect_include=respect_include,
                    exclude_patterns=exclude_patterns or [],
                    _depth=_depth + 1,
                )
                out_lines.append(included.rstrip("\n"))
                continue
        out_lines.append(line)

    return "\n".join(out_lines)


def _normalize_exclude_patterns(value) -> List[str]:
    """Normalize exclude patterns to a list of POSIX-style globs.

    Accepts None, a single string, or a list of strings. Patterns are used with
    PurePosixPath.match on the path relative to base_dir, so they should be
    specified relative to the docs root, e.g.:
      - ".git/**" (exclude any .git directory)
      - "guides/deep/**" (exclude a specific sub-tree)
      - "**/_*.md" (exclude underscore-prefixed md files anywhere)
      - "changelog.md" (exclude a root-level file)
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value if isinstance(v, (str, bytes))]
    return []


def _is_excluded(path: Path, base_dir: Path, patterns: List[str]) -> bool:
    """Return True if the path matches any exclude pattern.

    Matching is done against the POSIX-style relative path from base_dir.
    """
    try:
        rel = path.relative_to(base_dir)
    except Exception:
        return False
    rel_str = rel.as_posix()
    rel_posix = PurePosixPath(rel_str)
    for pat in patterns or []:
        try:
            if rel_posix.match(pat):
                return True
            # Special-case dir globs ending with '/**' to also exclude the dir itself
            if pat.endswith("/**"):
                base_pat = pat[:-3].rstrip("/")
                if base_pat and rel_str == base_pat:
                    return True
        except Exception:
            # Ignore bad patterns gracefully
            continue
    return False


def _dir_contains_visible_md(path: Path, base_dir: Path, patterns: List[str]) -> bool:
    try:
        for entry in path.iterdir():
            if _is_excluded(entry, base_dir, patterns):
                continue
            if entry.is_file() and entry.suffix.lower() == ".md":
                return True
        return False
    except PermissionError:
        return False


def _flatten_dir_for_listing(
    path: Path,
    base_dir: Path,
    patterns: List[str],
    _depth: int = 0,
    _max_depth: int = 50,
) -> List[Tuple[str, Path]]:
    """Return flattened sub-app entries (display_name, real_path) for a dir.

    Rules:
    - If the directory contains any visible .md files → return [(name, path)]
      (no flattening at this level).
    - Otherwise, if it has visible child directories, recurse into each and
      prefix this dir's name joined by ':' to their display names.
    - If it has no visible md and no non-empty child dirs → return [] (hidden).
    - Do not recurse into symlink directories to avoid cycles; treat them as
      regular entries (no flattening) so they appear as a simple sub-app.
    """
    if _depth >= _max_depth:
        return [(path.name, path)]

    # Avoid deep flatten on symlinks
    try:
        if path.is_symlink():
            return [(path.name, path)]
    except OSError:
        return []

    if _dir_contains_visible_md(path, base_dir, patterns):
        return [(path.name, path)]

    # Gather visible subdirs
    try:
        children = [
            p
            for p in sorted(path.iterdir(), key=lambda p: p.name.lower())
            if p.is_dir() and not _is_excluded(p, base_dir, patterns)
        ]
    except PermissionError:
        children = []

    results: List[Tuple[str, Path]] = []
    for c in children:
        flattened = _flatten_dir_for_listing(
            c, base_dir, patterns, _depth=_depth + 1, _max_depth=_max_depth
        )
        if not flattened:
            continue
        for disp, real in flattened:
            results.append((f"{path.name}:{disp}", real))

    return results


def _print_help(app_name: str, base_dir: Path):
    """Show help for docs app and list root-level entries."""
    print(f"{app_name}")
    print("Type: docs")
    print(f"Root: {base_dir}")
    print()
    _list_dir(app_name, base_dir, base_dir)


def _get_binary_name() -> str:
    # Try to follow main/mcp_parser behavior
    env_bin = os.environ.get("TASAK_BIN_NAME")
    if env_bin:
        return env_bin
    argv0 = os.path.basename(sys.argv[0] or "")
    if argv0 and argv0 not in {"python", "python3", "py", "pytest", "-m"}:
        return argv0
    cfg = os.environ.get("TASAK_CONFIG_NAME", "").strip()
    if cfg:
        base = os.path.basename(cfg)
        if base.lower().endswith((".yaml", ".yml")):
            base = base.rsplit(".", 1)[0]
        if base:
            return base
    return "tasak"
