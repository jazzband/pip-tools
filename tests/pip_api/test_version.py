from __future__ import annotations

import sys

import pip
from pip._vendor.packaging.version import Version

from piptools._pip_api import get_pip_version_for_python_executable


def test_get_pip_version_for_python_executable():
    result = get_pip_version_for_python_executable(sys.executable)
    assert Version(pip.__version__) == result
