"""Process-wide caches for pip helper functions hot during pylock.

Pylock iterates the same package set across multiple resolution cohorts, but pip
is built for long-running sessions and re-parses index responses and wheel
filenames each time through by design. This module installs memoizing wrappers
that short-circuit those repeats for the duration of a pip-tools command.

For ``parse_wheel_filename`` we also walk ``sys.modules`` to rebind every module
that imported it at module load time. ``from X import Y`` binds ``Y`` as a name
in the importer, not as a reference into ``X``, so patching the source module
alone would leave pip's ``Wheel.__init__`` calling the unwrapped copy.

Memory profile: the URL-keyed dicts grow with the number of distinct (link,
metadata, index-page) URLs the resolver touches and are bounded by the
``scope()`` lifetime. The wheel-filename cache caps at a configurable bound so
long-lived ``--jobs auto`` workers cannot grow the working set without limit.
"""

from __future__ import annotations

import importlib.metadata as _importlib_md
import os
import pathlib as _pathlib
import sys
import threading
import typing as _t
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager

from packaging import utils as _packaging_utils
from pip._internal.index import package_finder as _pkgfinder
from pip._internal.index.collector import LinkCollector as _LinkCollector
from pip._internal.operations.prepare import RequirementPreparer as _RequirementPreparer

from ..logging import log


class _InMemoryImportlibDistribution(_importlib_md.Distribution):
    """Decouples a parsed ``Distribution`` from the on-disk temp dir.

    Pip's stock backend wraps a ``PathDistribution`` that re-reads
    ``METADATA`` on every property access, against a temp dir whose
    lifetime ends with one resolver invocation. Caching that wrapper
    across passes raises ``FileNotFoundError`` on later reads. Reading
    from bytes held on the instance lets the wrapper survive across
    passes within a single lock command.
    """

    def __init__(self, metadata_bytes: bytes) -> None:
        self._metadata_bytes = metadata_bytes

    def read_text(self, filename: str) -> str | None:
        if filename in ("METADATA", "PKG-INFO"):
            return self._metadata_bytes.decode("utf-8", errors="replace")
        return None

    def locate_file(self, path: _t.Any) -> _t.Any:
        return _pathlib.Path(str(path))

    @property
    def name(self) -> str:
        # ``Distribution.name`` is a property from Python 3.10 on; on 3.9
        # pip's compat layer reaches for ``dist.name`` directly and crashes
        # without this fallback.
        return _t.cast(str, self.metadata.get("Name"))

    @property
    def version(self) -> str:
        # Mirrors the ``name`` fallback for the same Python 3.9 reason.
        return _t.cast(str, self.metadata.get("Version"))


if _t.TYPE_CHECKING:
    from collections.abc import Iterable

    from packaging.tags import Tag
    from packaging.utils import BuildTag, NormalizedName
    from packaging.version import Version
    from pip._internal.index.collector import IndexContent
    from pip._internal.metadata import BaseDistribution
    from pip._internal.models.link import Link
    from pip._internal.req import InstallRequirement

    _ParseLinks: _t.TypeAlias = "_t.Callable[[IndexContent], Iterable[Link]]"
    _ParseWheelFilename: _t.TypeAlias = (
        "_t.Callable[[str], tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]]"
    )
    _FetchResponse: _t.TypeAlias = (
        "_t.Callable[[_LinkCollector, Link], IndexContent | None]"
    )
    _FetchMetadata: _t.TypeAlias = (
        "_t.Callable[[_RequirementPreparer, InstallRequirement], BaseDistribution | None]"
    )


# Cache backing stores. ``Final`` marks the *binding* immutable; the dict
# contents are populated and cleared in-place. Caching the wrapped
# Distribution alongside the bytes amortises ``email.feedparser`` across the
# per-cohort, per-extra, and per-group resolver invocations a single
# ``pip-lock`` command fans out (the bytes alone do not, since pip's
# importlib backend re-parses on every property access).
_parsed_links_by_url: _t.Final[dict[str, list[Link]]] = {}
_index_content_by_url: _t.Final[dict[str, IndexContent | None]] = {}
_metadata_bytes_by_url: _t.Final[dict[str, bytes | None]] = {}
_metadata_dist_by_url: _t.Final[dict[str, _t.Any]] = {}
# Originals captured at import time so we swap them in and out around an
# installed scope. ``_fetch_metadata_using_link_data_attr`` ships in pip 22.3+
# which is our declared lower bound, so the method is present and the wrapper
# installs.
_original_parse_links: _t.Final[_ParseLinks] = _pkgfinder.parse_links
_original_parse_wheel_filename: _t.Final[_ParseWheelFilename] = (
    _packaging_utils.parse_wheel_filename
)
_original_fetch_response: _t.Final[_FetchResponse] = _LinkCollector.fetch_response
_original_fetch_metadata_using_link_data_attr: _t.Final[_FetchMetadata] = (
    _RequirementPreparer._fetch_metadata_using_link_data_attr
)
_installed = False
# RLock so an outer scope's install/clear/uninstall serializes with any
# concurrent thread's view of the patches. Without it two threads using
# pip-tools as a library race the install flag and produce one half-patched,
# one half-cleared session.
_scope_lock: _t.Final[threading.RLock] = threading.RLock()
_scope_depth = 0


@contextmanager
def scope() -> Iterator[None]:
    """Install pip helper caches for the duration of the block.

    Reverts and clears the caches on exit. Nested entries are idempotent:
    the outermost entry installs and uninstalls; inner entries are no-ops.
    Thread-safe via an ``RLock`` and a depth counter so in-process library
    callers can spawn parallel locks safely.

    :returns: Context manager that installs and reverts the pip helper caches.
    """
    global _scope_depth
    with _scope_lock:
        _scope_depth += 1
        outermost = _scope_depth == 1
        if outermost:
            install()
    try:
        yield
    finally:
        with _scope_lock:
            _scope_depth -= 1
            if outermost:
                uninstall()


def install() -> None:
    """Patch pip's helper functions process-wide with memoising wrappers.

    Idempotent. Prefer the symmetric scope context for in-process callers;
    this entry point serves worker processes that exit on pool teardown
    without running cleanup.
    """
    global _installed
    if _installed:
        return
    _pkgfinder.parse_links = _cached_parse_links
    _rebind_everywhere(
        _packaging_utils,
        "parse_wheel_filename",
        _original_parse_wheel_filename,
        _cached_parse_wheel_filename,
    )
    _LinkCollector.fetch_response = _cached_fetch_response
    _RequirementPreparer._fetch_metadata_using_link_data_attr = (
        _cached_fetch_metadata_using_link_data_attr
    )
    _installed = True


def clear() -> None:
    """Empty every memoising cache and reset eviction telemetry."""
    global _parsed_wheel_filename_evictions, _eviction_warning_emitted
    _parsed_links_by_url.clear()
    _parsed_wheel_filename_cache.clear()
    _index_content_by_url.clear()
    _metadata_bytes_by_url.clear()
    _metadata_dist_by_url.clear()
    _parsed_wheel_filename_evictions = 0
    _eviction_warning_emitted = False


def uninstall() -> None:
    """Restore pip's original helper functions and clear cached state."""
    global _installed
    if not _installed:
        return
    _pkgfinder.parse_links = _original_parse_links
    _rebind_everywhere(
        _packaging_utils,
        "parse_wheel_filename",
        _cached_parse_wheel_filename,
        _original_parse_wheel_filename,
    )
    _LinkCollector.fetch_response = _original_fetch_response
    _RequirementPreparer._fetch_metadata_using_link_data_attr = (
        _original_fetch_metadata_using_link_data_attr
    )
    clear()
    _installed = False


def _cached_parse_links(page: IndexContent) -> list[Link]:
    cached = _parsed_links_by_url.get(page.url)
    if cached is None:
        cached = list(_original_parse_links(page))
        _parsed_links_by_url[page.url] = cached
    return cached


# Bound the wheel-filename cache so a high cardinality of distinct wheel
# filenames cannot push the working set past a fixed ceiling. Under
# ``scope()`` the cache drops on exit, so the bound protects long-lived
# workers in ``--jobs auto``. ``OrderedDict`` gives LRU semantics whose
# lifetime ``clear()`` controls. ``functools.lru_cache`` would store its
# data on the function object and survive module re-imports in ways hard
# to reason about under multi-process pools. Override via
# ``PIP_TOOLS_PARSED_WHEEL_FILENAME_BOUND`` to lift the ceiling when the
# resolver sees more distinct filenames than the default holds.
_PARSED_WHEEL_FILENAME_BOUND = int(
    os.environ.get("PIP_TOOLS_PARSED_WHEEL_FILENAME_BOUND", "10000")
)
_parsed_wheel_filename_cache: _t.Final[
    OrderedDict[str, tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]]
] = OrderedDict()
# When the LRU evicts more than ~1% of capacity in a single resolution pass,
# every evicted-then-re-requested filename re-pays the parse cost. Surface a
# one-time hint so the user can lift the bound; otherwise the signal is
# "this lock is slow" with no pointer to the knob.
_EVICTION_WARN_THRESHOLD: _t.Final = max(1, _PARSED_WHEEL_FILENAME_BOUND // 100)
_parsed_wheel_filename_evictions = 0
_eviction_warning_emitted = False


def _cached_parse_wheel_filename(
    filename: str,
) -> tuple[NormalizedName, Version, BuildTag, frozenset[Tag]]:
    global _parsed_wheel_filename_evictions, _eviction_warning_emitted
    if (cached := _parsed_wheel_filename_cache.get(filename)) is not None:
        _parsed_wheel_filename_cache.move_to_end(filename)
        return cached
    parsed = _original_parse_wheel_filename(filename)
    _parsed_wheel_filename_cache[filename] = parsed
    if len(_parsed_wheel_filename_cache) > _PARSED_WHEEL_FILENAME_BOUND:
        _parsed_wheel_filename_cache.popitem(last=False)
        _parsed_wheel_filename_evictions += 1
        if (
            not _eviction_warning_emitted
            and _parsed_wheel_filename_evictions >= _EVICTION_WARN_THRESHOLD
        ):
            _eviction_warning_emitted = True
            log.info(
                f"Parsed-wheel-filename cache evicted "
                f"{_parsed_wheel_filename_evictions} entries (bound is "
                f"{_PARSED_WHEEL_FILENAME_BOUND}); set "
                f"PIP_TOOLS_PARSED_WHEEL_FILENAME_BOUND higher if locks are "
                f"slow on this project."
            )
    return parsed


def _cached_fetch_response(self: _LinkCollector, location: Link) -> IndexContent | None:
    url = location.url
    if url in _index_content_by_url:
        return _index_content_by_url[url]
    response = _original_fetch_response(self, location)
    _index_content_by_url[url] = response
    return response


def _cached_fetch_metadata_using_link_data_attr(
    self: _RequirementPreparer, req: InstallRequirement
) -> BaseDistribution | None:
    # Pip's stock backend reads ``METADATA`` off a temp dir whose lifetime
    # ends with the resolver invocation; the prior version of this wrapper
    # cached the byte payload alone because a Distribution-level cache
    # against that backend raises ``FileNotFoundError`` on the second
    # access. Re-routing through an in-memory reader amortises
    # ``email.feedparser`` across every pass that re-resolves the same link.
    if req.link is None or req.req is None:
        return None
    metadata_link = req.link.metadata_link()
    if metadata_link is None:
        return None

    cached_dist = _metadata_dist_by_url.get(metadata_link.url)
    if cached_dist is not None:
        return cached_dist

    # Defer the pip-23.2-only imports until after the early-return checks so
    # callers on older pip (where pip-tools never installs the wrapper, but
    # tests can call it directly) don't trip over the missing symbols.
    from packaging.utils import canonicalize_name
    from pip._internal.exceptions import MetadataInconsistent
    from pip._internal.metadata.importlib._dists import (
        Distribution as _ImportlibDistribution,
    )
    from pip._internal.operations.prepare import get_http_url

    # ``... in dict`` separates "key absent" from "key present with cached
    # ``None``" without a sentinel object; a sentinel would need ``object``
    # typing because the cache values are ``bytes | None``.
    if metadata_link.url in _metadata_bytes_by_url:
        metadata_contents = _metadata_bytes_by_url[metadata_link.url]
    else:
        metadata_file = get_http_url(
            metadata_link,
            self._download,
            hashes=metadata_link.as_hashes(),
        )
        with open(metadata_file.path, "rb") as fh:
            metadata_contents = fh.read()
        _metadata_bytes_by_url[metadata_link.url] = metadata_contents
    if metadata_contents is None:
        return None
    inner_dist = _InMemoryImportlibDistribution(metadata_contents)
    metadata_dist = _ImportlibDistribution(
        inner_dist, info_location=None, installed_location=None
    )
    if canonicalize_name(metadata_dist.raw_name) != canonicalize_name(req.req.name):
        raise MetadataInconsistent(req, "Name", req.req.name, metadata_dist.raw_name)
    _metadata_dist_by_url[metadata_link.url] = metadata_dist
    return metadata_dist


def _rebind_everywhere(
    source_module: _t.Any,
    attr: str,
    original: _t.Callable[..., _t.Any],
    replacement: _t.Callable[..., _t.Any],
) -> None:
    """Rebind ``attr`` on ``source_module`` and every importer of it.

    Many pip modules use ``from pkg import name`` at the top of the
    file, which captures ``name`` as a local module attribute pointing at
    the original function. Patching the source module alone would leave
    those local references untouched, so the hot call sites would keep
    hitting the unwrapped function.

    The blast radius is intentional but broad: every module in
    ``sys.modules`` that imported ``original`` (including third-party
    code in the same process) gets the memoized replacement. The wrapper
    is a pure cache around the same function (correctness-safe) but adds
    a memoization side-effect on those consumers. ``scope()``'s
    ``try/finally`` reverts on normal exceptions; SIGKILL skips
    finalisation (process dies), SIGTERM runs through the handler and
    the revert fires.
    """
    setattr(source_module, attr, replacement)
    for mod in list(sys.modules.values()):
        if mod is None or mod is source_module:
            continue
        if getattr(mod, attr, None) is original:
            setattr(mod, attr, replacement)


__all__ = [
    "clear",
    "install",
    "scope",
    "uninstall",
]
