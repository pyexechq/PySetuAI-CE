"""Unit tests for real file redaction and quarantine enforcement."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pysetu_agent.enforce import _atomic_write, enforce_file, quarantine_file
from pysetu_agent.policy import LocalPolicy
from pysetu_agent.scan import scan_directory


class EnforceFileTest(unittest.TestCase):
    def test_redacts_pii_file_and_writes_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "notes.txt")
            path.write_text("Contact me at john@example.com\n", encoding="utf-8")
            result = enforce_file(str(path), LocalPolicy.defaults())
            self.assertIsNotNone(result)
            self.assertEqual(result.action_taken, "redacted")
            self.assertNotIn("john@example.com", path.read_text(encoding="utf-8"))
            self.assertIn("[REDACTED]", path.read_text(encoding="utf-8"))
            backup = Path(str(path) + ".pysetu.bak")
            self.assertTrue(backup.exists())
            self.assertIn("john@example.com", backup.read_text(encoding="utf-8"))

    def test_quarantines_blocked_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "src")
            source.mkdir()
            path = Path(source, ".env")
            path.write_text("API_KEY=AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")
            quarantine = Path(directory, "quarantine")
            result = enforce_file(str(path), LocalPolicy.defaults(), quarantine_dir=str(quarantine))
            self.assertIsNotNone(result)
            self.assertEqual(result.action_taken, "quarantined")
            self.assertFalse(path.exists())
            self.assertTrue(Path(quarantine, ".env").exists())

    def test_returns_none_for_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "clean.txt")
            path.write_text("just some text\n", encoding="utf-8")
            self.assertIsNone(enforce_file(str(path), LocalPolicy.defaults()))

    def test_allow_decision_takes_no_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory, "src")
            src.mkdir()
            path = Path(src, "app.py")
            path.write_text("token = 'AKIAIOSFODNN7EXAMPLE'\n", encoding="utf-8")
            result = enforce_file(str(path), LocalPolicy.defaults())
            self.assertIsNotNone(result)
            self.assertEqual(result.action_taken, "none")
            self.assertIn("AKIAIOSFODNN7EXAMPLE", path.read_text(encoding="utf-8"))

    def test_atomic_write_leaves_no_temp_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "target.txt")
            _atomic_write(str(path), "new content")
            self.assertEqual(path.read_text(encoding="utf-8"), "new content")
            leftovers = [name for name in os.listdir(directory) if name.startswith(".pysetu-")]
            self.assertEqual(leftovers, [])

    def test_quarantine_file_dedupes_on_collision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory, "src")
            source.mkdir()
            quarantine = Path(directory, "quarantine")
            quarantine.mkdir()
            Path(quarantine, "secret.txt").write_text("existing", encoding="utf-8")
            path = Path(source, "secret.txt")
            path.write_text("new", encoding="utf-8")
            target = quarantine_file(str(path), str(quarantine))
            self.assertTrue(os.path.exists(target))
            self.assertNotEqual(target, str(Path(quarantine, "secret.txt")))

    def test_scan_directory_enforce_redacts_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory, "notes.txt")
            target.write_text("Email john@example.com\n", encoding="utf-8")
            events = scan_directory(directory, LocalPolicy.defaults(), enforce=True)
            self.assertEqual(len(events), 1)
            self.assertNotIn("john@example.com", target.read_text(encoding="utf-8"))
            self.assertTrue(Path(str(target) + ".pysetu.bak").exists())


if __name__ == "__main__":
    unittest.main()
