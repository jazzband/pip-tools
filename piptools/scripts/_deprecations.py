"""Module to deprecate script arguments."""

from __future__ import annotations

from ..logging import log
from ..utils import PIP_VERSION


def filter_deprecated_pip_args(args: list[str]) -> list[str]:
    """
    Warn about and drop pip args that are no longer supported by pip.

    Currently drops:

    - ``--use-pep517``
    - ``--no-use-pep517``
    - ``--global-option``
    - ``--build-option``
    """
    if PIP_VERSION < (25, 3):  # pragma: <3.9 cover
        return args

    deprecation_mapping = {
        "--use-pep517": "Pip always uses PEP 517 for building projects now.",
        "--no-use-pep517": "Pip always uses PEP 517 for building projects now.",
        "--global-option": (
            "--config-setting is now the only way to pass options to the build backend."
        ),
        "--build-option": (
            "--config-setting is now the only way to pass options to the build backend."
        ),
    }
    supported_args = []
    for arg in args:
        opt_key = arg.split("=")[0]
        try:
            warn_msg = deprecation_mapping[opt_key]
        except KeyError:
            supported_args.append(arg)
        else:
            log.warning(
                "WARNING: "
                f"{arg} is no longer supported by pip and is deprecated in pip-tools. "
                "This option is ignored and will result in errors in a future release. "
                f"{warn_msg}"
            )

    return supported_args
