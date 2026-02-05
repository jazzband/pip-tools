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
    if _pip_version.PIP_VERSION_MAJOR_MINOR >= (26, 0):
        cmdoptions.check_release_control_exclusive(options)
