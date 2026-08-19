"""Clipboard DLP monitor for the endpoint agent (macOS).

Polls the system clipboard via ``pbpaste``/``pbcopy``. When sensitive content
is detected, the clipboard is redacted in place (or cleared for a block
decision). ``read``/``write`` are injectable so the monitor is testable without
a real clipboard.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable

from .detection import ScanResult, detect
from .policy import LocalPolicy, evaluate


@dataclass(frozen=True)
class ClipboardDecision:
    action: str  # allow | redact | block
    redacted: str | None = None
    classifications: list[str] = field(default_factory=list)


def read_clipboard() -> str:
    proc = subprocess.run(["pbpaste"], capture_output=True, text=True)
    return proc.stdout


def write_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True)


def decide_clipboard(
    text: str,
    policy: LocalPolicy,
    detector: Callable[[str], ScanResult] = detect,
) -> ClipboardDecision:
    result = detector(text)
    if not result.has_sensitive:
        return ClipboardDecision(action="allow")
    decision = evaluate(policy, "clipboard", result.classifications)
    if decision == "block":
        return ClipboardDecision(action="block", classifications=result.classifications)
    if decision == "redact" and result.redacted_content is not None:
        return ClipboardDecision(
            action="redact",
            redacted=result.redacted_content,
            classifications=result.classifications,
        )
    return ClipboardDecision(action="allow")


def monitor_clipboard(
    policy: LocalPolicy,
    *,
    detector: Callable[[str], ScanResult] = detect,
    read: Callable[[], str] = read_clipboard,
    write: Callable[[str], None] = write_clipboard,
    on_event: Callable[[ClipboardDecision], None] | None = None,
    poll_interval: float = 1.0,
    stop: Callable[[], bool] | None = None,
) -> None:
    """Poll the clipboard until ``stop()`` returns True, enforcing decisions."""
    last = read()
    while True:
        if stop is not None and stop():
            return
        time.sleep(poll_interval)
        current = read()
        if current == last:
            continue
        last = current
        decision = decide_clipboard(current, policy, detector)
        if decision.action == "redact" and decision.redacted is not None:
            write(decision.redacted)
            last = decision.redacted
        elif decision.action == "block":
            write("")
            last = ""
        if decision.action != "allow" and on_event is not None:
            on_event(decision)
