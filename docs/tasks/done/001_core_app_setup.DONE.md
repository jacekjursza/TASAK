# Task 001: Core Application Setup

**Objective:** Create the basic scaffolding for the TASAK application, including the main entry point and argument parsing.

## Requirements

1.  **Create Project Structure:**
    *   Set up a `tasak` source directory with an initial `__init__.py` and `main.py`.

2.  **Implement Entry Point:**
    *   The application should be runnable from the command line.
    *   Create a `main` function in `tasak/main.py` that will serve as the primary entry point.

3.  **Argument Parsing:**
    *   Use a library like `argparse` or `click` to handle command-line arguments.
    *   The application should support a `--help` flag that displays a basic help message.
    *   It should accept an app name as a positional argument (e.g., `tasak my_app`).

## Acceptance Criteria

*   A `tasak` directory exists with the initial Python files.
*   Running `python -m tasak.main --help` displays a help message.
*   Running `python -m tasak.main my_app` executes the main logic (for now, it can just print the app name).
