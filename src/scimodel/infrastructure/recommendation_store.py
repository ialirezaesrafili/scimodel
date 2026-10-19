"""Persistent review lifecycle for assistant recommendations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


class RecommendationStore:
    """Store recommendations and explicit user outcomes."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, recommendation: dict[str, Any], run_id: str) -> str:
        payload = dict(recommendation)
        payload["run_id"] = run_id
        payload.setdefault("status", "pending")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        recommendation_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        payload["recommendation_id"] = recommendation_id
        payload.setdefault("created_at", datetime.now(UTC).isoformat())
        self.root.mkdir(parents=True, exist_ok=True)
        self._path(recommendation_id).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return recommendation_id

    def get(self, recommendation_id: str) -> dict[str, Any]:
        path = self._path(recommendation_id)
        if not path.is_file():
            raise FileNotFoundError(f"Recommendation was not found: {recommendation_id}")
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        records = [
            cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            for path in self.root.glob("*.json")
        ]
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def update(self, recommendation_id: str, status: str, **fields: Any) -> dict[str, Any]:
        if status not in {"pending", "accepted", "rejected", "corrected"}:
            raise ValueError("Status must be pending, accepted, rejected, or corrected.")
        payload = self.get(recommendation_id)
        payload["status"] = status
        payload["reviewed_at"] = datetime.now(UTC).isoformat()
        payload.update(fields)
        self._path(recommendation_id).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return payload

    def _path(self, recommendation_id: str) -> Path:
        if len(recommendation_id) != 16 or any(
            char not in "0123456789abcdef" for char in recommendation_id
        ):
            raise ValueError("Recommendation ID must be a 16-character hexadecimal identifier.")
        return self.root / f"{recommendation_id}.json"
