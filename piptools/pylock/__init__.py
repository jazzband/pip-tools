"""PEP 751 ``pylock.toml`` generation for pip-tools.

Overview
========

The pipeline runs in six stages, each implemented in a sibling module:

1. **Inputs** (``cli/_inputs``, ``cli/_targets``, ``config``): read
   ``requirements.in`` / ``pyproject.toml`` / dependency-groups, expand
   user-supplied ``--platform`` / ``--python-version`` / ``--implementation``
   axes, and gather conflict declarations.
2. **Marker discovery scan** (``resolve/_partition``): resolve once per python
   under ``platform_blind_marker_eval`` to discover every platform-conditional
   dependency the user's graph reaches, then sign each target env against the
   collected env-axis markers.
3. **Cohort partition** (``resolve/_partition``): envs with the same signature
   share a dependency graph; collapse them into cohorts so the resolver runs
   one resolution per cohort instead of one per env.
4. **Per-cohort resolution** (``resolve/_cohort_work``, ``resolve/_worker``):
   run the BacktrackingResolver once per ``(cohort, extras/groups)`` cell;
   parallelise across cohorts under a spawn-method process pool.
5. **Merge & validate** (``_merge``, ``validate``): collapse per-variant
   resolutions into one entry list per package, then verify marker
   disjointness and ``Requires-Python`` consistency.
6. **Render** (``builder``, ``sources``, ``cli/_file_io``): translate every
   resolved requirement into a ``packaging.pylock.Package`` and emit the
   byte-stable TOML, with wheels ordered newest-Python-first and the
   ``sdist`` block written after ``wheels``.

Three caching tiers keep cold-start cost reasonable
====================================================

* **Process-wide pip-helper caches** (``piptools._internal._pip_caches``):
  memoizing wrappers around pip's ``LinkCollector``, ``RequirementPreparer``,
  and ``parse_wheel_filename`` that survive across cohorts within one
  ``pip-lock`` invocation and rebind ``from X import Y`` consumers so
  ``Wheel.__init__`` benefits from the cache.
* **On-disk hash cache** (``piptools.repositories._hash_cache``):
  ``url -> (sha, size)`` pairs for content-addressable PyPI URLs, keyed under
  ``cache_dir``. A host allow-list excludes private indexes so stale
  digests don't leak across runs.
* **In-memory LRU caches in ``config``**: parsed ``pyproject.toml`` tables and
  marker shapes that several pipeline stages re-read; the caches hold for
  one resolution to avoid re-walking the same file.

Marker AST surface
==================

Anything that walks ``Marker._markers`` lives in ``_marker_ast`` (decomposer,
shape verifier, platform-blind rewriter). Anything that swaps a marker
evaluation entry point for a block lives in ``_marker_eval``
(``platform_blind_marker_eval`` for the scan, ``mock_marker_environment``
for per-target resolutions). Concentrating the private-API contact surface in
two files bounds the blast radius when ``packaging`` rearranges its AST.

Pip / resolvelib introspection
==============================

Two unavoidable reaches into private state (the partition scan's marker
extraction and the merge step's forward-dependency walk) live in
``resolve/_introspect`` so a future pip release that moves either shape
touches one diff.
"""

from __future__ import annotations

import typing as _t

if _t.TYPE_CHECKING:
    from .builder import build_pylock_document

__all__ = [
    "build_pylock_document",
]


def __getattr__(name: str) -> _t.Any:
    if name == "build_pylock_document":
        from .builder import build_pylock_document

        return build_pylock_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
