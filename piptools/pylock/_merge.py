"""Translate many per-variant resolutions into one per-package view."""

from __future__ import annotations

import typing as _t
from collections import defaultdict
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from packaging.markers import Marker
from packaging.version import InvalidVersion, Version
from pip._internal.req import InstallRequirement
from pip._vendor.resolvelib.resolvers import Result

from .._compat import canonicalize_name
from ..exceptions import PipToolsError
from ..utils import strip_extras
from ._marker_ast import has_top_level_or
from ._marker_patch import patch_markers_attr
from ._urls import normalize_for_compare
from .markers import build_combined_marker
from .platforms import TargetEnvironment


@dataclass(frozen=True)
class VariantKey:
    """Identifier for one ``(env, extra, group)`` cell in the variant matrix."""

    env: str
    extra: str | None = None
    group: str | None = None

    def __str__(self) -> str:
        if self.extra is not None:
            return f"{self.env}+{self.extra}"
        if self.group is not None:
            return f"{self.env}@{self.group}"
        return self.env


# Aliases for the nested generics that thread through the resolve pipeline. They keep
# signatures readable and let Sphinx autodoc render a single name instead of trying
# to resolve every component of a nested ``dict[..., dict[..., tuple[...]]]`` as a
# cross-reference target.
PerVariantMap: _t.TypeAlias = (
    "dict[VariantKey, dict[str, tuple[str, InstallRequirement]]]"
)
ForwardDeps: _t.TypeAlias = "dict[str, set[str]]"


@dataclass
class ResolvedEntry:
    """One ``(name, version)`` pin alongside the variants that selected it."""

    requirement: InstallRequirement
    version: str
    environments: set[str] = field(default_factory=set)
    extras_needed: set[str] | None = None
    groups_needed: set[str] | None = None
    marker: str | None = None


def merge_resolutions(
    per_variant: PerVariantMap,
    all_env_keys: set[str],
    all_extras: tuple[str, ...] = (),
    all_groups: tuple[str, ...] = (),
) -> dict[str, list[ResolvedEntry]]:
    """Collapse per-variant resolutions into one entry list per package name.

    Each resulting entry covers one ``(name, version)`` and records the
    environments, extras, and groups under which that pin was selected.
    Picks the requirement representative most likely to carry user-supplied
    URL or VCS metadata when several variants resolved to the same pin.

    :param per_variant: Per-variant package map produced by the resolver.
    :param all_env_keys: Universe of environment keys (used for marker emission).
    :param all_extras: User-requested extras across the whole lock run.
    :param all_groups: User-requested dependency groups across the whole lock run.
    :returns: Mapping from package name to its ordered list of resolved entries.
    :raises PipToolsError: When two variants pin the same name and version to
        non-equivalent direct-URL sources.
    """
    by_name: defaultdict[str, defaultdict[str, list[VariantKey]]] = defaultdict(
        lambda: defaultdict(list)
    )
    requirements_by_pin: dict[tuple[str, str], InstallRequirement] = {}
    variant_by_pin: dict[tuple[str, str], VariantKey] = {}

    for variant, packages in per_variant.items():
        for name, (version, requirement) in packages.items():
            by_name[name][version].append(variant)
            # Prefer the variant whose requirement carries ``original_link``: that
            # field holds user-supplied URL/VCS metadata, and a coin-flip last-
            # write-wins would lose it whenever a sibling variant resolved the
            # same ``(name, version)`` through the index instead.
            existing = requirements_by_pin.get((name, version))
            existing_link = getattr(existing, "original_link", None)
            new_link = getattr(requirement, "original_link", None)
            if existing is None:
                requirements_by_pin[(name, version)] = requirement
                variant_by_pin[(name, version)] = variant
                continue
            if existing_link is None and new_link is not None:
                requirements_by_pin[(name, version)] = requirement
                variant_by_pin[(name, version)] = variant
                continue
            if existing_link is None and new_link is None:
                # Both sides came from the index (no user-supplied URL); prefer
                # the non-constraint requirement so the kept ireq carries the
                # full user-intent metadata (extras, markers) rather than the
                # bare ``-c`` reference, which has no extras / hash info.
                if getattr(existing, "constraint", False) and not getattr(
                    requirement, "constraint", False
                ):
                    requirements_by_pin[(name, version)] = requirement
                    variant_by_pin[(name, version)] = variant
                continue
            if existing_link is not None and new_link is not None:
                # Two distinct user-supplied direct-URL pins for the same pin
                # would silently lose one to last-write-wins; surface the
                # collision so the user can collapse the inputs themselves.
                # Compare normalized URLs so trivially-equivalent shapes
                # (trailing slash, userinfo, scheme casing) don't false-fire;
                # show the original spellings in the error and name both
                # variants so the user can find the offending input set.
                existing_url = getattr(existing_link, "url", None)
                new_url = getattr(new_link, "url", None)
                if normalize_for_compare(existing_url) != normalize_for_compare(
                    new_url
                ):
                    existing_variant = variant_by_pin.get((name, version))
                    raise PipToolsError(
                        f"Conflicting direct-URL pins for {name}=={version}: "
                        f"variant {existing_variant!s} pinned {existing_url!r}, "
                        f"variant {variant!s} pinned {new_url!r}. Pick one "
                        f"URL (or pin the package to a single specifier)."
                    )

    result: dict[str, list[ResolvedEntry]] = {}
    for name, versions in sorted(by_name.items()):
        entries: list[ResolvedEntry] = []
        for version, variants in sorted(versions.items(), key=_version_sort_key):
            env_keys = {v.env for v in variants}
            extras_from_variants = {v.extra for v in variants if v.extra is not None}
            groups_from_variants = {v.group for v in variants if v.group is not None}
            is_in_base = any(v.extra is None and v.group is None for v in variants)

            extras_needed = (
                extras_from_variants
                if not is_in_base and extras_from_variants
                else None
            )
            groups_needed = (
                groups_from_variants
                if not is_in_base and groups_from_variants
                else None
            )
            entries.append(
                ResolvedEntry(
                    requirement=requirements_by_pin[(name, version)],
                    version=version,
                    environments=env_keys,
                    extras_needed=extras_needed,
                    groups_needed=groups_needed,
                    marker=build_combined_marker(
                        env_keys, all_env_keys, extras_needed, groups_needed
                    ),
                )
            )
        _widen_base_marker_against_overrides(entries)
        result[name] = entries
    return result


def _widen_base_marker_against_overrides(entries: list[ResolvedEntry]) -> None:
    """When base resolves ``black==26.3.1`` and the conflict group ``black24``
    resolves ``black==24.1.0``, both entries land in ``entries`` with markers
    ``None`` and ``'black24' in dependency_groups``. Both fire under
    ``--group black24`` so ``ensure_marker_disjointness`` correctly detects a
    collision. The user's intent under ``--group black24`` is the conflict-group
    version, so widen the base entry's marker with ``'black24' not in
    dependency_groups`` and the two entries become disjoint.

    Mutates ``entries`` in place because the base entry is replaced with a new
    ``ResolvedEntry`` whose marker carries the negation; the caller already
    owns ``entries`` and the rename signals that the function rewrites it.
    """
    base_idx = next(
        (
            i
            for i, e in enumerate(entries)
            if e.extras_needed is None and e.groups_needed is None
        ),
        None,
    )
    if base_idx is None or len(entries) < 2:
        return
    base = entries[base_idx]
    overrides = [
        other
        for idx, other in enumerate(entries)
        if idx != base_idx and other.version != base.version
    ]
    excluded_extras: set[str] = set().union(
        *(other.extras_needed for other in overrides if other.extras_needed)
    )
    excluded_groups: set[str] = set().union(
        *(other.groups_needed for other in overrides if other.groups_needed)
    )
    if not excluded_extras and not excluded_groups:
        return
    negations: list[str] = []
    negations.extend(f"'{e}' not in extras" for e in sorted(excluded_extras))
    negations.extend(f"'{g}' not in dependency_groups" for g in sorted(excluded_groups))
    parts: list[str] = []
    if base.marker:
        # Without the wrap, a trailing ``and X`` appended to a top-level ``or``
        # marker would bind to the rightmost disjunct under PEP 508 precedence
        # and silently narrow the truth set; ``has_top_level_or`` reads the
        # parsed AST so the decision survives whitespace variations and does
        # not over-wrap when the ``or`` already lives inside parens.
        wrap = has_top_level_or(Marker(base.marker))
        parts.append(f"({base.marker})" if wrap else base.marker)
    parts.extend(negations)
    entries[base_idx] = ResolvedEntry(
        requirement=base.requirement,
        version=base.version,
        environments=base.environments,
        extras_needed=base.extras_needed,
        groups_needed=base.groups_needed,
        marker=" and ".join(parts),
    )


def _version_sort_key(
    item: tuple[str, list[VariantKey]],
) -> tuple[int, Version | str]:
    """Sort ``(version, variants)`` pairs by PEP 440 ordering, not lexically.

    String sort puts ``"1.10.0"`` before ``"1.2.0"``; honor PEP 440 instead and fall
    back to literal-string ordering for requirements whose pin is not a spec-compliant
    version (e.g. arbitrary VCS labels).
    """
    version_str = item[0]
    try:
        return (0, Version(version_str))
    except InvalidVersion:
        return (1, version_str)


def get_forward_dependencies(
    resolver_result: Result,
) -> dict[str, set[str]]:
    """Return the parent-to-child dependency map for real (non-extras) candidates.

    Strips synthetic extras candidates from both sides of every edge so the
    returned map mirrors the package graph the lockfile emits.

    :param resolver_result: The result the backtracking resolver produced for
        the resolution to summarise.
    :returns: Mapping from each real package name to the names of its direct
        runtime dependencies.
    """
    forward_deps: defaultdict[str, set[str]] = defaultdict(set)

    real_packages = {
        strip_extras(canonicalize_name(c.name))
        for c in resolver_result.mapping.values()
        if c.get_install_requirement() is not None
    }

    for candidate in resolver_result.mapping.values():
        if (
            parent_name := strip_extras(canonicalize_name(candidate.name))
        ) not in real_packages:
            continue
        for child_name in resolver_result.graph.iter_children(candidate.name):
            if child_name is None:
                continue
            stripped_child = strip_extras(canonicalize_name(child_name))
            if stripped_child != parent_name and stripped_child in real_packages:
                forward_deps[parent_name].add(stripped_child)

        if parent_name not in forward_deps:
            forward_deps[parent_name] = set()

    return dict(forward_deps)


def mock_marker_environment(
    env: TargetEnvironment | Mapping[str, str],
) -> AbstractContextManager[None]:
    """Override the marker default environment for the duration of the block.

    Lets the resolver evaluate markers against a chosen target environment
    instead of the host interpreter's actual environment.

    :param env: Marker variables that ``default_environment`` should return
        while the context is active.
    :returns: Context manager that installs and reverts the override.
    """
    snapshot = _t.cast("dict[str, str]", dict(env.items()))
    return patch_markers_attr("default_environment", lambda _m, _o: lambda: snapshot)


__all__ = [
    "ForwardDeps",
    "PerVariantMap",
    "ResolvedEntry",
    "VariantKey",
    "get_forward_dependencies",
    "merge_resolutions",
    "mock_marker_environment",
]
