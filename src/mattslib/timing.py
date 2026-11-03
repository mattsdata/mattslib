# ==================================================================================================
# 📜 mattslib :: timing
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/timing.py
#  Author       : Mathew Varghese
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    "It feels slow" is not a performance report. Before optimising anything, measure it.
#    This module gives a one-line way to time a block of code or every call to a function.
#
#  🔧 WHAT IT DOES
#    - Timer  : context manager; records elapsed seconds in `.elapsed` and logs it at DEBUG.
#    - @timed : decorator that times each call to a function.
#
#  🧠 DESIGN NOTES
#    - time.perf_counter is the highest-resolution monotonic clock available; time.time()
#      can jump with system clock changes and is unsuitable for measuring durations.
#    - Timing is recorded even when the block raises: slow failures (timeouts) are often the
#      ones most worth measuring.
#    - Output goes to DEBUG, so instrumentation can stay in production code at zero noise
#      and be switched on by changing the log level.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the timing module.
#      - Added Timer context manager and @timed decorator.
#      - Durations logged at DEBUG and recorded even when the code raises.
# ==================================================================================================
"""Measure how long code takes, as a context manager or a decorator.

Example:
    >>> from mattslib.timing import Timer
    >>> with Timer("load data") as t:
    ...     total = sum(range(1000))
    >>> t.elapsed >= 0
    True
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from types import TracebackType
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

log = logging.getLogger(__name__)


# ========================================
# 📂 Timer (Context Manager)
# ========================================
class Timer:
    """Context manager that records elapsed seconds in ``.elapsed`` and logs it at DEBUG."""

    def __init__(self, label: str = "block", clock: Callable[[], float] = time.perf_counter):
        self.label = label
        self.elapsed = 0.0
        self._clock = clock  # injectable for deterministic tests
        self._start = 0.0

    def __enter__(self) -> Timer:
        self._start = self._clock()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Runs on success AND on exception; returning None lets any exception propagate.
        self.elapsed = self._clock() - self._start
        log.debug("%s took %.4fs", self.label, self.elapsed)


# ========================================
# 📂 Decorator
# ========================================
def timed(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs each call's duration at DEBUG, even when the call raises."""

    @functools.wraps(func)  # keeps __name__, __doc__ and signature for tools and tracebacks
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with Timer(func.__qualname__):
            return func(*args, **kwargs)

    return wrapper
