"""Construct ``BacktrackingResolver`` with the pylock-shared field set.

The partition scan and the cohort workers want the same eight-field
``BacktrackingResolver(...)`` call, differing in their constraints. A
single factory keeps the two call sites from drifting if pip's resolver
signature shifts and surfaces the project-wide invariant
(``clear_caches=False`` for both paths) in one place.
"""

from __future__ import annotations

from pip._internal.req import InstallRequirement

from ...cache import DependencyCache
from ...repositories import PyPIRepository
from ...resolver import BacktrackingResolver
from .._inputs import ResolverOptions


def make_resolver(
    *,
    constraints: list[InstallRequirement],
    repository: PyPIRepository,
    options: ResolverOptions,
) -> BacktrackingResolver:
    """Build a ``BacktrackingResolver`` configured for the pylock pipeline.

    The orchestrator owns cache clearing (see ``_orchestrate.resolve``) so every
    consumer here passes ``clear_caches=False``. Doing it again at this level
    would race sibling workers that opened files under ``cache_dir``.

    :param constraints: Install requirements feeding this resolution.
    :param repository: Repository the resolution consumes.
    :param options: Resolver tuning knobs (prereleases, allow-unsafe, max_rounds,
        cache_dir, unsafe_packages).
    :returns: A configured backtracking resolver instance ready to ``resolve()``.
    """
    return BacktrackingResolver(
        constraints=constraints,
        existing_constraints={},
        repository=repository,
        prereleases=options.prereleases,
        cache=DependencyCache(options.cache_dir),
        clear_caches=False,
        allow_unsafe=options.allow_unsafe,
        unsafe_packages=set(options.unsafe_packages),
    )


__all__ = ["make_resolver"]
