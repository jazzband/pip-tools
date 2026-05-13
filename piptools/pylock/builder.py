"""Build a pylock document from resolved entries and CLI options."""

from __future__ import annotations

import typing as _t
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from packaging.markers import Marker
from packaging.pylock import Package, PackageSdist, PackageWheel, Pylock
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version
from pip._internal.utils.misc import redact_auth_from_url

from .._internal import _pip_caches
from ..exceptions import PipToolsError
from ..logging import log
from ..repositories import PyPIRepository
from ._inputs import (
    LockInputs,
    LockSelection,
    LockTargets,
    ResolverOptions,
    ToolMetadataOptions,
    WorkerSpec,
)
from ._marker_ast import verify_packaging_marker_shape
from ._merge import ResolvedEntry
from ._urls import index_match_key
from .config import extract_requires_python
from .markers import compute_platform_marker
from .platforms import PLATFORM_ENVIRONMENTS, TargetEnvironment, parse_env_key
from .resolve import resolve
from .sources import build_pylock_package, detect_source_type
from .tool_block import build as _build_tool_metadata
from .tool_block import to_dict as _tool_metadata_to_dict
from .validate import ensure_marker_disjointness, ensure_requires_python_consistency

_DistFilesByPin: _t.TypeAlias = (
    "dict[tuple[str, str], list[PackageWheel | PackageSdist]]"
)


def build_pylock_document(
    *,
    src_files: tuple[str, ...],
    repository: PyPIRepository,
    inputs: LockInputs,
    selection: LockSelection,
    targets: LockTargets,
    options: ResolverOptions,
    workers: WorkerSpec,
    metadata: ToolMetadataOptions,
    lock_dir: Path | None = None,
    project_requires_python: tuple[str, ...] = (),
) -> Pylock:
    """Resolve every target environment and assemble a PEP 751 lock document.

    :param src_files: Project metadata or requirement files the resolver consumes.
    :param repository: Index-backed source of candidate distributions and metadata.
    :param inputs: Constraints, conflicts, and dependency-group inputs to resolve.
    :param selection: Extras and groups to expand into the resolution.
    :param targets: Target environments and the user-supplied platform/python axes.
    :param options: Resolver-tuning knobs (prereleases, allow-unsafe, cache dir, max rounds).
    :param workers: Parallelism configuration for the cohort dispatch.
    :param metadata: Inputs for the optional ``[tool.pip-tools]`` block in the lock file.
    :param lock_dir: Directory the lock file lives in. Used to relativise local paths.
    :param project_requires_python: ``Requires-Python`` strings sourced from project metadata.
    :returns: A populated lock document ready for serialisation.
    :raises PipToolsError: When marker disjointness fails or input contracts are violated.
    """
    # The marker AST walker and extras collector reach into
    # ``Marker._markers``; a ``packaging`` release that rearranges that AST
    # produces wrong output without warning. The platform-blind rewriter
    # has its own deferred verify (skipped under ``--no-universal``), so
    # guard the always-run path here.
    verify_packaging_marker_shape()
    # Scope pip-helper caches to one lock command so successive in-process
    # invocations don't inherit each other's parsed-link state. Nested
    # ``scope()`` entries are no-ops, so a programmatic caller that already
    # opened a scope before invoking us doesn't double-revert on exit.
    with _pip_caches.scope():
        merged, forward_deps = resolve(
            repository=repository,
            inputs=inputs,
            selection=selection,
            targets=targets,
            options=options,
            workers=workers,
        )

        environments = _build_top_level_environments(
            targets.target_envs, targets.python_versions, targets.platforms
        )

        log.debug("")
        log.debug("Collecting distribution files:")
        # Multi-version entries (the case the cohort/partition machinery
        # supports) need per-release dist files and ``requires-python``.
        # Keying by name alone collapses every release onto whichever
        # variant lands at ``entries[0]``.
        with repository.allow_all_wheels(), log.indentation():
            dist_files_map: _DistFilesByPin = {}
            pkg_requires_python: dict[tuple[str, str], str | None] = {}
            for name, entries in merged.items():
                log.debug(name)
                for entry in entries:
                    key = (name, entry.version)
                    dist_files_map[key] = repository.get_distribution_files(
                        entry.requirement
                    )
                    pkg_requires_python[key] = repository.get_requires_python(
                        entry.requirement
                    )

        index_urls = tuple(repository.finder.index_urls)

        ensure_marker_disjointness(
            merged,
            targets.target_envs,
            selection.extras,
            selection.groups,
            inputs.conflicts,
        )
        ensure_requires_python_consistency(
            merged, pkg_requires_python, targets.target_envs
        )

        packages: list[Package] = [
            build_pylock_package(
                requirement=entry.requirement,
                dist_files=dist_files_map.get((name, entry.version), []),
                dependencies=_build_package_dependencies(
                    entry, forward_deps.get(name, set()), merged
                ),
                marker=entry.marker,
                index_url=_index_for_entry(entry, index_urls),
                requires_python=pkg_requires_python.get((name, entry.version)),
                lock_dir=lock_dir,
            )
            for name in sorted(merged)
            for entry in merged[name]
        ]

        requires_python = extract_requires_python(
            src_files,
            targets.python_versions,
            metadata_specifiers=project_requires_python,
        )
        tool = _build_tool_metadata(
            selection=selection,
            targets=targets,
            options=options,
            metadata=metadata,
        )
        return Pylock(
            lock_version=Version("1.0"),
            created_by="pip-tools",
            requires_python=(
                SpecifierSet(requires_python) if requires_python else None
            ),
            packages=packages,
            environments=([Marker(e) for e in environments] if environments else None),
            extras=(
                # PEP 503 normalisation collapses ``Foo-bar`` and
                # ``foo_bar`` to the same key; dedup *after* canonicalising
                # so the lockfile never carries duplicate entries that name
                # the same opt-in.
                sorted({canonicalize_name(e) for e in selection.extras})
                if selection.extras
                else None
            ),
            dependency_groups=(
                # PEP 735 §"Dependency Group Names" mandates the same PEP 503
                # normalisation for groups; PEP 751 inherits that.
                sorted({canonicalize_name(g) for g in selection.groups})
                if selection.groups
                else None
            ),
            default_groups=(
                sorted({canonicalize_name(g) for g in selection.default_groups})
                if selection.default_groups
                else None
            ),
            tool={"pip-tools": _tool_metadata_to_dict(tool)} if tool else None,
        )


def _build_top_level_environments(
    target_envs: dict[str, TargetEnvironment],
    python_versions: tuple[str, ...] = (),
    platforms: tuple[str, ...] = (),
) -> list[str]:
    """Compose top-level ``[[environments]]`` markers, one per (version, impl) cell."""
    envs_by_axis: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    platform_keys_by_axis: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for env_key in target_envs:
        platform, version, implementation = parse_env_key(env_key)
        axis = (version, implementation)
        envs_by_axis[axis].add(env_key)
        platform_keys_by_axis[axis].add(f"{platform}-{version}-{implementation}")
    user_versions = set(python_versions)
    promote_to_full = {v.rsplit(".", 1)[0] for v in user_versions if v.count(".") >= 2}
    implementations_in_use = {axis[1] for axis in envs_by_axis}
    environments: list[str] = []
    for version, implementation in sorted(envs_by_axis):
        env_dict = target_envs[next(iter(envs_by_axis[(version, implementation)]))]
        major_minor = version.rsplit(".", 1)[0] if version.count(".") >= 2 else version
        if (version in user_versions and version.count(".") >= 2) or (
            major_minor in promote_to_full
        ):
            clauses = [f"python_full_version == '{env_dict['python_full_version']}'"]
        else:
            clauses = [f"python_version == '{env_dict['python_version']}'"]
        if len(implementations_in_use) > 1:
            clauses.append(
                f"implementation_name == '{env_dict['implementation_name']}'"
            )
        platform_universe = set(PLATFORM_ENVIRONMENTS) | set(platforms)
        universe_for_axis = {
            f"{p}-{version}-{implementation}" for p in platform_universe
        }
        platform_marker = compute_platform_marker(
            envs_by_axis[(version, implementation)], universe_for_axis
        )
        if platform_marker is not None:
            clauses.insert(0, platform_marker)
        environments.append(" and ".join(clauses))
    return environments


def _build_package_dependencies(
    parent: ResolvedEntry,
    dep_names: set[str],
    merged: dict[str, list[ResolvedEntry]],
) -> list[dict[str, str]]:
    """Return dependency references that uniquely identify each ``[[packages]]`` entry.

    PEP 751 §packages.dependencies demands "the minimum information that
    uniquely identifies another [[packages]] entry"; a bare ``{name = "X"}``
    becomes ambiguous as soon as the lockfile carries more than one ``X``
    entry, so installers cannot pick a candidate deterministically.
    """
    deps: list[dict[str, str]] = []
    for dep_name in sorted(dep_names):
        candidates = merged.get(dep_name, [])
        if len(candidates) <= 1:
            deps.append({"name": dep_name})
            continue
        matching = [
            c
            for c in candidates
            if not parent.environments or c.environments & parent.environments
        ]
        if not matching:
            deps.append({"name": dep_name})
            continue
        if len(matching) > 1 and all(
            detect_source_type(c.requirement) in ("vcs", "directory") for c in matching
        ):
            # PEP 751 lets vcs/directory entries omit ``version`` and
            # pip-tools has nothing minimal-and-stable to disambiguate
            # them with. A bare ``{name = "X"}`` for each produces a dep
            # list that identifies zero specific candidate; raise so the
            # user collapses the inputs rather than shipping an unusable
            # lockfile.
            sources = ", ".join(
                str(c.requirement.original_link or c.requirement.link) for c in matching
            )
            raise PipToolsError(
                f"Cannot uniquely identify {dep_name!r} as a dependency of "
                f"{parent.requirement.name!r}: multiple vcs/directory variants "
                f"{sources!r} match the parent's environment, and PEP 751 "
                f"dependency references carry no information that distinguishes "
                f"them. Pin the requirement to a single source."
            )
        # PEP 751 requires the *minimum* information that uniquely
        # identifies the target. ``(name, version)`` covers it when each
        # matching candidate has a distinct version; when two share a
        # version but disagree on marker (e.g. one wheel for
        # ``python_version == '3.12'``, another for ``'3.13'``), the tied
        # candidates need the ``marker`` field. Adding it to siblings
        # whose version is unique emits non-minimal refs.
        version_groups: defaultdict[str, list[ResolvedEntry]] = defaultdict(list)
        for candidate in matching:
            version_groups[candidate.version].append(candidate)
        for candidate in matching:
            entry: dict[str, str] = {"name": dep_name}
            # PEP 751 lets ``directory``/``vcs`` entries omit ``version``,
            # so version is the wrong disambiguator there; the parent's
            # marker selects the right variant in those cases.
            if detect_source_type(candidate.requirement) not in ("vcs", "directory"):
                if disambig := candidate.version or None:
                    entry["version"] = disambig
            tied = len(version_groups[candidate.version]) > 1
            if tied and candidate.marker is not None:
                # round-trip so pass-through markers match Marker's canonical
                # form (single space around ==, double quotes, paren cleanup)
                entry["marker"] = str(Marker(candidate.marker))
            deps.append(entry)
    return deps


def _index_for_entry(entry: ResolvedEntry, index_urls: tuple[str, ...]) -> str | None:
    """Return the configured index that served this candidate, or ``None``.

    Defaulting every entry to ``finder.index_urls[0]`` leaks
    ``--extra-index-url`` packages back to public PyPI as the installer's
    fallback URL, which PEP 751's ``index`` semantics class as a security
    issue. Match by ``Link.comes_from`` first (the index page pip
    recorded), then host-and-port equality on the candidate URL; omit the
    field when neither proves which index served the candidate.
    """
    if not index_urls:
        return None
    link = entry.requirement.link
    if link is None:
        return None
    # Sort prefixes longest-first so a more-specific index (e.g.
    # ``https://a.com/simple/extras/``) wins over its parent
    # (``https://a.com/simple/``). Compare parsed (scheme, netloc, path)
    # rather than raw ``startswith``: ``simple`` byte-prefixes
    # ``simple-mirror`` but at the path-segment level the two are
    # disjoint, so byte comparison attributes one index's packages to its
    # similarly-named neighbour.
    sorted_indexes = sorted(index_urls, key=len, reverse=True)
    comes_from = link.comes_from
    if isinstance(comes_from, str):
        cf_parts = urlsplit(comes_from)
        for index_url in sorted_indexes:
            iu_parts = urlsplit(index_url)
            if (cf_parts.scheme, cf_parts.netloc) != (
                iu_parts.scheme,
                iu_parts.netloc,
            ):
                continue
            iu_path = iu_parts.path.rstrip("/")
            cf_path = cf_parts.path
            if cf_path == iu_path or cf_path.startswith(iu_path + "/"):
                return _t.cast("str", redact_auth_from_url(index_url))
    candidate_id = index_match_key(link.url)
    for index_url in sorted_indexes:
        if index_match_key(index_url) == candidate_id:
            return _t.cast("str", redact_auth_from_url(index_url))
    return None


__all__ = [
    "build_pylock_document",
]
