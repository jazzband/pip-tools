"""Index-served install: validate filenames, localize URLs, split sdist/wheels."""

from __future__ import annotations

import typing as _t
from os.path import basename
from pathlib import Path

from packaging.pylock import PackageSdist, PackageWheel
from packaging.utils import (
    InvalidSdistFilename,
    InvalidWheelFilename,
    canonicalize_name,
    parse_sdist_filename,
    parse_wheel_filename,
)
from packaging.version import Version
from pip._internal.utils.urls import url_to_path

from ...exceptions import PipToolsError
from ...logging import log
from ._detection import relativize_path

_INTERPRETER_PREFIXES = ("cp", "pp", "py", "ip", "jy")


def _wheel_sort_key(wheel: PackageWheel) -> tuple[int, int, str, str, str, str]:
    # Newest Python first, then stable by (interpreter, abi, platform, name)
    name = wheel.name or ""
    try:
        _, _, _, tags = parse_wheel_filename(name)
    except InvalidWheelFilename:
        return (0, 0, "", "", "", name)

    def _python_rank(interpreter: str) -> tuple[int, int]:
        for prefix in _INTERPRETER_PREFIXES:
            if interpreter.startswith(prefix):
                digits = interpreter[len(prefix) :]
                if digits.isdigit():
                    return (int(digits[0]), int(digits[1:] or 0))
                break
        return (0, 0)

    best_tag = max(tags, key=lambda tag: _python_rank(tag.interpreter))
    major, minor = _python_rank(best_tag.interpreter)
    return (-major, -minor, best_tag.interpreter, best_tag.abi, best_tag.platform, name)


def build_index_source(
    package_name: str,
    version: Version | None,
    dist_files: _t.Sequence[PackageWheel | PackageSdist],
    lock_dir: Path | None,
) -> tuple[PackageSdist | None, list[PackageWheel] | None]:
    """Prepare index-served distribution files for the lock document.

    Validates each filename against the resolved pin, relativises file URLs,
    and splits the sequence into the sdist and wheels fields the lock entry
    expects.

    :param package_name: The package name the resolver pinned.
    :param version: The pinned version, or ``None`` for unpinned sources.
    :param dist_files: Distribution files supplied by the index.
    :param lock_dir: Lockfile directory used for path relativisation.
    :returns: A pair of ``(sdist or None, wheels or None)``.
    :raises PipToolsError: When an index file's name or version disagrees with
        the resolved pin.
    """
    if version is not None:
        _validate_dist_filenames(package_name, version, dist_files)
    localized = tuple(_localize_file_dist_url(d, lock_dir) for d in dist_files)
    return _split_dist_files(localized, package_name, str(version) if version else "")


def _validate_dist_filenames(
    package_name: str,
    resolved_version: Version,
    dist_files: _t.Sequence[PackageWheel | PackageSdist],
) -> None:
    """Reject index responses whose filename disagrees with the resolved pin.

    A mirror or compromised index could serve a wheel/sdist whose filename parses
    to a different ``(name, version)`` than the one ``find_best_match`` chose. The
    writer (``packaging.pylock.Package._from_dict``) re-runs this check at emit
    time, but failing here surfaces "the index returned a mis-labeled file" with
    the package context attached, instead of a generic ``PylockValidationError``.

    Sdists with non-PEP-625 extensions (``.tar.bz2``, ``.tar.xz``) bypass the
    name/version consistency check because ``parse_sdist_filename`` only accepts
    ``.tar.gz`` / ``.zip``; the writer already enforces PEP 625 strictly.
    """
    expected_name = canonicalize_name(package_name)
    expected_version = resolved_version
    for dist in dist_files:
        # PEP 751 lets path-only entries omit ``name``; derive from the
        # path's last component so a malicious mirror serving a path-only
        # entry can't bypass the check with a name=None.
        filename = dist.name
        if filename is None:
            path = getattr(dist, "path", None)
            if path:
                filename = basename(path)
        if filename is None:
            continue
        try:
            if isinstance(dist, PackageWheel):
                parsed_name, parsed_version, _, _ = parse_wheel_filename(filename)
            else:
                parsed_name, parsed_version = parse_sdist_filename(filename)
        except InvalidWheelFilename as exc:
            raise PipToolsError(
                f"Index returned a malformed wheel filename {filename!r} for "
                f"{package_name!r}: {exc}"
            ) from exc
        except InvalidSdistFilename:
            continue
        if parsed_name != expected_name or parsed_version != expected_version:
            raise PipToolsError(
                f"Index returned {filename!r} for {package_name!r}, but "
                f"its filename parses to {parsed_name}=={parsed_version} "
                f"while the resolver picked "
                f"{expected_name}=={expected_version}. The index may be "
                f"serving a mis-labeled artifact."
            )


def _localize_file_dist_url(
    dist: PackageWheel | PackageSdist, lock_dir: Path | None
) -> PackageWheel | PackageSdist:
    """Rewrite ``file://`` dist URLs to portable relative ``path`` entries.

    Local find-links wheels/sdists arrive from pip with ``link.url`` set to
    ``file:///abs/path/foo.whl``. Storing that in the lockfile breaks portability
    (absolute path) and round-trip safety on Windows (backslash escapes); split
    to ``path`` at write-time, matching uv's emitted shape and the PEP 751
    "relative to lock file" contract.
    """
    url = dist.url
    if url is None or not url.startswith("file:"):
        return dist
    rel = relativize_path(url_to_path(url), lock_dir)
    cls = type(dist)
    return cls(
        name=dist.name,
        path=rel,
        hashes=dist.hashes,
        size=dist.size,
        upload_time=dist.upload_time,
    )


_SDIST_SUFFIX_PRIORITY: dict[str, int] = {".tar.gz": 0, ".zip": 1}


def _sdist_sort_key(sdist: PackageSdist) -> tuple[int, str]:
    # Prefer ``.tar.gz`` over ``.zip``: indexes sometimes serve both for
    # the same release and the source distribution stored in ``.tar.gz``
    # is the historical default tools and humans expect first.
    name = sdist.name or ""
    for suffix, priority in _SDIST_SUFFIX_PRIORITY.items():
        if name.endswith(suffix):
            return (priority, name)
    return (len(_SDIST_SUFFIX_PRIORITY), name)


def _split_dist_files(
    dist_files: _t.Sequence[PackageWheel | PackageSdist],
    package_name: str = "",
    version: str = "",
) -> tuple[PackageSdist | None, list[PackageWheel] | None]:
    # The repository pre-filters to sdists/wheels: a suffix allowlist would
    # drop ``.tar.bz2`` / ``.tar.xz``, so any ``PackageSdist`` instance is
    # taken as sdist; ``PackageWheel`` instances go in the wheels bucket.
    # Sort sdists by ``name`` and wheels by parsed tag tuple so the lockfile
    # stays byte-stable across PyPI's listing order with newer Pythons first.
    sdists = sorted(
        (f for f in dist_files if isinstance(f, PackageSdist)),
        key=_sdist_sort_key,
    )
    wheels = sorted(
        (f for f in dist_files if isinstance(f, PackageWheel)),
        key=_wheel_sort_key,
    )
    if len(sdists) > 1:
        # PEP 751 allows one ``[packages.sdist]``; an index that serves
        # both ``.tar.gz`` and ``.zip`` for the same release would drop
        # the trailing one. Warn at top level so the user sees the drop
        # without ``--verbose``: the discarded sdist's hash leaves the
        # lockfile, and a future 404 on the kept variant has no recovery
        # hash to fall back on.
        dropped = ", ".join(repr(s.name) for s in sdists[1:])
        log.warning(
            f"Multiple sdists for {package_name}=={version}; keeping "
            f"{sdists[0].name!r}, dropped {dropped}."
        )
    return (
        sdists[0] if sdists else None,
        wheels if wheels else None,
    )


__all__ = [
    "build_index_source",
]
