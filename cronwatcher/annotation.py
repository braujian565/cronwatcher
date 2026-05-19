"""Job annotation support — attach free-form notes to jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Annotation:
    job_name: str
    note: str
    author: str = "system"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "note": self.note,
            "author": self.author,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        return cls(
            job_name=data["job_name"],
            note=data["note"],
            author=data.get("author", "system"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


class Annotator:
    """Persist and retrieve annotations for jobs."""

    def __init__(self, store_path: Path) -> None:
        self._path = store_path
        self._data: Dict[str, List[dict]] = self._load()

    def _load(self) -> Dict[str, List[dict]]:
        if self._path.exists():
            return json.loads(self._path.read_text())
        return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    def add(self, annotation: Annotation) -> None:
        self._data.setdefault(annotation.job_name, []).append(annotation.to_dict())
        self._save()

    def get(self, job_name: str) -> List[Annotation]:
        return [
            Annotation.from_dict(d) for d in self._data.get(job_name, [])
        ]

    def delete_all(self, job_name: str) -> int:
        removed = len(self._data.pop(job_name, []))
        self._save()
        return removed

    def all_job_names(self) -> List[str]:
        return sorted(self._data.keys())
