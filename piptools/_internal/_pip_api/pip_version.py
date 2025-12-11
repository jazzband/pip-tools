from __future__ import annotations

import pip
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

from ...subprocess_utils import run_python_snippet  # nosec

PIP_VERSION = parse_version(pip.__version__)
PIP_VERSION_TUPLE: tuple[int, ...] = tuple(
    map(int, PIP_VERSION.base_version.split("."))
)
PIP_VERSION_MAJOR_MINOR: tuple[int, int] = PIP_VERSION_TUPLE[:2]  # type: ignore[assignment]


def get_pip_version_for_python_executable(python_executable: str) -> Version:
    """Return pip version for the given python executable."""

    str_version = run_python_snippet(
        python_executable, "import pip; print(pip.__version__)"
    )
    return Version(str_version)
