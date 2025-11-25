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
from .version import PIP_VERSION, get_pip_version_for_python_executable

__all__ = (
    "PIP_VERSION",
    "get_pip_version_for_python_executable",
    "create_install_requirement",
    "create_install_requirement_from_line",
    "copy_install_requirement",
)
