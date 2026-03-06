"""
PackageFinder interfaces for pip-tools.

Because the PackageFinder class itself has evolved over pip's lifetime, these helpers
provide compatible interfaces which wrap methods and attributes.
"""

from __future__ import annotations

import functools

from pip._internal import exceptions as _pip_internal_exceptions
from pip._internal.index.package_finder import PackageFinder
from pip._internal.req import InstallRequirement
from pip._vendor.requests import RequestException

from . import pip_version as _pip_version


@functools.cache
def get_pip_request_failed_exception_types() -> tuple[type[Exception], ...]:
    """
    Get the error types which indicate a connection failure, as might be experienced by
    a client trying to reach an index server's JSON API when that API is not available.

    These are only the errors that indicate some kind of failure to connect.
    Errors about SSL configuration, etc, should not be included here, so that they
    raise all the way to the user.

    This functionality is provided as a cached function rather than a constant to defer
    the work of attribute lookups until it is actually needed. This increases the
    resilience of some ``pip-tools`` usages to changes in ``pip``, for when
    ``pip-tools`` is used with new and untested versions.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR < (26, 2):
        return (RequestException,)
    else:
        return (
            RequestException,
            _pip_internal_exceptions.ConnectionFailedError,
            _pip_internal_exceptions.ConnectionTimeoutError,
            _pip_internal_exceptions.ProxyConnectionError,
        )


def finder_allows_prereleases_of_req(
    finder: PackageFinder, ireq: InstallRequirement
) -> bool:
    """
    Check if a package finder will get prereleases for a given requirement.

    On older pip versions, this is not specific to the requirement, but on newer ones it
    is.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR < (26, 0):  # pragma: pip<26.0 cover
        return finder.allow_all_prereleases  # type: ignore[no-any-return]
    else:  # pragma: pip<26.0 no cover
        return finder.release_control.allows_prereleases(  # type: ignore[no-any-return]
            ireq.req.name
        )


def finder_allows_all_prereleases(finder: PackageFinder) -> bool:
    """
    Check if a package finder will get prereleases for all requirements.

    On older pip versions, this is not specific to the requirement, but on newer ones it
    is. However, ``--pre`` is translated internally to ``":all:"`` on those versions.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR < (26, 0):  # pragma: pip<26.0 cover
        return bool(finder.allow_all_prereleases)
    else:  # pragma: pip<26.0 no cover
        return ":all:" in finder.release_control.all_releases
