"""Helpers that walk packaging's marker AST.

Several call sites (``validate.ensure_marker_disjointness``,
``resolve._splice_extras._classify_extras_roots``,
``_marker_eval.platform_blind_marker_eval``) reach into the private
``Marker._markers`` AST plus ``packaging._parser.{Op, Value, Variable}``
node types. Centralising those reaches here keeps the private-API
contact surface in one file and holds the one-time shape verifier in a
single place that two unrelated modules can share.

The verifier runs on first call so a stale ``packaging`` on a user's
machine breaks the marker-shape-dependent code paths, not ``import
piptools`` at module-load time.
"""

from __future__ import annotations

import typing as _t
from collections.abc import Callable
from types import ModuleType

from packaging import markers as _pkg_markers
from packaging._parser import Op, Value, Variable
from packaging.markers import Marker

from ..exceptions import PipToolsError

# The marker AST is a heterogeneous nested structure: a sub-marker group is a list of nodes, a
# comparison is a 3-tuple of ``(lhs, Op, rhs)`` where each side is a ``Variable`` or a ``Value``,
# and the boolean operators between siblings are bare ``"and"`` / ``"or"`` strings. ``packaging``
# does not expose a public type alias for these nodes, so we name the constituent types off the
# ``packaging._parser`` private surface (the same module ``packaging.markers`` imports them from).
# The rewriter below needs the precise shape rather than ``Any``.
_AstAtom: _t.TypeAlias = "Variable | Value"
_AstComparison: _t.TypeAlias = "tuple[_AstAtom, Op, _AstAtom]"
_AstNode: _t.TypeAlias = "_AstComparison | list[_AstNode] | str"

# Variables the discovery scan folds to True so one scan covers every platform; python markers
# stay untouched to preserve per-python differences.
PLATFORM_MARKER_KEYS: _t.Final[frozenset[str]] = frozenset(
    {
        "sys_platform",
        "platform_machine",
        "platform_system",
        "platform_release",
        "platform_version",
        "os_name",
    }
)


class MarkerShape(_t.NamedTuple):
    """Decomposition of a marker into its extras, groups, and env-only parts."""

    extras_in: frozenset[str]
    groups_in: frozenset[str]
    env_marker: Marker | None


def decompose(marker: Marker | None) -> MarkerShape | None:
    """Split a marker into its extras, groups, and env-clause axes.

    The symbolic disjointness check reasons about extras, groups, and the env clause as independent
    axes; without that decomposition the check falls back to the bounded powerset on every input,
    defeating the symbolic shortcut.

    :param marker: Marker to decompose. ``None`` represents an always-true marker.
    :returns: The decomposed shape, or ``None`` when the marker mixes axes in a shape the walker
        refuses to flatten so the caller falls back to the powerset enumeration.
    """
    if marker is None:
        return MarkerShape(frozenset(), frozenset(), None)
    # Without this, a packaging release that moves the AST shape degrades decompose to ``None``
    # and pushes every marker into the powerset path; the verifier surfaces the regression as an
    # explicit failure.
    verify_packaging_marker_shape()
    if (decomposed := _decompose_axes(marker._markers)) is None:
        return None
    extras, groups, env_nodes = decomposed
    if not env_nodes:
        return MarkerShape(frozenset(extras), frozenset(groups), None)
    env_marker = Marker.__new__(Marker)
    env_marker._markers = env_nodes
    return MarkerShape(frozenset(extras), frozenset(groups), env_marker)


def _decompose_axes(
    nodes: list[_t.Any],
) -> tuple[set[str], set[str], list[_t.Any]] | None:
    """Decompose one AST level into extras, groups, and env-clause buckets.

    A bool plus in/out collectors would conflate "decomposed cleanly" with "left in a partial
    state on bail-out", forcing every caller to remember that the collectors hold valid data on
    success. Returning ``Optional[tuple]`` makes the success/failure contract a property of the
    signature so the caller cannot read half-populated mid-walk state.

    :param nodes: One AST level of a parsed marker (the body of ``Marker._markers`` or any
        recursive sub-list of the same shape).
    :returns: ``(extras, groups, env_nodes)`` when the level decomposes, or ``None`` when the
        caller should fall back to the powerset enumeration.
    """
    # Without the strip ``Marker("(extra == 'a')")`` decomposes differently from the unwrapped
    # form even though the markers carry identical meaning.
    while len(nodes) == 1 and isinstance(nodes[0], list):
        nodes = nodes[0]
    # An ``or`` joining an extras opt-in with an env clause cannot collapse to
    # ``(extras_in) and (env)``: the original fires when *either* side is true, while the
    # collapsed form needs *both*. Bail so the caller falls back.
    if _has_mixed_or_axes(nodes):
        return None
    extras: set[str] = set()
    groups: set[str] = set()
    env_nodes: list[_t.Any] = []
    op_seen: str | None = None
    for index, node in enumerate(nodes):
        if index % 2 == 1:
            if not isinstance(node, str) or node not in {"and", "or"}:
                return None
            if op_seen is None:
                op_seen = node
            elif node != op_seen:
                return None
            continue
        if isinstance(node, list):
            if (sub := _decompose_axes(node)) is None:
                return None
            sub_extras, sub_groups, sub_env = sub
            if sub_env:
                # An ``or`` group that mixes extras with env clauses is outside pip-tools'
                # emitted shape; refuse to decompose so the caller falls back to the powerset.
                if op_seen == "or" and (sub_extras or sub_groups):
                    return None
                _append_env(env_nodes, op_seen, node)
            extras |= sub_extras
            groups |= sub_groups
            continue
        if not isinstance(node, tuple) or len(node) != 3:
            return None
        if (opt_in_kind := _classify_opt_in(node)) is None:
            _append_env(env_nodes, op_seen, node)
            continue
        bucket, value = opt_in_kind
        if bucket == "extras":
            extras.add(value)
        else:
            groups.add(value)
    return extras, groups, env_nodes


def _append_env(env_nodes: list[_t.Any], op_seen: str | None, node: _t.Any) -> None:
    """Append ``node`` to ``env_nodes`` with the most recent boolean operator.

    Reaching a second operand means the loop crossed an odd-index step that assigned ``op_seen``;
    the assertion makes that invariant load-bearing rather than letting a fallback operator mask
    a future regression.
    """
    if not env_nodes:
        env_nodes.append(node)
        return
    assert op_seen is not None
    env_nodes.extend([op_seen, node])


def has_top_level_or(marker: Marker) -> bool:
    """Report whether the marker's top level carries an ``or`` operator.

    A trailing ``and X`` appended to a marker whose top level is ``or`` binds to the rightmost
    disjunct under PEP 508 precedence and narrows the marker's truth set, so callers building
    composite markers by string concatenation need this signal to know when wrapping in parens is
    required. Substring-checking the rendered marker for ``" or "`` encodes an undocumented
    spacing assumption from the producer and over-wraps when ``or`` lives inside a parenthesised
    sub-expression.

    :param marker: Parsed marker whose AST the function inspects.
    :returns: ``True`` when at least one ``or`` operator sits at the top level.
    """
    return any(node == "or" for i, node in enumerate(marker._markers) if i % 2 == 1)


def _has_mixed_or_axes(nodes: list[_t.Any]) -> bool:
    """Report whether ``nodes`` mix opt-in and env clauses under an ``or``.

    Without this guard ``_decompose_axes`` collapses an ``or`` that joins extras or groups with an
    env clause into the narrower ``extras AND env`` shape, fabricating disjointness that is not
    there; detecting the mix here forces the powerset fallback so the symbolic shortcut stays
    sound on inputs it cannot flatten.
    """
    if not any(node == "or" for i, node in enumerate(nodes) if i % 2 == 1):
        return False
    has_opt_in = False
    has_env = False
    for index, node in enumerate(nodes):
        if index % 2 == 1:
            continue
        if isinstance(node, tuple):
            if _classify_opt_in(node) is not None:
                has_opt_in = True
            else:
                has_env = True
        elif isinstance(node, list):
            # Nested groups: peek to see whether the sub-list contributes to the opt-in or env
            # axis. A single tuple inside counts; deeper nesting falls through to the recursive
            # walk's rejection.
            if len(node) == 1 and isinstance(node[0], tuple):
                if _classify_opt_in(node[0]) is not None:
                    has_opt_in = True
                else:
                    has_env = True
            else:
                # Defer to recursion; if the nested list itself mixes axes under ``or`` this
                # returns False here and the recursive call detects and rejects.
                return False
    return has_opt_in and has_env


def _classify_opt_in(
    node: tuple[_t.Any, Op, _t.Any],
) -> tuple[str, str] | None:
    lhs, op, rhs = node
    if op.value == "in":
        if isinstance(lhs, Value) and isinstance(rhs, Variable):
            if rhs.value == "extras":
                return ("extras", lhs.value)
            if rhs.value == "dependency_groups":
                return ("groups", lhs.value)
    if op.value == "==":
        if (
            isinstance(lhs, Variable)
            and lhs.value == "extra"
            and isinstance(rhs, Value)
        ):
            return ("extras", rhs.value)
        if (
            isinstance(rhs, Variable)
            and rhs.value == "extra"
            and isinstance(lhs, Value)
        ):
            return ("extras", lhs.value)
    return None


def collect_extras(nodes: list[_t.Any]) -> _t.Iterator[str]:
    """Yield extra names from ``extra == 'X'`` comparisons in either order.

    PEP 508 lets the comparison go in either direction (``extra == 'X'`` or ``'X' == extra``);
    regexing the stringified marker catches the first form, so an extras-conditional dep written
    the other way slips into the base set and loses its ``'X' in extras`` marker on the lockfile
    entry. Walking the AST in either operand order spots both shapes.

    :param nodes: AST nodes drawn from a parsed marker's internal representation.
    :returns: Iterator of extra names found in equality clauses.
    """
    for node in nodes:
        if isinstance(node, list):
            yield from collect_extras(node)
        elif isinstance(node, tuple):
            lhs, op, rhs = node
            if op.value != "==":
                continue
            if (
                isinstance(lhs, Variable)
                and lhs.value == "extra"
                and isinstance(rhs, Value)
            ):
                yield rhs.value
            elif (
                isinstance(rhs, Variable)
                and rhs.value == "extra"
                and isinstance(lhs, Value)
            ):
                yield lhs.value


_marker_shape_verified = False


def verify_packaging_marker_shape() -> None:
    """Probe packaging's marker AST shape before any caller relies on it.

    The rewriter and the partition scan depend on packaging's marker AST being a list of
    three-tuple comparison nodes, and on the ``[[]]`` empty-sub-marker idiom evaluating to
    ``True``. A future packaging release could rearrange that without breaking the string form of
    the marker, leaving the patch un-rewritten and producing a wrong lockfile. The probe runs on
    first use so a stale packaging install does not break ``import piptools`` outright.

    :raises PipToolsError: When the marker AST shape no longer matches the contract pip-tools
        relies on.
    """
    global _marker_shape_verified
    if _marker_shape_verified:
        return
    rewrite = make_platform_blind_evaluator(
        _pkg_markers, _pkg_markers._evaluate_markers
    )
    synthetic = [(Variable("sys_platform"), Op("=="), Value("linux"))]
    if not rewrite(synthetic, {}):
        raise PipToolsError(
            "packaging marker AST shape changed: platform-blind rewriter "
            "could not fold a synthetic ``sys_platform == 'linux'`` "
            "comparison to True. pip-tools' partition scan needs the "
            "rewriter intact; pin packaging to the supported version."
        )
    if not _pkg_markers._evaluate_markers([[]], {}):
        raise PipToolsError(
            "packaging marker evaluator changed: ``[[]]`` no longer evaluates "
            "to True, which the platform-blind rewriter relies on. pip-tools' "
            "partition scan cannot run on this packaging version."
        )
    probe = _pkg_markers.Marker("'a' in extras")
    if not (
        hasattr(probe, "_markers")
        and isinstance(probe._markers, list)
        and probe._markers
        and isinstance(probe._markers[0], tuple)
    ):
        raise PipToolsError(
            "packaging marker AST changed: ``Marker._markers`` is no "
            "longer a list of tuple comparison nodes. pip-tools' marker "
            "decomposer and extras-collection helpers depend on that "
            "shape; pin packaging to the supported version."
        )
    _marker_shape_verified = True


def make_platform_blind_evaluator(
    module: ModuleType, original: Callable[..., bool]
) -> Callable[..., bool]:
    """Build an evaluator that folds platform comparisons to ``True``.

    Without this rewriter the partition scan needs one resolution per target platform to discover
    every platform-conditional dependency; folding platform comparisons to ``True`` lets a single
    resolution see every branch in one walk while keeping python-version comparisons honoured.

    :param module: The packaging marker module whose ``Variable`` type identifies AST nodes.
    :param original: The original evaluator the patched form delegates to once platform clauses
        have been folded.
    :returns: A drop-in replacement evaluator that ignores platform clauses.
    """
    Variable = module.Variable

    def rewrite(markers: list[_AstNode]) -> list[_AstNode]:
        out: list[_AstNode] = []
        for m in markers:
            if isinstance(m, list):
                out.append(rewrite(m))
                continue
            if isinstance(m, tuple):
                lhs, _op, rhs = m
                if isinstance(lhs, Variable):
                    var = lhs.value
                elif isinstance(rhs, Variable):
                    var = rhs.value
                else:
                    var = None
                if var in PLATFORM_MARKER_KEYS:
                    out.append([])  # always-true sub-marker
                    continue
            out.append(m)
        return out

    def patched(markers: list[_AstNode], environment: dict[str, str]) -> bool:
        return bool(original(rewrite(markers), environment))

    return patched


__all__ = [
    "PLATFORM_MARKER_KEYS",
    "MarkerShape",
    "collect_extras",
    "decompose",
    "has_top_level_or",
    "make_platform_blind_evaluator",
    "verify_packaging_marker_shape",
]
