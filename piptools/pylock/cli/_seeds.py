"""Seeding pins from an existing ``pylock.toml`` for re-locks.

Replicates the pip-compile ``-P package requirements.txt`` workflow: when a
lockfile already exists, carry every pin forward except the ones the
caller upgrades. ``--upgrade`` bypasses this entirely; this module runs
when ``upgrade_lock`` is off.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.version import InvalidVersion, Version

from ..._compat import _tomllib_compat, canonicalize_name
from ...logging import log
from ...utils import UNSAFE_PACKAGES


def seed_pins_from_existing_lock(
    output_path: Path,
    upgrade_packages: tuple[str, ...],
    unsafe_packages: tuple[str, ...] = (),
    allow_unsafe: bool = False,
) -> tuple[str, ...]:
    """Return ``name==version`` pins seeded from an existing pylock.

    Replicates the pip-compile ``-P package requirements.txt`` workflow: when
    the lockfile at ``output_path`` exists, every pin carries forward
    except the packages named in ``upgrade_packages`` (those re-resolve).

    :param output_path: Path of the lockfile to seed pins from.
    :param upgrade_packages: Packages excluded from seeding so the resolver
        can pick a newer version.
    :param unsafe_packages: User-supplied unsafe package list to strip when
        ``allow_unsafe`` is ``False``.
    :param allow_unsafe: Preserve unsafe packages in the seed when ``True``.
    :returns: Tuple of ``name==version`` strings to feed back to the resolver,
        empty when no usable lockfile exists.
    """
    if not output_path.exists():
        return ()
    # ``upgrade_packages`` carries CLI tokens like ``foo[dev]==1.0``. A bare
    # ``canonicalize_name`` would normalize the whole spec into a hyphen-
    # mangled blob (``foo-dev-1-0``) that never matches an entry's name.
    # Parse via ``Requirement`` so the seed exclusion fires on the package
    # name; invalid tokens drop out, so a typo can't keep a seed in.
    upgrade_canon: set[str] = set()
    for package in upgrade_packages:
        try:
            upgrade_canon.add(canonicalize_name(Requirement(package).name))
        except InvalidRequirement:
            log.warning(
                f"Ignoring malformed --upgrade-package value {package!r}; "
                f"the seeded pin (if any) will be kept."
            )
    unsafe_canon = (
        set()
        if allow_unsafe
        else {
            canonicalize_name(package)
            for package in (*UNSAFE_PACKAGES, *unsafe_packages)
        }
    )
    try:
        with open(output_path, "rb") as f:
            doc = _tomllib_compat.load(f)
    except (OSError, ValueError) as err:
        # Warn rather than debug so a re-run against a corrupt lockfile
        # surfaces why the resolver re-resolves from scratch instead of
        # churning every package without explanation.
        log.warning(
            f"Existing {output_path.name} could not be parsed ({err}); "
            f"re-resolving from scratch."
        )
        return ()
    raw_lock_version = doc.get("lock-version", "")
    # PEP 751 says ``lock-version`` is a string; tools may emit ``1.0`` or
    # the equivalent normal forms ``1.0.0`` / ``v1.0``. Normalise via
    # ``packaging.Version`` so a uv-written lock pip-tools later seeds from
    # round-trips cleanly. A future PEP 751 v2 would change major;
    # accept any 1.x.y as v1.0-shape and refuse otherwise.
    try:
        seed_version = Version(str(raw_lock_version))
    except InvalidVersion:
        seed_version = None
    if seed_version is None or seed_version.major != 1:
        log.warning(
            f"Existing {output_path.name} has lock-version "
            f"{raw_lock_version!r}; pip-tools only seeds from v1.x. "
            f"Re-resolving from scratch."
        )
        return ()
    # A re-lock under conflict groups produces multiple ``[[packages]]``
    # entries for the same name (one per group). Flat seeding would emit
    # ``black==22.1.0`` and ``black==23.12.0`` together, then trip
    # ``RequirementsConflicted`` in the partition scan. Drop duplicated
    # names from the flat seed; the per-cohort resolutions reintroduce
    # them anyway.
    name_counts: Counter[str] = Counter(
        canonicalize_name(raw_name)
        for package in doc.get("packages", [])
        if (raw_name := package.get("name"))
    )
    pins: list[str] = [
        f"{name}=={version}"
        for package in doc.get("packages", [])
        if (name := package.get("name"))
        and (version := package.get("version"))
        and (canon := canonicalize_name(name)) not in upgrade_canon
        and canon not in unsafe_canon
        and name_counts.get(canon, 0) <= 1
    ]
    if pins:
        log.debug(f"Seeded {len(pins)} pin(s) from existing {output_path.name}")
    return tuple(pins)


__all__ = [
    "seed_pins_from_existing_lock",
]
