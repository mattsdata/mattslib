# ==================================================================================================
# 📜 mattslib :: logs
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/logs.py
#  Author       : Mathew Varghese
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Plain-text logs are fine on a laptop but painful in production, where logs are searched in
#    ELK, Loki, Splunk or CloudWatch. This module sets up structured JSON logging in one call,
#    so every service I build emits logs that can be filtered by field, not by grep.
#
#  🔧 WHAT IT DOES
#    - JsonFormatter : turns each log record into one JSON line (timestamp, level, logger,
#                      message, exception, plus any fields passed via `extra=`).
#    - setup_logging : configures the root logger once, in JSON or human-readable text.
#
#  🧠 DESIGN NOTES
#    - Uses the standard `logging` module, so existing third-party loggers are captured too.
#    - Timestamps are ISO-8601 in UTC: servers in different regions produce comparable logs.
#    - Context goes in `extra={"order_id": 42}` rather than inside the message string, which
#      makes it a searchable field instead of free text.
#    - setup_logging replaces handlers rather than adding them, so calling it twice never
#      produces duplicate log lines (a classic bug in long-running apps and notebooks).
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the logging module.
#      - Added JsonFormatter: one JSON line per record, including `extra=` fields.
#      - Added setup_logging: JSON or plain text; safe to call more than once.
# ==================================================================================================
"""One-call structured (JSON) logging, ready for log aggregators like ELK, Loki or CloudWatch.

Example:
    >>> from mattslib.logs import setup_logging
    >>> import logging
    >>> setup_logging(level="INFO", json_format=True)
    >>> logging.getLogger("app").info("user signed in", extra={"user_id": 42})
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, TextIO

# ========================================
# 📂 Constants
# ========================================
# Every LogRecord carries these attributes. Anything else on a record arrived via `extra=`,
# which is exactly the custom context we want to emit as JSON fields.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


# ========================================
# 📂 JSON Formatter
# ========================================
class JsonFormatter(logging.Formatter):
    """Format each record as a single JSON line, including any ``extra=`` fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Promote caller-supplied context (user_id, request_id ...) to top-level fields.
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # default=str: an unexpected object (datetime, UUID, Decimal) must never crash logging.
        return json.dumps(payload, default=str)


# ========================================
# 📂 Logger Setup
# ========================================
def setup_logging(
    level: str | int = "INFO",
    *,
    json_format: bool = True,
    stream: TextIO | None = None,
) -> None:
    """Configure the root logger once. Safe to call again: existing handlers are replaced."""
    # stderr by default: keeps stdout clean for program output and follows 12-factor practice.
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(
        JsonFormatter()
        if json_format
        else logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    # Replace, don't append: prevents duplicated lines when this is called more than once.
    root.handlers[:] = [handler]
    root.setLevel(level.upper() if isinstance(level, str) else level)
