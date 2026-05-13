from __future__ import annotations

import typing as _t
from collections.abc import Sequence

import pytest
from packaging.pylock import Package, PackageSdist, PackageWheel
from pytest_mock import MockerFixture

from piptools.pylock.sources import build_pylock_package

if _t.TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

FULL_SHA = "a1b2c3d4e5f6789012345678abcdef9012345678"


class RequirementFactory(_t.Protocol):
    def __call__(
        self,
        name: str = ...,
        version: str = ...,
        *,
        editable: bool = ...,
        link_url: str | None = ...,
        is_vcs: bool = ...,
        is_file: bool = ...,
        is_existing_dir: bool = ...,
        hash_name: str | None = ...,
        hash_value: str | None = ...,
        subdirectory_fragment: str | None = ...,
    ) -> MagicMock: ...


class PylockPackageFactory(_t.Protocol):
    def __call__(
        self,
        requirement: MagicMock,
        *,
        dist_files: Sequence[PackageWheel | PackageSdist] | None = ...,
        dependencies: list[dict[str, _t.Any]] | None = ...,
        marker: str | None = ...,
        index_url: str | None = ...,
        lock_dir: Path | None = ...,
        requires_python: str | None = ...,
    ) -> Package: ...


@pytest.fixture
def stub_sdist() -> list[PackageSdist]:
    return [
        PackageSdist(
            url="https://pypi.org/packages/pkg-1.0.tar.gz",
            name="pkg-1.0.tar.gz",
            hashes={"sha256": "abc"},
        )
    ]


@pytest.fixture
def make_requirement(mocker: MockerFixture) -> RequirementFactory:
    def _factory(
        name: str = "pkg",
        version: str = "1.0",
        *,
        editable: bool = False,
        link_url: str | None = None,
        is_vcs: bool = False,
        is_file: bool = False,
        is_existing_dir: bool = False,
        hash_name: str | None = None,
        hash_value: str | None = None,
        subdirectory_fragment: str | None = None,
    ) -> MagicMock:
        spec = mocker.MagicMock(version=version)
        requirement: MagicMock = mocker.MagicMock(
            specifier=mocker.MagicMock(__iter__=lambda _self: iter([spec])),
            extras=set(),
            editable=editable,
            markers=None,
        )
        requirement.name = name
        requirement.req.name = name

        if link_url is not None:
            link_mock: MagicMock = requirement.link
            link_mock.url = link_url
            link_mock.url_without_fragment = link_url.split("#")[0]
            link_mock.filename = link_url.split("/")[-1].split("#")[0]
            link_mock.scheme = link_url.split("://", 1)[0] if "://" in link_url else ""
            link_mock.is_vcs = is_vcs
            link_mock.is_file = is_file
            link_mock.is_existing_dir.return_value = is_existing_dir
            link_mock.has_hash = hash_name is not None
            link_mock.hash_name = hash_name
            link_mock.hash = hash_value
            link_mock.subdirectory_fragment = subdirectory_fragment
            requirement.original_link = link_mock
        else:
            requirement.link = None
            requirement.original_link = None

        return requirement

    return _factory


@pytest.fixture
def make_pkg() -> PylockPackageFactory:
    def _factory(
        requirement: MagicMock,
        *,
        dist_files: Sequence[PackageWheel | PackageSdist] | None = None,
        dependencies: list[dict[str, _t.Any]] | None = None,
        marker: str | None = None,
        index_url: str | None = None,
        lock_dir: Path | None = None,
        requires_python: str | None = None,
    ) -> Package:
        kwargs: dict[str, _t.Any] = {
            "requirement": requirement,
            "dist_files": list(dist_files) if dist_files is not None else [],
            "dependencies": dependencies or [],
            "marker": marker,
            "index_url": index_url,
        }
        if lock_dir is not None:
            kwargs["lock_dir"] = lock_dir
        if requires_python is not None:
            kwargs["requires_python"] = requires_python
        return build_pylock_package(**kwargs)

    return _factory
