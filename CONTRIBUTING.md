# Contributing & module standards

Every module in `mattslib` meets the same bar. This checklist is how new utilities get added.

## Adding a module

1. **Header first.** Start the file with the standard source header (below).
2. **One concern per module.** `src/mattslib/<name>.py`, with a module docstring that explains
   *when* to use it and includes a runnable example.
3. **Standard library only.** A runtime dependency needs an ADR in `docs/adr/` first.
4. **Typed.** Public functions have full type hints; `mypy --strict` must pass.
5. **Injectable side effects.** Time, sleeping, randomness and I/O targets are parameters with
   sensible defaults, so tests are fast and deterministic.
6. **Tested.** Cover the happy path, the failure path and input validation. Coverage stays ≥ 90%.
7. **Exported.** Add the public names to `src/mattslib/__init__.py` and the table in `README.md`.
8. **Recorded.** Add a line under "Unreleased" in `CHANGELOG.md`.

## Source file header (required)

Every Python file starts with this header. It tells a reader, before any code, what the file
is for, why it is designed the way it is, and how it has changed over time.

```python
# ==================================================================================================
#  mattslib :: <module>
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/<module>.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : YYYY-MM-DD
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  PURPOSE        - the real-world problem this module solves
#  WHAT IT DOES   - the public functions/classes, one line each
#  DESIGN NOTES   - the important decisions and trade-offs, and WHY
#  VERSION HISTORY
#    V1.0   YYYY-MM-DD   Mathew Varghese   Initial release.
# ==================================================================================================
```

When a module changes: bump `Version`, add a line to `VERSION HISTORY`, and update `CHANGELOG.md`.

**Comments explain *why*, not *what*.** The code shows what it does; comments record the
reasoning, the trap avoided or the trade-off accepted.

## Before opening a pull request

```bash
pip install -e ".[dev]"
pre-commit install          # optional: runs ruff on every commit
pytest && ruff check . && ruff format --check . && mypy src
```

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`,
`test:`, `refactor:`, `chore:`.
