from __future__ import annotations

import os
import sys

import pytest

from piptools.scripts.compile import _determine_linesep


def test_determine_linesep_skips_stdin_placeholder() -> None:
    """
    Test that "-" (the stdin placeholder) is skipped when detecting the
    line separator, falling back to the default rather than attempting to
    open a file named "-".
    """
    assert _determine_linesep(filenames=("-",)) == "\n"


@pytest.mark.skipif(
    sys.platform == "win32", reason="os.mkfifo() not available on Windows"
)
def test_determine_linesep_skips_named_pipe(tmp_path) -> None:
    """
    Test that a named pipe (FIFO) is skipped when detecting the line
    separator, instead of being opened for a blocking read.

    Regression test for https://github.com/jazzband/pip-tools/issues/2232:
    ``_determine_linesep`` used to open every candidate filename for a
    binary read, which hangs forever on a FIFO with no writer connected.
    """
    fifo_path = tmp_path / "input.fifo"
    os.mkfifo(fifo_path)

    # No writer is ever connected to the FIFO. If _determine_linesep tried
    # to read from it, this call would hang and the test would time out.
    assert _determine_linesep(filenames=(str(fifo_path),)) == "\n"


def test_determine_linesep_falls_back_to_default_when_no_regular_file() -> None:
    """
    Test that the default separator is returned when none of the given
    filenames is a regular, existing file.
    """
    assert _determine_linesep(filenames=("-", "/no/such/file/exists.in")) == "\n"


@pytest.mark.parametrize(
    ("linesep", "expected_strategy_char"),
    [
        (b"\r\n", "\r\n"),
        (b"\n", "\n"),
    ],
)
def test_determine_linesep_still_detects_regular_file(
    tmp_path, linesep, expected_strategy_char
) -> None:
    """
    Test that regular files are still inspected normally, and take
    precedence over the "-" placeholder and non-regular files.
    """
    req_in = tmp_path / "requirements.in"
    req_in.write_bytes(b"six" + linesep)

    assert _determine_linesep(filenames=("-", str(req_in))) == expected_strategy_char
