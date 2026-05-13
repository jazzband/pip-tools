"""Translate a resolved install requirement into a ``packaging.pylock.Package``."""

from __future__ import annotations

import typing as _t
from pathlib import Path

from packaging.markers import Marker
from packaging.pylock import Package, PackageSdist, PackageWheel
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version
from pip._internal.req import InstallRequirement

from ...exceptions import PipToolsError
from ._archive import build_archive_source
from ._detection import detect_source_type
from ._directory import build_directory_source
from ._index import build_index_source
from ._vcs import build_vcs_source


def build_pylock_package(
    requirement: InstallRequirement,
    dist_files: _t.Sequence[PackageWheel | PackageSdist],
    dependencies: list[dict[str, str]],
    marker: str | None,
    index_url: str | None,
    requires_python: str | None = None,
    lock_dir: Path | None = None,
) -> Package:
    """Build the PEP 751 ``Package`` entry for one resolved requirement.

    Picks the source field that matches the requirement (vcs, directory, archive, or index) and
    threads through every field PEP 751 attaches to a package entry.

    :param requirement: The resolved install requirement.
    :param dist_files: Distribution files (wheels and sdists) keyed for this pin.
    :param dependencies: Pre-built dependency reference list.
    :param marker: Composed marker string for the package, or ``None``.
    :param index_url: URL of the index that served the artifact, when applicable.
    :param requires_python: ``Requires-Python`` specifier string for the package.
    :param lock_dir: Directory the lockfile is being written to, used to relativise local paths.
    :returns: The populated package entry.
    :raises PipToolsError: When no installable source can be derived for the package.
    """
    source_type = detect_source_type(requirement)

    version: Version | None = None
    if (
        source_type not in ("directory", "vcs")
        and (raw := requirement_version(requirement)) is not None
    ):
        version = Version(raw)

    vcs = directory = archive = sdist = None
    wheels: list[PackageWheel] | None = None
    index: str | None = None

    if source_type == "vcs":
        vcs = build_vcs_source(requirement)
    elif source_type == "directory":
        directory = build_directory_source(requirement, lock_dir)
    elif source_type == "archive":
        archive = build_archive_source(requirement, lock_dir)
    else:
        index = index_url
        sdist, wheels = build_index_source(
            requirement.name, version, dist_files, lock_dir
        )

    if not (vcs or directory or archive or sdist or wheels):
        raise PipToolsError(
            f"No source available for {requirement.name!r}: PEP 751 requires every "
            f"package entry to declare one of vcs, directory, archive, or an "
            f"sdist/wheels pair. The index returned no installable files for "
            f"this version."
        )

    return Package(
        name=canonicalize_name(requirement.name),
        version=version,
        marker=Marker(marker) if marker is not None else None,
        requires_python=SpecifierSet(requires_python) if requires_python else None,
        dependencies=dependencies or None,
        vcs=vcs,
        directory=directory,
        archive=archive,
        index=index,
        sdist=sdist,
        wheels=wheels,
    )


def requirement_version(requirement: InstallRequirement) -> str | None:
    """Return the version pin on a resolved requirement, or ``None`` when absent.

    The backtracking resolver pins every requirement to one specifier before this is called; the
    ``None`` fallback protects against unpinned requirements re-entering the flow so the failure
    surface stays a missing-version error.

    :param requirement: The requirement to inspect.
    :returns: The pinned version string, or ``None`` when no pin is present.
    """
    return (
        None
        if (spec := next(iter(requirement.specifier), None)) is None
        else spec.version
    )


__all__ = [
    "build_pylock_package",
    "detect_source_type",
    "requirement_version",
]
