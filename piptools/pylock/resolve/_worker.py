"""Run a cohort resolution in a worker without breaking the IPC boundary.

Resolved requirements carry pip-internal state that doesn't pickle
cleanly across process boundaries. Isolating that fragility here lets
the orchestrator keep treating worker results as plain Python objects,
and confines the blast radius of any Python upgrade that changes the
picklability of those internals to one file.
"""

from __future__ import annotations

import typing as _t

from pip._internal.req import InstallRequirement

from ..._internal import _pip_api, _pip_caches
from ...repositories import PyPIRepository
from .._inputs import ResolverOptions
from .._merge import ForwardDeps, PerVariantMap
from ..platforms import TargetEnvironment
from ._cohort_work import resolve_cohort_work
from ._state import ResolverInputs

_WORKER_REPOSITORY: PyPIRepository | None = None


def init_worker_repository(pip_args: list[str], cache_dir: str) -> None:
    """Install pip caches and build the per-worker repository on pool start.

    Worker processes exit on pool teardown, so install-only is fine here.
    Storing the repository on a module-global lets every task in the worker
    reuse it without re-pickling the finder.

    A future caller that reuses worker processes across multiple invocations
    would inherit these patches between runs. Wrap the worker body in
    ``scope()`` for symmetric cleanup, or ensure the pool is torn down
    between invocations as the current ``--jobs`` flow does.

    :param pip_args: Pip-style argv used to build the repository.
    :param cache_dir: Cache directory the repository should reuse.
    """
    global _WORKER_REPOSITORY
    _pip_caches.install()
    _WORKER_REPOSITORY = PyPIRepository(pip_args, cache_dir=cache_dir)


def resolve_cohort_in_worker(
    *,
    cohort_envs: list[str],
    target_envs: dict[str, TargetEnvironment],
    inputs: ResolverInputs,
    options: ResolverOptions,
) -> tuple[PerVariantMap, ForwardDeps]:
    """Run a cohort resolution in the current worker and return picklable results.

    :param cohort_envs: Environment keys this cohort covers.
    :param target_envs: Map of every env key to its marker environment.
    :param inputs: Constraints and per-group requirement lists.
    :param options: Resolver tuning knobs.
    :returns: A picklable pair of the per-variant map and forward-deps map.
    """
    assert (
        _WORKER_REPOSITORY is not None
    ), "init_worker_repository must run before any task is dispatched"  # noqa: S101
    per_variant, forward_deps = resolve_cohort_work(
        cohort_envs=cohort_envs,
        target_envs=target_envs,
        repository=_WORKER_REPOSITORY,
        inputs=inputs,
        options=options,
    )
    return _strip_per_variant_for_pickle(per_variant), forward_deps


def _strip_per_variant_for_pickle(per_variant: PerVariantMap) -> PerVariantMap:
    """Rebuild every requirement from a minimal spec before crossing the IPC boundary.

    Pip's resolved ``InstallRequirement`` carries pip-internal state
    attached during resolution: link bookkeeping, cachecontrol response
    objects, and on Python 3.14 an ``email.message.Message`` whose
    ``__new__`` no longer round-trips through pickle.
    ``ProcessPoolExecutor``'s worker-to-main transport pickles the result
    regardless, so each requirement is re-minted from
    ``(name, version, original_link)`` here. ``build_pylock_package``
    only reads name, version, link, and editable flag, so the rebuild
    preserves every field the lockfile writes.
    """
    return {
        variant: {
            name: (version, _lite_requirement(requirement, name, version))
            for name, (version, requirement) in packages.items()
        }
        for variant, packages in per_variant.items()
    }


# Fields set by ``_lite_requirement`` and therefore the only ones downstream
# consumers can rely on after ``--jobs > 1`` has gone through the pickle
# transport. Adding a new consumer that reads a different field has to update
# this list and ``_lite_requirement`` together so the contract stays explicit.
_LITE_REQUIREMENT_FIELDS: _t.Final[frozenset[str]] = frozenset(
    {
        "name",
        "specifier",
        "extras",
        "link",
        "original_link",
        "editable",
        "markers",
        "hash_options",
    }
)


def _lite_requirement(
    requirement: InstallRequirement, name: str, version: str
) -> InstallRequirement:
    original_link = requirement.original_link
    extras = sorted(requirement.req.extras) if requirement.req is not None else []
    extras_str = f"[{','.join(extras)}]" if extras else ""
    if original_link is not None:
        # PEP 508 direct-URL form ``name @ url`` round-trips the name;
        # the bare URL would land in ``install_req_from_line`` without a
        # name, produce ``req=None``, and surface in the writer as
        # ``name = ""``. That's invisible under ``--jobs 1`` (no pickle
        # path) but spec-invalid under ``--jobs > 1``.
        line = f"{name}{extras_str} @ {original_link.url}"
    elif version:
        line = f"{name}{extras_str}=={version}"
    else:
        # Editable / VCS / local-archive requirements may resolve without a PEP 440
        # version; fall back to a name-only spec rather than constructing an invalid
        # ``name==`` (which `Requirement` would reject as malformed).
        line = f"{name}{extras_str}"
    fresh = _pip_api.create_install_requirement_from_line(line)
    fresh.editable = requirement.editable
    # Round-tripping through the line form drops ``markers`` because PEP 508
    # markers don't survive ``install_req_from_line`` round-trips of a bare
    # ``name@url`` shape. The marker is what feeds per-extra attribution in
    # ``splice_combined_extras``; without it ``--jobs > 1`` would silently
    # collapse extras-only deps into base. Re-attach the original marker.
    original_markers = getattr(requirement, "markers", None)
    if original_markers is not None:
        fresh.markers = original_markers
    # ``--hash=sha256:...`` in a requirements file lands in ``hash_options``,
    # which the line round-trip discards. PEP 751's threat model treats
    # user-supplied hashes as authoritative; without re-attaching them the
    # writer would silently fall back to the index's digest under
    # ``--jobs > 1`` and the lockfile's hash source-of-truth would shift
    # away from the user's authoritative pin.
    original_hash_options = getattr(requirement, "hash_options", None)
    if original_hash_options:
        fresh.hash_options = original_hash_options
    return fresh


__all__ = [
    "init_worker_repository",
    "resolve_cohort_in_worker",
]
