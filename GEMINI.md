# TASAK: The Agent's Swiss Army Knife

## Project Overview

TASAK is a command-line utility, written in Python, that acts as a proxy for running other "sub-applications". It features a dynamic configuration system that allows for both global and local setups. The project emphasizes clean code, TDD, and a modular structure.

**Key Technologies:**
*   Python

**Architecture:**
*   A core application that reads a hierarchical configuration.
*   Global configuration is stored in `<user-home-dir>/.tasak/tasak.yaml`.
*   Local configuration is searched for in the current directory and parent directories.
*   Configuration files are merged, with local configurations overriding global ones.
*   Supports different application types, including simple command-line wrappers and more complex server integrations.

## Building and Running

**TODO:** The project's `README.md` does not contain explicit instructions on how to build, run, or test the project. Based on the description, the following commands are likely to be used:

*   **Installation:** `pip install -e .`
*   **Running:** `tasak`
*   **Testing:** `pytest`

## Development Conventions

*   **Code Style:** The project enforces a maximum of 600 lines per file via pre-commit hooks.
*   **Testing:** Test-Driven Development (TDD) is the preferred methodology.
*   **Documentation:** All code, comments, and documentation should be in English.
*   **Modularity:** The code should be organized into logical modules and sub-modules, following DRY principles.

---

## Development Workflow

This section outlines the collaboration process for developing TASAK.

1.  **Task Management:**
    *   All development tasks are defined in Markdown files located in the `docs/tasks/` directory.
    *   When a task is completed, its file will be renamed from `*.md` to `*.DONE.md`.

2.  **Tooling & Environment:**
    *   I am permitted to use any standard bash commands for project setup, configuration, and testing (e.g., `git`, `pip`, `pytest`, `mkdir`).

3.  **Version Control:**
    *   This environment is authorized with the GitHub account `jacekjursza`.
    *   I will commit significant milestones directly to the repository, providing clear commit messages.

4.  **Testing & Verification:**
    *   From time to time, I may ask for your help in testing a specific feature. I will provide you with the exact terminal command to run and a description of the expected outcome.