"""Local directory scanning for context DLP.

Walks a directory tree, detects secrets/PII in text files, evaluates each
finding against the local policy, and returns events. No raw file contents
leave the endpoint.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable

from .detection import ScanResult, detect
from .policy import LocalPolicy, evaluate

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".idea", "dist", "build"}
MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 5000


@dataclass
class FileScanEvent:
    path: str
    classifications: list[str] = field(default_factory=list)
    decision: str = "allow"
    match_count: int = 0


def scan_file(path: str, policy: LocalPolicy, detector: Callable[[str], ScanResult] = detect) -> FileScanEvent | None:
    try:
        size = os.path.getsize(path)
        if size > MAX_FILE_BYTES or size == 0:
            return None
        with open(path, encoding="utf-8", errors="replace") as handle:
            content = handle.read()
    except (OSError, UnicodeError):
        return None

    result = detector(content)
    if not result.has_sensitive:
        return None

    return FileScanEvent(
        path=path,
        classifications=result.classifications,
        decision=evaluate(policy, path, result.classifications),
        match_count=result.match_count,
    )


def scan_directory(
    root: str,
    policy: LocalPolicy,
    detector: Callable[[str], ScanResult] = detect,
    *,
    max_files: int = MAX_FILES,
) -> list[FileScanEvent]:
    events: list[FileScanEvent] = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for filename in filenames:
            if scanned >= max_files:
                return events
            scanned += 1
            event = scan_file(os.path.join(dirpath, filename), policy, detector)
            if event is not None:
                events.append(event)
    return events
