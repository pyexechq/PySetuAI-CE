"""Unit tests for daemon payload builders."""

from __future__ import annotations

import unittest

from pysetu_agent.daemon import file_event_payload
from pysetu_agent.scan import FileScanEvent


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


if __name__ == "__main__":
    unittest.main()
