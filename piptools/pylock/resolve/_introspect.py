"""Concentrate every reach into pip and resolvelib internal state.

The pipeline has two unavoidable introspection sites. The partition scan
reads
``BacktrackingResolver._resolver_result.criteria[*].information[*].requirement._ireq.req.marker``
to extract env-axis markers. The merge step walks
``resolver_result.mapping`` and ``graph.iter_children`` to build the forward
dependency map. Both depend on private attributes of pip and resolvelib, so a
release that moves either shape breaks pip-tools. Holding both reaches in
one module bounds the blast radius to one diff when pip moves.
"""

from __future__ import annotations

import typing as _t
from collections import defaultdict

from pip._vendor.resolvelib.resolvers import Result

from ..._compat import canonicalize_name
from ...logging import log
from ...resolver import BacktrackingResolver
from ...utils import strip_extras
from .._marker_ast import PLATFORM_MARKER_KEYS

_PARTITION_MARKER_KEYS: _t.Final[frozenset[str]] = PLATFORM_MARKER_KEYS | {
    "python_version",
    "python_full_version",
    "implementation_name",
    "implementation_version",
}


def extract_dep_markers(scan_resolver: BacktrackingResolver) -> set[str]:
    """Return env-referencing markers seen during a scan resolution.

    The walk goes through the resolvelib ``Result`` directly. Pip-tools'
    wrapper does not surface pip's per-ireq markers, and resolvelib's
    criteria carry the same data with the marker attached to each
    information record. The walker drops markers that reference only
    ``extras`` or ``dependency_groups`` so the per-extra and per-group
    resolution passes keep ownership of those axes; emitting them here
    would collapse envs that those passes already separate.

    The walker logs one info line when criteria exist but none carry
    markers. That combination signals that pip's or resolvelib's internal
    shape has moved and turns up rarely in practice.

    :param scan_resolver: The backtracking resolver whose discovery scan
        produced the criteria graph the walker inspects.
    :returns: The set of marker strings referencing env-axis variables that
        the scan observed.
    """
    found: set[str] = set()
    result = getattr(scan_resolver, "_resolver_result", None)
    if result is None:
        return found
    saw_criterion_with_markers = False
    for criterion in result.criteria.values():
        for info in criterion.information:
            requirement = getattr(info.requirement, "_ireq", None)
            req = getattr(requirement, "req", None) if requirement is not None else None
            marker = getattr(req, "marker", None)
            if marker is None:
                continue
            saw_criterion_with_markers = True
            marker_str = str(marker)
            if any(key in marker_str for key in _PARTITION_MARKER_KEYS):
                found.add(marker_str)
    if result.criteria and not saw_criterion_with_markers:
        log.info(
            f"Marker-discovery scan resolved but extracted zero markers "
            f"across {len(result.criteria)} criteria. Single-cohort "
            f"collapse holds for projects with no env-conditional deps; "
            f"if your lock has such deps, please report (pip's resolver "
            f"introspection shape may have moved)."
        )
    return found


def get_forward_dependencies(resolver_result: Result) -> dict[str, set[str]]:
    """Return the parent-to-child dependency map for real (non-extras) candidates.

    Strips synthetic extras candidates from both sides of every edge so the
    returned map mirrors the package graph the lockfile emits.

    :param resolver_result: The result the backtracking resolver produced for
        the resolution to summarise.
    :returns: Mapping from each real package name to the names of its direct
        runtime dependencies.
    """
    forward_deps: defaultdict[str, set[str]] = defaultdict(set)

    real_packages = {
        strip_extras(canonicalize_name(c.name))
        for c in resolver_result.mapping.values()
        if c.get_install_requirement() is not None
    }

    for candidate in resolver_result.mapping.values():
        if (
            parent_name := strip_extras(canonicalize_name(candidate.name))
        ) not in real_packages:
            continue
        for child_name in resolver_result.graph.iter_children(candidate.name):
            if child_name is None:
                continue
            stripped_child = strip_extras(canonicalize_name(child_name))
            if stripped_child != parent_name and stripped_child in real_packages:
                forward_deps[parent_name].add(stripped_child)

        if parent_name not in forward_deps:
            forward_deps[parent_name] = set()

    return dict(forward_deps)


__all__ = ["extract_dep_markers", "get_forward_dependencies"]
