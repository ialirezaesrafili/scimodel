"""Inspectable storage for approved personal and project context."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from scimodel.domain.assistant import ContextItem

ALLOWED_KINDS = frozenset({"preference", "fact", "constraint"})
ALLOWED_CONFIDENCE = frozenset({"low", "medium", "high"})
ALLOWED_STATUS = frozenset({"active", "uncertain", "rejected"})


class ContextStore:
    """Store context as one inspectable JSON document per key."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def set(
        self,
        key: str,
        value: str,
        *,
        kind: str = "fact",
        source: str = "user",
        confidence: str = "high",
        status: str = "active",
    ) -> ContextItem:
        _validate(key, kind, value, source, confidence, status)
        item = ContextItem(
            key=key,
            kind=kind,
            value=value,
            source=source,
            confidence=confidence,
            status=status,
            updated_at=datetime.now(UTC).isoformat(),
        )
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / f"{key}.json").write_text(
            json.dumps(item_to_dict(item), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return item

    def get(self, key: str) -> dict[str, Any]:
        path = self.root / f"{key}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Context item was not found: {key}")
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        items = [
            cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
            for path in self.root.glob("*.json")
        ]
        return sorted(items, key=lambda item: str(item.get("key", "")))

    def remove(self, key: str) -> None:
        path = self.root / f"{key}.json"
        if not path.is_file():
            raise FileNotFoundError(f"Context item was not found: {key}")
        path.unlink()


def item_to_dict(item: ContextItem) -> dict[str, str]:
    return {
        "key": item.key,
        "kind": item.kind,
        "value": item.value,
        "source": item.source,
        "confidence": item.confidence,
        "status": item.status,
        "updated_at": item.updated_at,
    }


def _validate(key: str, kind: str, value: str, source: str, confidence: str, status: str) -> None:
    if not key.strip() or "/" in key or "\\" in key or key in {".", ".."}:
        raise ValueError("Context keys must be non-empty filenames without path separators.")
    if not value.strip() or not source.strip():
        raise ValueError("Context value and source must be non-empty.")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"Unsupported context kind: {kind}")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"Unsupported confidence level: {confidence}")
    if status not in ALLOWED_STATUS:
        raise ValueError(f"Unsupported context status: {status}")
