"""Pre/post job hook support for cronwatcher.

Allows users to define shell commands that run before or after a cron job,
independently of the job's own command. Hooks are fire-and-forget: a failing
pre-hook aborts the job; a failing post-hook is logged but does not change
the job's recorded outcome.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class HookResult:
    hook_type: str          # "pre" or "post"
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def __str__(self) -> str:  # pragma: no cover
        status = "ok" if self.ok else f"failed ({self.returncode})"
        return f"[{self.hook_type}-hook] {self.command!r} -> {status}"


def _run_hook(hook_type: str, command: str, timeout: int = 30) -> HookResult:
    """Execute a single hook command and return the result."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return HookResult(
            hook_type=hook_type,
            command=command,
            returncode=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        log.warning("%s-hook timed out: %s", hook_type, command)
        return HookResult(hook_type=hook_type, command=command,
                          returncode=-1, stdout="", stderr="timeout")


def run_pre_hooks(commands: List[str], timeout: int = 30) -> List[HookResult]:
    """Run all pre-hooks in order. Stops on first failure."""
    results: List[HookResult] = []
    for cmd in commands:
        result = _run_hook("pre", cmd, timeout)
        results.append(result)
        if not result.ok:
            log.error("pre-hook failed, aborting job: %s", cmd)
            break
    return results


def run_post_hooks(commands: List[str], timeout: int = 30) -> List[HookResult]:
    """Run all post-hooks in order. Continues even on failure."""
    results: List[HookResult] = []
    for cmd in commands:
        result = _run_hook("post", cmd, timeout)
        results.append(result)
        if not result.ok:
            log.warning("post-hook failed (ignored): %s", cmd)
    return results


def pre_hooks_passed(results: List[HookResult]) -> bool:
    """Return True only when every pre-hook succeeded."""
    return all(r.ok for r in results)
