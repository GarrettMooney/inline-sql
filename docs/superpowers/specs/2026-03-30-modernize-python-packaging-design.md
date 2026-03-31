# Modernize Python Packaging & Tooling

## Context

`inline-sql` is a small library (~150 lines of runtime code) that wraps DuckDB to allow inline SQL queries in Python. It was last actively maintained around 2022. The project targets Python 3.7+, uses `hatch` for dev workflows, `black` for formatting, and has no linter. CI tests Python 3.7-3.10 with outdated GitHub Actions.

The goal is to bring the project up to 2026 standards for Python packaging, CI, and developer tooling without changing the library's behavior.

## Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Min Python | 3.10 | Drops EOL versions while keeping broad library compatibility |
| duckdb floor | >=1.0 | 1.0 was the stability milestone (mid-2024); 0.x is years behind |
| Dev tooling | uv (replaces hatch for dev/CI) | Modern, fast; hatchling stays as build backend |
| Formatting/linting | ruff (replaces black) | Single tool for formatting + linting; industry standard |
| Type checking | None | Codebase is too small to justify the overhead |
| Project URLs | Unchanged | Keep pointing to original ekzhang/inline-sql repo |

## Changes

### 1. pyproject.toml

**Python version & classifiers:**
- `requires-python` changes from `">=3.7"` to `">=3.10"`
- Remove classifiers for 3.7, 3.8, 3.9; add 3.11, 3.12, 3.13

**Dependencies:**
- `duckdb>=0.5` becomes `duckdb>=1.0`
- `pandas>=1.3` stays (pandas 2.x is backward-compatible for our usage)
- `sqlparse>=0.4` stays

**Dev tooling:**
- Remove `[tool.hatch.envs.default]`, `[tool.hatch.envs.default.scripts]`, and `[[tool.hatch.envs.test.matrix]]` sections
- Retain `[tool.hatch.version]` — needed by the hatchling build backend for `dynamic = ["version"]`
- Retain `[tool.coverage.run]` and `[tool.coverage.report]` — still used by pytest-cov
- Add `[dependency-groups]` with a `dev` group: `ruff`, `pytest`, `pytest-cov`
- Add `[tool.ruff]` config:
  ```toml
  [tool.ruff]
  target-version = "py310"

  [tool.ruff.lint]
  select = ["E", "F", "I"]  # pycodestyle, pyflakes, isort
  ```
- Remove any black-specific configuration

**Lock file:**
- Generate `uv.lock` and commit it

### 2. CI workflow (.github/workflows/ci.yml)

- Upgrade `actions/checkout` from v3 to v4
- Upgrade `actions/setup-python` from v4 to v5
- Add `astral-sh/setup-uv@v5` step
- Test matrix: Python 3.10, 3.11, 3.12, 3.13 on ubuntu-latest, windows-latest, macos-latest
- Replace `pip install --upgrade hatch` with `uv sync --frozen` (install from lock file)
- Replace `hatch run black --check .` with `uv run ruff check .` and `uv run ruff format --check .`
- Replace `hatch run cov` with `uv run pytest --cov-report=term-missing --cov-config=pyproject.toml --cov=inline_sql --cov=tests`

### 3. README.md

- Update "Supports Python 3.7+" to "Supports Python 3.10+"

### 4. Modernize typing imports

With Python 3.10 as the floor, replace `typing` imports with built-in generics:
- `Dict[str, Any]` → `dict[str, Any]`, `List[str]` → `list[str]`, `Tuple[str, list[str]]` → `tuple[str, list[str]]`
- Remove `from typing import Dict, List, Tuple` (keep `Any`, `Generic`, `TypeVar` as needed)

### 5. Runtime code verification

- Confirm `duckdb.connect()` + `con.execute()` + `con.fetchdf()` still work with duckdb >=1.0 (they do; `fetchdf()` remains supported)
- Verify `duckdb.ParserException` is still the correct exception class in tests
- Run the full test suite to verify no regressions

### 6. Formatting pass

- Run `ruff format .` and `ruff check --fix .` to reformat codebase from black style to ruff defaults (these are compatible, so minimal/no diff expected)

## Out of Scope

- Library behavior changes
- Version bump
- New features
- Type checking / mypy / pyright
- Changing the build backend (hatchling stays)
- Updating project URLs
- Changes to `.editorconfig` or `.gitignore`
- `py.typed` marker
