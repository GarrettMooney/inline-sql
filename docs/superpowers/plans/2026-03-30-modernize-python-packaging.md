# Modernize Python Packaging & Tooling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update inline-sql from 2022-era Python packaging to 2026 standards — modern Python versions, uv, ruff, and updated CI.

**Architecture:** No architectural changes. This is a tooling/packaging modernization of a small library. The build backend (hatchling) stays, the library code is unchanged except for modernizing typing imports, and the dev/CI tooling moves from hatch+black to uv+ruff.

**Tech Stack:** Python 3.10+, hatchling (build), uv (dev/CI), ruff (lint/format), pytest + pytest-cov (testing), DuckDB 1.x, pandas, sqlparse

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Modify | Python version, deps, dev tooling config |
| `.github/workflows/ci.yml` | Modify | CI pipeline |
| `README.md` | Modify | Python version mention |
| `inline_sql/_src/runtime.py` | Modify | Modernize typing imports |
| `uv.lock` | Create | Generated lock file |

Files NOT modified (confirmed unchanged): `inline_sql/__init__.py`, `inline_sql/__about__.py`, `inline_sql/_src/executor.py`, `tests/sql_test.py`, `tests/files_test.py`, `.editorconfig`, `.gitignore`, `LICENSE`

---

## Chunk 1: Packaging and Tooling

### Task 1: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update Python version and classifiers**

Change `requires-python` and replace the classifiers block:

```toml
requires-python = ">=3.10"
```

Replace classifiers with:
```toml
classifiers = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Developers",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: SQL",
  "License :: OSI Approved :: MIT License",
  "Topic :: Database",
  "Topic :: Software Development :: Libraries",
]
```

- [ ] **Step 2: Bump duckdb dependency**

Change:
```toml
dependencies = [
  "duckdb>=1.0",
  "pandas>=1.3",
  "sqlparse>=0.4",
]
```

- [ ] **Step 3: Replace hatch dev config with dependency-groups and ruff config**

Delete these three sections entirely:
- `[tool.hatch.envs.default]` (lines 42-47)
- `[tool.hatch.envs.default.scripts]` (lines 48-50)
- `[[tool.hatch.envs.test.matrix]]` (lines 52-53)

Keep `[tool.hatch.version]` (lines 39-40) — needed by hatchling.
Keep `[tool.coverage.run]` and `[tool.coverage.report]` — needed by pytest-cov.

Add after `[tool.hatch.version]`:

```toml
[dependency-groups]
dev = [
  "pytest",
  "pytest-cov",
  "ruff",
]
```

Add at end of file (after coverage sections):

```toml
[tool.ruff]
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I"]
```

- [ ] **Step 4: Verify the final pyproject.toml is valid**

Run: `uv run python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"`
Expected: No output (no parse errors)

- [ ] **Step 5: Generate uv.lock**

Run: `uv lock`
Expected: Creates `uv.lock` file with resolved dependencies

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: modernize pyproject.toml — Python 3.10+, duckdb>=1.0, uv+ruff"
```

---

### Task 2: Update CI workflow

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Rewrite CI workflow**

Replace the entire contents of `.github/workflows/ci.yml` with:

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.13"
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  test:
    name: Python ${{ matrix.python-version }} on ${{ startsWith(matrix.os, 'macos-') && 'macOS' || startsWith(matrix.os, 'windows-') && 'Windows' || 'Linux' }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          python-version: ${{ matrix.python-version }}

      - run: uv sync --frozen

      - run: uv run pytest --cov-report=term-missing --cov-config=pyproject.toml --cov=inline_sql --cov=tests
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "chore: update CI to uv + ruff, test Python 3.10-3.13"
```

---

### Task 3: Modernize typing imports

**Files:**
- Modify: `inline_sql/_src/runtime.py`

- [ ] **Step 1: Update runtime.py imports**

In `inline_sql/_src/runtime.py`, change:

```python
from typing import Any, Dict, List, Tuple
```

to:

```python
from typing import Any
```

Then update the function signatures:

`prepare_query` signature changes from:
```python
def prepare_query(query: str) -> Tuple[str, List[str]]:
```
to:
```python
def prepare_query(query: str) -> tuple[str, list[str]]:
```

Inside `prepare_query`, change:
```python
    new_tokens: List[str] = []
    params_map: Dict[str, int] = {}
```
to:
```python
    new_tokens: list[str] = []
    params_map: dict[str, int] = {}
```

`run_query` signature changes from:
```python
def run_query(query: str, context: Dict[str, Any]) -> pd.DataFrame:
```
to:
```python
def run_query(query: str, context: dict[str, Any]) -> pd.DataFrame:
```

- [ ] **Step 2: Run tests to verify nothing broke**

Run: `uv run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add inline_sql/_src/runtime.py
git commit -m "chore: modernize typing imports for Python 3.10+"
```

---

### Task 4: Update README and run formatting

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update Python version in README**

Change line 25:
```
Supports Python 3.7+, tested on all major operating systems.
```
to:
```
Supports Python 3.10+, tested on all major operating systems.
```

- [ ] **Step 2: Run ruff formatter and linter**

Run: `uv run ruff format .`
Run: `uv run ruff check --fix .`
Expected: Minimal or no changes (black and ruff defaults are compatible)

- [ ] **Step 3: Commit**

```bash
git add README.md inline_sql/ tests/
git commit -m "chore: update README Python version, run ruff format"
```

---

### Task 5: Final verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest tests/ -v --cov-report=term-missing --cov-config=pyproject.toml --cov=inline_sql --cov=tests`
Expected: All tests pass, coverage report prints

- [ ] **Step 2: Verify ruff is clean**

Run: `uv run ruff check .`
Run: `uv run ruff format --check .`
Expected: No issues found, all files formatted

- [ ] **Step 3: Verify package builds**

Run: `uv build`
Expected: Creates dist/ with .whl and .tar.gz
