"""Unit tests for the local directory scanner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pysetu_agent.policy import LocalPolicy
from pysetu_agent.scan import scan_directory, scan_file


class ScanDirectoryTest(unittest.TestCase):
    def test_finds_secret_in_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text("API_KEY=AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")
            Path(directory, "app.py").write_text("print('ok')\n", encoding="utf-8")
            events = scan_directory(directory, LocalPolicy.defaults())
            self.assertEqual(len(events), 1)
            self.assertIn("AWS_ACCESS_KEY", events[0].classifications)
            self.assertEqual(events[0].decision, "block")

    def test_skips_clean_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "readme.md").write_text("hello", encoding="utf-8")
            events = scan_directory(directory, LocalPolicy.defaults())
            self.assertEqual(events, [])

    def test_skips_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            git_dir = Path(directory, ".git")
            git_dir.mkdir()
            Path(git_dir, "config").write_text("token=secretvalue123", encoding="utf-8")
            events = scan_directory(directory, LocalPolicy.defaults())
            self.assertEqual(events, [])

    def test_scan_file_returns_none_for_binary_or_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory, "empty.txt")
            empty.write_bytes(b"")
            self.assertIsNone(scan_file(str(empty), LocalPolicy.defaults()))


if __name__ == "__main__":
    unittest.main()
