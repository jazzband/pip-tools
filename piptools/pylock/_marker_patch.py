"""Swap an attribute on both ``packaging.markers`` modules for a block."""

from __future__ import annotations

import typing as _t
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import RLock
from types import ModuleType

from packaging import markers as _pkg
from pip._vendor.packaging import markers as _pm

# Mutating module-level attributes is process-wide; without a lock, two
# threads in the same process patching simultaneously would interleave the
# saves and one's restore would clobber the other's patch. The RLock makes
# patches mutually exclusive across threads (concurrent locks serialize
# rather than corrupt each other's view of ``packaging.markers``).
_PATCH_LOCK: _t.Final[RLock] = RLock()


@contextmanager
def patch_markers_attr(
    attr: str, replacement: Callable[[ModuleType, _t.Any], _t.Any]
) -> Iterator[None]:
    """Swap ``attr`` on both packaging marker modules for the duration of the block.

    Patches both the top-level packaging module and pip's vendored copy so
    every marker evaluator in-process honours the swap. Restores the original
    values on exit and serialises concurrent patches so threads cannot
    observe a half-swapped module.

    :param attr: Name of the attribute to replace on each marker module.
    :param replacement: Factory that receives the module being patched and its
        current attribute value, and returns the value to install in its place.
    :returns: Context manager yielding once the swap is in place.
    """
    modules: tuple[ModuleType, ModuleType] = (_pkg, _pm)
    with _PATCH_LOCK:
        saved = [(m, getattr(m, attr)) for m in modules]
        try:
            for module, original in saved:
                setattr(module, attr, replacement(module, original))
            yield
        finally:
            for module, original in saved:
                setattr(module, attr, original)


__all__ = [
    "patch_markers_attr",
]
