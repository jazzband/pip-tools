from __future__ import annotations

import sys

if sys.version_info >= (3, 10):
    from importlib.metadata import PackageMetadata
else:
    from typing import Any, Protocol, TypeVar, overload

    _T = TypeVar("_T")

    class PackageMetadata(Protocol):
        @overload
        def get_all(self, name: str, failobj: None = None) -> list[Any] | None: ...

        @overload
        def get_all(self, name: str, failobj: _T) -> list[Any] | _T: ...
