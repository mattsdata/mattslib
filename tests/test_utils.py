# ==================================================================================================
# 📜 mattslib :: tests :: config, cache, files, logs, timing
# --------------------------------------------------------------------------------------------------
#  File         : tests/test_utils.py
#  Author       : Mathew Varghese
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Proves the behaviour of the remaining mattslib modules, including their failure paths.
#
#  🔧 WHAT IT DOES
#    - config : type conversion, all-errors-at-once reporting, unsupported types.
#    - cache  : hits, expiry, LRU eviction and argument validation.
#    - files  : atomic writes, temp-file clean-up on failure, hashing, batching.
#    - logs   : JSON fields from `extra=`, exception capture, plain-text mode.
#    - timing : elapsed time and preserved function metadata.
#
#  🧠 TESTING APPROACH
#    Clocks are injected and file tests use pytest's tmp_path, so tests are isolated,
#    fast and repeatable. Failure paths are tested as carefully as the happy path.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial test suite for config, cache, files, logs and timing.
# ==================================================================================================
# ========================================
# 📂 Imports
# ========================================
import hashlib
import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from mattslib import (
    ConfigError,
    Timer,
    atomic_write,
    chunked,
    file_hash,
    load_config,
    setup_logging,
    timed,
    ttl_cache,
)

# ========================================
# 📂 Config Tests
# ========================================


@dataclass(frozen=True)
class Settings:
    db_url: str
    port: int = 8000
    ratio: float = 0.5
    debug: bool = False
    hosts: list[str] = field(default_factory=list)


def test_config_loads_and_converts_types() -> None:
    env = {
        "APP_DB_URL": "pg://x",
        "APP_PORT": "9000",
        "APP_DEBUG": "yes",
        "APP_RATIO": "0.9",
        "APP_HOSTS": "a, b,",
    }
    s = load_config(Settings, prefix="APP_", env=env)
    assert s == Settings("pg://x", 9000, 0.9, True, ["a", "b"])


def test_config_reports_all_errors_together() -> None:
    with pytest.raises(ConfigError) as err:
        load_config(Settings, prefix="APP_", env={"APP_PORT": "abc", "APP_DEBUG": "maybe"})
    msg = str(err.value)
    assert "APP_DB_URL: required" in msg and "APP_PORT" in msg and "APP_DEBUG" in msg


def test_config_rejects_non_dataclass_and_unsupported_types() -> None:
    with pytest.raises(TypeError):
        load_config(dict, env={})

    @dataclass
    class Odd:
        value: dict[str, str]

    with pytest.raises(ConfigError, match="unsupported"):
        load_config(Odd, env={"VALUE": "x"})


def test_config_reads_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_URL", "pg://env")
    assert load_config(Settings).db_url == "pg://env"


# ========================================
# 📂 Cache Tests
# ========================================


def test_ttl_cache_hits_then_expires() -> None:
    now = [0.0]
    calls = []

    @ttl_cache(seconds=10, clock=lambda: now[0])
    def square(x: int) -> int:
        calls.append(x)
        return x * x

    assert square(3) == 9 and square(3) == 9
    assert calls == [3]
    now[0] = 11
    square(3)
    assert calls == [3, 3]
    square.cache_clear()
    assert len(square) == 0


def test_ttl_cache_evicts_least_recently_used() -> None:
    @ttl_cache(seconds=60, maxsize=2)
    def ident(x: int) -> int:
        return x

    ident(1)
    ident(2)
    ident(1)  # 1 is now most recent
    ident(3)  # evicts 2
    assert len(ident) == 2


def test_ttl_cache_validates_arguments() -> None:
    with pytest.raises(ValueError):
        ttl_cache(seconds=0)


# ========================================
# 📂 Files Tests
# ========================================


def test_atomic_write_and_hash(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "out.txt"
    atomic_write(target, "hello")
    assert target.read_text() == "hello"
    atomic_write(target, b"bytes")
    assert target.read_bytes() == b"bytes"
    assert file_hash(target) == hashlib.sha256(b"bytes").hexdigest()
    assert len(file_hash(target, algorithm="md5")) == 32
    assert list(tmp_path.glob("nested/*.tmp")) == []


def test_atomic_write_cleans_up_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("mattslib.files.os.replace", explode)
    with pytest.raises(OSError):
        atomic_write(tmp_path / "x.txt", "data")
    assert list(tmp_path.iterdir()) == []


def test_chunked() -> None:
    assert list(chunked(range(5), 2)) == [[0, 1], [2, 3], [4]]
    assert list(chunked([], 3)) == []
    with pytest.raises(ValueError):
        list(chunked([1], 0))


# ========================================
# 📂 Logging Tests
# ========================================


def test_json_logging_includes_extra_fields() -> None:
    buf = io.StringIO()
    setup_logging("info", stream=buf)
    logging.getLogger("svc").info("signed in", extra={"user_id": 7})
    try:
        raise RuntimeError("bad")
    except RuntimeError:
        logging.getLogger("svc").exception("failed")
    first, second = (json.loads(line) for line in buf.getvalue().splitlines())
    assert first["message"] == "signed in" and first["user_id"] == 7 and first["level"] == "INFO"
    assert "RuntimeError" in second["exception"]


def test_plain_text_logging() -> None:
    buf = io.StringIO()
    setup_logging(logging.WARNING, json_format=False, stream=buf)
    logging.getLogger("svc").warning("careful")
    assert "WARNING" in buf.getvalue() and "careful" in buf.getvalue()


# ========================================
# 📂 Timing Tests
# ========================================


def test_timer_measures_with_injected_clock() -> None:
    ticks = iter([1.0, 3.5])
    with Timer("work", clock=lambda: next(ticks)) as t:
        pass
    assert t.elapsed == 2.5


def test_timed_preserves_return_value_and_name() -> None:
    @timed
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert add.__name__ == "add"
