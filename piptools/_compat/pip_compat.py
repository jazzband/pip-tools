import optparse
from typing import Iterator, Optional

import pip
from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.req import parse_requirements as _parse_requirements
from pip._internal.req.constructors import install_req_from_parsed_requirement
from pip._vendor.packaging.version import parse as parse_version

PIP_VERSION = tuple(map(int, parse_version(pip.__version__).base_version.split(".")))


__all__ = [
    "get_build_tracker",
    "update_env_context_manager",
]


def parse_requirements(
    filename: str,
    session: PipSession,
    finder: Optional[PackageFinder] = None,
    options: Optional[optparse.Values] = None,
    constraint: bool = False,
    isolated: bool = False,
) -> Iterator[InstallRequirement]:
    for parsed_req in _parse_requirements(
        filename, session, finder=finder, options=options, constraint=constraint
    ):
        yield install_req_from_parsed_requirement(parsed_req, isolated=isolated)


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
