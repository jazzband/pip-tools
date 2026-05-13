from __future__ import annotations

import sys
from pathlib import Path

import pytest

from .conftest import PylockPackageFactory, RequirementFactory


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows file:// URL parsing differs across drives; covered on Unix",
)
def test_build_pylock_package_directory_path_is_relative_posix(  # pragma: win32 no cover
    make_requirement: RequirementFactory, make_pkg: PylockPackageFactory, tmp_path: Path
) -> None:
    # PEP 751: ``path`` is "relative to lock file" with POSIX separators. An
    # absolute, native-separator path would defeat the canonical use-case of a
    # committed pylock shared across machines.
    repo_dir = tmp_path / "src" / "lib"
    repo_dir.mkdir(parents=True)
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url=f"file://{repo_dir.as_posix()}",
        is_file=True,
        is_existing_dir=True,
    )
    pkg = make_pkg(
        requirement,
        lock_dir=tmp_path,
    )
    assert pkg.directory is not None
    assert pkg.directory.path == "src/lib"


def test_build_pylock_package_directory_carries_subdirectory(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    # PEP 751 lists ``packages.directory.subdirectory`` as supported; without
    # threading ``link.subdirectory_fragment`` an installer would build the
    # outer tree and miss the user-pinned subtree.
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url="file:///repo#subdirectory=packages/lib",
        is_file=True,
        is_existing_dir=True,
        subdirectory_fragment="packages/lib",
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.directory is not None
    assert pkg.directory.subdirectory == "packages/lib"


def test_build_pylock_package_editable(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="project",
        version="0.1.0",
        editable=True,
        link_url="file:///home/user/project",
        is_file=True,
        is_existing_dir=True,
    )
    pkg = make_pkg(
        requirement,
        dependencies=[{"name": "requests"}],
    )
    assert pkg.name == "project"
    assert pkg.version is None
    assert pkg.directory is not None
    assert pkg.directory.editable is True
    assert pkg.dependencies is not None
    assert len(pkg.dependencies) == 1


def test_build_pylock_package_directory(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="local-pkg",
        version="1.0",
        link_url="file:///local/pkg",
        is_file=True,
        is_existing_dir=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.version is None
    assert pkg.directory is not None
    assert pkg.directory.editable is False


@pytest.mark.parametrize(
    "link_url",
    (
        pytest.param("file:///local/pkg", id="absolute"),
        pytest.param("file://localhost/local/pkg", id="explicit-localhost"),
    ),
)
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="url_to_path returns Windows-native paths on win32",
)
def test_build_pylock_package_directory_file_url_decodes_to_path(  # pragma: win32 no cover
    make_requirement: RequirementFactory, make_pkg: PylockPackageFactory, link_url: str
) -> None:
    requirement = make_requirement(
        name="local-pkg",
        version="1.0",
        link_url=link_url,
        is_file=True,
        is_existing_dir=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.directory is not None
    assert pkg.directory.path == "/local/pkg"


def test_build_pylock_package_directory_non_file_url(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="local-pkg",
        version="1.0",
        link_url="/absolute/path/pkg",
        is_file=True,
        is_existing_dir=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.directory is not None
    assert pkg.directory.path == "/absolute/path/pkg"
