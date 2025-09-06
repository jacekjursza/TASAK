#!/usr/bin/env python3
"""
PyPI Publishing Script for TASAK

This script handles the complete publishing workflow:
1. Checks current version vs PyPI
2. Runs tests and quality checks
3. Builds distribution packages
4. Publishes to PyPI (or TestPyPI)
5. Creates git tag

Usage:
    python scripts/publish.py           # Publish to PyPI
    python scripts/publish.py --test    # Publish to TestPyPI
    python scripts/publish.py --check   # Dry run, check only
"""

import argparse
import subprocess
import sys
from pathlib import Path
import tomllib
import re
from typing import Optional, Tuple


def run_command(
    cmd: list[str], capture: bool = False, check: bool = True
) -> Optional[str]:
    """Run a shell command and optionally capture output."""
    print(f"→ Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=check)
        if capture:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as e:
        if capture and not check:
            return e.stdout.strip() if e.stdout else ""
        print(f"✗ Command failed: {e}")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        sys.exit(1)


def get_project_version() -> str:
    """Get version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        print("✗ pyproject.toml not found")
        sys.exit(1)

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    version = data.get("project", {}).get("version")
    if not version:
        print("✗ Version not found in pyproject.toml")
        sys.exit(1)

    return version


def get_pypi_version(package_name: str, test_pypi: bool = False) -> Optional[str]:
    """Get latest version from PyPI."""
    index_url = (
        "https://test.pypi.org/simple/" if test_pypi else "https://pypi.org/simple/"
    )

    output = run_command(
        ["pip", "index", "versions", package_name, "--index-url", index_url],
        capture=True,
        check=False,
    )

    if not output or "ERROR" in output:
        return None

    # Parse version from pip output
    match = re.search(r"Available versions: ([0-9]+\.[0-9]+\.[0-9]+)", output)
    if match:
        return match.group(1)

    # Try alternate format
    match = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", output)
    if match:
        return match.group(1)

    return None


def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string."""
    parts = version.split(".")
    return (
        int(parts[0]) if len(parts) > 0 else 0,
        int(parts[1]) if len(parts) > 1 else 0,
        int(parts[2]) if len(parts) > 2 else 0,
    )


def compare_versions(v1: str, v2: str) -> int:
    """Compare two versions. Returns: -1 if v1<v2, 0 if equal, 1 if v1>v2."""
    p1 = parse_version(v1)
    p2 = parse_version(v2)

    if p1 < p2:
        return -1
    elif p1 > p2:
        return 1
    return 0


def check_git_status():
    """Ensure git working directory is clean."""
    print("\n📋 Checking git status...")

    # Check for uncommitted changes
    status = run_command(["git", "status", "--porcelain"], capture=True)
    if status:
        print("✗ Uncommitted changes detected:")
        print(status)
        print("\nPlease commit or stash changes before publishing.")
        sys.exit(1)

    # Check we're on main branch
    branch = run_command(["git", "branch", "--show-current"], capture=True)
    if branch != "main":
        response = input(
            f"⚠️  Not on main branch (current: {branch}). Continue? [y/N]: "
        )
        if response.lower() != "y":
            sys.exit(1)

    print("✓ Git status clean")


def run_tests():
    """Run test suite."""
    print("\n🧪 Running tests...")
    run_command(["pytest", "-q"])
    print("✓ Tests passed")


def run_quality_checks():
    """Run code quality checks."""
    print("\n🔍 Running quality checks...")

    # Run ruff
    run_command(["ruff", "check", "."])
    print("✓ Ruff check passed")

    # Run ruff format check
    run_command(["ruff", "format", "--check", "."])
    print("✓ Ruff format check passed")

    print("✓ All quality checks passed")


def clean_build_artifacts():
    """Remove old build artifacts."""
    print("\n🧹 Cleaning build artifacts...")

    dirs_to_clean = ["dist", "build", "*.egg-info"]
    for pattern in dirs_to_clean:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                run_command(["rm", "-rf", str(path)])
                print(f"  Removed {path}")


def build_package():
    """Build distribution packages."""
    print("\n📦 Building distribution packages...")

    # Ensure build tool is installed
    run_command([sys.executable, "-m", "pip", "install", "--quiet", "build"])

    # Build the package
    run_command([sys.executable, "-m", "build"])

    # List built files
    dist_files = list(Path("dist").glob("*"))
    print(f"✓ Built {len(dist_files)} distribution files:")
    for f in dist_files:
        print(f"  - {f.name}")


def publish_package(test_pypi: bool = False):
    """Publish package to PyPI."""
    repo_url = "https://test.pypi.org/legacy/" if test_pypi else None
    repo_name = "TestPyPI" if test_pypi else "PyPI"

    print(f"\n📤 Publishing to {repo_name}...")

    # Ensure twine is installed
    run_command([sys.executable, "-m", "pip", "install", "--quiet", "twine"])

    # Upload
    cmd = [sys.executable, "-m", "twine", "upload"]
    if test_pypi:
        cmd.extend(["--repository-url", repo_url])
    cmd.append("dist/*")

    run_command(cmd)
    print(f"✓ Successfully published to {repo_name}")


def create_git_tag(version: str):
    """Create and push git tag."""
    print(f"\n🏷️  Creating git tag v{version}...")

    tag_name = f"v{version}"

    # Check if tag exists
    existing = run_command(["git", "tag", "-l", tag_name], capture=True)
    if existing:
        print(f"⚠️  Tag {tag_name} already exists")
        return

    # Create tag
    run_command(["git", "tag", "-a", tag_name, "-m", f"Release {version}"])
    print(f"✓ Created tag {tag_name}")

    # Ask to push
    response = input("Push tag to origin? [y/N]: ")
    if response.lower() == "y":
        run_command(["git", "push", "origin", tag_name])
        print(f"✓ Pushed tag {tag_name}")


def main():
    parser = argparse.ArgumentParser(
        description="Publish TASAK to PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--test", action="store_true", help="Publish to TestPyPI instead of PyPI"
    )
    parser.add_argument(
        "--check", action="store_true", help="Run checks only, don't publish"
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--skip-tag", action="store_true", help="Skip creating git tag")

    args = parser.parse_args()

    print("🚀 TASAK Publishing Script")
    print("=" * 50)

    # Get current version
    current_version = get_project_version()
    print(f"📌 Current version: {current_version}")

    # Check PyPI version
    pypi_version = get_pypi_version("tasak", test_pypi=args.test)
    if pypi_version:
        print(
            f"📦 Latest {'TestPyPI' if args.test else 'PyPI'} version: {pypi_version}"
        )

        comparison = compare_versions(current_version, pypi_version)
        if comparison <= 0:
            print(
                f"✗ Current version ({current_version}) is not greater than PyPI version ({pypi_version})"
            )
            print("  Please update version in pyproject.toml")
            sys.exit(1)
    else:
        print(
            f"📦 Package not found on {'TestPyPI' if args.test else 'PyPI'} (first release)"
        )

    # Run checks
    check_git_status()

    if not args.skip_tests:
        run_tests()

    run_quality_checks()

    if args.check:
        print("\n✅ All checks passed! Ready to publish.")
        print(f"   Run without --check to publish v{current_version}")
        return

    # Build and publish
    clean_build_artifacts()
    build_package()

    # Final confirmation
    repo_name = "TestPyPI" if args.test else "PyPI"
    print(f"\n⚠️  Ready to publish v{current_version} to {repo_name}")
    response = input("Continue? [y/N]: ")
    if response.lower() != "y":
        print("Aborted.")
        sys.exit(1)

    publish_package(test_pypi=args.test)

    # Create git tag
    if not args.skip_tag and not args.test:
        create_git_tag(current_version)

    # Success message
    print("\n✨ Success! TASAK has been published.")
    print(f"   Version {current_version} is now available on {repo_name}")

    if args.test:
        print("\n📝 To install from TestPyPI:")
        print(
            f"   pip install -i https://test.pypi.org/simple/ tasak=={current_version}"
        )
    else:
        print("\n📝 To install from PyPI:")
        print(f"   pip install tasak=={current_version}")


if __name__ == "__main__":
    main()
