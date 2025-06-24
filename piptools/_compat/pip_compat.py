from __future__ import annotations

import optparse
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Set, cast

from pip._internal.cache import WheelCache
from pip._internal.index.package_finder import PackageFinder
from pip._internal.metadata import BaseDistribution
from pip._internal.metadata.pkg_resources import Distribution as _PkgResourcesDist
from pip._internal.models.direct_url import DirectUrl
from pip._internal.models.link import Link
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.req import parse_requirements as _parse_requirements
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._vendor.pkg_resources import Requirement

# The Distribution interface has changed between pkg_resources and
# importlib.metadata, so this compat layer allows for a consistent access
# pattern. In pip 22.1, importlib.metadata became the default on Python 3.11
# (and later), but is overridable. `select_backend` returns what's being used.
if TYPE_CHECKING:
    from pip._internal.metadata.importlib import Distribution as _ImportLibDist

from ..utils import PIP_VERSION, copy_install_requirement


@dataclass(frozen=True)
class Distribution:
    key: str
    version: str
    requires: Iterable[Requirement]
    direct_url: DirectUrl | None

    @classmethod
    def from_pip_distribution(cls, dist: BaseDistribution) -> Distribution:
        # TODO: Use only the BaseDistribution protocol properties and methods
        # instead of specializing by type.
        if isinstance(dist, _PkgResourcesDist):
            return cls._from_pkg_resources(dist)
        else:
            return cls._from_importlib(dist)

    @classmethod
    def _from_pkg_resources(cls, dist: _PkgResourcesDist) -> Distribution:
        return cls(
            dist._dist.key, dist._dist.version, dist._dist.requires(), dist.direct_url
        )

    @classmethod
    def _from_importlib(cls, dist: _ImportLibDist) -> Distribution:
        """Mimic pkg_resources.Distribution.requires for the case of no
        extras.

        This doesn't fulfill that API's ``extras`` parameter but
        satisfies the needs of pip-tools.
        """
        reqs = (Requirement.parse(req) for req in (dist._dist.requires or ()))
        requires = [
            req
            for req in reqs
            if not req.marker or req.marker.evaluate({"extra": None})
        ]
        return cls(dist._dist.name, dist._dist.version, requires, dist.direct_url)


class FileLink(Link):  # type: ignore[misc]
    """Wrapper for ``pip``'s ``Link`` class."""

    _url: str

    @property
    def file_path(self) -> str:
        # overriding the actual property to bypass some validation
        return self._url


def parse_requirements(
    filename: str,
    session: PipSession,
    finder: PackageFinder | None = None,
    options: optparse.Values | None = None,
    constraint: bool = False,
    isolated: bool = False,
    comes_from_stdin: bool = False,
) -> Iterator[InstallRequirement]:
    # the `comes_from` data will be rewritten based on a number of conditions
    #
    #   None        do not rewrite
    #   callable    programmatic rewrite
    #   str         fixed rewrite
    rewrite_comes_from: str | Callable[[str], str] | None = None

    if comes_from_stdin:
        # if data is coming from stdin, then `comes_from="-r -"`
        rewrite_comes_from = "-r -"
    else:
        # if the input was a relative path, set the rewrite rule to rewrite
        # absolute paths to be relative
        if not _filename_is_abspath(filename):
            rewrite_comes_from = _rewrite_absolute_comes_from_location

    for parsed_req in _parse_requirements(
        filename, session, finder=finder, options=options, constraint=constraint
    ):
        install_req = install_req_from_parsed_requirement(parsed_req, isolated=isolated)
        if install_req.editable and not parsed_req.requirement.startswith("file://"):
            # ``Link.url`` is what is saved to the output file
            # we set the url directly to undo the transformation in pip's Link class
            file_link = FileLink(install_req.link.url)
            file_link._url = parsed_req.requirement
            install_req.link = file_link
        install_req = copy_install_requirement(install_req)
        if rewrite_comes_from is None:
            pass
        elif isinstance(rewrite_comes_from, str):
            install_req.comes_from = rewrite_comes_from
        else:
            install_req.comes_from = rewrite_comes_from(install_req.comes_from)
        yield install_req


def _filename_is_abspath(filename: str) -> bool:
    """
    Check if a path is an absolute path, using exactly the normalization
    used in pip>24.3 in order to ensure consistent results.
    """
    return os.path.abspath(filename) == filename


def _rewrite_absolute_comes_from_location(original_comes_from: str, /) -> str:
    """
    This is the rewrite rule used when `-r` or `-c` appears in `comes_from` data
    with an absolute path.

    The `-r` or `-c` qualifier is retained, and the path is relativized with
    respect to the CWD.
    """
    # require `-r` or `-c` as the source
    if not original_comes_from.startswith(("-r ", "-c ")):
        return original_comes_from

    # split on the space
    prefix, _, suffix = original_comes_from.partition(" ")

    # if the path was not absolute, bail out
    if not _filename_is_abspath(suffix):
        return original_comes_from

    # make it relative to the current working dir
    suffix = os.path.relpath(suffix)
    return f"{prefix} {suffix}"


def create_wheel_cache(cache_dir: str, format_control: str | None = None) -> WheelCache:
    kwargs: dict[str, str | None] = {"cache_dir": cache_dir}
    if PIP_VERSION[:2] <= (23, 0):
        kwargs["format_control"] = format_control
    return WheelCache(**kwargs)


def get_dev_pkgs() -> set[str]:
    if PIP_VERSION[:2] <= (23, 1):
        from pip._internal.commands.freeze import DEV_PKGS

        return cast(Set[str], DEV_PKGS)

    from pip._internal.commands.freeze import _dev_pkgs

    return cast(Set[str], _dev_pkgs())
