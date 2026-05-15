"""Executes cron job commands and captures results."""

import subprocess
import time
from dataclasses import dataclass
from typing import Optional

from cronwatcher.config import JobConfig


@dataclass
class RunResult:
    job_name: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    started_at: float

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def timed_out(self) -> bool:
        """Return True if the job was killed due to a timeout."""
        return self.exit_code == -1


def run_job(job: JobConfig, timeout: Optional[int] = None) -> RunResult:
    """Run a job command and return the result.

    Args:
        job: The job configuration to execute.
        timeout: Optional override for the job's configured timeout (seconds).

    Returns:
        A RunResult containing the exit code, output, and timing information.
    """
    started_at = time.time()
    effective_timeout = timeout or job.timeout

    try:
        proc = subprocess.run(
            job.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired:
        exit_code = -1
        stdout = ""
        stderr = f"Job timed out after {effective_timeout} seconds"
    except Exception as exc:  # noqa: BLE001
        exit_code = -2
        stdout = ""
        stderr = str(exc)

    duration = time.time() - started_at
    return RunResult(
        job_name=job.name,
        command=job.command,
        exit_code=exit_code,
        stdout=stdout.strip(),
        stderr=stderr.strip(),
        duration_seconds=round(duration, 3),
        started_at=started_at,
    )
