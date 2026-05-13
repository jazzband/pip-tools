"""``pip-lock`` console-script entry point.

The entry-point string ``pip-lock = piptools.scripts.lock:cli`` resolves
here for parity with ``pip-compile``/``pip-sync``. The command itself
lives in the pylock CLI package.
"""

from __future__ import annotations

from ..pylock.cli import cli

__all__ = [
    "cli",
]
