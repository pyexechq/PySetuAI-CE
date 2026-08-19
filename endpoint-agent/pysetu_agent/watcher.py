"""Portable polling file watcher for the endpoint agent.

Takes periodic directory snapshots, diffs them to find created/modified files,
scans changed files with the local detector, and emits events for findings.

Native FSEvents/inotify integration is a future per-OS enhancement; this polling
watcher is standard-library-only and works on macOS, Windows, and Linux.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

from .detection import ScanResult, detect
from .policy import LocalPolicy
from .scan import SKIP_DIRS, FileScanEvent, scan_file

# path -> (st_mtime_ns, st_size)
Snapshot = dict[str, tuple[int, int]]


def snapshot(root: str) -> Snapshot:
    result: Snapshot = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                stat = os.stat(path)
                result[path] = (stat.st_mtime_ns, stat.st_size)
            except OSError:
                continue
    return result


def diff_snapshots(before: Snapshot, after: Snapshot) -> list[str]:
    """Return paths that are new or whose (mtime, size) signature changed."""
    changed = []
    for path, signature in after.items():
        if before.get(path) != signature:
            changed.append(path)
    return changed


def scan_changes(
    paths: list[str],
    policy: LocalPolicy,
    detector: Callable[[str], ScanResult] = detect,
    *,
    enforce: bool = False,
    quarantine_dir: str | None = None,
) -> list[FileScanEvent]:
    events: list[FileScanEvent] = []
    for path in paths:
        event = scan_file(path, policy, detector)
        if event is not None:
            if enforce:
                from .enforce import enforce_file

                enforce_file(path, policy, detector, quarantine_dir=quarantine_dir)
            events.append(event)
    return events


def watch_directory(
    root: str,
    policy: LocalPolicy,
    on_events: Callable[[list[FileScanEvent]], None],
    detector: Callable[[str], ScanResult] = detect,
    *,
    poll_interval: float = 2.0,
    stop: Callable[[], bool] | None = None,
    enforce: bool = False,
    quarantine_dir: str | None = None,
) -> None:
    """Poll ``root`` until ``stop()`` returns True, invoking ``on_events`` for findings."""
    current = snapshot(root)
    while True:
        if stop is not None and stop():
            return
        time.sleep(poll_interval)
        previous = current
        current = snapshot(root)
        changed = diff_snapshots(previous, current)
        if changed:
            events = scan_changes(changed, policy, detector, enforce=enforce, quarantine_dir=quarantine_dir)
            if events:
                on_events(events)
