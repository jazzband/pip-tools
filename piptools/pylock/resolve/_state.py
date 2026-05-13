"""Internal dataclasses passed through the resolve pipeline.

The per-cohort loop and the marker-discovery scan share the same inputs
and per-call mutable state. Bundling them into dataclasses keeps call
sites inside the resolve package from drowning in 12-parameter
signatures and keeps the function bodies as the focus of every diff.

These types are private to the resolve package; the public ``resolve``
entry in ``_orchestrate`` decomposes the user-facing dataclasses
(``LockInputs`` / ``LockSelection`` / ``LockTargets`` /
``ResolverOptions``) into them.
"""

from __future__ import annotations

import typing as _t
from dataclasses import dataclass, field
from sys import version_info

from pip._internal.req import InstallRequirement

from .._merge import ForwardDeps, PerVariantMap

_KW_ONLY: _t.Final[dict[str, bool]] = (
    {"kw_only": True} if version_info >= (3, 10) else {}
)


@dataclass(frozen=True, **_KW_ONLY)
class ResolverInputs:
    """Constraints the per-cohort loop and partition scan share.

    ``extras_configs`` and ``group_configs`` are the result of expanding the user's
    extras/groups against the conflict matrix; both sub-pipelines need that expansion
    to know which extras/groups to bundle into a single resolution and which to keep
    separate.
    """

    raw_constraints: list[InstallRequirement]
    extras_configs: list[tuple[str | None, tuple[str, ...]]]
    group_configs: list[tuple[str | None, tuple[str, ...]]]
    group_constraints: dict[str, list[InstallRequirement]]


@dataclass(**_KW_ONLY)
class ResolutionState:
    """Mutable per-call accumulator threaded through nested resolution helpers.

    The orchestrator builds one of these and the per-cohort workers append to it;
    keeping the state in a single object avoids the "pass two long-lived dicts as
    out-parameters everywhere" pattern that nested resolver helpers would otherwise
    fall into.
    """

    per_variant: PerVariantMap = field(default_factory=dict)
    all_forward_deps: ForwardDeps = field(default_factory=dict)


@dataclass(frozen=True, **_KW_ONLY)
class VariantSlice:
    """One ``(extras x groups)`` cell evaluated against a list of envs.

    The same resolver result is replicated to every env in ``env_keys``
    because by construction they belong to the same cohort; running the
    resolver once per env would duplicate work the partition scan exists
    to avoid.
    """

    env_keys: list[str]
    extra: str | None
    group: str | None


__all__ = [
    "ResolutionState",
    "ResolverInputs",
    "VariantSlice",
]
