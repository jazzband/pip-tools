"""Public input dataclasses for the lock pipeline."""

from __future__ import annotations

import typing as _t
from dataclasses import dataclass
from sys import version_info

from pip._internal.req import InstallRequirement

from .config import ConflictItem
from .platforms import TargetEnvironment

# kw_only arrived in Python 3.10; opt in on supported runtimes so call sites
# cannot drift to positional construction (and produce ambiguous reorderings
# when a new field lands).
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

    Mixes user-supplied input with derived state on purpose; the surface is
    small enough today (six fields) that splitting introduces more friction
    than it saves. Future readers should expect the following split when the
    bag grows: ``platforms`` / ``python_versions`` / ``implementations`` /
    ``no_universal`` come from the CLI verbatim, while ``target_envs`` (the
    cross product the orchestrator iterates) and ``discover_envs`` (the
    marker-driven cohort shortcut toggle) are derived by ``resolve_targets``.
    ``tool_block.build`` reads only the user-input fields, the resolver reads
    only the derived ones, and a future split should mirror that boundary.
    """

    target_envs: dict[str, TargetEnvironment]
    platforms: tuple[str, ...]
    python_versions: tuple[str, ...]
    implementations: tuple[str, ...] = ("cpython",)
    no_universal: bool = False
    discover_envs: bool = False


@dataclass(frozen=True, **_KW_ONLY)
class ResolverOptions:
    """Knobs forwarded into the backtracking resolver.

    Same user-input / derived split as ``LockTargets``: ``pre``, ``rebuild``,
    ``allow_unsafe``, ``unsafe_packages``, ``max_rounds``, and ``cache_dir``
    come from the CLI verbatim; ``prereleases`` is derived (``pre`` or
    ``finder.allow_all_prereleases()``). ``tool_block.build`` records the
    user input, the resolver consumes ``prereleases``.
    """

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

    The worker initializer consumes ``pip_args`` to rebuild a
    ``PyPIRepository`` per worker; it is not a resolver knob. Splitting it off
    keeps the resolution-semantics fields in ``ResolverOptions`` separate from
    the value that crosses the IPC boundary.
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
