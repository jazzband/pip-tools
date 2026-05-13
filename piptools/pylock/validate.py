"""Refuse pylock outputs that violate PEP 751 marker disjointness.

PEP 751 requires same-name ``[[packages]]`` entries to use markers no
installer can satisfy simultaneously. A naive check would iterate
``|envs| x 2^|extras| x 2^|groups|`` combinations, which hangs on real
projects with ``--all-extras --all-groups`` long before producing a result.

The fast path exploits pip-tools' emitted marker shape
``(opt-in disjunction) and <env clause>`` to reduce the problem to a
linear sweep over ``target_envs``: extras and groups can never make
pip-tools markers disjoint on their own (the user can always request the
union), so disjointness is determined by the env axis. The bounded
powerset stays as a safety net for markers whose shape we can't
recognize.
"""

from __future__ import annotations

import typing as _t
from itertools import combinations
from os import environ

from packaging.markers import Marker, UndefinedComparison, UndefinedEnvironmentName
from packaging.specifiers import InvalidSpecifier, SpecifierSet

from ..exceptions import MarkerDisjointnessError, PipToolsError
from ._marker_ast import MarkerShape, decompose
from .config import ConflictItem
from .platforms import TargetEnvironment, to_marker_env

if _t.TYPE_CHECKING:
    from ._merge import ResolvedEntry

# Override via ``PIP_TOOLS_POWERSET_FALLBACK_LIMIT`` to tune the ceiling.
# The default has to cover the ``--all-extras --all-groups`` working set
# across a representative platform matrix without raising. The symbolic
# shortcut covers pip-tools' own emitted shape, but user markers that mix
# environment and extra clauses routinely fall through. The default sits
# well past the realistic working set so common inputs don't trip the
# bail-out.
_POWERSET_FALLBACK_LIMIT: _t.Final[int] = int(
    environ.get("PIP_TOOLS_POWERSET_FALLBACK_LIMIT", "100000")
)


def ensure_marker_disjointness(
    merged: dict[str, list[ResolvedEntry]],
    target_envs: dict[str, TargetEnvironment],
    all_extras: tuple[str, ...],
    all_groups: tuple[str, ...],
    conflicts: list[list[ConflictItem]] | None = None,
) -> None:
    """Raise when two same-name lock entries can both match a single install.

    PEP 751 requires same-name package entries to carry mutually-exclusive
    markers. Detects collisions symbolically first, then falls back to a
    bounded powerset search across extras and groups when the symbolic
    shortcut is inconclusive.

    :param merged: Per-name ordered list of resolved entries.
    :param target_envs: Map of env keys to their marker environments.
    :param all_extras: Extras the lock covers; used to seed the powerset.
    :param all_groups: Dependency groups the lock covers; used to seed the powerset.
    :param conflicts: Conflict matrix that prunes impossible opt-in combinations.
    :raises MarkerDisjointnessError: When a pair of entries can both match
        a single install context.
    """
    conflicts = conflicts or []
    for name, entries in merged.items():
        if len(entries) < 2:
            continue
        markers = [Marker(e.marker) if e.marker else None for e in entries]
        pairs = combinations(enumerate(markers), 2)
        for (left_idx, left_marker), (right_idx, right_marker) in pairs:
            collision = _first_collision(
                left_marker,
                right_marker,
                target_envs,
                all_extras,
                all_groups,
                conflicts,
            )
            if collision is None:
                continue
            env_key, extras, groups = collision
            left_text = entries[left_idx].marker or "<no marker>"
            right_text = entries[right_idx].marker or "<no marker>"
            message = (
                f"Cannot lock {name!r}: versions "
                f"{entries[left_idx].version!r} (marker: {left_text!r}) and "
                f"{entries[right_idx].version!r} (marker: {right_text!r}) "
                f"both match environment {env_key!r} "
                f"(extras={sorted(extras)}, groups={sorted(groups)}). "
                f"PEP 751 requires same-name `[[packages]]` entries to have "
                f"mutually-exclusive markers. Pin {name!r} to a single "
                f"version (e.g. via a constraints file) so every variant "
                f"resolves to the same release."
            )
            if extras or groups:
                hint_parts: list[str] = []
                if len(extras) >= 2:
                    items = ", ".join(f'{{extra = "{e}"}}' for e in sorted(extras))
                    hint_parts.append(f"[[{items}]]")
                if len(groups) >= 2:
                    items = ", ".join(f'{{group = "{g}"}}' for g in sorted(groups))
                    hint_parts.append(f"[[{items}]]")
                if hint_parts:
                    message += (
                        " Or declare the overlapping axes as conflicting in "
                        "`[tool.pip-tools].conflicts`, e.g. "
                        f"`conflicts = [{', '.join(hint_parts)}]`."
                    )
            raise MarkerDisjointnessError(message)


def ensure_requires_python_consistency(
    merged: dict[str, list[ResolvedEntry]],
    pkg_requires_python: dict[tuple[str, str], str | None],
    target_envs: dict[str, TargetEnvironment],
) -> None:
    """Refuse the lock when a target env cannot satisfy a package's ``Requires-Python``.

    Cohort partitioning collapses envs that share a dep graph into one
    resolution, so a package whose ``Requires-Python`` rejects one python
    version could still replicate to that env if the cohort grouped it
    with a compatible one. Surfacing the inconsistency at lock time
    avoids a confusing post-install failure.

    :param merged: Per-name ordered list of resolved entries.
    :param pkg_requires_python: ``Requires-Python`` strings keyed by name and version.
    :param target_envs: Map of env keys to their marker environments.
    :raises PipToolsError: When a target env's python version falls outside
        the package's declared range.
    """
    for name, entries in merged.items():
        for entry in entries:
            raw = pkg_requires_python.get((name, entry.version))
            if not raw:
                continue
            try:
                spec = SpecifierSet(raw)
            except InvalidSpecifier:
                # Malformed ``Requires-Python`` strings should not abort
                # the lock; pip's own metadata path accepts plenty of
                # invalid forms in the wild and emits the field verbatim.
                # Skip the consistency check rather than crash here.
                continue
            for env_key in entry.environments:
                env = target_envs.get(env_key)
                if env is None:
                    continue
                full_version = env["python_full_version"]
                if not spec.contains(full_version, prereleases=True):
                    raise PipToolsError(
                        f"Package {name}=={entry.version} has Requires-Python "
                        f"{raw!r} but cohort partition retained target env "
                        f"{env_key!r} (python_full_version={full_version!r}). "
                        f"This drift would emit a lockfile entry the installer "
                        f"rejects on {env_key}. Workarounds: pass narrower "
                        f"--python-version flags so the lock only targets "
                        f"interpreters that satisfy {raw!r}; pass --no-universal "
                        f"to lock for the current host only; or constrain "
                        f"{name} to a release whose Requires-Python admits "
                        f"every targeted python_full_version."
                    )


def _first_collision(
    left: Marker | None,
    right: Marker | None,
    target_envs: dict[str, TargetEnvironment],
    all_extras: tuple[str, ...],
    all_groups: tuple[str, ...],
    conflicts: list[list[ConflictItem]],
) -> tuple[str, frozenset[str], frozenset[str]] | None:
    left_shape = decompose(left)
    right_shape = decompose(right)
    if left_shape is not None and right_shape is not None:
        return _first_collision_symbolic(
            left_shape, right_shape, target_envs, conflicts
        )
    return _first_collision_powerset(
        left, right, target_envs, all_extras, all_groups, conflicts
    )


def _first_collision_symbolic(
    left: MarkerShape,
    right: MarkerShape,
    target_envs: dict[str, TargetEnvironment],
    conflicts: list[list[ConflictItem]],
) -> tuple[str, frozenset[str], frozenset[str]] | None:
    extras_witness = _extras_witness(left.extras_in, right.extras_in)
    groups_witness = _extras_witness(left.groups_in, right.groups_in)
    if _subset_violates_conflicts(extras_witness, groups_witness, conflicts):
        # The witness is the smallest opt-in set covering both markers.
        # A user can never request that combination, so the markers can
        # never both fire; the conflict declaration *is* the disjointness
        # proof.
        return None
    for env_key, env_dict in target_envs.items():
        env = to_marker_env(env_dict)
        context: dict[str, str | _t.AbstractSet[str]] = {
            **env,
            "extras": set(extras_witness),
            "dependency_groups": set(groups_witness),
        }
        if _evaluate(left.env_marker, context) and _evaluate(right.env_marker, context):
            return env_key, extras_witness, groups_witness
    return None


def _extras_witness(left: frozenset[str], right: frozenset[str]) -> frozenset[str]:
    # Pick one element from each non-empty side. ``'X' in extras`` markers fire
    # on any superset, so the smallest set covering both sides is the union of
    # one-element samples.
    return frozenset(min(side) for side in (left, right) if side)


def _first_collision_powerset(
    left: Marker | None,
    right: Marker | None,
    target_envs: dict[str, TargetEnvironment],
    all_extras: tuple[str, ...],
    all_groups: tuple[str, ...],
    conflicts: list[list[ConflictItem]],
) -> tuple[str, frozenset[str], frozenset[str]] | None:
    iterations = 0
    for env_key, env_dict in target_envs.items():
        env = to_marker_env(env_dict)
        for extras_subset in _powerset(all_extras):
            extras_frozen = frozenset(extras_subset)
            for groups_subset in _powerset(all_groups):
                groups_frozen = frozenset(groups_subset)
                if _subset_violates_conflicts(extras_frozen, groups_frozen, conflicts):
                    # The user can never request a combination that violates a
                    # declared conflict, so a marker collision in that subspace
                    # is unobservable; skip without spending budget on it.
                    continue
                iterations += 1
                if iterations > _POWERSET_FALLBACK_LIMIT:
                    # PEP 751 forbids ambiguous installer matches;
                    # bailing out silently would flip a spec-mandated
                    # error into an install-time bug. Raise so the user
                    # narrows the markers, reduces extras/groups, or
                    # lifts ``PIP_TOOLS_POWERSET_FALLBACK_LIMIT`` once
                    # the cost is acceptable.
                    raise MarkerDisjointnessError(
                        f"Marker disjointness check exceeded the "
                        f"{_POWERSET_FALLBACK_LIMIT}-iteration powerset budget "
                        f"for envs={len(target_envs)} extras={len(all_extras)} "
                        f"groups={len(all_groups)}; the symbolic shortcut "
                        f"could not prove disjointness for these markers. "
                        f"Narrow the markers, reduce extras/groups, or raise "
                        f"the bound via PIP_TOOLS_POWERSET_FALLBACK_LIMIT "
                        f"once the cost is acceptable."
                    )
                context: dict[str, str | _t.AbstractSet[str]] = {
                    **env,
                    "extras": set(extras_subset),
                    "dependency_groups": set(groups_subset),
                }
                if _evaluate(left, context) and _evaluate(right, context):
                    return env_key, extras_frozen, groups_frozen
    return None


def _subset_violates_conflicts(
    extras: frozenset[str],
    groups: frozenset[str],
    conflicts: list[list[ConflictItem]],
) -> bool:
    """Return True if an installer cannot request all of ``extras``+``groups``.

    Each conflict group declares a set of extras/groups the user has marked as
    mutually exclusive. The user requesting two or more items from the same
    conflict group is what the declaration forbids; the resolver runs separate
    passes for each, so the validator can skip the combination entirely
    instead of reporting a collision the installer would never observe.
    """
    for group in conflicts:
        count = 0
        for item in group:
            if (item.kind == "extra" and item.name in extras) or (
                item.kind == "group" and item.name in groups
            ):
                count += 1
                if count >= 2:
                    return True
    return False


def _evaluate(
    marker: Marker | None, context: dict[str, str | _t.AbstractSet[str]]
) -> bool:
    if marker is None:
        return True
    try:
        return bool(marker.evaluate(context))
    except (UndefinedComparison, UndefinedEnvironmentName):
        return False


def _powerset(items: tuple[str, ...]) -> _t.Iterator[tuple[str, ...]]:
    for size in range(len(items) + 1):
        yield from combinations(items, size)


__all__ = [
    "ensure_marker_disjointness",
    "ensure_requires_python_consistency",
]
