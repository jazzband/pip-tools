"""Public input dataclasses for the lock pipeline."""

from __future__ import annotations

import typing as _t
from dataclasses import dataclass
from sys import version_info

from pip._internal.req import InstallRequirement

from .config import ConflictItem
from .platforms import TargetEnvironment

# kw_only arrived in Python 3.10; opt in on supported runtimes so call sites can't
# accidentally drift to positional construction (and produce ambiguous reorderings the
# next time fields are added).
_KW_ONLY: _t.Final[dict[str, bool]] = (
    {"kw_only": True} if version_info >= (3, 10) else {}
)


@dataclass(frozen=True, **_KW_ONLY)
class LockInputs:
    """User-supplied source material for the lock pipeline.

    Bundles the parsed requirements, the conflict matrix, and the per-group
    requirement lists so callers don't pass three orthogonal collections
    side-by-side through every helper that touches user input.
    """

    raw_constraints: list[InstallRequirement]
    conflicts: list[list[ConflictItem]]
    group_constraints: dict[str, list[InstallRequirement]]


@dataclass(frozen=True, **_KW_ONLY)
class LockSelection:
    """Which extras and groups the user asked the lockfile to cover."""

    extras: tuple[str, ...]
    all_extras: bool
    groups: tuple[str, ...]
    all_groups: bool
    default_groups: tuple[str, ...] = ()


@dataclass(frozen=True, **_KW_ONLY)
class LockTargets:
    """Resolution targets and how to expand them.

    ``target_envs`` is the cross product of ``platforms`` x ``python_versions`` the
    resolver iterates over. ``discover_envs`` opts into the marker-driven cohort
    shortcut, which collapses envs that share a dependency graph into one
    resolution; flipping it off forces one resolution per env, which is the
    safety net for surprising marker configurations.
    """

    target_envs: dict[str, TargetEnvironment]
    platforms: tuple[str, ...]
    python_versions: tuple[str, ...]
    implementations: tuple[str, ...] = ("cpython",)
    no_universal: bool = False
    discover_envs: bool = False


@dataclass(frozen=True, **_KW_ONLY)
class ResolverOptions:
    """Knobs forwarded directly into the backtracking resolver."""

    prereleases: bool
    rebuild: bool
    allow_unsafe: bool
    unsafe_packages: frozenset[str]
    max_rounds: int
    cache_dir: str
    pre: bool


@dataclass(frozen=True, **_KW_ONLY)
class WorkerSpec:
    """How parallel resolution is dispatched.

    ``pip_args`` is only consumed by the worker initializer to rebuild a
    ``PyPIRepository`` per worker; it is not a resolver knob. Splitting it off keeps
    ``ResolverOptions`` honest about what affects resolution semantics versus what
    only crosses the IPC boundary.
    """

    jobs: int
    pip_args: tuple[str, ...]


@dataclass(frozen=True, **_KW_ONLY)
class ToolMetadataOptions:
    """Filters that gate what lands in the ``[tool.pip-tools]`` block."""

    no_metadata: bool
    skip_metadata_fields: tuple[str, ...]


__all__ = [
    "LockInputs",
    "LockSelection",
    "LockTargets",
    "ResolverOptions",
    "ToolMetadataOptions",
    "WorkerSpec",
]
