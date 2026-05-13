"""Translate a directory-installed requirement into ``PackageDirectory``."""

from __future__ import annotations

from pathlib import Path

from packaging.pylock import PackageDirectory
from pip._internal.req import InstallRequirement
from pip._internal.utils.urls import url_to_path

from ._detection import effective_link, relativize_path


def build_directory_source(
    requirement: InstallRequirement, lock_dir: Path | None
) -> PackageDirectory:
    """Return the ``directory`` source for a path-installed requirement.

    :param requirement: Resolved requirement whose ``link`` points at a directory.
    :param lock_dir: Directory the lockfile lives in. ``relativize_path`` rewrites the directory
        path relative to this so a checked-in ``pylock.toml`` stays portable across checkouts.
    :returns: A populated ``PackageDirectory`` carrying the editable flag and the
        ``#subdirectory=`` fragment.
    """
    link = effective_link(requirement)
    assert link is not None
    raw = link.url_without_fragment
    return PackageDirectory(
        path=relativize_path(
            url_to_path(raw) if raw.startswith("file:") else raw, lock_dir
        ),
        editable=requirement.editable,
        # PEP 751 lists ``packages.directory.subdirectory`` as supported. The fragment carries the
        # path inside the source tree; dropping it makes ``pkg @ file:///repo#subdirectory=sub``
        # installs build the wrong tree.
        subdirectory=link.subdirectory_fragment,
    )


__all__ = ["build_directory_source"]
