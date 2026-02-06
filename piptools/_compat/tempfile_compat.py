"""
Compatibility helpers for :mod:`tempfile` usage across platforms
and python versions.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import typing as _t
from collections.abc import Iterator


@contextlib.contextmanager
def named_temp_file(mode: str = "wt") -> Iterator[_t.IO[str]]:
    """
    A safe wrapper over NamedTemporaryFile for usage on Windows as well as
    POSIX systems.

    The issue we have is that we cannot guarantee that ``pip`` will open temporary
    files on Windows with ``O_TEMPORARY`` when passed the path, resulting in surprising
    behavior.
    """
    temp_file = tempfile.NamedTemporaryFile(mode=mode, delete=False)
    yield temp_file
    temp_file.close()
    os.unlink(temp_file.name)
