"""Context managers that swap marker evaluation entry points for a block.

Both helpers wrap ``_marker_patch.patch_markers_attr`` and expose named
operations so the resolve and merge layers stay ignorant of the
attribute-swap mechanism. Sitting next to the AST walker keeps the marker
manipulation surface in one place.
"""

from __future__ import annotations

import typing as _t
from collections.abc import Mapping
from contextlib import AbstractContextManager

from ._marker_ast import make_platform_blind_evaluator, verify_packaging_marker_shape
from ._marker_patch import patch_markers_attr
from .platforms import TargetEnvironment


def platform_blind_marker_eval() -> AbstractContextManager[None]:
    """Force the marker evaluator to treat platform clauses as always true.

    The discovery scan resolves once per python version. Without the patch a
    platform-conditional dependency would surface only when resolving against
    that platform. Python-version comparisons stay honored so the partition
    can split python-conditional cohorts.

    The patch targets ``_evaluate_markers`` instead of the per-comparison
    helper because the latter's signature has shifted across pip releases and
    the former has stayed stable.

    :returns: Context manager that installs and reverts the patch.
    :raises PipToolsError: When the marker AST shape has moved.
    """
    verify_packaging_marker_shape()
    return patch_markers_attr("_evaluate_markers", make_platform_blind_evaluator)


def mock_marker_environment(
    env: TargetEnvironment | Mapping[str, str],
) -> AbstractContextManager[None]:
    """Override the marker default environment for the duration of the block.

    Makes the resolver evaluate markers against a chosen target environment
    in place of the host interpreter's environment.

    :param env: Marker variables that ``default_environment`` returns while
        the context is active.
    :returns: Context manager that installs and reverts the override.
    """
    snapshot = _t.cast("dict[str, str]", dict(env.items()))
    return patch_markers_attr("default_environment", lambda _m, _o: lambda: snapshot)


__all__ = ["mock_marker_environment", "platform_blind_marker_eval"]
