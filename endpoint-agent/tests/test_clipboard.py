"""Unit tests for the clipboard DLP monitor."""

from __future__ import annotations

import unittest

from pysetu_agent.clipboard import decide_clipboard, monitor_clipboard
from pysetu_agent.policy import LocalPolicy


class DecideClipboardTest(unittest.TestCase):
    def test_allows_clean_text(self) -> None:
        decision = decide_clipboard("just some text", LocalPolicy.defaults())
        self.assertEqual(decision.action, "allow")

    def test_redacts_pii(self) -> None:
        decision = decide_clipboard("Email john@example.com", LocalPolicy.defaults())
        self.assertEqual(decision.action, "redact")
        self.assertIsNotNone(decision.redacted)
        self.assertNotIn("john@example.com", decision.redacted)

    def test_blocks_secret(self) -> None:
        decision = decide_clipboard("AKIAIOSFODNN7EXAMPLE", LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")


class MonitorClipboardTest(unittest.TestCase):
    def _stop_after(self, n):
        count = {"n": 0}

        def stop():
            count["n"] += 1
            return count["n"] > n

        return stop

    def _changing_read(self, state, sequence):
        index = {"i": 0}

        def read():
            value = sequence[min(index["i"], len(sequence) - 1)]
            index["i"] += 1
            state["clip"] = value
            return value

        return read

    def test_redacts_on_change_and_calls_event(self) -> None:
        state = {"clip": "clean"}
        events = []

        def write(text):
            state["clip"] = text

        monitor_clipboard(
            LocalPolicy.defaults(),
            read=self._changing_read(state, ["clean", "Email john@example.com"]),
            write=write,
            on_event=events.append,
            poll_interval=0,
            stop=self._stop_after(1),
        )
        self.assertNotIn("john@example.com", state["clip"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].action, "redact")

    def test_clears_on_block(self) -> None:
        state = {"clip": "clean"}
        events = []

        def write(text):
            state["clip"] = text

        monitor_clipboard(
            LocalPolicy.defaults(),
            read=self._changing_read(state, ["clean", "AKIAIOSFODNN7EXAMPLE"]),
            write=write,
            on_event=events.append,
            poll_interval=0,
            stop=self._stop_after(1),
        )
        self.assertEqual(state["clip"], "")
        self.assertEqual(events[0].action, "block")

    def test_does_not_rewrite_unchanged_clipboard(self) -> None:
        state = {"clip": "clean text"}
        writes = []

        def write(text):
            writes.append(text)
            state["clip"] = text

        monitor_clipboard(
            LocalPolicy.defaults(),
            read=self._changing_read(state, ["clean text", "clean text"]),
            write=write,
            poll_interval=0,
            stop=self._stop_after(1),
        )
        self.assertEqual(writes, [])


if __name__ == "__main__":
    unittest.main()
