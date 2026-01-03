from __future__ import annotations

import sys

from piptools._internal import _subprocess


def test_run_python_snippet_returns_multilne():
    result = _subprocess.run_python_snippet(
        sys.executable, r'print("MULTILINE\nOUTPUT", end="")'
    )
    assert result == "MULTILINE\nOUTPUT"
