"""
Compatibility helpers for working with paths and :mod:`pathlib` across platforms
and Python versions.
"""

from __future__ import annotations

import os.path
import pathlib
import sys

__all__ = ("relative_to_walk_up",)


def relative_to_walk_up(path: pathlib.Path, start: pathlib.Path) -> pathlib.Path:
    """
    Compute a relative path allowing for the input to not be a subpath of the start.

    This is a compatibility helper for ``pathlib.Path.relative_to(..., walk_up=True)``
    on all Python versions. (``walk_up: bool`` is Python 3.12+)
    """
    # prefer `pathlib.Path.relative_to` where available
    if sys.version_info >= (3, 12):
        return path.relative_to(start, walk_up=True)

    str_result = os.path.relpath(path, start=start)
    return pathlib.Path(str_result)
