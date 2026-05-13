from __future__ import annotations

import typing as _t

import pytest
from pytest_mock import MockerFixture

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock

from pip._internal.req import InstallRequirement

from piptools.exceptions import NoCandidateFound, PipToolsError
from piptools.logging import log
from piptools.pylock._inputs import (
    LockInputs,
    LockSelection,
    LockTargets,
    ResolverOptions,
    WorkerSpec,
)
from piptools.pylock._merge import VariantKey
from piptools.pylock.config import ConflictItem
from piptools.pylock.platforms import TargetEnvironment, build_target_environments
from piptools.pylock.resolve import resolve
from piptools.pylock.resolve._orchestrate import _dispatch_cohorts
from piptools.pylock.resolve._state import ResolverInputs
from piptools.pylock.resolve._worker import init_worker_repository
from piptools.repositories import PyPIRepository

from .conftest import _OptionsFactory, _ResolverFactory


def _call_resolve(
    *,
    target_envs: dict[str, TargetEnvironment],
    repository: MagicMock,
    options: ResolverOptions,
    extras: tuple[str, ...] = (),
    groups: tuple[str, ...] = (),
    group_constraints: dict[str, list[MagicMock]] | None = None,
    conflicts: list[list[ConflictItem]] | None = None,
    raw_constraints: list[MagicMock] | None = None,
    discover_envs: bool = True,
) -> None:
    resolve(
        repository=repository,
        inputs=LockInputs(
            raw_constraints=raw_constraints or [],
            conflicts=conflicts or [],
            group_constraints=group_constraints or {},
        ),
        selection=LockSelection(
            extras=extras, all_extras=False, groups=groups, all_groups=False
        ),
        targets=LockTargets(
            target_envs=target_envs,
            platforms=(),
            python_versions=(),
            no_universal=False,
            discover_envs=discover_envs,
        ),
        options=options,
        workers=WorkerSpec(jobs=1, pip_args=()),
    )


def test_resolve_calls_clear_finder_cache_per_env(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    _call_resolve(
        target_envs=linux_envs,
        repository=mock_repo,
        options=make_options(cache_dir=tmp_path),
    )

    mock_repo._clear_finder_cache.assert_called_once()


@pytest.mark.parametrize(
    ("exception_cls", "exception_args_factory"),
    (
        pytest.param(
            NoCandidateFound,
            lambda mocker: (mocker.MagicMock(), [], mocker.MagicMock()),
            id="no-candidate-found",
        ),
        pytest.param(
            PipToolsError,
            lambda mocker: ("something went wrong",),
            id="pip-tools-error",
        ),
    ),
)
def test_resolve_propagates_resolver_error(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    exception_cls: type[Exception],
    exception_args_factory: _t.Callable[[MockerFixture], tuple[object, ...]],
    mocker: MockerFixture,
    make_options: _OptionsFactory,
) -> None:
    # ``NoCandidateFound`` carries pip-internal ``PackageFinder`` and
    # ``InstallRequirement`` state that does not pickle across the
    # ``ProcessPoolExecutor`` IPC boundary, so the worker rewraps it as a
    # ``PipToolsError`` carrying the formatted message. Both input
    # exception classes surface as ``PipToolsError`` from the orchestrator's
    # perspective.
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value.resolve.side_effect = exception_cls(
        *exception_args_factory(mocker)
    )
    with pytest.raises(PipToolsError):
        _call_resolve(
            target_envs=linux_envs,
            repository=mock_repo,
            options=make_options(cache_dir=tmp_path),
        )


def test_resolve_with_conflicts_runs_per_extra_pass(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    conflicts = [
        [ConflictItem(kind="extra", name="gpu"), ConflictItem(kind="extra", name="cpu")]
    ]

    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    _call_resolve(
        target_envs=linux_envs,
        repository=mock_repo,
        extras=("gpu", "cpu"),
        conflicts=conflicts,
        options=make_options(cache_dir=tmp_path),
    )

    # base pass + gpu pass + cpu pass = 3 calls for 1 env.
    assert mock_resolver.call_count == 3


def test_resolve_rebuild_clears_caches_once_before_dispatch(
    mocker: MockerFixture,
    tmp_path: str,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # ``--rebuild`` under ``--jobs > 1`` was racy when the cache-clear lived
    # inside the first cohort: sibling workers were already reading the same
    # ``cache_dir`` the rmtree would wipe. The orchestrator owns the clear so
    # it happens once, before any cohort touches the cache.
    envs = build_target_environments(("linux-x86_64", "linux-aarch64"), ("3.12",))
    mock_class_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_partition_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    pip_caches_clear = mocker.patch(
        "piptools.pylock.resolve._orchestrate._pip_caches.clear"
    )
    mock_class_resolver.return_value = make_resolver_returning([])
    mock_partition_resolver.return_value = make_resolver_returning([])
    repo = mocker.MagicMock(_clear_finder_cache=mocker.MagicMock())
    resolve(
        repository=repo,
        inputs=LockInputs(raw_constraints=[], conflicts=[], group_constraints={}),
        selection=LockSelection(
            extras=(), all_extras=False, groups=(), all_groups=False
        ),
        targets=LockTargets(
            target_envs=envs,
            platforms=(),
            python_versions=(),
            no_universal=False,
            discover_envs=True,
        ),
        options=make_options(cache_dir=tmp_path, rebuild=True),
        workers=WorkerSpec(jobs=1, pip_args=()),
    )

    repo.clear_caches.assert_called_once()
    pip_caches_clear.assert_called_once()
    clear_caches_calls = [
        bool(call.kwargs.get("clear_caches"))
        for call in (
            *mock_partition_resolver.call_args_list,
            *mock_class_resolver.call_args_list,
        )
    ]
    assert clear_caches_calls
    assert not any(clear_caches_calls)


def test_resolve_skips_partition_when_sys_platforms_unique(
    mocker: MockerFixture,
    tmp_path: str,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # When ``--platform linux-x86_64 --platform windows-amd64 --platform macos-arm64``
    # gives every env a distinct sys_platform, no two envs share a cohort,
    # so the partition scan cannot collapse them; running it is one extra
    # resolver pass paid for nothing.
    envs = build_target_environments(
        ("linux-x86_64", "windows-amd64", "macos-arm64"), ("3.12",)
    )
    partition_spy = mocker.patch(
        "piptools.pylock.resolve._orchestrate.partition_envs_by_marker_equivalence"
    )
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    repo = mocker.MagicMock(_clear_finder_cache=mocker.MagicMock())
    resolve(
        repository=repo,
        inputs=LockInputs(raw_constraints=[], conflicts=[], group_constraints={}),
        selection=LockSelection(
            extras=(), all_extras=False, groups=(), all_groups=False
        ),
        targets=LockTargets(
            target_envs=envs,
            platforms=(),
            python_versions=(),
            no_universal=False,
            discover_envs=True,
        ),
        options=make_options(cache_dir=tmp_path),
        workers=WorkerSpec(jobs=1, pip_args=()),
    )
    partition_spy.assert_not_called()


def test_resolve_runs_partition_when_two_envs_share_sys_platform(
    mocker: MockerFixture,
    tmp_path: str,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # Two ``linux-*`` envs share ``sys_platform == 'linux'`` so they could
    # in principle resolve to the same dependency graph; the partition
    # scan proves that out, so it runs on this shape even though it would
    # waste work on fully-distinct platforms.
    envs = build_target_environments(("linux-x86_64", "linux-aarch64"), ("3.12",))
    partition_spy = mocker.patch(
        "piptools.pylock.resolve._orchestrate.partition_envs_by_marker_equivalence",
        return_value=[list(envs)],
    )
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    repo = mocker.MagicMock(_clear_finder_cache=mocker.MagicMock())
    resolve(
        repository=repo,
        inputs=LockInputs(raw_constraints=[], conflicts=[], group_constraints={}),
        selection=LockSelection(
            extras=(), all_extras=False, groups=(), all_groups=False
        ),
        targets=LockTargets(
            target_envs=envs,
            platforms=(),
            python_versions=(),
            no_universal=False,
            discover_envs=True,
        ),
        options=make_options(cache_dir=tmp_path),
        workers=WorkerSpec(jobs=1, pip_args=()),
    )
    partition_spy.assert_called_once()


def test_resolve_without_rebuild_does_not_clear_caches(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # The orchestrator-level clear is gated on ``--rebuild``. Firing it on
    # every lock would defeat the cache pip-tools shares with pip itself.
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    pip_caches_clear = mocker.patch(
        "piptools.pylock.resolve._orchestrate._pip_caches.clear"
    )
    _call_resolve(
        target_envs=linux_envs,
        repository=mock_repo,
        options=make_options(cache_dir=tmp_path),
    )

    mock_repo.clear_caches.assert_not_called()
    pip_caches_clear.assert_not_called()


def test_resolve_group_pass_excludes_extras_only_constraints(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # Before the fix, the group pass copied all ``raw_constraints`` without the
    # ``match_markers`` filter, so ``drop_extras()`` would strip the
    # ``extra == "dev"`` marker and resolve the package unconditionally.
    extras_req = mocker.create_autospec(InstallRequirement, instance=True)
    extras_req.match_markers.return_value = False

    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    _call_resolve(
        target_envs=linux_envs,
        repository=mock_repo,
        groups=("test",),
        group_constraints={"test": []},
        raw_constraints=[extras_req],
        options=make_options(cache_dir=tmp_path),
    )

    constraints_seen = [
        list(call.kwargs["constraints"]) for call in mock_resolver.call_args_list
    ]
    assert len(constraints_seen) == 2
    assert extras_req not in constraints_seen[1]


def test_resolve_drop_extras_called_on_nonempty_constraints(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    # Plain ``MagicMock`` (not ``create_autospec``): ``copy.deepcopy`` on an
    # autospec-constructed mock raises on PyPy 3.10 because the autospec
    # carries function references PyPy's copyreg cannot reconstruct, and the
    # resolver path runs ``deepcopy`` on every constraint before resolution.
    base_req = mocker.MagicMock(spec=InstallRequirement, markers=None, extras=set())
    base_req.match_markers.return_value = True

    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    _call_resolve(
        target_envs=linux_envs,
        repository=mock_repo,
        groups=("test",),
        group_constraints={"test": []},
        raw_constraints=[base_req],
        options=make_options(cache_dir=tmp_path),
    )

    assert base_req.extras == set()


def test_resolve_forward_deps_propagated(
    linux_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mocker.patch(
        "piptools.pylock.resolve._cohort_work.get_forward_dependencies",
        return_value={"requests": {"certifi"}},
    )
    mock_resolver.return_value = make_resolver_returning([])
    _, forward_deps = resolve(
        repository=mock_repo,
        inputs=LockInputs(raw_constraints=[], conflicts=[], group_constraints={}),
        selection=LockSelection(
            extras=(), all_extras=False, groups=(), all_groups=False
        ),
        targets=LockTargets(
            target_envs=linux_envs,
            platforms=(),
            python_versions=(),
            no_universal=False,
            discover_envs=True,
        ),
        options=make_options(cache_dir=tmp_path),
        workers=WorkerSpec(jobs=1, pip_args=()),
    )

    assert forward_deps == {"requests": {"certifi"}}


def test_resolve_skips_discovery_when_disabled(
    linux_windows_envs: dict[str, TargetEnvironment],
    mock_repo: MagicMock,
    tmp_path: str,
    mocker: MockerFixture,
    make_options: _OptionsFactory,
    make_resolver_returning: _ResolverFactory,
) -> None:
    """When ``discover_envs=False`` we run one resolution per env (no scan)."""
    mock_resolver = mocker.patch(
        "piptools.pylock.resolve._resolver_factory.BacktrackingResolver"
    )
    mock_resolver.return_value = make_resolver_returning([])
    _call_resolve(
        target_envs=linux_windows_envs,
        repository=mock_repo,
        options=make_options(cache_dir=tmp_path),
        discover_envs=False,
    )
    # Two envs x one resolution each, no scan.
    assert mock_resolver.call_count == 2


def test_dispatch_classes_sequential_runs_inline(
    mocker: MockerFixture,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
) -> None:
    # ``workers <= 1`` short-circuits to in-process iteration so ``jobs=1``
    # (and the implicit cap when there is a single class) does not pay the
    # fork or pickle cost.
    work = mocker.patch(
        "piptools.pylock.resolve._orchestrate.resolve_cohort_work",
        return_value=({}, {}),
    )
    pool = mocker.patch("piptools.pylock.resolve._orchestrate.ProcessPoolExecutor")

    list(
        _dispatch_cohorts(
            env_cohorts=[["a"], ["b"]],
            target_envs=_t.cast("dict[str, TargetEnvironment]", {"a": {}, "b": {}}),
            repository=mocker.create_autospec(PyPIRepository, instance=True),
            inputs=empty_inputs,
            options=make_options(),
            workers=WorkerSpec(jobs=1, pip_args=()),
        )
    )

    assert work.call_count == 2
    pool.assert_not_called()


def test_dispatch_classes_parallel_uses_process_pool(
    mocker: MockerFixture,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
) -> None:
    # The parallel branch builds a ``ProcessPoolExecutor`` with the cache
    # dir and pip args wired into ``init_worker_repository``. Stub the
    # executor so the test never forks; verify dispatch order, the dropped
    # ``repository`` kwarg (workers build their own), and that results
    # stream back in submission order.
    fake_pool = mocker.MagicMock()
    fake_pool.__enter__.return_value = fake_pool
    fake_pool.__exit__.return_value = False
    keys = [VariantKey(env=name, extra=None, group=None) for name in ("a", "b", "c")]
    futures = [mocker.MagicMock() for _ in range(3)]
    futures[0].result.return_value = ({keys[0]: {}}, {"f0": {"a"}})
    futures[1].result.return_value = ({keys[1]: {}}, {"f1": {"b"}})
    futures[2].result.return_value = ({keys[2]: {}}, {"f2": {"c"}})
    fake_pool.submit.side_effect = futures
    executor_cls = mocker.patch(
        "piptools.pylock.resolve._orchestrate.ProcessPoolExecutor",
        return_value=fake_pool,
    )

    results = list(
        _dispatch_cohorts(
            env_cohorts=[["a"], ["b"], ["c"]],
            target_envs=_t.cast(
                "dict[str, TargetEnvironment]", {"a": {}, "b": {}, "c": {}}
            ),
            repository=mocker.create_autospec(PyPIRepository, instance=True),
            inputs=empty_inputs,
            options=make_options(cache_dir="/some/cache"),
            workers=WorkerSpec(jobs=4, pip_args=("--index-url", "https://example/")),
        )
    )

    # Workers cap at the number of classes; ``repository`` is stripped
    # because each worker rebuilds its own.
    executor_cls.assert_called_once()
    assert executor_cls.call_args.kwargs["max_workers"] == 3
    assert executor_cls.call_args.kwargs["initializer"] is init_worker_repository
    assert executor_cls.call_args.kwargs["initargs"] == (
        ["--index-url", "https://example/"],
        "/some/cache",
    )
    submit_kwargs = [call.kwargs for call in fake_pool.submit.call_args_list]
    assert all("repository" not in kw for kw in submit_kwargs)
    assert [r[0] for r in results] == [{keys[0]: {}}, {keys[1]: {}}, {keys[2]: {}}]


def test_dispatch_classes_logs_when_verbose(
    mocker: MockerFixture,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
) -> None:
    # ``log.debug`` is gated on ``log.verbosity >= 1`` so the f-string is
    # not built when the user did not ask for it; verify the gated branch
    # when verbosity is raised.
    mocker.patch.object(log, "verbosity", 1)
    debug = mocker.patch.object(log, "debug")
    fake_pool = mocker.MagicMock()
    fake_pool.__enter__.return_value = fake_pool
    fake_pool.__exit__.return_value = False
    fake_pool.submit.return_value = mocker.MagicMock(
        result=mocker.MagicMock(return_value=({}, {}))
    )
    mocker.patch(
        "piptools.pylock.resolve._orchestrate.ProcessPoolExecutor",
        return_value=fake_pool,
    )

    list(
        _dispatch_cohorts(
            env_cohorts=[["a"], ["b"]],
            target_envs=_t.cast("dict[str, TargetEnvironment]", {"a": {}, "b": {}}),
            repository=mocker.create_autospec(PyPIRepository, instance=True),
            inputs=empty_inputs,
            options=make_options(),
            workers=WorkerSpec(jobs=2, pip_args=()),
        )
    )

    debug.assert_called_once()


def test_dispatch_classes_cancels_pending_on_failure(
    mocker: MockerFixture,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
) -> None:
    # When the first cohort's resolver raises, the dispatcher cancels the
    # already-submitted siblings so the caller does not pay for work it
    # will discard, then propagates the original failure.
    fake_pool = mocker.MagicMock()
    fake_pool.__enter__.return_value = fake_pool
    fake_pool.__exit__.return_value = False
    failing_future = mocker.MagicMock()
    failing_future.result.side_effect = RuntimeError("cohort blew up")
    pending_future = mocker.MagicMock()
    fake_pool.submit.side_effect = [failing_future, pending_future]
    mocker.patch(
        "piptools.pylock.resolve._orchestrate.ProcessPoolExecutor",
        return_value=fake_pool,
    )

    with pytest.raises(RuntimeError, match="cohort blew up"):
        list(
            _dispatch_cohorts(
                env_cohorts=[["a"], ["b"]],
                target_envs=_t.cast("dict[str, TargetEnvironment]", {"a": {}, "b": {}}),
                repository=mocker.create_autospec(PyPIRepository, instance=True),
                inputs=empty_inputs,
                options=make_options(),
                workers=WorkerSpec(jobs=2, pip_args=()),
            )
        )

    failing_future.cancel.assert_called_once()
    pending_future.cancel.assert_called_once()
    fake_pool.shutdown.assert_called_once_with(wait=True, cancel_futures=True)
