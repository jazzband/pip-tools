"""On-disk cache for streamed-file hashes.

Pip-tools hashes wheels/sdists itself when a private index doesn't expose
``digests`` in its JSON response. Pip's ``CacheControlAdapter`` keeps the body
bytes between runs, so the network round-trip is usually skipped, but the SHA
loop runs every time and scales linearly with package count. Caching the
``url -> sha`` pair under ``cache_dir`` lets the second run skip the loop for
URLs whose bytes can't change, turning a 200-package lock from "rehash
everything" into "validate the index match."

Only ``*.pythonhosted.org`` URLs are cached: PyPI/Warehouse serves
content-addressable URLs (the digest is part of the path), so the same URL
cannot serve different bytes across runs. Private indexes that re-publish
the same URL with different bytes would otherwise return stale digests
forever, so they're explicitly excluded from caching.
"""

from __future__ import annotations

import json
import os
from hashlib import sha224
from pathlib import Path
from urllib.parse import urlsplit

_FILENAME_VERSION = 2
_CACHEABLE_HOSTS = frozenset({"files.pythonhosted.org"})


def _is_cacheable(url: str) -> bool:
    return urlsplit(url).netloc in _CACHEABLE_HOSTS


def cache_path(cache_dir: str, url: str) -> Path:
    return (
        Path(cache_dir)
        / "pip-tools"
        / "hashes"
        / f"{sha224(url.encode('utf-8')).hexdigest()}.json"
    )


def load(cache_dir: str, url: str) -> tuple[str, int | None] | None:
    """Return the cached ``(sha256, size)`` for ``url`` or ``None``.

    Best-effort: any I/O or JSON failure falls through to a recompute so a
    corrupt cache file never blocks a lock. Non-content-addressable hosts
    bypass the cache entirely. ``size`` may be ``None`` for entries written
    before the size field was tracked; bumping ``_FILENAME_VERSION`` makes
    those records ineligible so a re-stream will populate it.
    """
    if not _is_cacheable(url):
        return None
    path = cache_path(cache_dir, url)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if data.get("v") != _FILENAME_VERSION or data.get("url") != url:
        return None
    sha = data.get("sha256")
    if not isinstance(sha, str):
        return None
    size = data.get("size")
    return sha, size if isinstance(size, int) else None


def store(cache_dir: str, url: str, sha256: str, size: int | None) -> None:
    """Persist the ``url -> (sha256, size)`` mapping atomically.

    Writes to a sibling temp file then ``os.replace`` so a concurrent
    reader never sees a half-written entry. Failures are swallowed
    because the cache is opportunistic; a missing entry just means the
    next run rehashes. Non-content-addressable hosts skip persistence
    entirely.
    """
    if not _is_cacheable(url):
        return
    path = cache_path(cache_dir, url)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(
                {"v": _FILENAME_VERSION, "url": url, "sha256": sha256, "size": size}
            )
        )
        os.replace(tmp, path)
    except OSError:
        return


__all__ = [
    "load",
    "store",
]
