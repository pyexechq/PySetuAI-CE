"""Unit tests for the polling file watcher."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from pysetu_agent.policy import LocalPolicy
from pysetu_agent.watcher import diff_snapshots, scan_changes, snapshot


class SnapshotTest(unittest.TestCase):
    def test_diff_detects_new_and_modified_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            before = snapshot(directory)

            (root / "b.txt").write_text("world", encoding="utf-8")
            time.sleep(0.01)
            (root / "a.txt").write_text("hello again", encoding="utf-8")

            after = snapshot(directory)
            changed = sorted(diff_snapshots(before, after))
            self.assertEqual(len(changed), 2)

    def test_unchanged_files_are_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("hello", encoding="utf-8")
            before = snapshot(directory)
            after = snapshot(directory)
            self.assertEqual(diff_snapshots(before, after), [])

    def test_scan_changes_finds_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, ".env")
            path.write_text("API_KEY=AKIAIOSFODNN7EXAMPLE", encoding="utf-8")
            events = scan_changes([str(path)], LocalPolicy.defaults())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].decision, "block")


if __name__ == "__main__":
    unittest.main()
