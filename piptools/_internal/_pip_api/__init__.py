"""
The ``piptools._pip_api`` subpackage defines an API layer on top of ``pip`` internals
and usage. It is a private API for the rest of ``piptools`` to leverage.
"""

from __future__ import annotations

from .install_requirements import (
    copy_install_requirement,
    create_install_requirement,
    create_install_requirement_from_line,
)
from .pip_version import (
    PIP_VERSION,
    PIP_VERSION_MAJOR_MINOR,
    PIP_VERSION_TUPLE,
    get_pip_version_for_python_executable,
)
from .requirement_utils import (
    format_requirement,
    format_specifier,
    is_pinned_requirement,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
    strip_extras,
)

__all__ = (
    # pip_version
    "PIP_VERSION",
    "PIP_VERSION_MAJOR_MINOR",
    "PIP_VERSION_TUPLE",
    "get_pip_version_for_python_executable",
    # install_requirements
    "create_install_requirement",
    "create_install_requirement_from_line",
    "copy_install_requirement",
    # requirement_utils
    "format_requirement",
    "format_specifier",
    "is_pinned_requirement",
    "is_url_requirement",
    "key_from_ireq",
    "key_from_req",
    "strip_extras",
)
