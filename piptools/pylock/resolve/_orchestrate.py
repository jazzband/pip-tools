"""Coordinate the resolve pipeline so callers see one entry point."""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context

from ..._internal import _pip_caches
from ...logging import log
from ...repositories import PyPIRepository
from .._inputs import (
    LockInputs,
    LockSelection,
    LockTargets,
    ResolverOptions,
    WorkerSpec,
)
from .._merge import (
    ForwardDeps,
    PerVariantMap,
    ResolvedEntry,
    merge_resolutions,
)
from ..config import build_extras_configs, build_group_configs
from ..platforms import TargetEnvironment
from ._cohort_work import resolve_cohort_work
from ._partition import partition_envs_by_marker_equivalence
from ._state import ResolutionState, ResolverInputs
from ._worker import init_worker_repository, resolve_cohort_in_worker


def resolve(
    *,
    repository: PyPIRepository,
    inputs: LockInputs,
    selection: LockSelection,
    targets: LockTargets,
    options: ResolverOptions,
    workers: WorkerSpec,
) -> tuple[dict[str, list[ResolvedEntry]], ForwardDeps]:
    """Resolve every variant for every target environment and merge the results.

    Partitions the target environments into cohorts that share a dependency
    graph, dispatches one resolution per cohort (in-process or in a worker
    pool), and merges the per-variant results into one entry list per package.

    :param repository: Repository the cohort resolutions consume.
    :param inputs: Constraints, conflicts, and per-group requirement lists.
    :param selection: Extras and groups the lock should cover.
    :param targets: Target environments and partitioning hints.
    :param options: Resolver tuning knobs and cache directory.
    :param workers: Worker pool configuration for parallel cohort resolution.
    :returns: A pair of merged entries (by name) and the forward-deps map.
    """
    state = ResolutionState()
    resolver_inputs = ResolverInputs(
        raw_constraints=inputs.raw_constraints,
        extras_configs=build_extras_configs(selection.extras, inputs.conflicts),
        group_configs=build_group_configs(selection.groups, inputs.conflicts),
        group_constraints=inputs.group_constraints,
    )

    if options.rebuild:
        # Clear caches once up front, before any cohort can race for the same
        # ``cache_dir``. Doing the clear inside the first cohort (against pip's
        # ``BacktrackingResolver(clear_caches=True)``) is unsafe under
        # ``--jobs > 1`` because sibling workers are already reading the same
        # download directory the rmtree would wipe.
        repository.clear_caches()
        _pip_caches.clear()

    # Perf shortcut, not a correctness gate. Skip the partition scan when no
    # two envs share a ``(sys_platform, python_version)`` signature. The scan
    # verifies each env's dep graph on its own, so this sharpens the perf cut
    # without changing the grouping.
    cohort_signatures: set[tuple[str, str]] = set()
    can_share_cohort = False
    for env in targets.target_envs.values():
        signature = (env["sys_platform"], env["python_version"])
        if signature in cohort_signatures:
            can_share_cohort = True
            break
        cohort_signatures.add(signature)
    if targets.discover_envs and len(targets.target_envs) > 1 and can_share_cohort:
        env_cohorts = partition_envs_by_marker_equivalence(
            target_envs=targets.target_envs,
            repository=repository,
            inputs=resolver_inputs,
            options=options,
        )
    else:
        env_cohorts = [[env_key] for env_key in targets.target_envs]

    for cohort_per_variant, cohort_forward_deps in _dispatch_cohorts(
        env_cohorts=env_cohorts,
        target_envs=targets.target_envs,
        repository=repository,
        inputs=resolver_inputs,
        options=options,
        workers=workers,
    ):
        state.per_variant.update(cohort_per_variant)
        for name, deps in cohort_forward_deps.items():
            state.all_forward_deps.setdefault(name, set()).update(deps)

    all_env_keys = {v.env for v in state.per_variant}
    merged = merge_resolutions(
        state.per_variant, all_env_keys, selection.extras, selection.groups
    )
    return merged, state.all_forward_deps


def _dispatch_cohorts(
    *,
    env_cohorts: list[list[str]],
    target_envs: dict[str, TargetEnvironment],
    repository: PyPIRepository,
    inputs: ResolverInputs,
    options: ResolverOptions,
    workers: WorkerSpec,
) -> Iterator[tuple[PerVariantMap, ForwardDeps]]:
    """Stream cohort results, in-process or via a process pool.

    Cohorts share no state (``rep_env``, constraints, and resolver state
    never cross cohort boundaries), so the parallel branch matches the
    sequential one for correctness. Marker patching is a per-worker
    global, and each worker drains its tasks in sequence.

    The worker count caps at the cohort count and short-circuits to an
    in-process loop at 1, so ``--jobs 1`` and tiny locks skip the
    fork-and-pickle overhead that would dwarf the resolver work.
    """
    worker_count = min(workers.jobs, len(env_cohorts))
    if worker_count <= 1:
        for cohort_envs in env_cohorts:
            yield resolve_cohort_work(
                cohort_envs=cohort_envs,
                target_envs=target_envs,
                repository=repository,
                inputs=inputs,
                options=options,
            )
        return

    # Build the PyPIRepository inside each worker rather than pickle one
    # across the IPC boundary. pip's vendored ``CacheControlAdapter``
    # fails to round-trip pickle (its ``__setstate__`` reads
    # ``_ssl_context``, which ``__getstate__`` never sets), and sharing
    # a connection pool across processes would be unsound regardless.
    # Construction takes a few hundred ms, bounded once per worker.
    if log.verbosity >= 1:
        log.debug(
            f"Dispatching {len(env_cohorts)} cohort(s) across "
            f"{worker_count} worker process(es)."
        )
    pip_args = list(workers.pip_args)
    # Pin ``spawn`` rather than letting Python pick the platform default.
    # ``fork`` (Linux's default) clones the parent process state,
    # including any open SSL sockets the partition scan left in pip's
    # ``requests.Session`` keep-alive pool. Forked workers race the
    # parent on those file descriptors, producing flaky network errors
    # that no retry survives. ``spawn`` re-imports per worker, and
    # ``init_worker_repository`` then builds one repo per worker, so the
    # marginal cost over fork is the import alone.
    pool = ProcessPoolExecutor(
        max_workers=worker_count,
        initializer=init_worker_repository,
        initargs=(pip_args, options.cache_dir),
        mp_context=get_context("spawn"),
    )
    try:
        futures = [
            pool.submit(
                resolve_cohort_in_worker,
                cohort_envs=cohort_envs,
                target_envs=target_envs,
                inputs=inputs,
                options=options,
            )
            for cohort_envs in env_cohorts
        ]
        try:
            # Drain in submission order so the merge step sees results in
            # a deterministic sequence. The lockfile sorts everything, and
            # stable ordering keeps logs and tests reproducible.
            for future in futures:
                yield future.result()
        except BaseException:
            # On a cohort failure, stop pulling sibling results and mark unstarted
            # futures canceled so the caller doesn't pay for work whose output we
            # are about to discard.
            for pending in futures:
                pending.cancel()
            raise
    finally:
        # ``cancel_futures`` (3.9+) drops queued-but-unstarted submissions on
        # shutdown; in-flight workers still run to completion because pip's
        # resolver is not interruptible from outside the worker.
        pool.shutdown(wait=True, cancel_futures=True)


__all__ = [
    "resolve",
]
