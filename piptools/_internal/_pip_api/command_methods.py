"""
Interfaces for interacting with methods on RequirementCommand and other ``pip``-defined
command types.

Because these classes change over time, pip-tools needs functional interfaces which wrap
methods, making their usage compatible across versions.
"""

from __future__ import annotations

import optparse

from pip._internal.cli.req_command import RequirementCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.network.session import PipSession
from pip._internal.operations.build.build_tracker import BuildTracker
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.utils.temp_dir import TempDirectory

from . import pip_version as _pip_version


def make_requirement_preparer_from_command(
    command: RequirementCommand,
    /,
    *,
    temp_build_dir: TempDirectory,
    options: optparse.Values,
    build_tracker: BuildTracker,
    session: PipSession,
    finder: PackageFinder,
    download_dir: str | None = None,
) -> RequirementPreparer:
    """
    Wrap ``RequirementCommand.make_requirement_preparer()`` to be compatible across
    pip versions.
    Also pre-fill values which are fixed constants within pip-tools.
    """
    # within pip, allow_editables is set thusly:
    #   pip install:   True
    #   pip lock:      True
    #   pip download:  False
    #   pip wheel:     False
    #
    # as such, True seems the best fit for pip-compile and pip-sync
    allow_editables: bool = True

    use_user_site: bool = False

    # in pip v26.2, tracking of "permit_editable_wheels" moved from being
    # per-requirement object to tracked centrally on the preparer object
    # this takes the form of a new `allow_editables` bool flag
    # see also: https://github.com/pypa/pip/pull/14206
    pip_version_specific_kwargs: dict[str, object] = {}
    if _pip_version.PIP_VERSION_MAJOR_MINOR >= (26, 2):  # pragma: pip>=26.2 cover
        pip_version_specific_kwargs["allow_editables"] = allow_editables

    return command.make_requirement_preparer(
        temp_build_dir=temp_build_dir,
        options=options,
        session=session,
        finder=finder,
        use_user_site=use_user_site,
        build_tracker=build_tracker,
        **pip_version_specific_kwargs,
    )
