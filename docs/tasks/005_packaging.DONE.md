# Task 005: Packaging and Installation

**Objective:** Prepare the project for distribution and installation via `pip`.

## Requirements

1.  **`pyproject.toml`:**
    *   Create a `pyproject.toml` file to define the project metadata (name, version, author, etc.) and dependencies.
    *   Use a modern build backend like `setuptools` or `flit`.

2.  **Dependencies:**
    *   List all project dependencies (e.g., `PyYAML`, `click`) in the `pyproject.toml` file.

3.  **Console Script Entry Point:**
    *   Configure the `pyproject.toml` to create a `tasak` console script that points to the `main` function in `tasak.main`.
    *   This will make the `tasak` command available globally after installation.

4.  **Installation:**
    *   The project should be installable in editable mode using `pip install -e .`.

## Acceptance Criteria

*   A `pyproject.toml` file is present and correctly configured.
*   Running `pip install .` successfully installs the package.
*   After installation, the `tasak` command is available in the shell and executes the application.
*   Dependencies are automatically installed along with the package.
