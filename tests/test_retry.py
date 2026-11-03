# ==================================================================================================
# 📜 mattslib :: tests :: retry
# --------------------------------------------------------------------------------------------------
#  File         : tests/test_retry.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Proves that mattslib.retry recovers from transient failures and gives up correctly.
#
#  🔧 WHAT IT DOES
#    - Success after transient failures, with the exact exponential wait sequence.
#    - Re-raising the original exception after the final attempt.
#    - Never retrying exceptions that were not listed (bugs must not be retried).
#    - Backoff cap, jitter range, argument validation and the async variant.
#
#  🧠 TESTING APPROACH
#    `sleep` is injected (a list.append or a no-op), so no test ever actually waits.
#    The whole suite runs in milliseconds and is fully deterministic.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial test suite for mattslib.retry (sync and async).
# ==================================================================================================
# ========================================
# 📂 Imports
# ========================================
import asyncio

import pytest

from mattslib.retry import async_retry, backoff_delay, retry


# ========================================
# 📂 Sync Retry Tests
# ========================================
def test_succeeds_after_transient_failures() -> None:
    calls, waits = [], []

    @retry(attempts=3, exceptions=(ConnectionError,), jitter=False, sleep=waits.append)
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("boom")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3
    assert waits == [0.5, 1.0]  # exponential backoff


def test_reraises_after_last_attempt() -> None:
    @retry(attempts=2, sleep=lambda _: None)
    def always_fails() -> None:
        raise TimeoutError("nope")

    with pytest.raises(TimeoutError):
        always_fails()


def test_does_not_retry_unlisted_exceptions() -> None:
    calls = []

    @retry(attempts=5, exceptions=(ConnectionError,), sleep=lambda _: None)
    def bad_input() -> None:
        calls.append(1)
        raise ValueError("not transient")

    with pytest.raises(ValueError):
        bad_input()
    assert len(calls) == 1


def test_backoff_is_capped_and_jitter_stays_in_range() -> None:
    assert backoff_delay(10, base=1, cap=5, jitter=False) == 5
    assert 0 <= backoff_delay(3, base=1, cap=30, jitter=True) <= 4


@pytest.mark.parametrize("factory", [retry, async_retry])
def test_rejects_zero_attempts(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        factory(attempts=0)


# ========================================
# 📂 Async Retry Tests
# ========================================
def test_async_retry() -> None:
    calls = []

    @async_retry(attempts=3, base_delay=0, jitter=False)
    async def flaky() -> int:
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError
        return 42

    assert asyncio.run(flaky()) == 42


def test_async_retry_reraises() -> None:
    @async_retry(attempts=2, base_delay=0)
    async def broken() -> None:
        raise ConnectionError

    with pytest.raises(ConnectionError):
        asyncio.run(broken())
