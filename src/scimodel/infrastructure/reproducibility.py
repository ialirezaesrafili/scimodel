"""Reproducibility metadata and artifact helpers."""

from __future__ import annotations

import hashlib
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scimodel import __version__


def build_manifest(
    input_path: Path,
    *,
    command: str,
    configuration: dict[str, Any],
) -> dict[str, Any]:
    """Build a manifest identifying the input, software, and configuration."""
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    return {
        "manifest_version": "1",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "command": command,
        "input": {
            "path": str(input_path),
            "sha256": digest,
            "size_bytes": input_path.stat().st_size,
        },
        "configuration": configuration,
        "software": {
            "scimodel": __version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "implementation": sys.implementation.name,
        },
    }
