from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from piptools.exceptions import PipToolsError

from .conftest import PylockPackageFactory, RequirementFactory


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows file:// URL parsing differs across drives; covered on Unix",
)
def test_build_pylock_package_archive_path_is_relative_posix(  # pragma: win32 no cover
    make_requirement: RequirementFactory, make_pkg: PylockPackageFactory, tmp_path: Path
) -> None:
    archive = tmp_path / "wheels" / "lib-1.0.tar.gz"
    archive.parent.mkdir(parents=True)
    archive.touch()
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url=f"file://{archive.as_posix()}",
        hash_name="sha256",
        hash_value="abc",
    )
    pkg = make_pkg(
        requirement,
        lock_dir=tmp_path,
    )
    assert pkg.archive is not None
    assert pkg.archive.path == "wheels/lib-1.0.tar.gz"


def test_build_pylock_package_archive_redacts_credentials(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    # An archive URL with embedded basic-auth credentials must be redacted
    # before it lands in a committed lockfile; the source is still resolvable
    # by an installer that re-supplies the credential at install time.
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url="https://user:secret@private.example.com/lib-1.0.tar.gz",
        hash_name="sha256",
        hash_value="abc",
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.archive is not None
    assert pkg.archive.url is not None
    assert "secret" not in pkg.archive.url
    assert pkg.archive.url.endswith("@private.example.com/lib-1.0.tar.gz")


def test_build_pylock_package_archive(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="anyio",
        version="4.3.0",
        link_url="https://example.com/anyio-4.3.0-py3-none-any.whl",
        hash_name="sha256",
        hash_value="048e05d0f6",
    )
    pkg = make_pkg(
        requirement,
    )
    assert str(pkg.version) == "4.3.0"
    assert pkg.archive is not None
    assert pkg.archive.hashes == {"sha256": "048e05d0f6"}
    assert pkg.archive.url == "https://example.com/anyio-4.3.0-py3-none-any.whl"


def test_build_pylock_package_archive_no_hash_raises(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="pkg",
        version="1.0",
        link_url="https://example.com/pkg-1.0.tar.gz",
    )
    with pytest.raises(PipToolsError, match="archive hash"):
        make_pkg(
            requirement,
        )


@pytest.mark.parametrize(
    "weak_algo",
    (pytest.param("md5", id="md5"), pytest.param("sha1", id="sha1")),
)
def test_build_pylock_package_archive_weak_hash_raises(
    make_requirement: RequirementFactory, make_pkg: PylockPackageFactory, weak_algo: str
) -> None:
    # PEP 751 requires "at least one secure algorithm" in ``hashes``; md5 and
    # sha1 satisfy pip's checks but not the spec's intent, so emitting a weak-
    # only entry would silently produce a non-conforming lockfile.
    requirement = make_requirement(
        name="pkg",
        version="1.0",
        link_url=f"https://example.com/pkg-1.0.tar.gz#{weak_algo}=deadbeef",
        hash_name=weak_algo,
        hash_value="deadbeef",
    )
    with pytest.raises(PipToolsError, match="secure"):
        make_pkg(
            requirement,
        )


def test_build_pylock_package_archive_with_subdirectory(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="root",
        version="0.0.1",
        link_url="https://example.com/mono.tar.gz#subdirectory=packages/root",
        subdirectory_fragment="packages/root",
        hash_name="sha256",
        hash_value="abc",
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.archive is not None
    assert pkg.archive.subdirectory == "packages/root"


@pytest.mark.parametrize(
    "link_url",
    (
        pytest.param("file:///home/user/mylib-1.0.tar.gz", id="absolute"),
        pytest.param(
            "file://localhost/home/user/mylib-1.0.tar.gz", id="explicit-localhost"
        ),
    ),
)
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="url_to_path returns Windows-native paths on win32",
)
def test_build_pylock_package_local_archive_uses_path(  # pragma: win32 no cover
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    link_url: str,
    mocker: MockerFixture,
) -> None:
    # The collector validates that ``file://`` archive paths exist so a typo'd
    # path raises a clear "does not exist" error rather than the misleading
    # missing-hash one. This test is about the path-emission shape, so stub
    # ``Path.exists`` rather than fabricate a real file under ``/home/user``.
    mocker.patch("piptools.pylock.sources._archive.Path.exists", return_value=True)
    requirement = make_requirement(
        name="mylib",
        version="1.0",
        link_url=link_url,
        hash_name="sha256",
        hash_value="abc123",
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.archive is not None
    assert pkg.archive.path == "/home/user/mylib-1.0.tar.gz"
    assert pkg.archive.url is None
    assert pkg.archive.hashes == {"sha256": "abc123"}


def test_build_pylock_package_archive_missing_file_raises(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    # ``file://`` archive that doesn't resolve to a real file would otherwise
    # fall through to the missing-hash error and the user can't tell which
    # condition tripped them.
    requirement = make_requirement(
        name="pkg",
        version="1.0",
        link_url="file:///does-not-exist-on-disk-pkg-1.0.tar.gz",
        is_file=True,
        hash_name="sha256",
        hash_value="abc",
    )
    with pytest.raises(PipToolsError, match="does not exist"):
        make_pkg(
            requirement,
        )
