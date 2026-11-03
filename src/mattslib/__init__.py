# ==================================================================================================
# 📜 mattslib
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/__init__.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.1
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Package entry point for mattslib, my personal library of reusable, production-grade
#    Python utilities. Every module solves a problem I have met repeatedly across projects,
#    built once to a consistent standard and reused everywhere.
#
#  🔧 WHAT IT DOES
#    Re-exports the public API so users can write `from mattslib import retry` without knowing
#    the internal module layout. That layout can then change without breaking anyone.
#
#  MODULES
#    retry   - retries with exponential backoff and jitter (sync and async)
#    logs    - structured JSON logging in one call
#    config  - typed settings from environment variables, failing fast
#    cache   - in-memory cache with expiry (TTL) and size limit
#    timing  - measure how long code takes
#    files   - atomic writes, file hashing, batching
#    registry - typed plugin registry with lazily imported built-ins
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of mattslib with six core modules.
#      - Public API re-exported from the package root.
#
#    V1.1 (2026-11-03) - Mathew Varghese
#      - Added Registry (plugin registry), extracted from AI Lab's vision package.
# ==================================================================================================
"""mattslib: reusable, well-tested Python utilities with zero runtime dependencies."""

# ========================================
# 📂 Imports
# ========================================
from mattslib.cache import ttl_cache
from mattslib.config import ConfigError, load_config
from mattslib.files import atomic_write, chunked, file_hash
from mattslib.logs import JsonFormatter, setup_logging
from mattslib.registry import Registry
from mattslib.retry import async_retry, retry
from mattslib.timing import Timer, timed

# ========================================
# 📂 Package Metadata
# ========================================
__version__ = "1.1.0"
__author__ = "Mathew Varghese"

# ========================================
# 📂 Public API
# ========================================
# The public API: anything not listed here is internal and may change without notice.
__all__ = [
    "ConfigError",
    "JsonFormatter",
    "Registry",
    "Timer",
    "async_retry",
    "atomic_write",
    "chunked",
    "file_hash",
    "load_config",
    "retry",
    "setup_logging",
    "timed",
    "ttl_cache",
]
