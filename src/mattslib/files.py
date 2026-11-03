# ==================================================================================================
# 📜 mattslib :: files
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/files.py
#  Author       : Mathew Varghese
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Small file and data-handling helpers that prevent real production incidents: config files
#    left half-written after a crash, out-of-memory errors when hashing large files, and
#    overloaded APIs when thousands of records are sent at once.
#
#  🔧 WHAT IT DOES
#    - atomic_write : writes a file so readers see the old version or the new one, never half.
#    - file_hash    : checksums a file of any size using constant memory.
#    - chunked      : splits any iterable into fixed-size batches.
#
#  🧠 DESIGN NOTES
#    - atomic_write uses the write-temp, fsync, rename pattern. The temp file is created in
#      the SAME directory as the target because a rename is only atomic within one filesystem.
#    - fsync before rename: without it a power cut can leave a renamed but empty file.
#    - On any failure the temp file is removed, so no stray *.tmp files accumulate.
#    - chunked consumes its input lazily, so it works on generators and database cursors
#      without loading everything into memory.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the files module.
#      - Added atomic_write (temp file + fsync + atomic rename).
#      - Added file_hash (constant memory) and chunked (lazy batching).
# ==================================================================================================
"""Safe file helpers: crash-proof writes, chunked hashing and batching large inputs.

Example:
    >>> from mattslib.files import chunked
    >>> list(chunked(range(5), 2))
    [[0, 1], [2, 3], [4]]
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import TypeVar

# ========================================
# 📂 Types & Constants
# ========================================
T = TypeVar("T")

_ONE_MIB = 1 << 20  # read size for hashing: large enough to be fast, small enough to be cheap


# ========================================
# 📂 Atomic Write
# ========================================
def atomic_write(path: str | Path, data: str | bytes, *, encoding: str = "utf-8") -> None:
    """Write ``data`` to ``path`` so readers see either the old file or the new one, never half.

    Writes to a temporary file in the same directory, flushes it to disk, then renames it
    over the target (``os.replace`` is atomic on POSIX and Windows).
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = data.encode(encoding) if isinstance(data, str) else data
    # Same directory as the target -> same filesystem -> the final rename is atomic.
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())  # force bytes to disk before the rename makes them visible
        os.replace(tmp, target)  # atomic swap; overwrites an existing file on every platform
    except BaseException:
        # BaseException also covers Ctrl+C: never leave a half-written temp file behind.
        Path(tmp).unlink(missing_ok=True)
        raise


# ========================================
# 📂 File Hash
# ========================================
def file_hash(path: str | Path, *, algorithm: str = "sha256", chunk_size: int = _ONE_MIB) -> str:
    """Return the hex digest of a file, reading it in chunks so memory use stays flat."""
    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as fh:
        # Walrus loop: read until an empty bytes object signals end of file.
        while block := fh.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()


# ========================================
# 📂 Batching
# ========================================
def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield lists of up to ``size`` items — handy for batched API calls or DB inserts."""
    if size < 1:
        raise ValueError("size must be >= 1")
    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []  # new list, so callers can safely keep the previous batch
    if batch:
        yield batch  # final partial batch
