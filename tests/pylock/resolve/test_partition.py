from __future__ import annotations

import typing as _t

from packaging.markers import Marker, UndefinedEnvironmentName
from pytest_mock import MockerFixture

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock

from piptools.exceptions import PipToolsError
from piptools.pylock.platforms import TargetEnvironment
from piptools.pylock.resolve._partition import (
    _scan_constraints,
    partition_envs_by_marker_equivalence,
)
from piptools.pylock.resolve._state import ResolverInputs

from .conftest import _OptionsFactory, _ResolverFactory


def _info_with_marker(mocker: MockerFixture, marker: Marker | None) -> MagicMock:
    requirement = mocker.MagicMock()
    requirement.req.marker = marker
    info = mocker.MagicMock()
    info.requirement._ireq = requirement
    return _t.cast("MagicMock", info)


def test_partition_envs_collapses_when_no_platform_markers(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
    mocker: MockerFixture,
) -> None:
    scan_resolver = make_resolver_returning([])
    scan_resolver._resolver_result.criteria = {}
    mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver",
        return_value=scan_resolver,
    )
    groups = partition_envs_by_marker_equivalence(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        inputs=empty_inputs,
        options=make_options(cache_dir=tmp_path),
    )
    assert len(groups) == 1
    assert set(groups[0]) == set(linux_windows_envs)


def test_partition_envs_falls_back_on_scan_failure(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
    mocker: MockerFixture,
) -> None:
    failing = mocker.MagicMock()
    failing.resolve.side_effect = PipToolsError("scan failed")
    mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver",
        return_value=failing,
    )
    groups = partition_envs_by_marker_equivalence(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        inputs=empty_inputs,
        options=make_options(cache_dir=tmp_path),
    )
    assert len(groups) == 2
    assert {tuple(g) for g in groups} == {(env_key,) for env_key in linux_windows_envs}


def test_partition_envs_splits_on_platform_markers(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
    mocker: MockerFixture,
) -> None:
    info_win = _info_with_marker(mocker, Marker("sys_platform == 'win32'"))
    criterion = mocker.MagicMock(information=[info_win])

    scan_resolver = make_resolver_returning([])
    scan_resolver._resolver_result.criteria = {"pywin32": criterion}
    mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver",
        return_value=scan_resolver,
    )
    groups = partition_envs_by_marker_equivalence(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        inputs=empty_inputs,
        options=make_options(cache_dir=tmp_path),
    )
    # win32 vs non-win32 envs split into two classes.
    assert len(groups) == 2
    flat = {env for group in groups for env in group}
    assert flat == set(linux_windows_envs)


def test_partition_handles_marker_referencing_undefined_environment_name(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
    mocker: MockerFixture,
) -> None:
    # ``packaging.markers`` raises ``UndefinedEnvironmentName`` when a scan-
    # collected marker references a variable absent from the target env;
    # treat that as ``None`` in the equivalence signature so the partition
    # falls back to per-env granularity instead of aborting the lock.
    scan_resolver = make_resolver_returning([])
    mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver",
        return_value=scan_resolver,
    )
    raising_marker = mocker.create_autospec(Marker, instance=True)
    raising_marker.evaluate.side_effect = UndefinedEnvironmentName("missing variable")
    mocker.patch(
        "piptools.pylock.resolve._partition.Marker", return_value=raising_marker
    )
    mocker.patch(
        "piptools.pylock.resolve._partition.extract_dep_markers",
        return_value={"sys_platform == 'win32'"},
    )
    groups = partition_envs_by_marker_equivalence(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        inputs=empty_inputs,
        options=make_options(cache_dir=tmp_path),
    )
    assert len(groups) == 1
    assert set(groups[0]) == set(linux_windows_envs)


def test_partition_skips_unparseable_scan_marker(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
    mocker: MockerFixture,
) -> None:
    # If a transitive dep has a corrupt marker, ``Marker(marker_str)``
    # raises ``InvalidMarker``; the partition logs and continues rather
    # than abort the whole lock. Drive the path by stubbing the marker
    # collector to return a string PEP 508 cannot parse alongside a real one.
    scan_resolver = make_resolver_returning([])
    mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver",
        return_value=scan_resolver,
    )
    mocker.patch(
        "piptools.pylock.resolve._partition.extract_dep_markers",
        return_value={"definitely not a marker", "sys_platform == 'win32'"},
    )
    groups = partition_envs_by_marker_equivalence(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        inputs=empty_inputs,
        options=make_options(cache_dir=tmp_path),
    )
    # The valid marker still drives the partition into win32 vs non-win32.
    assert len(groups) == 2


def test_scan_constraints_extends_with_group_reqs(mocker: MockerFixture) -> None:
    # The marker-discovery scan covers transitive deps that surface via
    # groups; without this collection path, group-only deps would not
    # influence the partition and equivalent envs could collapse when
    # they need separate resolutions.
    base_req = mocker.MagicMock()
    base_req.match_markers.return_value = True
    group_req = mocker.MagicMock()
    constraints = _scan_constraints(
        ResolverInputs(
            raw_constraints=[base_req],
            extras_configs=[(None, ())],
            group_configs=[("test", ("test",))],
            group_constraints={"test": [group_req]},
        )
    )
    assert len(constraints) == 2


def test_scan_constraints_keeps_python_conditional_reqs(
    mocker: MockerFixture,
) -> None:
    # Filtering by ``req.match_markers()`` here would evaluate against the
    # *host* interpreter's ``default_environment`` (not the target env
    # ``mock_marker_environment`` will install later). A req like
    # ``tomli; python_version < '3.11'`` running on a 3.13 host would be
    # dropped, the scan would not see ``tomli``, the partition would
    # collapse 3.10 and 3.13 envs together, and the rep-env's resolution
    # would replicate to a 3.10 lockfile missing ``tomli``: a silent
    # over-collapse producing a wrong lock.
    host_filtered = mocker.MagicMock()
    host_filtered.match_markers.return_value = False
    always_kept = mocker.MagicMock()
    always_kept.match_markers.return_value = True
    constraints = _scan_constraints(
        ResolverInputs(
            raw_constraints=[host_filtered, always_kept],
            extras_configs=[(None, ())],
            group_configs=[],
            group_constraints={},
        )
    )
    assert len(constraints) == 2


def test_scan_constraints_skips_conflicting_groups(mocker: MockerFixture) -> None:
    # H_partition_scan_conflicts: when two groups conflict (e.g. ``black22``
    # and ``black23`` declared mutually exclusive in
    # ``[tool.pip-tools].conflicts``), unioning their constraints into one
    # scan resolution makes pip raise ``RequirementsConflicted`` long
    # before the per-cohort resolutions run. The scan intersects to the
    # groups every conflict family sees, so conflicting groups drop out
    # and the scan resolves cleanly.
    base_req = mocker.MagicMock()
    base_req.match_markers.return_value = True
    shared_req = mocker.MagicMock()
    black22_req = mocker.MagicMock()
    black23_req = mocker.MagicMock()
    constraints = _scan_constraints(
        ResolverInputs(
            raw_constraints=[base_req],
            extras_configs=[(None, ())],
            # ``build_group_configs`` shape: each conflict family gets a
            # config bundling the non-conflicting groups with the family member.
            group_configs=[
                (None, ()),
                ("black22", ("dev", "black22")),
                ("black23", ("dev", "black23")),
            ],
            group_constraints={
                "dev": [shared_req],
                "black22": [black22_req],
                "black23": [black23_req],
            },
        )
    )
    # The intersection (``dev``) makes it into the scan; ``black22``
    # and ``black23`` would conflict if both threaded through.
    assert shared_req in constraints
    assert black22_req not in constraints
    assert black23_req not in constraints
