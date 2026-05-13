"""Resolve user-supplied platform / python-version / group inputs.

Owns the ``--platform current`` and ``--python-version current``
shorthand expansions, the universal-vs-explicit-target inference,
and the dependency-group resolution that feeds the cohort partitioner.
"""

from __future__ import annotations

import typing as _t
from sys import version_info

from click import BadParameter
from packaging.dependency_groups import DependencyGroupResolver
from packaging.errors import ExceptionGroup
from packaging.markers import default_environment
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from pip._internal.req import InstallRequirement

from ..._internal import _pip_api
from ...logging import log
from .._inputs import LockTargets
from ..config import load_dependency_groups_table
from ..platforms import PLATFORM_ENVIRONMENTS, build_target_environments


def resolve_groups(
    src_files: tuple[str, ...],
    groups: tuple[str, ...],
    all_groups: bool,
) -> tuple[dict[str, list[InstallRequirement]], tuple[str, ...]]:
    """Expand the requested PEP 735 groups into resolver constraints.

    :param src_files: Project files whose ``[dependency-groups]`` table is read.
    :param groups: Group names the user asked for.
    :param all_groups: When true, expand every group declared in the table.
    :returns: Mapping of each resolved group name to its constraint list, and
        the (possibly expanded) ordered tuple of group names.
    :raises click.BadParameter: When the group table is malformed or names an unknown group.
    """
    raw_groups = load_dependency_groups_table(src_files)
    try:
        resolver = DependencyGroupResolver(raw_groups)
    except ExceptionGroup as eg:
        # `packaging` wraps validation errors in an ExceptionGroup so it can report
        # several malformed entries together; the CLI surface needs a flat message,
        # so unwrap and concatenate the inner exceptions verbatim.
        raise BadParameter(
            "; ".join(str(e) for e in eg.exceptions), param_hint="--group"
        ) from eg
    if all_groups:
        groups = tuple(raw_groups.keys())
    if unknown_groups := [g for g in groups if g not in raw_groups]:
        # Dropping unknown groups would mask typos; surfacing them up front
        # tells the user the lockfile would not include the deps they expected.
        available = ", ".join(sorted(raw_groups)) or "(none defined)"
        raise BadParameter(
            f"unknown dependency group(s): {', '.join(unknown_groups)}. "
            f"Available: {available}.",
            param_hint="--group",
        )
    # Resolving every declared group when the user only asked for a subset
    # walks include-group chains we don't need; restrict to the selected
    # groups so projects with many declared groups (dev/test/lint/docs/...)
    # don't pay the resolution cost for ones they discarded.
    group_constraints: dict[str, list[InstallRequirement]] = {}
    for group_name in groups:
        try:
            resolved = resolver.resolve(group_name)
        except ExceptionGroup as eg:
            raise BadParameter(
                "; ".join(str(e) for e in eg.exceptions), param_hint="--group"
            ) from eg
        group_constraints[group_name] = [
            _pip_api.create_install_requirement_from_line(str(req)) for req in resolved
        ]
    return group_constraints, groups


def resolve_targets(
    platforms: tuple[str, ...],
    python_versions: tuple[str, ...],
    implementations: tuple[str, ...] = ("cpython",),
    no_universal: bool = False,
    project_requires_python: tuple[str, ...] = (),
) -> LockTargets:
    """Expand platform / python-version inputs into the lock target matrix.

    Honours ``current`` shorthand for both axes, derives the python axis from
    the project's ``requires-python`` when none is supplied on the command line,
    and decides whether the marker-driven cohort scan is worth running.

    :param platforms: Platform names supplied on the command line.
    :param python_versions: Python versions supplied on the command line.
    :param no_universal: Force a current-host-only resolution when true.
    :param project_requires_python: ``Requires-Python`` specifiers gathered from
        the project's ``pyproject.toml``. Used to derive the python axis when
        no ``--python-version`` is supplied so the universal lock covers every
        interpreter the project actually targets.
    :returns: The fully expanded lock targets bundle.
    :raises click.BadParameter: When ``current`` cannot be inferred for the host.
    """
    user_picked_platforms = bool(platforms)
    # ``--platform current`` is a shorthand for the host's auto-detected
    # preset; expand here so the rest of the pipeline sees concrete
    # platform names.
    if "current" in platforms:
        # ``_infer_platforms`` raises ``BadParameter(..., "--no-universal")``
        # for unknown hosts. The user spelled ``--platform current``, so
        # rewrap the flag name in both the message and the hint. The rest
        # of the message keeps the supported-presets list and the current
        # ``(sys_platform, platform_machine)`` context for picking a target.
        try:
            host_platform = _infer_platforms(no_universal=True)
        except BadParameter as exc:
            rewritten = str(exc.message).replace("--no-universal", "--platform current")
            raise BadParameter(rewritten, param_hint="--platform current") from exc
        # ``dict.fromkeys`` preserves order while collapsing duplicates so
        # ``--platform current --platform linux-x86_64`` on a Linux host
        # doesn't land ``("linux-x86_64", "linux-x86_64")`` in
        # ``[tool.pip-tools].platforms``.
        platforms = tuple(
            dict.fromkeys(host_platform[0] if p == "current" else p for p in platforms)
        )
    if not platforms:
        platforms = _infer_platforms(no_universal)
    # ``--python-version current`` mirrors ``--platform current`` and expands
    # to the host's ``MAJOR.MINOR``; users who want to lock just the
    # interpreter they're running can spell it once.
    if "current" in python_versions:
        host_version = f"{version_info.major}.{version_info.minor}"
        python_versions = tuple(
            dict.fromkeys(
                host_version if v == "current" else v for v in python_versions
            )
        )
    if not python_versions:
        # In universal mode, derive the python axis from the project's
        # ``requires-python`` so the lock covers every supported interpreter
        # by default. The host-only fallback applies when the project does
        # not declare one or when the user passes ``--no-universal``.
        if not no_universal and project_requires_python:
            python_versions = _expand_requires_python(project_requires_python)
        if not python_versions:
            python_versions = (f"{version_info.major}.{version_info.minor}",)
    if not implementations:
        implementations = ("cpython",)
    target_envs = build_target_environments(platforms, python_versions, implementations)
    if len(target_envs) > 1:
        # Cohort partitioning + per-env resolution scales with the matrix size;
        # surface a heads-up so progress is observable when the user lands a
        # large explicit matrix or a wide universal default.
        opt_out = (
            "Pass fewer --platform flags or --no-universal "
            "for current-host-only to narrow the matrix."
            if user_picked_platforms
            else "Pass --no-universal for current-host-only or --platform to "
            "narrow the matrix."
        )
        log.info(
            f"Locking for {len(platforms)} platforms x "
            f"{len(python_versions)} python versions "
            f"({len(target_envs)} target envs total). {opt_out}"
        )
    return LockTargets(
        target_envs=target_envs,
        platforms=platforms,
        python_versions=python_versions,
        implementations=implementations,
        no_universal=no_universal,
        # The marker-driven scan amortizes across every (platform, python)
        # cell by collapsing envs that share a dep graph into one cohort,
        # so it pays off whenever the matrix has more than one target,
        # including multiple explicit ``--platform`` flags.
        discover_envs=len(target_envs) > 1,
    )


# Range of CPython MAJOR.MINOR releases the universal-mode expander considers.
# The lower bound is pinned at the lowest CPython still receiving upstream
# security updates; older releases are end-of-life and do not deserve a slot
# in a fresh universal lock unless the user names one with ``--python-version``.
# The upper bound tracks the latest stable CPython at the time of writing.
_PYTHON_VERSION_FLOOR: _t.Final[tuple[int, int]] = (3, 10)
_PYTHON_VERSION_CEILING: _t.Final[tuple[int, int]] = (3, 14)


def _expand_requires_python(specifiers: tuple[str, ...]) -> tuple[str, ...]:
    """Return every CPython ``MAJOR.MINOR`` release that satisfies the specifiers.

    :param specifiers: Each ``Requires-Python`` specifier collected from project
        metadata. Composite ranges are intersected so the result is the strict
        subset every input admits.
    :returns: Sorted tuple of versions, narrowest matrix the universal lock
        must cover. Empty when no specifier parses or when the intersection
        excludes every supported release.
    """
    intersected = SpecifierSet()
    for raw in specifiers:
        try:
            intersected &= SpecifierSet(raw)
        except InvalidSpecifier:
            # Malformed specifiers should not abort the lock; pip's metadata
            # path tolerates plenty of invalid forms in the wild. Skip the bad
            # entry and let the remaining specifiers narrow the range.
            continue
    if not str(intersected):
        return ()
    # CPython has stayed on the 3.x line for over a decade; the floor and
    # ceiling sharing one major is the case worth materializing. A Python 4
    # release would force a wider candidate sweep, which is a design
    # discussion the universal lock should not pre-commit to.
    floor_major, floor_minor = _PYTHON_VERSION_FLOOR
    _, ceiling_minor = _PYTHON_VERSION_CEILING
    candidates = (
        f"{floor_major}.{minor}" for minor in range(floor_minor, ceiling_minor + 1)
    )
    return tuple(
        candidate
        for candidate in candidates
        if intersected.contains(candidate, prereleases=True)
    )


def _infer_platforms(no_universal: bool) -> tuple[str, ...]:
    if not no_universal:
        return tuple(PLATFORM_ENVIRONMENTS.keys())
    current_env = default_environment()
    matching = [
        key
        for key, env in PLATFORM_ENVIRONMENTS.items()
        if env["sys_platform"] == current_env["sys_platform"]
        and env["platform_machine"] == current_env["platform_machine"]
    ]
    if not matching:
        supported = ", ".join(sorted(PLATFORM_ENVIRONMENTS))
        raise BadParameter(
            f"Cannot infer platform for --no-universal: current "
            f"environment ({current_env['sys_platform']!r} on "
            f"{current_env['platform_machine']!r}) is not in the "
            f"supported set ({supported}). Pass --platform explicitly "
            f"to choose a target.",
            param_hint="--no-universal",
        )
    if len(matching) > 1:
        raise BadParameter(
            f"Multiple platform presets match the current environment "
            f"({current_env['sys_platform']!r} on "
            f"{current_env['platform_machine']!r}): {sorted(matching)}. "
            f"Pass --platform explicitly to disambiguate.",
            param_hint="--no-universal",
        )
    return (matching[0],)


__all__ = [
    "resolve_groups",
    "resolve_targets",
]
