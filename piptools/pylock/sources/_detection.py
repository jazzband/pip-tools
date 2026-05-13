"""Source-type detection plus the path relativizer shared by file sources."""

from __future__ import annotations

from os.path import relpath
from pathlib import Path

from pip._internal.models.link import Link
from pip._internal.req import InstallRequirement


def effective_link(requirement: InstallRequirement) -> Link | None:
    """Return the user-supplied link, pip's resolved link, or ``None``."""
    return requirement.original_link or requirement.link


def detect_source_type(requirement: InstallRequirement) -> str:
    """Classify a requirement by which PEP 751 source field describes it.

    :param requirement: Resolved install requirement to classify.
    :returns: One of ``"vcs"``, ``"directory"``, ``"archive"``, or ``"index"``.
    """
    if requirement.editable:
        return "directory"
    # ``original_link`` is set when the user spelled out a URL/VCS/file source; pip's own resolution
    # adds a ``link`` from the index but leaves ``original_link`` None, which distinguishes
    # user-supplied sources from index downloads.
    if (original := getattr(requirement, "original_link", None)) is not None:
        if original.is_vcs:
            return "vcs"
        if original.is_file and original.is_existing_dir():
            return "directory"
        return "archive"
    return "index"


def relativize_path(path: str, lock_dir: Path | None) -> str:
    """Render ``path`` relative to ``lock_dir`` using POSIX separators.

    PEP 751 specifies that local paths are written relative to the lock file with POSIX separators
    so a committed lockfile remains portable across machines.

    :param path: The path to relativise.
    :param lock_dir: Directory the lockfile is being written to. ``None`` keeps the path as
        supplied.
    :returns: The relative POSIX path string when relativisation works, otherwise the absolute
        POSIX form.
    """
    candidate = Path(path)
    if lock_dir is not None:
        try:
            candidate = candidate.relative_to(lock_dir)
        except ValueError:
            # Sibling/parent of ``lock_dir``. ``relative_to`` raises in 3.10/3.11 without
            # ``walk_up``; ``os.path.relpath`` produces some relative form for siblings. On Windows
            # it raises again when the two paths are on different drives, where no relative path
            # can spell the difference. Keep the absolute form in that case; the lockfile isn't
            # portable across machines for that input anyway.
            try:  # pragma: win32 cover
                candidate = Path(relpath(candidate, lock_dir))
            except ValueError:  # pragma: win32 cover
                pass
    return candidate.as_posix()


__all__ = [
    "detect_source_type",
    "effective_link",
    "relativize_path",
]
