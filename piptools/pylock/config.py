"""Read pip-tools-specific configuration out of input files.

Walks the user's ``pyproject.toml`` (and friends) to extract the bits
``pip-lock`` needs but PEP 751 does not own: the project's
``requires-python``, ``[tool.pip-tools].conflicts``, and
``[dependency-groups]`` (PEP 735). All read-only; the writer surfaces
the resulting structures into the lock file.
"""

from __future__ import annotations

import typing as _t
from dataclasses import dataclass
from functools import lru_cache
from os.path import abspath, basename

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from .._compat import _tomllib_compat as tomllib
from ..exceptions import PipToolsError
from ..logging import log


@dataclass(frozen=True)
class ConflictItem:
    """One leg of a ``[tool.pip-tools].conflicts`` declaration."""

    kind: str
    name: str


def extract_requires_python(
    src_files: tuple[str, ...],
    python_versions: tuple[str, ...] = (),
    metadata_specifiers: tuple[str, ...] = (),
) -> str | None:
    """Return the lockfile-wide ``requires-python`` lower bound.

    PEP 751's top-level ``requires-python`` documents the lowest viable
    Python version for the entire lock file. The function intersects every
    discovered ``Requires-Python`` clause (from project metadata and from
    backend-resolved metadata) with a floor derived from the user's
    ``--python-version`` flags so the spec's contract holds end to end.

    :param src_files: Project files whose ``[project].requires-python`` is read.
    :param python_versions: User-supplied python versions to derive a floor from.
    :param metadata_specifiers: ``Requires-Python`` strings sourced from build
        backend metadata (covers ``setup.cfg`` and dynamic pyproject metadata).
    :returns: The intersected requires-python string, or ``None`` when no
        contributor specified a bound.
    :raises PipToolsError: When the intersection is empty (no Python release
        satisfies every clause).
    """
    combined = SpecifierSet()
    found = False
    static_seen: set[str] = set()
    for src_file in src_files:
        if (data := _load_pyproject_or_skip(src_file)) is None:
            continue
        raw = data.get("project", {}).get("requires-python")
        if not raw:
            continue
        try:
            combined &= SpecifierSet(str(raw))
        except InvalidSpecifier:
            continue
        found = True
        static_seen.add(abspath(src_file))
    for raw in metadata_specifiers:
        # Backend-supplied ``Requires-Python`` covers ``setup.cfg``, dynamic
        # pyproject metadata, and every other source the static parse missed;
        # skipping projects captured by the static read keeps the
        # intersection idempotent.
        if not raw:
            continue
        try:
            combined &= SpecifierSet(str(raw))
        except InvalidSpecifier:
            continue
        found = True
    if (cli_floor := _python_versions_floor(python_versions)) is not None:
        combined &= cli_floor
        found = True
    if found:
        # An intersected ``requires-python`` that no Python release satisfies
        # would land in the lockfile without warning and surface as an
        # install-time error far from the cause. Probe a coarse grid of
        # interpreter versions; a release inside the grid satisfies any
        # non-empty SpecifierSet, so a complete miss is sufficient evidence
        # of emptiness. The grid spans Python 1 through Python 4 with patch
        # samples up to 99 so legacy ``==1.5.0`` and forward-looking
        # ``==4.0.0`` pins both find a witness; the cost is a few thousand
        # ``SpecifierSet.contains`` calls.
        candidates = (
            f"{major}.{minor}.{patch}"
            for major in (1, 2, 3, 4)
            for minor in range(0, 100)
            for patch in (0, 1, 5, 9, 99)
        )
        if not any(combined.contains(v, prereleases=True) for v in candidates):
            # ``combined`` absorbs every contributor (pyproject,
            # metadata-specifiers, cli-floor). Naming sources from one
            # branch would hide the half of the contradiction coming
            # from the other side; walk the SpecifierSet itself so
            # the diagnostic cites every clause.
            constituents = sorted({str(s) for s in combined})
            raise PipToolsError(
                f"Intersected requires-python {str(combined)!r} is empty: no "
                f"Python release satisfies all of "
                f"{', '.join(constituents)!r}. Reconcile the project "
                f"metadata's ``requires-python`` with the "
                f"``--python-version`` flag(s) before locking."
            )
        # SpecifierSet's ``__str__`` joins in insertion order, and ``&=`` does
        # not dedupe identical specifiers (pyproject + metadata both carry
        # the same bound for the common case). Dedupe on the string form
        # and sort so the lockfile diff is stable across runs and across
        # callers that supply the same bound twice.
        return ",".join(sorted({str(s) for s in combined}))
    return None


def _python_versions_floor(python_versions: tuple[str, ...]) -> SpecifierSet | None:
    if not python_versions:
        return None
    # ``packaging.Version`` enforces PEP 440 sort semantics and surfaces
    # malformed inputs as ``InvalidVersion`` rather than ``int("11rc1")``
    # -shaped ``ValueError`` from a hand-rolled split. The original CLI
    # string threads through so the emitted floor preserves the user's
    # spelling (``3.12.5`` vs ``3.12``); ``Version.__init__``
    # normalizes to canonical form, which would drop the trailing ``.0``
    # on ``3.12``.
    lowest_version = sorted(python_versions, key=Version)[0]
    return SpecifierSet(f">={lowest_version}")


def extract_conflicts(src_files: tuple[str, ...]) -> list[list[ConflictItem]]:
    """Read the ``[tool.pip-tools].conflicts`` table from the first project file.

    :param src_files: Project files searched in order for the conflicts table.
    :returns: A list of conflict groups, each holding two or more conflict items.
    :raises PipToolsError: When a conflict entry uses unknown keys.
    """
    for src_file in src_files:
        if (data := _load_pyproject_or_skip(src_file)) is None:
            continue
        raw_conflicts = data.get("tool", {}).get("pip-tools", {}).get("conflicts", [])
        result: list[list[ConflictItem]] = []
        for group in raw_conflicts:
            items: list[ConflictItem] = []
            for item in group:
                # Surface unknown keys instead of dropping them: a
                # typo'd ``extras = "..."`` (plural) would produce a no-op
                # conflicts entry the user notices when the disjointness
                # check rejects the lock.
                unknown = set(item) - {"extra", "group"}
                if unknown:
                    raise PipToolsError(
                        f"[tool.pip-tools].conflicts entry has unknown "
                        f"key(s) {sorted(unknown)!r}; valid keys are "
                        f"`extra` and `group`."
                    )
                if "extra" in item:
                    items.append(ConflictItem(kind="extra", name=item["extra"]))
                elif "group" in item:
                    items.append(ConflictItem(kind="group", name=item["group"]))
            if len(items) >= 2:
                result.append(items)
        return result
    return []


def load_default_groups(src_files: tuple[str, ...]) -> tuple[str, ...]:
    """Return the project's ``[dependency-groups].default-groups`` list.

    Honours PEP 735's convention of placing ``default-groups`` inside the
    ``[dependency-groups]`` table; an installer reading the resulting
    lockfile installs those groups even when the user passes no ``--group``.
    Returns an empty tuple when the project omits the key.
    """
    for src_file in src_files:
        if (data := _load_pyproject_or_skip(src_file)) is None:
            continue
        raw_groups = data.get("dependency-groups", {})
        if not isinstance(raw_groups, dict):
            continue
        defaults = raw_groups.get("default-groups", [])
        if not isinstance(defaults, list):
            continue
        return tuple(str(g) for g in defaults if isinstance(g, str))
    return ()


def load_dependency_groups_table(
    src_files: tuple[str, ...],
) -> dict[str, list[str | dict[str, str]]]:
    """Return the raw ``[dependency-groups]`` table from the first ``pyproject.toml``.

    Returns the loose mapping shape the dependency-group resolver in packaging
    consumes; expansion, cycle detection, and duplicate-name checks live there.

    :param src_files: Project files searched in order.
    :returns: The raw groups table, or an empty mapping when none was found.
    """
    for src_file in src_files:
        if (data := _load_pyproject_or_skip(src_file)) is None:
            continue
        raw_groups: dict[str, list[str | dict[str, str]]] = data.get(
            "dependency-groups", {}
        )
        if not raw_groups:
            continue
        # ``default-groups`` is an installer hint, not a group itself;
        # skip it so the dependency resolver doesn't try to resolve a
        # phantom group of that name.
        return {k: v for k, v in raw_groups.items() if k != "default-groups"}
    return {}


def build_group_configs(
    groups: tuple[str, ...],
    conflicts: list[list[ConflictItem]],
) -> list[tuple[str | None, tuple[str, ...]]]:
    """Return the per-resolution group configurations.

    Non-conflicting groups land in one base resolution; each conflicting
    group spawns a dedicated pass that includes the non-conflicting set
    plus that one group.

    :param groups: All groups the user requested.
    :param conflicts: Conflict matrix loaded from ``[tool.pip-tools].conflicts``.
    :returns: Ordered list of ``(label, group tuple)`` pairs the resolver
        iterates over. ``label`` is ``None`` for the base pass.
    """
    conflicting_groups: set[str] = {
        item.name
        for conflict_group in conflicts
        for item in conflict_group
        if item.kind == "group"
    }

    configs: list[tuple[str | None, tuple[str, ...]]] = [(None, ())]

    for group in groups:
        if group in conflicting_groups:
            non_conflicting = tuple(g for g in groups if g not in conflicting_groups)
            configs.append((group, non_conflicting + (group,)))
        else:
            configs.append((group, (group,)))

    return configs


def build_extras_configs(
    extras: tuple[str, ...],
    conflicts: list[list[ConflictItem]],
) -> list[tuple[str | None, tuple[str, ...]]]:
    """Return resolver passes covering ``extras`` under ``conflicts``.

    Non-conflicting extras coexist by definition, so one combined pass
    suffices. Per-extra attribution for that combined pass is reconstructed
    from a forward-deps walk so PEP 751 markers like ``'X' in extras`` still
    fire on extras-only packages.

    :param extras: All extras the user requested.
    :param conflicts: Conflict matrix loaded from ``[tool.pip-tools].conflicts``.
    :returns: Ordered list of ``(label, extras tuple)`` pairs the resolver
        iterates over. ``label`` is ``None`` for the combined base pass.
    """
    conflicting_extras: set[str] = {
        item.name for group in conflicts for item in group if item.kind == "extra"
    }

    non_conflicting = tuple(e for e in extras if e not in conflicting_extras)
    configs: list[tuple[str | None, tuple[str, ...]]] = [(None, non_conflicting)]
    for extra in extras:
        if extra in conflicting_extras:
            configs.append((extra, non_conflicting + (extra,)))
    return configs


def _load_pyproject_or_skip(src_file: str) -> dict[str, _t.Any] | None:
    """Return the parsed ``pyproject.toml`` for ``src_file`` or ``None``.

    Filters non-``pyproject.toml`` inputs and turns parser failures into a
    debug log + skip so a corrupt or BOM-prefixed file (or a CI permissions
    issue) doesn't abort the lock; a skip without a log would surface as a
    missing ``requires-python`` / empty conflicts / empty groups in the
    lockfile with no trail to follow.
    """
    if basename(src_file) != "pyproject.toml":
        return None
    try:
        return _load_toml(src_file)
    except (OSError, ValueError) as err:
        log.debug(f"Skipping {src_file}: {err}")
        return None


@lru_cache(maxsize=64)
def _load_toml(path: str) -> dict[str, _t.Any]:
    # Each ``extract_*`` helper reads the same ``pyproject.toml`` for its
    # own slice (requires-python, conflicts, dependency-groups). LRU-cached
    # by absolute path so a multi-source lock parses each file once;
    # invalidation isn't a concern because the lock command is one-shot.
    with open(path, "rb") as f:
        return tomllib.load(f)


__all__ = [
    "ConflictItem",
    "build_extras_configs",
    "build_group_configs",
    "extract_conflicts",
    "extract_requires_python",
    "load_default_groups",
    "load_dependency_groups_table",
]
