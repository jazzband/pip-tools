from __future__ import annotations

import pytest

from piptools.exceptions import PipToolsError
from piptools.resolver import LegacyResolver


def test_legacy_resolver_checks_that_deprecated_feature_is_enabled(
    repository, depcache, tmp_path
):
    # first, as a sanity check, confirm that a LegacyResolver can be constructed
    # in the process, also construct some baseline init args
    init_args = {"constraints": [], "existing_constraints": {}, "cache": depcache}
    LegacyResolver(repository=repository, **init_args)

    # having confirmed those args work, try with a repo object which does not enable
    # the legacy resolver and confirm that it errors
    repository.options.deprecated_features_enabled = []
    with pytest.raises(
        PipToolsError, match="Legacy resolver deprecated feature must be enabled."
    ):
        LegacyResolver(repository=repository, **init_args)
