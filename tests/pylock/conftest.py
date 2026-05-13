from __future__ import annotations

import typing as _t

import pytest
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.pylock._merge import ResolvedEntry
from piptools.pylock.platforms import TargetEnvironment, build_target_environments


@pytest.fixture
def linux_envs() -> dict[str, TargetEnvironment]:
    return build_target_environments(("linux-x86_64",), ("3.12",))


class EntryFactory(_t.Protocol):
    def __call__(
        self, version: str, marker: str | None = ..., *, environments: set[str] = ...
    ) -> ResolvedEntry: ...


@pytest.fixture
def make_entry(mocker: MockerFixture) -> EntryFactory:
    def _factory(
        version: str,
        marker: str | None = None,
        *,
        environments: set[str] | None = None,
    ) -> ResolvedEntry:
        kwargs: dict[str, _t.Any] = {
            "requirement": mocker.create_autospec(InstallRequirement, instance=True),
            "version": version,
            "marker": marker,
        }
        if environments is not None:
            kwargs["environments"] = environments
        return ResolvedEntry(**kwargs)

    return _factory
