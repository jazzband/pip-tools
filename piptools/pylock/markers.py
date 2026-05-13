"""Marker-string composition for the pylock pipeline."""

from __future__ import annotations

from collections import defaultdict

from .platforms import (
    PLATFORM_ENVIRONMENTS,
    PlatformEnvironment,
    _best_effort_platform_env,
    parse_env_key,
)


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
    """Return the marker that selects exactly ``envs`` out of ``all_envs``.

    Reasons about both the platform and the python-version dimensions so a
    package pulled in only on one python version across every platform emits
    a python-only clause rather than a platform disjunction.

    :param envs: Environment keys the marker must include.
    :param all_envs: Universe of environment keys the marker is evaluated against.
    :returns: The platform marker string, or ``None`` when ``envs`` already covers
        the entire universe and no narrowing is required.
    """
    if envs == all_envs:
        return None

    envs_by_python = _group_by_python(envs)
    universe_by_python = _group_by_python(all_envs)

    sub_markers: dict[str, str | None] = {
        py: _platform_only_marker(plats, universe_by_python[py])
        for py, plats in envs_by_python.items()
    }

    if (
        set(envs_by_python) == set(universe_by_python)
        and len(set(sub_markers.values())) == 1
    ):
        # Every python is partially or fully present and they all share
        # the same platform shape; the python-version dimension carries
        # no information and can be dropped.
        return next(iter(sub_markers.values()))

    clauses: list[str] = []
    for py in sorted(envs_by_python):
        sub = sub_markers[py]
        # `python_version` is MAJOR.MINOR; only switch to `python_full_version`
        # when the user supplied a patch component.
        key = "python_full_version" if py.count(".") >= 2 else "python_version"
        py_clause = f"{key} == '{py}'"
        clauses.append(py_clause if sub is None else f"{sub} and {py_clause}")

    if len(clauses) == 1:
        return clauses[0]
    return f"({' or '.join(clauses)})"


def _group_by_python(envs: set[str]) -> dict[str, set[str]]:
    """Bucket ``<platform>-<version>-<impl>`` env keys by their version.

    Bare platform keys (no version suffix) bucket under the empty string
    so the single-python codepath stays available.
    """
    grouped: dict[str, set[str]] = defaultdict(set)
    for env_key in envs:
        platform, version, _ = parse_env_key(env_key)
        if version and "." in version and platform:
            grouped[version].add(platform)
        else:
            grouped[""].add(env_key)
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
    rest of the pipeline already accepted.
    """
    if plat in PLATFORM_ENVIRONMENTS:
        return PLATFORM_ENVIRONMENTS[plat]
    return _best_effort_platform_env(plat)


__all__ = [
    "build_combined_marker",
    "compute_platform_marker",
]
