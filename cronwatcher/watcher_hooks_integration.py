"""Integration helpers that wire hook execution into the Watcher run loop.

The Watcher itself stays unchanged; call ``run_job_with_hooks`` instead of
``runner.run_job`` when the job config carries pre/post hook lists.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from cronwatcher.config import JobConfig
from cronwatcher.hooks import (
    HookResult,
    run_pre_hooks,
    run_post_hooks,
    pre_hooks_passed,
)
from cronwatcher.runner import RunResult, run_job

log = logging.getLogger(__name__)

_HOOK_TIMEOUT = 30  # seconds


def run_job_with_hooks(job: JobConfig) -> RunResult:
    """Execute pre-hooks → job → post-hooks and return the job's RunResult.

    If any pre-hook fails the job command is *not* executed and a synthetic
    RunResult with returncode=-2 is returned so the watcher can record the
    failure normally.
    """
    pre_cmds: List[str] = getattr(job, "pre_hooks", []) or []
    post_cmds: List[str] = getattr(job, "post_hooks", []) or []

    pre_results = run_pre_hooks(pre_cmds, timeout=_HOOK_TIMEOUT)
    if pre_cmds and not pre_hooks_passed(pre_results):
        failed = next(r for r in pre_results if not r.ok)
        log.error("Job '%s' skipped due to pre-hook failure: %s",
                  job.name, failed.command)
        return RunResult(
            returncode=-2,
            stdout="",
            stderr=f"pre-hook failed: {failed.command} (rc={failed.returncode})",
            duration_seconds=0.0,
        )

    result = run_job(job)

    run_post_hooks(post_cmds, timeout=_HOOK_TIMEOUT)

    return result
