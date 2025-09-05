# Task 006: Pre-commit Hooks Setup

**Objective:** Set up pre-commit hooks to enforce code quality and consistency.

## Requirements

1.  **Configuration File:**
    *   Create a `.pre-commit-config.yaml` file in the project root.

2.  **Basic Hooks:**
    *   Add standard hooks for Python projects:
        *   `check-yaml`: For checking YAML file syntax.
        *   `check-added-large-files`: To prevent committing large binary files.
        *   `end-of-file-fixer`: To ensure files end with a newline.
        *   `trailing-whitespace`: To remove trailing whitespace.

3.  **Code Formatting & Linting:**
    *   Add hooks for a code formatter like `black` or `ruff format`.
    *   Add hooks for a linter like `ruff` or `flake8`.

4.  **Custom Hook (Line Count):**
    *   Implement a custom pre-commit hook to check if any Python file exceeds 600 lines.
    *   This can be a simple shell script or a Python script.

## Acceptance Criteria

*   A `.pre-commit-config.yaml` file is present with the configured hooks.
*   Running `pre-commit install` successfully sets up the hooks.
*   Committing a file that violates a rule (e.g., has trailing whitespace, or is longer than 600 lines) fails with an appropriate error message.
*   Committing a compliant file succeeds.
