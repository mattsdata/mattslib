# mattslib

[![CI](https://github.com/mattsdata/mattslib/actions/workflows/ci.yml/badge.svg)](https://github.com/mattsdata/mattslib/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)
![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)
![Typed](https://img.shields.io/badge/typing-mypy%20strict-informational)
![Dependencies](https://img.shields.io/badge/runtime%20deps-0-success)
![License](https://img.shields.io/badge/license-MIT-blue)

*Author: **Mathew Varghese** · Version 1.0*

**A small, well-tested library of Python utilities I reuse across projects** — the pieces
almost every production service needs and almost every team rewrites: retries, structured
logging, typed config, caching, timing and safe file I/O.

Design principles:

- **Zero runtime dependencies** — standard library only, so it drops into any project ([ADR-0001](docs/adr/0001-zero-runtime-dependencies.md))
- **Fully typed** — passes `mypy --strict`; ships `py.typed`
- **Tested** — 99% coverage, plus every docstring example runs as a test
- **Documented to a standard**: every file opens with a source header (purpose, design notes, version history)
- **Testable by design** — clocks and sleeps are injectable, so tests never actually wait

## Install

```bash
pip install "git+https://github.com/mattsdata/mattslib.git"
```

## What's inside

| Module | Use it for | Key API |
|---|---|---|
| `mattslib.retry` | Calling flaky networks, APIs and databases | `@retry`, `@async_retry` |
| `mattslib.logs` | JSON logs for ELK / Loki / CloudWatch | `setup_logging()`, `JsonFormatter` |
| `mattslib.config` | Typed settings from env vars, failing fast | `load_config()`, `ConfigError` |
| `mattslib.cache` | Caching values that go stale | `@ttl_cache` |
| `mattslib.timing` | Measuring slow code | `Timer`, `@timed` |
| `mattslib.files` | Crash-safe writes, hashing, batching | `atomic_write()`, `file_hash()`, `chunked()` |

## Quick tour

```python
from dataclasses import dataclass
import logging

import requests
from mattslib import load_config, retry, setup_logging, ttl_cache, chunked, Timer


@dataclass(frozen=True)
class Settings:
    api_url: str
    timeout: float = 5.0
    debug: bool = False


settings = load_config(Settings, prefix="APP_")  # reads APP_API_URL, APP_TIMEOUT, APP_DEBUG
setup_logging("DEBUG" if settings.debug else "INFO")
log = logging.getLogger("orders")


@ttl_cache(seconds=300)
@retry(attempts=4, exceptions=(requests.ConnectionError, requests.Timeout))
def get_customer(customer_id: int) -> dict:
    resp = requests.get(f"{settings.api_url}/customers/{customer_id}", timeout=settings.timeout)
    resp.raise_for_status()
    return resp.json()


with Timer("sync") as t:
    for batch in chunked(range(1, 1001), 100):
        customers = [get_customer(cid) for cid in batch]
log.info("sync finished", extra={"seconds": round(t.elapsed, 2)})
```

If configuration is wrong, every problem is reported at once:

```
mattslib.config.ConfigError: Invalid configuration:
  APP_API_URL: required but not set
  APP_TIMEOUT: expected float, got 'fast'
```

## Development

```bash
pip install -e ".[dev]"
pytest              # tests + docstring examples + coverage gate (90%)
ruff check . && ruff format --check .
mypy src
```

CI runs all of the above on Python 3.10–3.13 for every push and pull request.

## Project layout

```
src/mattslib/      library code (one focused module per concern)
tests/            pytest suite
docs/adr/         architecture decision records — the "why" behind design choices
```

## Roadmap

- `mattslib.http` — session with sensible timeouts and retries built in
- `mattslib.cli` — helpers for consistent command-line tools
- Publish to PyPI

See [CHANGELOG.md](CHANGELOG.md) for releases and [CONTRIBUTING.md](CONTRIBUTING.md) for the standards every module follows.

## License

MIT © Mathew Varghese
