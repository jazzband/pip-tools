"""
PackageFinder interfaces for pip-tools.

Because the PackageFinder class itself has evolved over pip's lifetime, these helpers
provide compatible interfaces which wrap methods and attributes.
"""

from __future__ import annotations

from pip._internal.index.package_finder import PackageFinder
from pip._internal.req import InstallRequirement

from . import pip_version as _pip_version


def finder_allows_prereleases_of_req(
    finder: PackageFinder, ireq: InstallRequirement
) -> bool:
    """
    Check if a package finder will get prereleases for a given requirement.

    On older pip versions, this is not specific to the requirement, but on newer ones it
    is.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR < (26, 0):
        return finder.allow_all_prereleases  # type: ignore[no-any-return]
    else:
        return finder.release_control.allows_prereleases(  # type: ignore[no-any-return]
            ireq.req.name
        )


def finder_allows_all_prereleases(finder: PackageFinder) -> bool:
    """
    Check if a package finder will get prereleases for all requirements.

    On older pip versions, this is not specific to the requirement, but on newer ones it
    is. However, ``--pre`` is translated internally to ``":all:"`` on those versions.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR < (26, 0):
        return bool(finder.allow_all_prereleases)
    else:
        return ":all:" in finder.release_control.all_releases
