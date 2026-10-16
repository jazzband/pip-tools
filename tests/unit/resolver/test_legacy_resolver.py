from __future__ import annotations

import contextlib
import pathlib
import typing as _t

import pytest

from piptools.cache import DependencyCache
from piptools.exceptions import PipToolsError
from piptools.repositories.base import BaseRepository
from piptools.resolver import LegacyResolver


@pytest.mark.parametrize(
    "enabled", (pytest.param(True, id="enabled"), pytest.param(False, id="disabled"))
)
def test_legacy_resolver_init_only_succeeds_if_flag_is_enabled(
    repository: BaseRepository,
    depcache: DependencyCache,
    tmp_path: pathlib.Path,
    enabled: bool,
) -> None:
    """
    Test that, given a repository object, a legacy resolver can only be initialized if
    the options contain the ``legacy-resolver`` flag.
    """
    # `context` is a `pytest.raises()` context manager or a nullcontext depending on
    # which case we are testing -- nullcontext effectively requires that is no error
    context: contextlib.AbstractContextManager[_t.Any]
    if enabled:
        repository.options.deprecated_features_enabled = ["legacy-resolver"]
        context = contextlib.nullcontext()
    else:
        repository.options.deprecated_features_enabled = []
        context = pytest.raises(
            PipToolsError, match="Legacy resolver deprecated feature must be enabled."
        )

    with context:
        LegacyResolver(
            repository=repository,
            constraints=[],
            existing_constraints={},
            cache=depcache,
        )
