"""Unit tests for the shell-command interception wrapper."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
from pathlib import Path

from pysetu_agent.policy import LocalPolicy
from pysetu_agent.wrapper import WRAPPER_ACTIVE_ENV, decide, install_shim, main, resolve_real_binary


class DecideTest(unittest.TestCase):
    def test_blocks_destructive_shell_command(self) -> None:
        decision = decide(["claude", "rm", "-rf", "/"], None, LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_blocks_secret_in_argv(self) -> None:
        decision = decide(["claude", "echo", "AKIAIOSFODNN7EXAMPLE"], None, LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_blocks_secret_in_argv_even_when_policy_would_redact(self) -> None:
        # argv cannot be safely rewritten, so it is blocked regardless.
        decision = decide(["claude", "echo", "john@example.com"], None, LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_redacts_pii_in_piped_stdin(self) -> None:
        decision = decide(["claude", "summarize"], "Contact john@example.com\n", LocalPolicy.defaults())
        self.assertEqual(decision.action, "redact")
        self.assertIsNotNone(decision.redacted_stdin)
        self.assertNotIn("john@example.com", decision.redacted_stdin)

    def test_blocks_secret_in_piped_stdin(self) -> None:
        decision = decide(["claude", "run"], "API_KEY=AKIAIOSFODNN7EXAMPLE\n", LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_allows_clean_argv_and_stdin(self) -> None:
        decision = decide(["claude", "help"], "just some text\n", LocalPolicy.defaults())
        self.assertEqual(decision.action, "allow")


class ResolveRealBinaryTest(unittest.TestCase):
    def test_skips_shim_dir(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shim_dir = Path(directory, "shim")
            real_dir = Path(directory, "real")
            shim_dir.mkdir()
            real_dir.mkdir()
            Path(shim_dir, "claude").write_text("#!/bin/sh\n", encoding="utf-8")
            Path(shim_dir, "claude").chmod(0o755)
            Path(real_dir, "claude").write_text("#!/bin/sh\n", encoding="utf-8")
            Path(real_dir, "claude").chmod(0o755)
            path_entries = [str(shim_dir), str(real_dir)]
            resolved = resolve_real_binary("claude", str(shim_dir), path_entries)
            self.assertEqual(resolved, str(Path(real_dir, "claude")))


class MainTest(unittest.TestCase):
    def _fake_runner(self, calls):
        def runner(real, argv, stdin_text, env):
            calls.append((real, argv, stdin_text, env))
            return 0

        return runner

    def test_block_returns_1_and_never_runs(self) -> None:
        calls = []
        code = main(
            ["claude", "rm", "-rf", "/"],
            stdin=io.StringIO(""),
            stderr=io.StringIO(),
            env={"PATH": "/usr/bin"},
            shim_dir="/tmp/shim",
            runner=self._fake_runner(calls),
        )
        self.assertEqual(code, 1)
        self.assertEqual(calls, [])

    def test_redact_runs_with_redacted_stdin_and_marker(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            real_dir = Path(directory, "real")
            real_dir.mkdir()
            Path(real_dir, "claude").write_text("#!/bin/sh\n", encoding="utf-8")
            Path(real_dir, "claude").chmod(0o755)
            env = {"PATH": str(real_dir)}
            code = main(
                ["claude", "summarize"],
                stdin=io.StringIO("Contact john@example.com\n"),
                stderr=io.StringIO(),
                env=env,
                shim_dir="/tmp/shim",
                runner=self._fake_runner(calls),
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            real, argv, stdin_text, child_env = calls[0]
            self.assertEqual(real, str(Path(real_dir, "claude")))
            self.assertNotIn("john@example.com", stdin_text)
            self.assertEqual(child_env.get(WRAPPER_ACTIVE_ENV), "1")

    def test_marker_set_passes_through_without_scanning(self) -> None:
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            real_dir = Path(directory, "real")
            real_dir.mkdir()
            Path(real_dir, "claude").write_text("#!/bin/sh\n", encoding="utf-8")
            Path(real_dir, "claude").chmod(0o755)
            env = {"PATH": str(real_dir), WRAPPER_ACTIVE_ENV: "1"}
            code = main(
                ["claude", "echo", "AKIAIOSFODNN7EXAMPLE"],
                stdin=io.StringIO(""),
                stderr=io.StringIO(),
                env=env,
                shim_dir="/tmp/shim",
                runner=self._fake_runner(calls),
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            # Pass-through: stdin is None (not scanned/redacted).
            self.assertIsNone(calls[0][2])


class InstallShimTest(unittest.TestCase):
    def test_installs_executable_shims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            created = install_shim(directory, package_dir="/pkg")
            self.assertEqual(len(created), 3)
            for path in created:
                self.assertTrue(os.path.exists(path))
                self.assertTrue(os.access(path, os.X_OK))
                content = Path(path).read_text(encoding="utf-8")
                self.assertIn("from pysetu_agent.wrapper import main", content)


if __name__ == "__main__":
    unittest.main()
