"""Discover analyzable data files in a project folder, like a coding agent reads a repo."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scimodel.adapters.tabular_reader import SUPPORTED_SUFFIXES, TableReadError, read_table

IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".scimodel",
        "scimodel_reports",
        "dist",
        "build",
        ".ipynb_checkpoints",
        "site-packages",
    }
)


@dataclass(frozen=True)
class WorkspaceEntry:
    path: str
    relative: str
    size_bytes: int
    rows: int | None
    numeric_columns: tuple[str, ...]
    other_columns: tuple[str, ...]
    error: str | None = None

    @property
    def analyzable(self) -> bool:
        return self.error is None and len(self.numeric_columns) >= 2

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["analyzable"] = self.analyzable
        return result


def scan_workspace(
    root: Path, *, max_depth: int = 3, max_files: int = 200, max_bytes: int = 50_000_000
) -> list[WorkspaceEntry]:
    """Find supported data files under ``root`` and summarize each one."""
    root = root.resolve()
    if root.is_file():
        return [_entry(root, root.parent, max_bytes)]
    entries: list[WorkspaceEntry] = []
    for directory, subdirectories, files in os.walk(root):
        depth = len(Path(directory).relative_to(root).parts)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if name not in IGNORED_DIRECTORIES and not name.startswith(".") and depth < max_depth
        )
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() not in SUPPORTED_SUFFIXES or name.startswith("."):
                continue
            if name in {"results.json", "run_manifest.json", "package.json"}:
                continue
            entries.append(_entry(path, root, max_bytes))
            if len(entries) >= max_files:
                return entries
    return sorted(entries, key=lambda e: (not e.analyzable, e.relative))


def _entry(path: Path, root: Path, max_bytes: int) -> WorkspaceEntry:
    relative = str(path.relative_to(root)) if path.is_relative_to(root) else path.name
    size = path.stat().st_size
    if size > max_bytes:
        return WorkspaceEntry(str(path), relative, size, None, (), (), "File is too large to scan.")
    try:
        dataset = read_table(path)
    except (TableReadError, OSError, ValueError) as exc:
        return WorkspaceEntry(str(path), relative, size, None, (), (), str(exc))
    return WorkspaceEntry(
        str(path),
        relative,
        size,
        dataset.row_count,
        dataset.numeric_columns,
        tuple(name for name in dataset.columns if name not in dataset.numeric),
    )
