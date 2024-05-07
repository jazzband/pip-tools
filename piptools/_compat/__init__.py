from __future__ import annotations

from .pip_compat import (
    PIP_VERSION,
    Distribution,
    canonicalize_ireq,
    create_wheel_cache,
    get_dev_pkgs,
    install_req_from_line,
    parse_requirements,
)

__all__ = [
    "PIP_VERSION",
    "Distribution",
    "parse_requirements",
    "install_req_from_line",
    "create_wheel_cache",
    "get_dev_pkgs",
    "canonicalize_ireq",
]
