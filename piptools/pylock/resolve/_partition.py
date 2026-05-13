"""Find which target environments share a dep graph.

Two envs that resolve to the same packages don't need separate
resolutions, but the resolver doesn't know that up front. This module
discovers the equivalence by scanning once per python version with
platform markers neutralised, then signing every env against the
env-distinguishing markers the scan observed: same signature, same
cohort. A failed scan falls back to one cohort per env, so worst case
the caller pays the NxM cost it was already prepared for.
"""

from __future__ import annotations

import typing as _t
from collections import defaultdict
from contextlib import AbstractContextManager
from copy import deepcopy

from packaging.markers import (
    InvalidMarker,
    Marker,
    UndefinedComparison,
    UndefinedEnvironmentName,
)
from pip._internal.req import InstallRequirement

from ...cache import DependencyCache
from ...exceptions import PipToolsError
from ...logging import log
from ...repositories import PyPIRepository
from ...resolver import BacktrackingResolver
from ...utils import drop_extras
from .._inputs import ResolverOptions
from .._marker_ast import (
    PLATFORM_MARKER_KEYS,
    make_platform_blind_evaluator,
    verify_packaging_marker_shape,
)
from .._marker_patch import patch_markers_attr
from .._merge import mock_marker_environment
from ..platforms import TargetEnvironment, to_marker_env
from ._state import ResolverInputs


def partition_envs_by_marker_equivalence(
    *,
    target_envs: dict[str, TargetEnvironment],
    repository: PyPIRepository,
    inputs: ResolverInputs,
    options: ResolverOptions,
) -> list[list[str]]:
    """Group target environments into cohorts that share a dependency graph.

    Falls back to one cohort per env when the scan cannot complete or its
    collected markers cannot be evaluated against an env. A partition
    failure can never produce a wrong lock, only a slower one. Scanning
    blinds the resolver to platform markers so the scan graph spans every
    platform-conditional dependency reachable from the user's constraints
    under each unique python version.

    :param target_envs: Environments to partition.
    :param repository: Repository used by the discovery resolution.
    :param inputs: Constraints feeding the discovery scan.
    :param options: Resolver options forwarded to the scan resolver.
    :returns: A list of cohorts, each a list of environment keys to resolve together.
    """
    envs_by_python: defaultdict[str, list[str]] = defaultdict(list)
    for env_key, env_dict in target_envs.items():
        envs_by_python[env_dict["python_full_version"]].append(env_key)
    partition_markers: set[str] = set()
    failed_pythons: dict[str, list[str]] = {}
    for python_full_version, env_keys in envs_by_python.items():
        scan_resolver = _scan_with_retry(
            python_full_version=python_full_version,
            env_dict=to_marker_env(target_envs[env_keys[0]]),
            repository=repository,
            options=options,
            inputs=inputs,
        )
        if scan_resolver is None:
            # Preserve per-python granularity on partial failure: only
            # python versions whose scan blew up fall back to per-env,
            # while the others keep their cohort collapse. A network-blip
            # on one python doesn't drag the whole matrix to N x M.
            failed_pythons[python_full_version] = list(env_keys)
            continue
        partition_markers.update(_collect_partition_markers(scan_resolver))

    failed_envs = {k for keys in failed_pythons.values() for k in keys}
    successful_envs = [k for k in target_envs if k not in failed_envs]
    parsed_markers: list[Marker] = []
    for marker_str in sorted(partition_markers):
        try:
            parsed_markers.append(Marker(marker_str))
        except InvalidMarker as err:
            log.debug(f"Skipping unparseable scan marker {marker_str!r}: {err}")

    cohorts: list[list[str]] = []
    if successful_envs:
        if not parsed_markers:
            # No env-distinguishing markers reached the resolver for any of
            # the successful pythons, so those envs share a dep set; one
            # cohort skips N-1 resolutions for them.
            cohorts.append(successful_envs)
        else:
            grouped: defaultdict[tuple[bool | None, ...], list[str]] = defaultdict(list)
            for env_key in successful_envs:
                env = to_marker_env(target_envs[env_key])
                evaluated: list[bool | None] = []
                for marker in parsed_markers:
                    try:
                        evaluated.append(bool(marker.evaluate(dict(env))))
                    except (UndefinedComparison, UndefinedEnvironmentName):
                        evaluated.append(None)
                grouped[tuple(evaluated)].append(env_key)
            cohorts.extend(grouped.values())
    # Per-python failures keep their per-env granularity rather than being
    # grouped: the scan never produced markers for that python so a shared
    # signature would falsely collapse envs the failed scan should have
    # disambiguated.
    cohorts.extend([env_key] for env_key in failed_envs)
    log.debug(
        f"Marker-driven discovery collapsed {len(target_envs)} envs into "
        f"{len(cohorts)} resolution cohort(s)."
    )
    return cohorts


def _scan_with_retry(
    *,
    python_full_version: str,
    env_dict: dict[str, str],
    repository: PyPIRepository,
    options: ResolverOptions,
    inputs: ResolverInputs,
) -> BacktrackingResolver | None:
    """Run the marker-discovery scan once, retry once on failure.

    A transient network blip during the scan would otherwise force one
    cohort per env for the whole matrix; one extra attempt is cheap
    relative to that 17xNx slowdown and is the smallest-blast-radius
    response for the common flaky-CI failure mode.
    """
    last_err: PipToolsError | None = None
    for attempt in range(2):
        try:
            return _scan_resolve(
                constraints=_scan_constraints(inputs),
                env_dict=env_dict,
                repository=repository,
                options=options,
            )
        except PipToolsError as err:
            last_err = err
            if attempt == 0:
                log.debug(
                    f"Marker-discovery scan for python {python_full_version} "
                    f"failed ({err}); retrying once before falling back."
                )
    log.warning(
        f"Marker-discovery scan for python {python_full_version} "
        f"failed twice ({last_err}); falling back to per-env resolution "
        f"for that python only."
    )
    return None


def _scan_constraints(inputs: ResolverInputs) -> list[InstallRequirement]:
    """Build the partition-scan input set, skipping conflicting groups.

    The scan must not filter by host markers. The discovery resolution
    runs under ``mock_marker_environment(target)`` for each
    ``python_full_version``, so ``req.match_markers()`` here would
    evaluate against the *host* ``default_environment()`` and drop
    python-conditional inputs (e.g. ``tomli; python_version < '3.11'``
    on 3.13), then the partition would collapse envs that genuinely
    need separate resolutions.

    Group inputs need extra care: a naive union across every config
    would include conflict-declared groups that pin incompatible
    specifiers, and the scan resolver would raise
    ``RequirementsConflicted`` before any cohort resolution runs. Take
    the *intersection* across non-base configs (the set
    ``build_group_configs`` shares across all conflict families,
    ``non_conflicting + (label,)`` for each label) so the scan only
    sees the groups every per-cohort resolution will see too.
    """
    constraints = [deepcopy(req) for req in inputs.raw_constraints]
    for req in constraints:
        drop_extras(req)
    non_base_configs = [
        frozenset(groups) for label, groups in inputs.group_configs if label is not None
    ]
    if non_base_configs:
        scan_groups: frozenset[str] = frozenset.intersection(*non_base_configs)
    else:
        scan_groups = frozenset()
    constraints.extend(
        deepcopy(r)
        for group_name in scan_groups
        for r in inputs.group_constraints.get(group_name, [])
    )
    return constraints


def _scan_resolve(
    *,
    constraints: list[InstallRequirement],
    env_dict: dict[str, str],
    repository: PyPIRepository,
    options: ResolverOptions,
) -> BacktrackingResolver:
    with mock_marker_environment(env_dict), platform_blind_marker_eval():
        resolver = BacktrackingResolver(
            constraints=constraints,
            existing_constraints={},
            repository=repository,
            prereleases=options.prereleases,
            cache=DependencyCache(options.cache_dir),
            # Cache clearing is owned by the orchestrator (it has to happen
            # before any worker touches the shared ``cache_dir``); the scan must
            # never trigger it again or it would race the very workers it is
            # about to feed.
            clear_caches=False,
            allow_unsafe=options.allow_unsafe,
            unsafe_packages=set(options.unsafe_packages),
        )
        resolver.resolve(max_rounds=options.max_rounds)
        return resolver


def platform_blind_marker_eval() -> AbstractContextManager[None]:
    """Force the marker evaluator to treat platform clauses as always true.

    The discovery scan resolves once per python version. Without this patch,
    a platform-conditional dependency would surface only when resolving against
    that platform. Python-version comparisons stay honored so the partition
    can still distinguish python-conditional cohorts.

    Patches ``_evaluate_markers`` rather than the per-comparison helper
    because the latter's signature has shifted across pip releases while
    the former has stayed stable.

    :returns: Context manager that installs and reverts the patch.
    :raises PipToolsError: When the marker AST shape has moved.
    """
    verify_packaging_marker_shape()
    return patch_markers_attr("_evaluate_markers", make_platform_blind_evaluator)


_PARTITION_MARKER_KEYS: _t.Final[frozenset[str]] = PLATFORM_MARKER_KEYS | {
    "python_version",
    "python_full_version",
    "implementation_name",
    "implementation_version",
}


def _collect_partition_markers(scan_resolver: BacktrackingResolver) -> set[str]:
    """Return env-referencing markers seen during a scan resolution.

    Walks the resolvelib ``Result`` directly: pip-tools' wrapper does
    not surface pip's per-ireq markers, and resolvelib's criteria carry
    the same data with the marker attached to each information record.
    Markers referencing only ``extras`` or ``dependency_groups`` are
    dropped because those axes split out into their own resolution
    passes, so emitting them here would collapse envs that the
    per-extra / per-group passes already separate.

    Raises ``PipToolsError`` if criteria exist but none carry markers;
    that combination is effectively impossible in practice and signals
    that pip's or resolvelib's internal shape has moved. Surface it as
    an error to mirror the disjointness check's "fail loud rather than
    silently produce a wrong lock" stance: collapsing every env into
    one cohort under a broken introspection would replicate the
    rep-env's resolution to envs that genuinely diverge.
    """
    found: set[str] = set()
    result = getattr(scan_resolver, "_resolver_result", None)
    if result is None:
        return found
    saw_criterion_with_markers = False
    for criterion in result.criteria.values():
        for info in criterion.information:
            requirement = getattr(info.requirement, "_ireq", None)
            req = getattr(requirement, "req", None) if requirement is not None else None
            marker = getattr(req, "marker", None)
            if marker is None:
                continue
            saw_criterion_with_markers = True
            marker_str = str(marker)
            if any(key in marker_str for key in _PARTITION_MARKER_KEYS):
                found.add(marker_str)
    if result.criteria and not saw_criterion_with_markers:
        # Marker-free projects hit this path normally so a default-on
        # warning would be too noisy; ``info`` matches the "Locking for
        # N platforms x M python versions" line. The criterion count
        # lets a reporter distinguish "no deps at all" from "criteria
        # present but markers missing".
        log.info(
            f"Marker-discovery scan resolved but extracted zero markers "
            f"across {len(result.criteria)} criteria. Single-cohort "
            f"collapse is correct for projects with no env-conditional "
            f"deps; if your lock has such deps, please report (pip's "
            f"resolver introspection shape may have moved)."
        )
    return found


__all__ = [
    "partition_envs_by_marker_equivalence",
    "platform_blind_marker_eval",
]
