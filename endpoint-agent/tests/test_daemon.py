"""Unit tests for daemon payload builders and CLI wiring."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from pysetu_agent.daemon import file_event_payload, main
from pysetu_agent.scan import FileScanEvent


def _set_env(**kwargs):
    previous = {key: os.environ.get(key) for key in kwargs}
    for key, value in kwargs.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    return previous


def _restore_env(previous):
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class FileEventPayloadTest(unittest.TestCase):
    def test_maps_event_to_ingest_payload(self) -> None:
        event = FileScanEvent(path="/repo/.env", classifications=["GENERIC_SECRET"], decision="block", match_count=1)
        payload = file_event_payload("ep-1", event)
        self.assertEqual(payload["endpoint_id"], "ep-1")
        self.assertEqual(payload["decision"], "blocked")
        self.assertEqual(payload["risk_score"], 90)
        self.assertEqual(payload["classification"], ["GENERIC_SECRET"])
        self.assertEqual(payload["metadata"], {"match_count": 1})

    def test_redact_decision_maps_risk(self) -> None:
        event = FileScanEvent(path="/repo/data.sql", classifications=["SSN"], decision="redact", match_count=3)
        payload = file_event_payload("ep-1", event)
        self.assertEqual(payload["decision"], "redacted")
        self.assertEqual(payload["risk_score"], 50)


class CliWiringTest(unittest.TestCase):
    def test_wrap_shell_installs_shims(self) -> None:
        previous = _set_env(PYSETU_API_KEY="k", PYSETU_HOSTNAME="h")
        try:
            with tempfile.TemporaryDirectory() as directory:
                code = main(["--wrap-shell", "--wrap-shell-dir", directory])
                self.assertEqual(code, 0)
                for binary in ("claude", "cursor", "code"):
                    self.assertTrue(Path(directory, binary).exists())
        finally:
            _restore_env(previous)

    def test_scan_enforce_flag_parses(self) -> None:
        previous = _set_env(
            PYSETU_API_KEY="k",
            PYSETU_HOSTNAME="h",
            PYSETU_BACKEND_URL="http://127.0.0.1:1",
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                # Control plane unreachable -> returns 1, but the --enforce flag parses
                # and reaches the scan path without a CLI error.
                code = main(
                    ["--scan-dir", directory, "--enforce", "--quarantine-dir", str(Path(directory, "q"))]
                )
                self.assertEqual(code, 1)
        finally:
            _restore_env(previous)


if __name__ == "__main__":
    unittest.main()
