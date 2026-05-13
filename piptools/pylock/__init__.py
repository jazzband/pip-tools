"""PEP 751 ``pylock.toml`` generation for pip-tools."""

from __future__ import annotations

import typing as _t

if _t.TYPE_CHECKING:
    from .builder import build_pylock_document

__all__ = [
    "build_pylock_document",
]


def __getattr__(name: str) -> _t.Any:
    if name == "build_pylock_document":
        from .builder import build_pylock_document

        return build_pylock_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
