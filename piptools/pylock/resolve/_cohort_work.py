"""Resolve one cohort across the user's extras and dependency groups.

Both the in-process orchestrator and the parallel worker funnel into
this single body, which keeps the sequential and parallel paths from
drifting on the parts that matter to correctness (the resolver
invocations, the constraint preparation, the cache-clear semantics on
the first pass).
"""

from __future__ import annotations

from copy import deepcopy

from pip._internal.req import InstallRequirement

from ...cache import DependencyCache
from ...exceptions import NoCandidateFound, PipToolsError
from ...logging import log
from ...repositories import PyPIRepository
from ...resolver import BacktrackingResolver
from ...utils import drop_extras, key_from_ireq
from .._inputs import ResolverOptions
from .._merge import (
    ForwardDeps,
    PerVariantMap,
    VariantKey,
    get_forward_dependencies,
    mock_marker_environment,
)
from ..platforms import TargetEnvironment, to_marker_env
from ..sources import requirement_version
from ._splice_extras import splice_combined_extras
from ._state import ResolutionState, ResolverInputs, VariantSlice


def resolve_cohort_work(
    *,
    cohort_envs: list[str],
    target_envs: dict[str, TargetEnvironment],
    repository: PyPIRepository,
    inputs: ResolverInputs,
    options: ResolverOptions,
) -> tuple[PerVariantMap, ForwardDeps]:
    """Run a cohort's per-extra and per-group resolutions in the current process.

    Pulled out of the orchestrator so the same body runs sequentially in the
    parent process or dispatches to a worker. Cache clearing is owned by the
    orchestrator so siblings cannot race the rmtree.

    :param cohort_envs: Environment keys this cohort covers.
    :param target_envs: Map of every env key to its marker environment.
    :param repository: Repository the resolutions consume.
    :param inputs: Constraints and per-group requirement lists.
    :param options: Resolver tuning knobs.
    :returns: A pair of the per-variant package map and the forward-deps map
        produced by every resolution in the cohort.
    """
    state = ResolutionState()
    rep_dict = target_envs[next(iter(cohort_envs))]

    for extra_label, extra_set in inputs.extras_configs:
        with mock_marker_environment(to_marker_env(rep_dict)):
            constraints = [
                deepcopy(req)
                for req in inputs.raw_constraints
                if req.match_markers(extra_set)
            ]
            for req in constraints:
                drop_extras(req)

            _run_resolution_replicated(
                slice=VariantSlice(env_keys=cohort_envs, extra=extra_label, group=None),
                constraints=constraints,
                repository=repository,
                options=options,
                state=state,
            )
        # The combined-extras pass folds every non-conflicting extra into one
        # resolution; split its result back into per-extra variant entries so
        # ``merge_resolutions`` can still emit per-extra markers.
        if extra_label is None and extra_set:
            splice_combined_extras(
                cohort_envs=cohort_envs,
                raw_constraints=inputs.raw_constraints,
                combined_extras=extra_set,
                forward_deps=state.all_forward_deps,
                per_variant=state.per_variant,
            )

    for group_label, groups_set in inputs.group_configs:
        if group_label is None:
            continue
        with mock_marker_environment(to_marker_env(rep_dict)):
            constraints = [
                deepcopy(req) for req in inputs.raw_constraints if req.match_markers(())
            ]
            for req in constraints:
                drop_extras(req)
            constraints.extend(
                deepcopy(r)
                for group_name in groups_set
                for r in inputs.group_constraints.get(group_name, [])
            )

            _run_resolution_replicated(
                slice=VariantSlice(env_keys=cohort_envs, extra=None, group=group_label),
                constraints=constraints,
                repository=repository,
                options=options,
                state=state,
            )

    repository._clear_finder_cache()
    return state.per_variant, state.all_forward_deps


def _run_resolution_replicated(
    *,
    slice: VariantSlice,
    constraints: list[InstallRequirement],
    repository: PyPIRepository,
    options: ResolverOptions,
    state: ResolutionState,
) -> None:
    rep_variant = VariantKey(
        env=slice.env_keys[0], extra=slice.extra, group=slice.group
    )
    log.debug(
        f"Resolving for {rep_variant} (replicating to {len(slice.env_keys)} env(s))..."
    )
    _run_resolution(
        variant=rep_variant,
        constraints=constraints,
        repository=repository,
        options=options,
        state=state,
    )
    rep_result = state.per_variant[rep_variant]
    for env_key in slice.env_keys[1:]:
        replica = VariantKey(env=env_key, extra=slice.extra, group=slice.group)
        state.per_variant[replica] = dict(rep_result)


def _run_resolution(
    *,
    variant: VariantKey,
    constraints: list[InstallRequirement],
    repository: PyPIRepository,
    options: ResolverOptions,
    state: ResolutionState,
) -> None:
    try:
        resolver = BacktrackingResolver(
            constraints=constraints,
            existing_constraints={},
            repository=repository,
            prereleases=options.prereleases,
            cache=DependencyCache(options.cache_dir),
            # The orchestrator clears caches once before any cohort dispatch
            # (see ``_orchestrate.resolve``); doing it again here would race
            # sibling workers that already opened files in ``cache_dir``.
            clear_caches=False,
            allow_unsafe=options.allow_unsafe,
            unsafe_packages=set(options.unsafe_packages),
        )
        results = resolver.resolve(max_rounds=options.max_rounds)
    except NoCandidateFound as e:
        # ``NoCandidateFound`` carries pip-internal ``PackageFinder`` /
        # ``InstallRequirement`` state that doesn't pickle cleanly across
        # ``ProcessPoolExecutor``'s IPC boundary; the parent would receive a
        # ``BrokenProcessPool`` with no ``except NoCandidateFound`` match.
        # Convert to a picklable ``PipToolsError`` carrying the formatted
        # message so the orchestrator's handler still fires under
        # ``--jobs > 1``.
        log.error(f"Resolution failed for {variant}: {e}")
        raise PipToolsError(str(e)) from None
    except PipToolsError as e:
        log.error(f"Resolution failed for {variant}: {e}")
        raise

    for name, deps in get_forward_dependencies(resolver._resolver_result).items():
        state.all_forward_deps.setdefault(name, set()).update(deps)

    state.per_variant[variant] = {
        key_from_ireq(requirement): (
            requirement_version(requirement) or "",
            requirement,
        )
        for requirement in results
    }


__all__ = [
    "resolve_cohort_work",
]
