"""Persistent, inspectable storage for assistant run records."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from scimodel.domain.assistant import AssistantRun

_SENSITIVE_KEY = re.compile(r"(token|secret|password|api[_-]?key|credential)", re.IGNORECASE)


class RunStore:
    """Store complete assistant runs as one JSON file per run."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, run: AssistantRun) -> str:
        """Write a redacted run and return its stable content-derived ID."""
        payload = redact_sensitive(run.to_dict())
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        run_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        directory = self.root / run_id
        directory.mkdir(parents=True, exist_ok=True)
        payload["run_id"] = run_id
        payload["stored_at"] = datetime.now(UTC).isoformat()
        (directory / "run.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return run_id

    def load(self, run_id: str) -> dict[str, Any]:
        """Load one run after validating the ID format."""
        if not re.fullmatch(r"[0-9a-f]{16}", run_id):
            raise ValueError("Run ID must be a 16-character hexadecimal identifier.")
        path = self.root / run_id / "run.json"
        if not path.is_file():
            raise FileNotFoundError(f"Run was not found: {run_id}")
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[dict[str, Any]]:
        """Return compact summaries ordered from newest stored record."""
        records: list[dict[str, Any]] = []
        if not self.root.is_dir():
            return records
        for path in self.root.glob("*/run.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(
                {
                    "run_id": payload.get("run_id", path.parent.name),
                    "status": payload.get("status"),
                    "objective": payload.get("request", {}).get("objective"),
                    "stored_at": payload.get("stored_at"),
                }
            )
        return sorted(records, key=lambda record: record.get("stored_at") or "", reverse=True)


def redact_sensitive(value: Any) -> Any:
    """Recursively redact values under common secret-bearing field names."""
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return [redact_sensitive(item) for item in value]
    return value


def compare_runs(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Compare two records without copying raw scientific payloads."""
    first_validation = _validation_summary(first)
    second_validation = _validation_summary(second)
    return {
        "first_run": first.get("run_id"),
        "second_run": second.get("run_id"),
        "status_changed": first.get("status") != second.get("status"),
        "validation": {"first": first_validation, "second": second_validation},
        "recommendation_changed": first.get("recommendation") != second.get("recommendation"),
    }


def _validation_summary(run: dict[str, Any]) -> dict[str, Any] | None:
    for call in run.get("tool_calls", []):
        if call.get("tool") == "validate_model":
            validation = call.get("output", {}).get("validation", {})
            return {
                "valid": validation.get("valid"),
                "checks": validation.get("checks", []),
            }
    return None
