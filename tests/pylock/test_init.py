from __future__ import annotations

import pytest

import piptools.pylock as pylock_pkg
from piptools.pylock import build_pylock_document


def test_build_pylock_document_resolves_via_lazy_getattr() -> None:
    # Lazy ``__getattr__`` exists to keep ``import piptools.pylock`` cheap for
    # type-only consumers; without exercising the public-name path the lazy
    # branch could regress to a stale return without anyone noticing.
    assert callable(build_pylock_document)


def test_unknown_attribute_raises_attribute_error() -> None:
    # Without the explicit ``AttributeError`` raise, a misspelled import would
    # silently return ``None`` from the lazy hook and fail far from the cause.
    with pytest.raises(AttributeError, match="no attribute 'nonexistent'"):
        pylock_pkg.nonexistent
