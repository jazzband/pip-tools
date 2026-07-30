"""
The ``piptools._pip_api`` subpackage defines an API layer on top of ``pip`` internals
and usage. It is a private API for the rest of ``piptools`` to leverage.
"""

from __future__ import annotations

from .cli_options import postprocess_cli_options
from .command_methods import make_requirement_preparer_from_command
from .install_requirements import (
    copy_install_requirement,
    create_install_requirement,
    create_install_requirement_from_line,
)
from .package_finder import (
    finder_allows_all_prereleases,
    finder_allows_prereleases_of_req,
    request_failed_exception_types,
)
from .pip_version import (
    PIP_VERSION,
    PIP_VERSION_MAJOR_MINOR,
    PIP_VERSION_TUPLE,
    get_pip_version_for_python_executable,
)

__all__ = (
    "PIP_VERSION",
    "PIP_VERSION_MAJOR_MINOR",
    "PIP_VERSION_TUPLE",
    "get_pip_version_for_python_executable",
    "create_install_requirement",
    "create_install_requirement_from_line",
    "copy_install_requirement",
    "request_failed_exception_types",
    "finder_allows_all_prereleases",
    "finder_allows_prereleases_of_req",
    "postprocess_cli_options",
    "make_requirement_preparer_from_command",
)
