"""Build a ``packaging.pylock.PackageArchive`` from a URL/file install."""

from __future__ import annotations

from pathlib import Path

from packaging.pylock import PackageArchive
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import redact_auth_from_url
from pip._internal.utils.urls import url_to_path

from ...exceptions import PipToolsError
from .._hashes import PREFERRED_HASH_ALGORITHMS, is_secure_hash_name
from ._detection import relativize_path


def build_archive_source(
    requirement: InstallRequirement, lock_dir: Path | None
) -> PackageArchive:
    """Build the PEP 751 archive source for a requirement pinned to a file or URL.

    :param requirement: The requirement whose link points at an archive.
    :param lock_dir: Directory the lockfile is being written to, for path
        relativisation. ``None`` keeps absolute paths.
    :returns: The populated archive entry.
    :raises PipToolsError: When the archive does not exist, has no hash, or
        carries only an algorithm PEP 751 considers insecure.
    """
    link = requirement.original_link or requirement.link
    raw = link.url_without_fragment
    if raw.startswith("file:") and not Path(url_to_path(raw)).exists():
        # ``detect_source_type`` routes any non-directory ``file://`` link
        # to the archive branch; without this guard a typo'd path falls
        # through to the missing-hash error and the user can't tell why.
        raise PipToolsError(
            f"Local archive for {requirement.name!r} does not exist: "
            f"{url_to_path(raw)!r}. Check the path in the requirement spec."
        )
    if not link.has_hash:
        raise PipToolsError(
            f"Cannot determine archive hash for {requirement.name!r}: PEP 751 requires "
            f"at least one hash on archive entries. Pin the requirement to a URL "
            f"that includes a hash fragment (e.g. "
            f"`pkg @ https://.../foo.tar.gz#sha256=<digest>`)."
        )
    if not is_secure_hash_name(link.hash_name):
        # PEP 751 demands at least one secure algorithm in ``hashes``; md5/sha1
        # satisfy pip's checks but not the spec's intent. Surface a clear error
        # rather than silently emit a weak-only entry the spec forbids.
        raise PipToolsError(
            f"Archive hash for {requirement.name!r} uses {link.hash_name!r}, which "
            f"PEP 751 does not consider secure. Pin the requirement with one of "
            f"{sorted(PREFERRED_HASH_ALGORITHMS)} (e.g. "
            f"`pkg @ https://.../foo.tar.gz#sha256=<digest>`)."
        )
    hashes = {link.hash_name: link.hash}
    if raw.startswith("file:"):
        return PackageArchive(
            path=relativize_path(url_to_path(raw), lock_dir),
            hashes=hashes,
            subdirectory=link.subdirectory_fragment,
        )
    return PackageArchive(
        url=redact_auth_from_url(raw),
        hashes=hashes,
        subdirectory=link.subdirectory_fragment,
    )


__all__ = [
    "build_archive_source",
]
