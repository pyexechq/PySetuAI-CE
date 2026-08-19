"""Shell-command interception wrapper (PATH shim) for the endpoint agent.

Wraps AI tool binaries (``claude``, ``cursor``, ``code``) so that every
invocation is scanned for secrets/PII before the real binary runs. Piped stdin
can be redacted in place; sensitive data in argv is blocked (argv cannot be
safely rewritten). Recursion is prevented two ways: the shim directory is
excluded when resolving the real binary, and a ``PYSETU_WRAPPER_ACTIVE`` marker
env var forces a pass-through if the wrapper is ever re-entered.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable

from .detection import ScanResult, detect
from .policy import LocalPolicy
from .shell import ShellDecision, classify_command

WRAPPER_ACTIVE_ENV = "PYSETU_WRAPPER_ACTIVE"
WRAPPED_BINARIES = ("claude", "cursor", "code")


@dataclass(frozen=True)
class WrapperDecision:
    action: str  # "block" | "redact" | "allow"
    reason: str
    redacted_stdin: str | None = None
    classifications: list[str] = field(default_factory=list)


def resolve_real_binary(
    name: str,
    shim_dir: str,
    path_entries: list[str] | None = None,
) -> str | None:
    """Find the real ``name`` on PATH, skipping the shim directory."""
    path_entries = path_entries if path_entries is not None else os.environ.get("PATH", "").split(os.pathsep)
    shim_real = os.path.realpath(shim_dir)
    for entry in path_entries:
        if not entry:
            continue
        if os.path.realpath(entry) == shim_real:
            continue
        candidate = os.path.join(entry, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        if os.name == "nt" and os.path.isfile(candidate + ".exe"):
            return candidate + ".exe"
    return None


def decide(
    argv: list[str],
    stdin_text: str | None,
    policy: LocalPolicy,
    *,
    detector: Callable[[str], ScanResult] = detect,
    classifier: Callable[[str], ShellDecision] = classify_command,
) -> WrapperDecision:
    """Decide whether to block, redact, or allow a wrapped invocation."""
    command = " ".join(argv)
    shell_decision = classifier(command)
    if shell_decision.action == "block":
        return WrapperDecision(action="block", reason=shell_decision.reason)

    # argv secrets cannot be safely rewritten -> block.
    argv_result = detector(command)
    if argv_result.has_sensitive:
        return WrapperDecision(
            action="block",
            reason="Sensitive data in command line",
            classifications=argv_result.classifications,
        )

    if stdin_text is None:
        return WrapperDecision(action="allow", reason="No sensitive data detected")

    stdin_result = detector(stdin_text)
    if not stdin_result.has_sensitive:
        return WrapperDecision(action="allow", reason="No sensitive data detected")

    from .policy import evaluate

    decision = evaluate(policy, "stdin", stdin_result.classifications)
    if decision == "block":
        return WrapperDecision(
            action="block",
            reason="Sensitive data in piped input",
            classifications=stdin_result.classifications,
        )
    if decision == "redact" and stdin_result.redacted_content is not None:
        return WrapperDecision(
            action="redact",
            reason="Redacted sensitive data in piped input",
            redacted_stdin=stdin_result.redacted_content,
            classifications=stdin_result.classifications,
        )
    return WrapperDecision(action="allow", reason="No sensitive data detected")


def _default_runner(real: str, argv: list[str], stdin_text: str | None, env: dict) -> int:
    if stdin_text is not None:
        proc = subprocess.run([real, *argv], input=stdin_text, text=True, env=env)
        return proc.returncode
    os.execvpe(real, [real, *argv], env)
    return 127  # pragma: no cover - execvpe never returns on success


def main(
    argv: list[str] | None = None,
    *,
    stdin=None,
    stderr=None,
    env: dict | None = None,
    shim_dir: str | None = None,
    policy: LocalPolicy | None = None,
    runner: Callable[[str, list[str], str | None, dict], int] = _default_runner,
) -> int:
    """Entry point for a shim script. All I/O and exec are injectable."""
    argv = argv if argv is not None else sys.argv[1:]
    stdin = stdin if stdin is not None else sys.stdin
    stderr = stderr if stderr is not None else sys.stderr
    env = env if env is not None else os.environ.copy()
    policy = policy if policy is not None else LocalPolicy.defaults()

    name = os.path.basename(argv[0]) if argv else "claude"
    shim_dir = shim_dir if shim_dir is not None else os.path.dirname(os.path.abspath(__file__))

    if env.get(WRAPPER_ACTIVE_ENV):
        real = resolve_real_binary(name, shim_dir, env.get("PATH", "").split(os.pathsep))
        if real is None:
            return 127
        return runner(real, argv[1:], None, env)

    stdin_text: str | None = None
    if not stdin.isatty():
        stdin_text = stdin.read()

    decision = decide(argv[1:], stdin_text, policy)
    if decision.action == "block":
        print(f"pysetu: blocked: {decision.reason}", file=stderr)
        return 1

    real = resolve_real_binary(name, shim_dir, env.get("PATH", "").split(os.pathsep))
    if real is None:
        print(f"pysetu: could not resolve real binary for {name}", file=stderr)
        return 127

    child_env = dict(env)
    child_env[WRAPPER_ACTIVE_ENV] = "1"
    if decision.action == "redact":
        return runner(real, argv[1:], decision.redacted_stdin, child_env)
    return runner(real, argv[1:], stdin_text, child_env)


def install_shim(
    shim_dir: str,
    *,
    binaries: tuple[str, ...] = WRAPPED_BINARIES,
    package_dir: str | None = None,
) -> list[str]:
    """Write one executable shim script per wrapped binary. Returns created paths."""
    package_dir = package_dir if package_dir is not None else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(shim_dir, exist_ok=True)
    created: list[str] = []
    for binary in binaries:
        path = os.path.join(shim_dir, binary)
        script = (
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            f"sys.path.insert(0, {package_dir!r})\n"
            "from pysetu_agent.wrapper import main\n"
            "raise SystemExit(main())\n"
        )
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(path, 0o755)
        created.append(path)
    return created
