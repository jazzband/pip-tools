"""Translate many per-variant resolutions into one per-package view."""

from __future__ import annotations

import typing as _t
from collections import defaultdict
from dataclasses import dataclass, field

from packaging.markers import Marker
from packaging.version import InvalidVersion, Version
from pip._internal.req import InstallRequirement

from ..exceptions import PipToolsError
from ._marker_ast import has_top_level_or
from ._urls import normalize_for_compare
from .markers import build_combined_marker


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


# Aliases for the nested generics that thread through the resolve pipeline. They keep signatures
# readable and let Sphinx autodoc render a single name rather than chasing every component of a
# nested ``dict[..., dict[..., tuple[...]]]`` as a cross-reference target.
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

    Each resulting entry covers one ``(name, version)`` and records the environments, extras, and
    groups whose resolution selected that pin. Picks the requirement whose metadata carries
    user-supplied URL or VCS information when several variants resolved to the same pin.

    :param per_variant: Per-variant package map the resolver produces.
    :param all_env_keys: Universe of environment keys the marker emitter uses.
    :param all_extras: User-requested extras across the whole lock run.
    :param all_groups: User-requested dependency groups across the whole lock run.
    :returns: Mapping from package name to its ordered list of resolved entries.
    :raises PipToolsError: When two variants pin the same name and version to non-equivalent
        direct-URL sources.
    """
    by_name: defaultdict[str, defaultdict[str, list[VariantKey]]] = defaultdict(
        lambda: defaultdict(list)
    )
    requirements_by_pin: dict[tuple[str, str], InstallRequirement] = {}
    variant_by_pin: dict[tuple[str, str], VariantKey] = {}

    for variant, packages in per_variant.items():
        for name, (version, requirement) in packages.items():
            by_name[name][version].append(variant)
            # Prefer the variant whose requirement carries ``original_link``: that field holds
            # user-supplied URL/VCS metadata, and a coin-flip last-write-wins drops it whenever a
            # sibling variant resolves the same ``(name, version)`` through the index instead.
            existing = requirements_by_pin.get((name, version))
            existing_link = existing.original_link if existing is not None else None
            new_link = requirement.original_link
            if existing is None:
                requirements_by_pin[(name, version)] = requirement
                variant_by_pin[(name, version)] = variant
                continue
            if existing_link is None and new_link is not None:
                requirements_by_pin[(name, version)] = requirement
                variant_by_pin[(name, version)] = variant
                continue
            if existing_link is None and new_link is None:
                # Both sides came from the index (no user-supplied URL); prefer the non-constraint
                # requirement so the kept ireq carries the full user-intent metadata (extras,
                # markers) rather than the bare ``-c`` reference, which has no extras or hash info.
                if existing.constraint and not requirement.constraint:
                    requirements_by_pin[(name, version)] = requirement
                    variant_by_pin[(name, version)] = variant
                continue
            if existing_link is not None and new_link is not None:
                # Two distinct user-supplied direct-URL pins for the same pin lose one to
                # last-write-wins; surface the collision so the user can collapse the inputs.
                # Compare normalized URLs so equivalent shapes (trailing slash, userinfo, scheme
                # casing) do not false-fire; show the original spellings in the error and name
                # both variants so the user can find the offending input set.
                if normalize_for_compare(existing_link.url) != normalize_for_compare(
                    new_link.url
                ):
                    existing_variant = variant_by_pin.get((name, version))
                    raise PipToolsError(
                        f"Conflicting direct-URL pins for {name}=={version}: "
                        f"variant {existing_variant!s} pinned {existing_link.url!r}, "
                        f"variant {variant!s} pinned {new_link.url!r}. Pick one "
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
    """Negate override extras/groups in the base entry's marker.

    When base resolves ``black==26.3.1`` and the conflict group ``black24`` resolves
    ``black==24.1.0``, both entries land in ``entries`` with markers ``None`` and
    ``'black24' in dependency_groups``. Both fire under ``--group black24`` so
    ``ensure_marker_disjointness`` flags a collision. The user's intent under ``--group black24``
    is the conflict-group version, so widen the base entry's marker with
    ``'black24' not in dependency_groups`` and the two entries become disjoint.

    Mutates ``entries`` in place: this function replaces the base entry with a new
    ``ResolvedEntry`` whose marker carries the negation. The caller owns ``entries``; the
    function name records the rewrite.
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
        # Without the wrap, a trailing ``and X`` appended to a top-level ``or`` marker binds to
        # the rightmost disjunct under PEP 508 precedence and narrows the truth set;
        # ``has_top_level_or`` reads the parsed AST so the decision survives whitespace
        # variations and does not over-wrap when the ``or`` already lives inside parens.
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

    String sort puts ``"1.10.0"`` before ``"1.2.0"``; honor PEP 440 instead and fall back to
    literal-string ordering for requirements whose pin is not a spec-compliant version (e.g.
    arbitrary VCS labels).
    """
    version_str = item[0]
    try:
        return (0, Version(version_str))
    except InvalidVersion:
        return (1, version_str)


__all__ = [
    "ForwardDeps",
    "PerVariantMap",
    "ResolvedEntry",
    "VariantKey",
    "merge_resolutions",
]
