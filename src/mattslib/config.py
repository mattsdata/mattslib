# ==================================================================================================
# 📜 mattslib :: config
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/config.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Configuration errors are among the most common causes of failed deployments. A missing
#    variable or a typo like PORT="80OO" should stop the service at start-up with a clear
#    message, not cause a confusing failure hours later. This module loads settings from
#    environment variables into a typed dataclass and fails fast when anything is wrong.
#
#  🔧 WHAT IT DOES
#    - load_config : builds a dataclass from env vars named PREFIX + FIELD_NAME (upper case),
#                    converting each value to the field's declared type.
#    - ConfigError : raised with a list of every problem found.
#
#  SUPPORTED TYPES
#    str, int, float, bool (1/0, true/false, yes/no, on/off) and list[...] (comma-separated).
#
#  🧠 DESIGN NOTES
#    - All errors are collected and reported together. Fixing one variable per redeploy is
#      slow and frustrating; one message listing everything is kinder to whoever is on call.
#    - Booleans are parsed strictly. bool("false") is True in Python, a well-known trap,
#      so unknown spellings are rejected instead of guessed.
#    - `env` can be passed in, so tests never touch or depend on the real os.environ.
#    - Deliberately small. For nested models or complex validation use pydantic-settings
#      (see docs/adr/0001-zero-runtime-dependencies.md).
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the config module.
#      - Added load_config: typed settings from env vars (str, int, float, bool, list).
#      - All configuration errors reported together via ConfigError.
# ==================================================================================================
"""Load typed settings from environment variables into a dataclass, failing fast on bad config.

Example:
    >>> from dataclasses import dataclass
    >>> from mattslib.config import load_config
    >>> @dataclass(frozen=True)
    ... class Settings:
    ...     db_url: str
    ...     port: int = 8000
    ...     debug: bool = False
    >>> s = load_config(Settings, prefix="APP_", env={"APP_DB_URL": "postgres://x"})
    >>> s.port
    8000
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import dataclasses
import os
import typing
from collections.abc import Mapping
from typing import Any, TypeVar

# ========================================
# 📂 Types & Constants
# ========================================
T = TypeVar("T")

# Explicit allow-lists: anything else is an error rather than a silent guess.
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}


# ========================================
# 📂 Errors
# ========================================
class ConfigError(ValueError):
    """Raised when required settings are missing or cannot be converted."""


# ========================================
# 📂 Type Conversion
# ========================================
def _convert(raw: str, target: Any, name: str) -> Any:
    """Convert one raw environment string to ``target`` type, or raise ConfigError."""
    if target is bool:
        value = raw.strip().lower()
        if value in _TRUE:
            return True
        if value in _FALSE:
            return False
        raise ConfigError(f"{name}: expected a boolean, got {raw!r}")
    if target in (int, float, str):
        try:
            return target(raw)
        except ValueError as exc:
            raise ConfigError(f"{name}: expected {target.__name__}, got {raw!r}") from exc
    if typing.get_origin(target) is list:
        # "a, b,,c" -> ["a", "b", "c"]: tolerate spaces and trailing commas from hand-edited files.
        (item_type,) = typing.get_args(target) or (str,)
        return [_convert(part.strip(), item_type, name) for part in raw.split(",") if part.strip()]
    raise ConfigError(f"{name}: unsupported type {target!r}")


# ========================================
# 📂 Public API
# ========================================
def load_config(cls: type[T], *, prefix: str = "", env: Mapping[str, str] | None = None) -> T:
    """Build ``cls`` from environment variables named ``PREFIX + FIELD_NAME.upper()``.

    Supports ``str``, ``int``, ``float``, ``bool`` and ``list[...]`` (comma-separated).
    All problems are collected and reported together, so a deployment fails once, clearly.
    """
    if not dataclasses.is_dataclass(cls):
        raise TypeError("load_config expects a dataclass type")
    source = os.environ if env is None else env
    # get_type_hints resolves string annotations created by `from __future__ import annotations`.
    hints = typing.get_type_hints(cls)
    values: dict[str, Any] = {}
    errors: list[str] = []

    for field in dataclasses.fields(cls):
        var = f"{prefix}{field.name}".upper()
        if var in source:
            try:
                values[field.name] = _convert(source[var], hints[field.name], var)
            except ConfigError as exc:
                errors.append(str(exc))  # keep going: report everything in one pass
        elif field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            errors.append(f"{var}: required but not set")
        # Otherwise the field has a default and the dataclass applies it.

    if errors:
        raise ConfigError("Invalid configuration:\n  " + "\n  ".join(errors))
    return cls(**values)
