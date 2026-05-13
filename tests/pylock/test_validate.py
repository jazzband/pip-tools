from __future__ import annotations

import time

import pytest
from packaging.markers import Marker, UndefinedEnvironmentName
from pytest_mock import MockerFixture

from piptools.exceptions import MarkerDisjointnessError, PipToolsError
from piptools.pylock.config import ConflictItem
from piptools.pylock.platforms import TargetEnvironment, build_target_environments
from piptools.pylock.validate import (
    _evaluate,
    ensure_marker_disjointness,
    ensure_requires_python_consistency,
)

from .conftest import EntryFactory


def test_passes_for_single_entry(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    ensure_marker_disjointness({"foo": [make_entry("1.0")]}, linux_envs, (), ())


def test_passes_for_platform_split(make_entry: EntryFactory) -> None:
    envs = build_target_environments(("linux-x86_64", "macos-arm64"), ("3.12",))
    merged = {
        "urllib3": [
            make_entry("1.0", marker="sys_platform == 'linux'"),
            make_entry("2.0", marker="sys_platform == 'darwin'"),
        ],
    }
    ensure_marker_disjointness(merged, envs, (), ())


def test_passes_when_extras_explicitly_exclude_each_other(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    merged = {
        "urllib3": [
            make_entry("1.0", marker="'a' in extras and 'b' not in extras"),
            make_entry("2.0", marker="'b' in extras and 'a' not in extras"),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_raises_when_user_can_request_both_extras(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    merged = {
        "urllib3": [
            make_entry("1.0", marker="'a' in extras"),
            make_entry("2.0", marker="'b' in extras"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_raises_when_one_marker_is_unconditional(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    merged = {
        "urllib3": [
            make_entry("1.0"),
            make_entry("2.0", marker="'dev' in extras"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("dev",), ())


def test_collision_error_hints_at_conflicts_for_extras(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # The fix for an extras-driven collision is to declare the extras as
    # conflicting in pyproject, not to pin a single version. Surface that
    # remedy in the error message instead of the generic one.
    merged = {
        "urllib3": [
            make_entry("1.0", marker="'a' in extras"),
            make_entry("2.0", marker="'b' in extras"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError) as exc_info:
        ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())
    assert "[tool.pip-tools].conflicts" in str(exc_info.value)
    assert '{extra = "a"}' in str(exc_info.value)
    assert '{extra = "b"}' in str(exc_info.value)


def test_collision_error_omits_conflicts_hint_for_env_only_collision(
    make_entry: EntryFactory,
) -> None:
    # When the env axis alone triggers the collision, the conflicts hint
    # is the wrong remedy; emitting it would point users at a knob that
    # cannot fix the situation.
    envs = build_target_environments(("linux-x86_64",), ("3.12",))
    merged = {
        "urllib3": [
            make_entry("1.0"),
            make_entry("2.0"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError) as exc_info:
        ensure_marker_disjointness(merged, envs, (), ())
    assert "[tool.pip-tools].conflicts" not in str(exc_info.value)


def test_disjointness_check_scales_with_many_extras_and_groups(
    make_entry: EntryFactory,
) -> None:
    # The unrestricted ``|envs| x 2^|extras| x 2^|groups|`` walk is
    # unusable on real projects: 12 extras x 8 groups x dozens of envs =
    # 53M evaluations. The symbolic shortcut for pip-tools-shaped markers
    # finishes in well under a second on the same shape.
    extras = tuple(f"e{i}" for i in range(12))
    groups = tuple(f"g{i}" for i in range(8))
    envs = build_target_environments(
        ("linux-x86_64", "windows-amd64", "macos-arm64"), ("3.10", "3.11", "3.12")
    )
    merged = {
        "pkg": [
            make_entry("1.0", marker="'e0' in extras"),
            make_entry("2.0", marker="'e1' in extras"),
        ],
    }

    start = time.perf_counter()
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, envs, extras, groups)
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"symbolic check too slow: {elapsed:.2f}s"


def test_powerset_fallback_handles_negation(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``'a' not in extras`` is outside pip-tools' emitted shape so the
    # decomposer refuses; the bounded powerset fallback still proves these
    # markers disjoint without exploding on the user.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' in extras and 'b' not in extras"),
            make_entry("2.0", marker="'b' in extras and 'a' not in extras"),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_evaluate_treats_undefined_environment_as_no_match(
    mocker: MockerFixture,
) -> None:
    # PEP 508 markers can reference env vars the lockfile's target env
    # never sets, in which case ``Marker.evaluate`` raises
    # ``UndefinedEnvironmentName``. The disjointness check swallows that
    # and treats the marker as "does not match this env" rather than
    # crash mid-lock.
    marker = mocker.create_autospec(Marker, instance=True)
    marker.evaluate.side_effect = UndefinedEnvironmentName("platform_release")
    assert _evaluate(marker, {"sys_platform": "linux"}) is False


def test_powerset_fallback_runs_when_decompose_refuses(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # An ``or`` whose right side mixes env and extras is outside the shape the
    # symbolic check accepts; the bounded powerset fallback still proves the
    # collision (left and right both fire on extras={'a'}).
    merged = {
        "pkg": [
            make_entry("1.0", marker="'a' in extras"),
            make_entry(
                "2.0",
                marker="'a' in extras or (python_version == '3.12' and 'a' in extras)",
            ),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="mutually-exclusive markers"):
        ensure_marker_disjointness(merged, linux_envs, ("a",), ())


def test_powerset_fallback_raises_when_limit_exceeded(
    make_entry: EntryFactory, mocker: MockerFixture
) -> None:
    # The bounded powerset cannot bail without a signal: PEP 751 forbids
    # ambiguous installer matches, and "treat as not provably overlapping"
    # flips a spec-mandated error into an install-time bug. The user has
    # to act (narrow markers, reduce extras and groups, or raise the bound).
    mocker.patch("piptools.pylock.validate._POWERSET_FALLBACK_LIMIT", 4)
    envs = build_target_environments(("linux-x86_64",), ("3.12",))
    extras = ("a", "b", "c", "d", "e", "f", "g", "h")
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
    with pytest.raises(MarkerDisjointnessError, match="powerset budget"):
        ensure_marker_disjointness(merged, envs, extras, ())


def test_powerset_fallback_returns_disjoint_when_no_collision(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # Mirror of the previous test, but with markers the powerset loop
    # cannot satisfy together. Hits the "no collision found" exit of the
    # fallback so ``_powerset`` runs to completion.
    merged = {
        "pkg": [
            make_entry(
                "1.0",
                marker="'a' in extras and 'b' not in extras",
            ),
            make_entry(
                "2.0",
                marker="'b' in extras or (python_version >= '3.10' "
                "and 'a' not in extras)",
            ),
        ],
    }
    ensure_marker_disjointness(merged, linux_envs, ("a", "b"), ())


def test_requires_python_consistency_passes_when_unset(
    make_entry: EntryFactory,
) -> None:
    envs = build_target_environments(("linux-x86_64",), ("3.12",))
    entry = make_entry("1.0", environments=set(envs))
    ensure_requires_python_consistency({"pkg": [entry]}, {("pkg", "1.0"): None}, envs)


def test_requires_python_consistency_passes_when_satisfied(
    make_entry: EntryFactory,
) -> None:
    envs = build_target_environments(("linux-x86_64",), ("3.12",))
    entry = make_entry("1.0", environments=set(envs))
    ensure_requires_python_consistency(
        {"pkg": [entry]}, {("pkg", "1.0"): ">=3.10"}, envs
    )


def test_requires_python_consistency_raises_on_mismatch(
    make_entry: EntryFactory,
) -> None:
    envs = build_target_environments(("linux-x86_64",), ("3.10",))
    entry = make_entry("1.0", environments=set(envs))
    with pytest.raises(PipToolsError, match="Requires-Python"):
        ensure_requires_python_consistency(
            {"pkg": [entry]}, {("pkg", "1.0"): ">=3.12"}, envs
        )


def test_requires_python_consistency_skips_invalid_specifier(
    make_entry: EntryFactory,
) -> None:
    envs = build_target_environments(("linux-x86_64",), ("3.10",))
    entry = make_entry("1.0", environments=set(envs))
    # Malformed Requires-Python; pip's metadata path emits plenty of
    # these in the wild. The consistency check falls through rather than
    # crash.
    ensure_requires_python_consistency(
        {"pkg": [entry]}, {("pkg", "1.0"): "not-a-spec"}, envs
    )


def test_requires_python_consistency_skips_unknown_env_key(
    make_entry: EntryFactory,
) -> None:
    # An entry whose ``environments`` set carries a key the partition no
    # longer recognizes (e.g. cohort merge artifact) is tolerated rather
    # than raising; the check is opportunistic and fires when both ends
    # agree on the env identity.
    envs = build_target_environments(("linux-x86_64",), ("3.12",))
    entry = make_entry("1.0", environments={"phantom-env"})
    ensure_requires_python_consistency(
        {"pkg": [entry]}, {("pkg", "1.0"): ">=3.99"}, envs
    )


def test_marker_disjointness_passes_when_groups_are_conflicting(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # ``[tool.pip-tools].conflicts`` declares pairs the user can never request
    # together, so a marker pair like ``'A' in dependency_groups`` and ``'B' in
    # dependency_groups`` is disjoint by construction once A and B conflict.
    # Without threading the conflict matrix into the validator, the powerset
    # would still try ``groups={A, B}`` and false-positive a collision.

    merged = {
        "black": [
            make_entry("1.0", marker="'A' in dependency_groups"),
            make_entry("2.0", marker="'B' in dependency_groups"),
        ],
    }
    conflicts = [
        [ConflictItem(kind="group", name="A"), ConflictItem(kind="group", name="B")]
    ]
    ensure_marker_disjointness(merged, linux_envs, (), ("A", "B"), conflicts)


def test_marker_disjointness_raises_without_declared_conflicts(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # Same shape as the previous test but with no conflicts declared:
    # the user could request ``--group A --group B`` together, both
    # entries would match, and the installer would face an ambiguous
    # choice. The validator raises so the user declares the conflict or
    # fixes their groups.
    merged = {
        "black": [
            make_entry("1.0", marker="'A' in dependency_groups"),
            make_entry("2.0", marker="'B' in dependency_groups"),
        ],
    }
    with pytest.raises(MarkerDisjointnessError, match="Cannot lock 'black'"):
        ensure_marker_disjointness(merged, linux_envs, (), ("A", "B"))


def test_marker_disjointness_passes_when_extras_are_conflicting(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # Same logic on the extras axis: ``[[{extra="x"}, {extra="y"}]]`` makes
    # ``'x' in extras`` and ``'y' in extras`` disjoint by user declaration.

    merged = {
        "pkg": [
            make_entry("1.0", marker="'x' in extras"),
            make_entry("2.0", marker="'y' in extras"),
        ],
    }
    conflicts = [
        [ConflictItem(kind="extra", name="x"), ConflictItem(kind="extra", name="y")]
    ]
    ensure_marker_disjointness(merged, linux_envs, ("x", "y"), (), conflicts)


def test_powerset_fallback_skips_subsets_that_violate_conflicts(
    linux_envs: dict[str, TargetEnvironment], make_entry: EntryFactory
) -> None:
    # The conflict-aware skip in the powerset path is otherwise unreachable;
    # without this case a subset the user can never request would still raise
    # ``MarkerDisjointnessError`` and break valid locks.
    merged = {
        "pkg": [
            make_entry("1.0", marker="'x' in extras or sys_platform == 'win32'"),
            make_entry("2.0", marker="'y' in extras"),
        ],
    }
    conflicts = [
        [ConflictItem(kind="extra", name="x"), ConflictItem(kind="extra", name="y")]
    ]
    ensure_marker_disjointness(merged, linux_envs, ("x", "y"), (), conflicts)
