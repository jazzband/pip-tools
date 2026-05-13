from __future__ import annotations

import typing as _t

import pytest
from pytest_mock import MockerFixture

from piptools.pylock._inputs import ResolverOptions
from piptools.pylock.platforms import TargetEnvironment, build_target_environments
from piptools.pylock.resolve._state import ResolverInputs

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock


class _OptionsFactory(_t.Protocol):
    def __call__(
        self, *, cache_dir: str = ..., rebuild: bool = ...
    ) -> ResolverOptions: ...


class _ResolverFactory(_t.Protocol):
    def __call__(self, requirements: list[MagicMock]) -> MagicMock: ...


@pytest.fixture
def make_options() -> _OptionsFactory:
    def _factory(*, cache_dir: str = "/tmp", rebuild: bool = False) -> ResolverOptions:
        return ResolverOptions(
            prereleases=False,
            rebuild=rebuild,
            allow_unsafe=False,
            unsafe_packages=frozenset(),
            max_rounds=10,
            cache_dir=cache_dir,
            pre=False,
        )

    return _factory


@pytest.fixture
def make_resolver_returning(mocker: MockerFixture) -> _ResolverFactory:
    def _factory(requirements: list[MagicMock]) -> MagicMock:
        return _t.cast(
            "MagicMock",
            mocker.MagicMock(
                resolve=mocker.MagicMock(return_value=requirements),
                _resolver_result=mocker.MagicMock(
                    mapping={},
                    graph=mocker.MagicMock(
                        iter_children=mocker.MagicMock(return_value=iter([]))
                    ),
                ),
            ),
        )

    return _factory


@pytest.fixture
def empty_inputs() -> ResolverInputs:
    return ResolverInputs(
        raw_constraints=[],
        extras_configs=[(None, ())],
        group_configs=[(None, ())],
        group_constraints={},
    )


@pytest.fixture
def linux_windows_envs() -> dict[str, TargetEnvironment]:
    return build_target_environments(("linux-x86_64", "windows-amd64"), ("3.12",))


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> MagicMock:
    return _t.cast(
        "MagicMock", mocker.MagicMock(_clear_finder_cache=mocker.MagicMock())
    )
