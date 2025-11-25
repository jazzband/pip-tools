from __future__ import annotations

import subprocess  # nosec

import pip
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version

PIP_VERSION = tuple(map(int, parse_version(pip.__version__).base_version.split(".")))


def get_pip_version_for_python_executable(python_executable: str) -> Version:
    """Return pip version for the given python executable."""

    str_version = subprocess.check_output(  # nosec
        [python_executable, "-c", "import pip; print(pip.__version__)"],
        shell=False,
        text=True,
    )
    return Version(str_version)
