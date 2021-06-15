import sys

from piptools.subprocess_utils import run_python_snippet


def test_run_python_snippet_returns_multilne():
    result = run_python_snippet(sys.executable, r'print("MULTILINE\nOUTPUT", end="")')
    assert result == "MULTILINE\nOUTPUT"
