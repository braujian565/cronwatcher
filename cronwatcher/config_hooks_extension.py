"""Helpers to read pre/post hook lists from raw job config dicts.

This keeps hook-related parsing out of the core config module so that
existing code is unaffected. Call ``apply_hooks`` after loading a
``JobConfig`` to attach hook attributes dynamically, or use
``parse_hooks_from_raw`` when building ``JobConfig`` objects manually.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from cronwatcher.config import JobConfig


_HOOK_FIELDS = ("pre_hooks", "post_hooks")


def parse_hooks_from_raw(raw: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract and validate hook lists from a raw job dict.

    Returns a dict with keys ``pre_hooks`` and ``post_hooks``, each a
    (possibly empty) list of strings.

    Raises ``ValueError`` if a hook entry is not a non-empty string.
    """
    result: Dict[str, List[str]] = {"pre_hooks": [], "post_hooks": []}
    for field in _HOOK_FIELDS:
        raw_hooks = raw.get(field) or []
        if not isinstance(raw_hooks, list):
            raise ValueError(
                f"'{field}' must be a list of strings, got {type(raw_hooks).__name__}"
            )
        validated: List[str] = []
        for i, entry in enumerate(raw_hooks):
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError(
                    f"'{field}[{i}]' must be a non-empty string, got {entry!r}"
                )
            validated.append(entry.strip())
        result[field] = validated
    return result


def apply_hooks(job: JobConfig, raw: Dict[str, Any]) -> JobConfig:
    """Attach pre/post hook lists to an existing ``JobConfig`` instance.

    Because ``JobConfig`` is a dataclass we use ``object.__setattr__`` to
    avoid issues with frozen dataclasses in the future.
    """
    hooks = parse_hooks_from_raw(raw)
    for field, value in hooks.items():
        try:
            object.__setattr__(job, field, value)
        except AttributeError:
            # Fallback for non-frozen dataclasses
            setattr(job, field, value)
    return job


def has_hooks(job: JobConfig) -> bool:
    """Return True if the job has at least one pre- or post-hook defined."""
    for field in _HOOK_FIELDS:
        if getattr(job, field, None):
            return True
    return False
