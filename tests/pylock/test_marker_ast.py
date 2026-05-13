from __future__ import annotations

import pytest
from packaging import markers as _packaging_markers
from packaging._parser import Op, Value, Variable
from packaging.markers import Marker
from pytest_mock import MockerFixture

from piptools.exceptions import MarkerDisjointnessError, PipToolsError
from piptools.pylock import _marker_ast
from piptools.pylock._marker_ast import (
    _classify_opt_in,
    _has_mixed_or_axes,
    collect_extras,
    decompose,
    make_platform_blind_evaluator,
)
from piptools.pylock.platforms import TargetEnvironment, build_target_environments
from piptools.pylock.validate import ensure_marker_disjointness

from .conftest import EntryFactory


def _opt_in_node(name: str) -> tuple[Value, Op, Variable]:
    return (Value(name), Op("in"), Variable("extras"))


@pytest.mark.parametrize(
    "ast_nodes",
    (
        pytest.param(
            [_opt_in_node("a"), 42, _opt_in_node("b")],
            id="non-string-operator",
        ),
        pytest.param(
            [_opt_in_node("a"), "xor", _opt_in_node("b")],
            id="unsupported-operator",
        ),
        pytest.param(
            ["bare-string"],
            id="non-tuple-non-list-operand",
        ),
    ),
)
def test_decomposer_refuses_malformed_ast(
    ast_nodes: list[tuple[Value, Op, Variable] | str | int],
) -> None:
    # The disjointness shortcut walks an AST shape produced by
    # ``Marker(...)``; a hand-crafted or future-extended shape can carry
    # nodes outside the parser's vocabulary. ``decompose`` returns
    # ``None`` for those so callers fall back to the safer powerset path.
    fake_marker = Marker.__new__(Marker)
    object.__setattr__(fake_marker, "_markers", ast_nodes)
    assert decompose(fake_marker) is None


def test_handles_reversed_extras_comparison(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # The decomposer matches both ``'X' in extras`` and the legacy
    # ``extra == 'X'`` shape so the fast path applies to either form.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' == extra"),
            make_entry("2.0", marker="extra == 'b'"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_handles_dependency_groups_marker(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``'X' in dependency_groups`` is the PEP 735-style opt-in marker; the
    # decomposer classifies it into the groups bucket so the symbolic shortcut
    # produces the right witness instead of falling back to powerset.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'g1' in dependency_groups"),
            make_entry("2.0", marker="'g2' in dependency_groups"),
        ],
    }
    with pytest.raises(
        MarkerDisjointnessError, match="mutually-exclusive markers"
    ) as exc:
        ensure_marker_disjointness(merged, linux_envs, (), ("g1", "g2"))
    assert '{group = "g1"}' in str(exc.value)
    assert '{group = "g2"}' in str(exc.value)


def test_handles_nested_env_subexpressions(
    make_entry: EntryFactory,
) -> None:
    # Parenthesized env clauses parse as a nested list at the top level. The
    # recursive walk has to merge the sub-list's env nodes into the running
    # env_marker rather than mistreat the wrapper as an extras opt-in.
    envs = build_target_environments(("linux-x86_64", "windows-amd64"), ("3.12",))
    merged = {
        "pkg": [
            make_entry(
                "1.0",
                marker="'a' in extras and (python_version >= '3.10' "
                "and sys_platform == 'linux')",
            ),
            make_entry(
                "2.0",
                marker="'a' in extras and (python_version >= '3.10' "
                "and sys_platform == 'win32')",
            ),
        ],
    }
    ensure_marker_disjointness(merged, envs, ("a",), ())


def test_decomposer_strips_double_wrapped_markers(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``(('a' in extras))`` parses as ``[[[t]]]``; the top-level wrapper-strip
    # loop has to peel until it reaches the operand level so the symbolic path
    # still recognizes the shape.
    merged = {
        "pkg": [
            make_entry("1.0", marker="(('a' in extras))"),
            make_entry("2.0", marker="(('b' in extras))"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_decomposer_rejects_mixed_and_or_at_top_level(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``a or b and c`` mixes operators at the same level; not in pip-tools'
    # emitted shape. Reject so the powerset path proves disjointness instead
    # of the symbolic shortcut walking a malformed AST.
    merged = {
        "pkg": [
            make_entry(
                "1.0",
                marker="'a' in extras or 'b' in extras and 'c' in extras",
            ),
            make_entry(
                "2.0",
                marker="'d' in extras and 'a' not in extras "
                "and 'b' not in extras and 'c' not in extras",
            ),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b", "c", "d"), ())


def test_decomposer_rejects_top_level_or_mixing_extras_and_env(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``'a' in extras or sys_platform == 'win32'`` cannot collapse to
    # ``extras_in={a} AND env``: the original fires when *either* side is
    # true, while the collapsed form needs *both*. Decomposing it that
    # way would miss collisions on envs where one side fires alone;
    # refuse the decomposition so the powerset proves disjointness. The
    # pair below *is* disjoint on linux-only target_envs, which is what
    # the test asserts.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' in extras or sys_platform == 'win32'"),
            make_entry(
                "2.0",
                marker="'b' in extras and 'a' not in extras and "
                "sys_platform == 'linux'",
            ),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_decomposer_rejects_or_with_mixed_inner_shape(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # Inside an ``or`` group, a parenthesized ``(env or extras)`` mixes axes
    # in a way the symbolic shortcut cannot reduce; the bounded powerset
    # then proves the pair (incidentally collide on extras={'a'}).
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' in extras"),
            make_entry(
                "2.0",
                marker="'a' in extras and ('b' in extras or python_version == '3.12'"
                " and 'c' in extras)",
            ),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("a", "b", "c"), ())


def test_decomposer_handles_bare_extras_subexpression(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # A parenthesized inner clause that is purely extras (no env nodes) must
    # propagate its extras up without trying to attach an env_marker.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' in extras and ('b' in extras)"),
            make_entry("2.0", marker="'c' in extras and 'a' not in extras"),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b", "c"), ())


def test_decomposer_extends_env_nodes_across_subexpressions(
    make_entry: EntryFactory,
) -> None:
    # Two parenthesized env clauses joined by ``and`` need to extend the
    # running env_nodes list, not overwrite it; otherwise both sides would
    # appear unconditional and look like a collision.
    envs = build_target_environments(("linux-x86_64", "windows-amd64"), ("3.12",))
    merged = {
        "pkg": [
            make_entry(
                "1.0",
                marker="(sys_platform == 'linux') and (python_version >= '3.10')",
            ),
            make_entry(
                "2.0",
                marker="(sys_platform == 'win32') and (python_version >= '3.10')",
            ),
        ],
    }
    ensure_marker_disjointness(merged, envs, (), ())


@pytest.mark.parametrize(
    "marker_text",
    (
        pytest.param("'g' in os_name", id="value-in-non-extras-variable"),
        pytest.param("os_name in 'foo'", id="variable-in-value"),
    ),
)
def test_classify_opt_in_ignores_in_against_other_shapes(
    linux_envs: dict[str, TargetEnvironment],
    make_entry: EntryFactory,
    marker_text: str,
) -> None:
    # ``in`` counts as an opt-in clause when it reads ``'X' in extras``
    # or ``'X' in dependency_groups``; every other ``in`` shape (substring
    # checks, reversed operands) falls through to the env-side path.
    merged = {
        "pkg": [
            make_entry("1.0", marker=marker_text),
            make_entry("2.0", marker=marker_text.replace("'g'", "'h'")),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, (), ())


def test_classify_opt_in_recognises_extras_membership() -> None:
    # Direct call: a ``'X' in extras`` tuple classifies into the extras bucket.
    node = (Value("a"), Op("in"), Variable("extras"))
    assert _classify_opt_in(node) == ("extras", "a")


def test_classify_opt_in_recognises_groups_membership() -> None:
    node = (Value("g"), Op("in"), Variable("dependency_groups"))
    assert _classify_opt_in(node) == ("groups", "g")


def test_collect_extras_walks_nested_lists() -> None:
    nested = [
        (Variable("extra"), Op("=="), Value("a")),
        "or",
        [(Value("b"), Op("=="), Variable("extra"))],
    ]
    assert sorted(collect_extras(nested)) == ["a", "b"]


def test_collect_extras_skips_non_equality_comparisons() -> None:
    # ``==`` produces an extras name; any other comparison the AST
    # carries (``in``, ``!=``, ``<``) gets skipped so the collector does
    # not pick up unrelated env clauses.
    nodes = [(Variable("extra"), Op("!="), Value("a"))]
    assert list(collect_extras(nodes)) == []


@pytest.mark.parametrize(
    "nodes",
    (
        pytest.param(
            [(Variable("python_version"), Op("=="), Value("3.12"))],
            id="env-equality-neither-side-is-extra",
        ),
        pytest.param(
            [(Value("3.12"), Op("=="), Value("3.12"))],
            id="literal-equality-no-variable-side",
        ),
    ),
)
def test_collect_extras_skips_equalities_unrelated_to_extras(
    nodes: list[tuple[Variable | Value, Op, Variable | Value]],
) -> None:
    # Non-extras equalities do not surface as phantom extras.
    assert list(collect_extras(nodes)) == []


@pytest.mark.parametrize(
    "even_index_node",
    (
        pytest.param("bare-string", id="string-at-even-index"),
        pytest.param(42, id="int-at-even-index"),
    ),
)
def test_has_mixed_or_axes_skips_non_tuple_non_list_operands(
    even_index_node: object,
) -> None:
    # A malformed AST skips the operand instead of crashing.
    nodes = [
        even_index_node,
        "or",
        (Variable("python_version"), Op("=="), Value("3.12")),
    ]
    assert _has_mixed_or_axes(nodes) is False


def test_make_platform_blind_evaluator_handles_literal_only_comparison() -> None:
    # A malformed marker tuple with a literal on both sides does not
    # crash the scan; the rewrite passes such tuples through to the
    # original evaluator unchanged.
    literal_only = (Value("x"), Op("=="), Value("y"))
    captured: list[list[object]] = []

    def fake_evaluate(markers: list[object], environment: dict[str, str]) -> bool:
        captured.append(markers)
        return False

    patched = make_platform_blind_evaluator(_packaging_markers, fake_evaluate)
    patched([literal_only], {})
    assert captured == [[literal_only]]


def test_verify_packaging_marker_shape_is_idempotent() -> None:
    # The smoke check ran once at module import; calling it again
    # post-import keeps passing on the supported packaging version,
    # otherwise the rewriter has acquired an unintended side-effect.
    _marker_ast.verify_packaging_marker_shape()


def test_verify_packaging_marker_shape_raises_when_evaluator_lies(
    mocker: MockerFixture,
) -> None:
    # If a future packaging release breaks the ``[[]]`` -> True
    # invariant the rewriter relies on, the partition scan would leave
    # platform comparisons un-rewritten and produce wrong cohorts.
    # ``PipToolsError`` (rather than ``ImportError``) lets the
    # partition's caller fall back to per-env resolution instead of
    # breaking ``import piptools`` entirely.
    mocker.patch.object(_marker_ast, "_marker_shape_verified", False)
    mocker.patch.object(_packaging_markers, "_evaluate_markers", return_value=False)
    with pytest.raises(PipToolsError, match="rewriter"):
        _marker_ast.verify_packaging_marker_shape()


def test_verify_packaging_marker_shape_raises_when_empty_marker_changes(
    mocker: MockerFixture,
) -> None:
    # The rewriter substitutes ``[[]]`` for platform comparisons it
    # forces to True. An upstream packaging refactor that flipped the
    # empty-AST identity would invert that semantics. Detecting it here
    # keeps the cohort scan trustworthy across packaging upgrades.
    mocker.patch.object(_marker_ast, "_marker_shape_verified", False)
    mocker.patch.object(
        _packaging_markers,
        "_evaluate_markers",
        side_effect=[True, False],
    )
    with pytest.raises(PipToolsError, match="``\\[\\[\\]\\]``"):
        _marker_ast.verify_packaging_marker_shape()


def test_verify_packaging_marker_shape_raises_when_markers_attr_changes(
    mocker: MockerFixture,
) -> None:
    # If a packaging release renames ``Marker._markers`` or returns
    # something other than ``[(lhs, op, rhs)]``, the decomposer's
    # tuple-shape assumptions break. Trip the shape check so callers fall
    # back to per-env resolution rather than produce wrong cohorts.
    mocker.patch.object(_marker_ast, "_marker_shape_verified", False)
    mocker.patch.object(
        _packaging_markers, "_evaluate_markers", side_effect=[True, True]
    )
    fake_marker = mocker.MagicMock()
    fake_marker._markers = []
    mocker.patch.object(_packaging_markers, "Marker", return_value=fake_marker)
    with pytest.raises(PipToolsError, match="``Marker._markers`` is no longer"):
        _marker_ast.verify_packaging_marker_shape()


def test_decomposer_or_with_paren_wrapped_extras_and_env(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``('a' in extras) or (python_version == '3.10')`` parses to
    # ``[[t1], 'or', [t2]]``; both operands are 1-element lists. The
    # mixed-axis detector needs to peek inside each wrapper to classify
    # the inner tuple, otherwise the shortcut would happily collapse this
    # ``or`` into a narrower ``and`` and miss collisions.
    merged = {
        "pkg": [
            make_entry(
                "1.0",
                marker="('a' in extras) or (python_version == '3.10')",
            ),
            make_entry(
                "2.0",
                marker="'b' in extras and 'a' not in extras "
                "and python_version != '3.10'",
            ),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())
