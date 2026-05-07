"""Capture and truncate job output (stdout/stderr) for storage and alerting."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MAX_BYTES = 4096
TRUNCATED_MARKER = "\n... [output truncated]"


@dataclass
class CapturedOutput:
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    def has_output(self) -> bool:
        return bool(self.stdout or self.stderr)

    def has_errors(self) -> bool:
        return bool(self.stderr)

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CapturedOutput":
        return cls(
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            stdout_truncated=data.get("stdout_truncated", False),
            stderr_truncated=data.get("stderr_truncated", False),
        )


def _truncate(text: str, max_bytes: int) -> tuple[str, bool]:
    """Return (possibly truncated text, was_truncated)."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="replace")
    return truncated + TRUNCATED_MARKER, True


def capture_output(
    stdout: Optional[str],
    stderr: Optional[str],
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> CapturedOutput:
    """Normalise and optionally truncate raw stdout/stderr strings."""
    raw_out = stdout or ""
    raw_err = stderr or ""

    out, out_trunc = _truncate(raw_out, max_bytes)
    err, err_trunc = _truncate(raw_err, max_bytes)

    return CapturedOutput(
        stdout=out,
        stderr=err,
        stdout_truncated=out_trunc,
        stderr_truncated=err_trunc,
    )
