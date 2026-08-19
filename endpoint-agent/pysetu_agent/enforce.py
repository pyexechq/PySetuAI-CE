"""Real enforcement for the endpoint agent: file redaction and quarantine.

Turns policy decisions into actual on-disk actions. A file flagged ``redact``
is rewritten with the redacted content (a ``*.pysetu.bak`` backup is kept); a
file flagged ``block`` is moved to a quarantine directory. All writes are
atomic (temp file + ``os.replace``) so a crash never leaves a partial file.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Callable

from .detection import ScanResult, detect
from .policy import LocalPolicy, evaluate

DEFAULT_QUARANTINE_DIR = os.path.join(os.path.expanduser("~"), ".pysetu", "quarantine")
BACKUP_SUFFIX = ".pysetu.bak"


@dataclass
class EnforceResult:
    path: str
    decision: str
    action_taken: str
    backup_path: str | None = None
    match_count: int = 0


def _atomic_write(path: str, content: str) -> None:
    """Write ``content`` to ``path`` atomically (temp file + os.replace)."""
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".pysetu-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def quarantine_file(path: str, quarantine_dir: str = DEFAULT_QUARANTINE_DIR) -> str:
    """Move ``path`` into ``quarantine_dir``, deduping on name collision."""
    os.makedirs(quarantine_dir, exist_ok=True)
    base = os.path.basename(path)
    target = os.path.join(quarantine_dir, base)
    if os.path.exists(target):
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
        target = os.path.join(quarantine_dir, f"{base}.{stamp}")
    shutil.move(path, target)
    return target


def enforce_file(
    path: str,
    policy: LocalPolicy,
    detector: Callable[[str], ScanResult] = detect,
    *,
    backup_suffix: str = BACKUP_SUFFIX,
    quarantine_dir: str = DEFAULT_QUARANTINE_DIR,
) -> EnforceResult | None:
    """Apply the policy decision to a single file. Returns None if no findings."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except (OSError, UnicodeError):
        return None

    result = detector(content)
    if not result.has_sensitive:
        return None

    decision = evaluate(policy, path, result.classifications)
    if decision == "redact" and result.redacted_content is not None:
        backup_path = path + backup_suffix
        shutil.copy2(path, backup_path)
        _atomic_write(path, result.redacted_content)
        return EnforceResult(
            path=path,
            decision=decision,
            action_taken="redacted",
            backup_path=backup_path,
            match_count=result.match_count,
        )

    if decision == "block":
        target = quarantine_file(path, quarantine_dir)
        return EnforceResult(
            path=path,
            decision=decision,
            action_taken="quarantined",
            backup_path=target,
            match_count=result.match_count,
        )

    return EnforceResult(
        path=path,
        decision=decision,
        action_taken="none",
        match_count=result.match_count,
    )
