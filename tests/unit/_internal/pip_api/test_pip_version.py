from __future__ import annotations

import sys

import pip
from pip._vendor.packaging.version import Version

from piptools._internal import _pip_api


def test_get_pip_version_for_python_executable():
    result = _pip_api.get_pip_version_for_python_executable(sys.executable)
    assert Version(pip.__version__) == result
