from __future__ import annotations

import optparse
import pathlib
import urllib.parse
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

from .path_compat import relative_to_walk_up

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
    # the `comes_from` data will be rewritten in different ways in different conditions
    # each rewrite rule is expressible as a str->str function
    rewrite_comes_from: Callable[[str], str]

    if comes_from_stdin:
        # if data is coming from stdin, then `comes_from="-r -"`
        rewrite_comes_from = _rewrite_comes_from_to_hardcoded_stdin_value
    elif pathlib.Path(filename).is_absolute():
        # if the input path is absolute, just normalize paths to posix-style
        rewrite_comes_from = _normalize_comes_from_location
    else:
        # if the input was a relative path, set the rewrite rule to rewrite
        # absolute paths to be relative
        rewrite_comes_from = _relativize_comes_from_location

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

        install_req.comes_from = rewrite_comes_from(install_req.comes_from)

        yield install_req


def _rewrite_comes_from_to_hardcoded_stdin_value(_: str, /) -> str:
    """Produce the hardcoded ``comes_from`` value for stdin."""
    return "-r -"


def _relativize_comes_from_location(original_comes_from: str, /) -> str:
    """
    Convert a ``comes_from`` path to a relative posix path.

    This is the rewrite rule used when ``-r`` or ``-c`` appears in
    ``comes_from`` data with an absolute path.

    The ``-r`` or ``-c`` qualifier is retained, the path is relativized
    with respect to the CWD, and the path is converted to posix style.
    """
    # require `-r` or `-c` as the source
    if not original_comes_from.startswith(("-r ", "-c ")):
        return original_comes_from

    # split on the space
    prefix, space_sep, suffix = original_comes_from.partition(" ")

    # if the value part is a remote URI for pip, return the original
    if _is_remote_pip_uri(suffix):
        return original_comes_from

    file_path = pathlib.Path(suffix)

    # if the path was not absolute, normalize to posix-style and finish processing
    if not file_path.is_absolute():
        return f"{prefix} {file_path.as_posix()}"

    # make it relative to the current working dir
    suffix = relative_to_walk_up(file_path, pathlib.Path.cwd()).as_posix()
    return f"{prefix}{space_sep}{suffix}"


def _normalize_comes_from_location(original_comes_from: str, /) -> str:
    """
    Convert a ``comes_from`` path to a posix-style path.

    This is the rewrite rule when ``-r`` or ``-c`` appears in ``comes_from``
    data and the input path was absolute, meaning we should not relativize the
    locations.

    The ``-r`` or ``-c`` qualifier is retained, and the path is converted to
    posix style.
    """
    # require `-r` or `-c` as the source
    if not original_comes_from.startswith(("-r ", "-c ")):
        return original_comes_from

    # split on the space
    prefix, space_sep, suffix = original_comes_from.partition(" ")

    # if the value part is a remote URI for pip, return the original
    if _is_remote_pip_uri(suffix):
        return original_comes_from

    # convert to a posix-style path
    suffix = pathlib.Path(suffix).as_posix()
    return f"{prefix}{space_sep}{suffix}"


def _is_remote_pip_uri(value: str) -> bool:
    """
    Test a string to see if it is a URI treated as a remote file in ``pip``.
    Specifically this means that it's a 'file', 'http', or 'https' URI.

    The test is performed by trying a URL parse and reading the scheme.
    """
    scheme = urllib.parse.urlsplit(value).scheme
    return scheme in {"file", "http", "https"}


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
