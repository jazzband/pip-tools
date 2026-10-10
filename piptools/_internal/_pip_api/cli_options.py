"""
Tools for parsing pip CLI options.
"""

from __future__ import annotations

import optparse

from pip._internal.cli import cmdoptions

from . import pip_version as _pip_version


def postprocess_cli_options(options: optparse.Values) -> None:
    """
    After CLI parsing, pip processes options further to check various constraints and
    coalesce values. Emulate and/or invoke those same behaviors.
    """
    if _pip_version.PIP_VERSION_MAJOR_MINOR >= (26, 0):  # pragma: pip>=26.0 cover
        # `check_release_control_exclusive` was added in pip 26.0, so it
        # cannot be referenced directly without breaking type checking
        # against older pip versions. Use getattr for version-agnostic access.
        getattr(cmdoptions, "check_release_control_exclusive")(options)
