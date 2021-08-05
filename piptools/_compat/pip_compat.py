import optparse
import platform
import re
from typing import Callable, Iterable, Iterator, Optional, cast

import pip
from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.req import parse_requirements as _parse_requirements
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pkg_resources import Requirement

from ..utils import abs_ireq, working_dir

PIP_VERSION = tuple(map(int, parse_version(pip.__version__).base_version.split(".")))

file_url_schemes_re = re.compile(r"^((git|hg|svn|bzr)\+)?file:")

__all__ = [
    "get_build_tracker",
    "update_env_context_manager",
    "dist_requires",
    "uses_pkg_resources",
    "Distribution",
]


def parse_requirements(
    filename: str,
    session: PipSession,
    finder: Optional[PackageFinder] = None,
    options: Optional[optparse.Values] = None,
    constraint: bool = False,
    isolated: bool = False,
    from_dir: Optional[str] = None,
) -> Iterator[InstallRequirement]:
    for parsed_req in _parse_requirements(
        filename, session, finder=finder, options=options, constraint=constraint
    ):
        # This context manager helps pip locate relative paths specified
        # with non-URI (non file:) syntax, e.g. '-e ..'
        with working_dir(from_dir):
            ireq = install_req_from_parsed_requirement(parsed_req, isolated=isolated)

        # But the resulting ireq is absolute (ahead of schedule),
        # so abs_ireq will not apply the _was_relative attribute,
        # which is needed for the writer to use the relpath.
        a_ireq = abs_ireq(ireq, from_dir)

        # To account for that, we guess if the path was initially relative and
        # set _was_relative ourselves:
        bare_path = file_url_schemes_re.sub("", parsed_req.requirement)
        is_win = platform.system() == "Windows"
        if is_win:
            bare_path = bare_path.lstrip("/")
        if (
            a_ireq.link is not None
            and a_ireq.link.scheme.endswith("file")
            and not bare_path.startswith("/")
        ):
            if not (is_win and re.match(r"[a-zA-Z]:", bare_path)):
                a_ireq._was_relative = True

        yield a_ireq


if PIP_VERSION[:2] <= (22, 0):
    from pip._internal.req.req_tracker import (
        get_requirement_tracker as get_build_tracker,
    )
    from pip._internal.req.req_tracker import update_env_context_manager
else:
    from pip._internal.operations.build.build_tracker import (
        get_build_tracker,
        update_env_context_manager,
    )


# The Distribution interface has changed between pkg_resources and
# importlib.metadata, so this compat layer allows for a consistent access
# pattern. In pip 22.1, importlib.metdata became the default on Python 3.11
# (and later), but is overrideable. `select_backend` returns what's being used.


def _uses_pkg_resources() -> bool:

    if PIP_VERSION[:2] < (22, 1):
        return True
    else:
        from pip._internal.metadata import select_backend
        from pip._internal.metadata.pkg_resources import Distribution as _Dist

        return select_backend().Distribution is _Dist


uses_pkg_resources = _uses_pkg_resources()

if uses_pkg_resources:
    from operator import methodcaller

    from pip._vendor.pkg_resources import Distribution

    dist_requires = cast(
        Callable[[Distribution], Iterable[Requirement]], methodcaller("requires")
    )
else:
    from pip._internal.metadata import select_backend

    Distribution = select_backend().Distribution

    def dist_requires(dist: "Distribution") -> Iterable[Requirement]:
        """Mimics pkg_resources.Distribution.requires for the case of no
        extras. This doesn't fulfill that API's `extras` parameter but
        satisfies the needs of pip-tools."""
        reqs = (Requirement.parse(req) for req in (dist.requires or ()))
        return [
            req
            for req in reqs
            if not req.marker or req.marker.evaluate({"extra": None})
        ]
