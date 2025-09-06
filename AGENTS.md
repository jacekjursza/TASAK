# Repository Guidelines

## Project Structure & Module Organization
- `tasak/`: Core package (CLI entry `main.py`, config loader `config.py`, runners: `app_runner.py`, `mcp_*`, `curated_app.py`, admin `admin_commands.py`).
- `tests/`: Unit and e2e tests (`tests/e2e/mini-apps/` contains small sample servers).
- `docs/`: Final user docs under `docs/`.
- `examples/`: Example configuration files.
- Top-level: `pyproject.toml` (package + `tasak` console script), `.pre-commit-config.yaml`, `requirements.txt`.

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`.
- Install dev mode: `pip install -e .` (optional MCP extras: `pip install -e .[mcp]`).
- Install tools: `pip install -r requirements.txt && pip install pytest`.
- Run CLI: `tasak` (lists enabled apps) or `tasak <app> [--help]`.
- Run tests: `pytest -q` (select: `pytest -k mcp_remote`).
- Lint/format: `ruff check . --fix && ruff format .`.
- Pre-commit (one-off): `pre-commit run --all-files`.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, type hints required for new/changed code.
- Naming: `snake_case` functions/vars, `PascalCase` classes, modules lowercase; tests as `tests/test_*.py`.
- Keep files ≤ 600 lines (enforced by pre-commit). Keep functions focused and small.
- Use Ruff for linting/formatting; run hooks before pushing.

## Testing Guidelines
- Framework: `pytest` with `unittest.mock` for isolation. Prefer fast unit tests; e2e live under `tests/e2e/`.
- Add tests alongside changed modules; maintain or improve coverage of touched code.
- Example: run a single file `pytest tests/test_main.py -q`.

## Commit & Pull Request Guidelines
- Commit style: Conventional Commits (e.g., `feat: add curated mode`, `fix(mcp): handle OAuth errors`).
- PRs: concise description, linked issues, test coverage for changes, update docs under `docs/` when applicable, include CLI output or screenshots for UX changes.
- Keep PRs small and focused; ensure `pre-commit` and `pytest` pass.

## Security & Configuration Tips
- Do not commit secrets; prefer env vars in `tasak.yaml` (`meta.env` supports `${VAR}` expansion).
- Global config: `~/.tasak/tasak.yaml`; project config: `./tasak.yaml` or `./.tasak/tasak.yaml` (merged hierarchically).
