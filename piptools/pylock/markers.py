"""Marker-string composition for the pylock pipeline."""

from __future__ import annotations

from collections import defaultdict

from .platforms import (
    PLATFORM_ENVIRONMENTS,
    PlatformEnvironment,
    _best_effort_platform_env,
    parse_env_key,
)

# Bucket for env keys that don't follow the ``platform-version-impl``
# shape (bare platform names in legacy callers). Keeps the legacy
# single-axis codepath reachable so old callers don't crash.
_BARE_AXIS: tuple[str, str] = ("", "")


def build_combined_marker(
    platform_envs: set[str],
    all_envs: set[str],
    extras_needed: set[str] | None,
    groups_needed: set[str] | None = None,
) -> str | None:
    """Compose the marker that selects ``platform_envs`` and any opt-ins.

    Joins an opt-in clause (extras and groups) with a platform clause so the
    resulting marker fires only when both halves match.

    :param platform_envs: Environments the marker should select.
    :param all_envs: Universe the marker is evaluated against.
    :param extras_needed: Extras that must be opted into for the marker to fire.
    :param groups_needed: Dependency groups that must be opted into.
    :returns: The composed marker string, or ``None`` when no narrowing is needed.
    """
    opt_in_clauses: list[str] = []

    if extras_needed is not None:
        opt_in_clauses.extend(f"'{e}' in extras" for e in sorted(extras_needed))
    if groups_needed is not None:
        opt_in_clauses.extend(
            f"'{g}' in dependency_groups" for g in sorted(groups_needed)
        )

    parts: list[str] = []
    if opt_in_clauses:
        if len(opt_in_clauses) == 1:
            parts.append(opt_in_clauses[0])
        else:
            parts.append("(" + " or ".join(opt_in_clauses) + ")")

    if (
        platform_marker := compute_platform_marker(platform_envs, all_envs)
    ) is not None:
        parts.append(platform_marker)

    return " and ".join(parts) if parts else None


def compute_platform_marker(envs: set[str], all_envs: set[str]) -> str | None:
    """Return the marker that selects ``envs`` out of ``all_envs``.

    Reasons about the (python-version, implementation) cell each env belongs
    to and the platform within the cell so a package pulled in on one
    python or under CPython emits the narrowest correct clause, instead of
    over-firing on impls or pythons it never resolved against.

    :param envs: Environment keys the marker must include.
    :param all_envs: Universe of environment keys the marker is evaluated against.
    :returns: The platform marker string, or ``None`` when ``envs`` covers
        the entire universe and no narrowing is required.
    """
    if envs == all_envs:
        return None

    envs_by_cell = _group_by_axes(envs)
    universe_by_cell = _group_by_axes(all_envs)

    sub_markers: dict[tuple[str, str], str | None] = {
        cell: _platform_only_marker(plats, universe_by_cell[cell])
        for cell, plats in envs_by_cell.items()
    }

    multi_py = len({cell[0] for cell in universe_by_cell}) > 1
    multi_impl = len({cell[1] for cell in universe_by_cell}) > 1

    if (
        set(envs_by_cell) == set(universe_by_cell)
        and len(set(sub_markers.values())) == 1
    ):
        # Every cell present and every cell shares the platform shape:
        # python and impl carry no information.
        return next(iter(sub_markers.values()))

    clauses: list[str] = []
    for cell in sorted(envs_by_cell):
        version, implementation = cell
        sub = sub_markers[cell]
        cell_clauses: list[str] = [] if sub is None else [sub]
        if multi_py and version:
            key = "python_full_version" if version.count(".") >= 2 else "python_version"
            cell_clauses.append(f"{key} == '{version}'")
        if multi_impl and implementation:
            cell_clauses.append(f"implementation_name == '{implementation}'")
        if cell_clauses:
            clauses.append(" and ".join(cell_clauses))

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return f"({' or '.join(clauses)})"


def _group_by_axes(envs: set[str]) -> dict[tuple[str, str], set[str]]:
    """Bucket ``<platform>-<version>-<impl>`` env keys by (version, impl).

    Bare platform keys (no version/impl suffix) bucket under ``_BARE_AXIS``
    so the legacy single-axis callers still work.
    """
    grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
    for env_key in envs:
        platform, version, implementation = parse_env_key(env_key)
        if version and "." in version and platform and implementation:
            grouped[(version, implementation)].add(platform)
        else:
            grouped[_BARE_AXIS].add(env_key)
    return grouped


def _platform_only_marker(envs: set[str], all_envs: set[str]) -> str | None:
    if envs == all_envs:
        return None

    by_platform: dict[str, set[str]] = defaultdict(set)
    for plat in envs:
        by_platform[_platform_env(plat)["sys_platform"]].add(plat)

    clauses: list[str] = []
    for sys_plat in sorted(by_platform):
        present = by_platform[sys_plat]
        all_for_os = {
            p for p in all_envs if _platform_env(p)["sys_platform"] == sys_plat
        }
        if present == all_for_os:
            clauses.append(f"sys_platform == '{sys_plat}'")
        else:
            for p in sorted(present):
                machine = _platform_env(p)["platform_machine"]
                clauses.append(
                    f"sys_platform == '{sys_plat}' and platform_machine == '{machine}'"
                )

    if len(clauses) == 1:
        return clauses[0]
    return f"({' or '.join(clauses)})"


def _platform_env(plat: str) -> PlatformEnvironment:
    """Return the marker-env dict for ``plat`` whether or not it's a preset.

    ``--platform freebsd-amd64`` flows through the click validator and
    ``build_target_environments`` synthesises an env for it via
    ``_best_effort_platform_env``. This composer honors the same
    fallback so the per-package marker doesn't ``KeyError`` on inputs the
    rest of the pipeline accepted.
    """
    if plat in PLATFORM_ENVIRONMENTS:
        return PLATFORM_ENVIRONMENTS[plat]
    return _best_effort_platform_env(plat)


__all__ = [
    "build_combined_marker",
    "compute_platform_marker",
]
