from __future__ import annotations

import pytest
from packaging.pylock import PackageSdist, PackageWheel
from packaging.version import Version
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.exceptions import PipToolsError
from piptools.pylock.sources import requirement_version
from piptools.pylock.sources._index import (
    _validate_dist_filenames,
    _wheel_sort_key,
    build_index_source,
)

from .conftest import PylockPackageFactory, RequirementFactory


def test_build_pylock_package_index(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(name="anyio", version="3.7.0")
    dist_files: list[PackageWheel | PackageSdist] = [
        PackageSdist(
            url="https://pypi.org/packages/anyio-3.7.0.tar.gz",
            name="anyio-3.7.0.tar.gz",
            hashes={"sha256": "sdist_hash"},
            size=142737,
        ),
        PackageWheel(
            url="https://pypi.org/packages/anyio-3.7.0-py3-none-any.whl",
            name="anyio-3.7.0-py3-none-any.whl",
            hashes={"sha256": "whl_hash"},
            size=80873,
        ),
    ]
    pkg = make_pkg(
        requirement,
        dist_files=dist_files,
        dependencies=[{"name": n} for n in sorted({"idna", "sniffio"})],
        index_url="https://pypi.org/simple",
    )
    assert pkg.name == "anyio"
    assert str(pkg.version) == "3.7.0"
    assert pkg.index == "https://pypi.org/simple"
    assert pkg.sdist is not None
    assert pkg.sdist.name == "anyio-3.7.0.tar.gz"
    assert pkg.wheels is not None
    assert len(pkg.wheels) == 1
    assert pkg.wheels[0].name == "anyio-3.7.0-py3-none-any.whl"
    assert pkg.dependencies is not None
    assert len(pkg.dependencies) == 2
    assert pkg.marker is None


def test_build_pylock_package_index_raises_when_no_dist_files(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(name="ghost", version="1.0")
    with pytest.raises(PipToolsError, match="No source available"):
        make_pkg(
            requirement,
            index_url="https://pypi.org/simple",
        )


def test_validate_dist_filenames_skips_unnamed_dists(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    # PEP 751 lets ``PackageWheel.name`` be omitted for path-only entries
    # (e.g. archive sources). The validator has to skip those rather than
    # crash on the missing filename.
    requirement = make_requirement(name="pkg", version="1.0")
    dist_files: list[PackageWheel | PackageSdist] = [
        PackageWheel(
            url="https://example.com/p.whl", name=None, hashes={"sha256": "x"}
        ),
    ]
    pkg = make_pkg(
        requirement,
        dist_files=dist_files,
        index_url="https://pypi.org/simple",
    )
    assert pkg.wheels is not None
    assert pkg.wheels[0].name is None


def test_build_pylock_package_index_skips_filename_check_when_unpinned(
    mocker: MockerFixture,
    make_pkg: PylockPackageFactory,
) -> None:
    # An unpinned index requirement (no ``==`` specifier) reaches the
    # collector when pip-tools is asked to lock something the resolver
    # could not pin to a single version. The version-consistency check
    # is meaningless without a known pin, so it has to be skipped.
    requirement = mocker.MagicMock(
        spec=InstallRequirement,
        editable=False,
        original_link=None,
        link=None,
        markers=None,
        extras=set(),
    )
    requirement.name = "pkg"
    requirement.specifier = mocker.MagicMock(__iter__=lambda _self: iter([]))
    sdist = PackageSdist(
        url="https://example.com/x.tar.gz",
        name="other-1.0.tar.gz",
        hashes={"sha256": "x"},
    )
    pkg = make_pkg(
        requirement,
        dist_files=[sdist],
        index_url="https://pypi.org/simple",
    )
    assert pkg.version is None


@pytest.mark.parametrize(
    ("filename", "match"),
    (
        pytest.param(
            "pkg-2.0-py3-none-any.whl",
            "filename parses to pkg==2.0",
            id="wheel-version",
        ),
        pytest.param(
            "other-1.0-py3-none-any.whl",
            "filename parses to other==1.0",
            id="wheel-name",
        ),
        pytest.param(
            "pkg-2.0.tar.gz", "filename parses to pkg==2.0", id="sdist-version"
        ),
        pytest.param(
            "pkg-1.0-broken.whl", "malformed wheel filename", id="wheel-malformed"
        ),
    ),
)
def test_build_pylock_package_rejects_mislabelled_dist_filename(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    filename: str,
    match: str,
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    cls = PackageWheel if filename.endswith(".whl") else PackageSdist
    dist_files: list[PackageWheel | PackageSdist] = [
        cls(
            url=f"https://example.com/{filename}",
            name=filename,
            hashes={"sha256": "abc"},
        )
    ]
    with pytest.raises(PipToolsError, match=match):
        make_pkg(
            requirement,
            dist_files=dist_files,
            index_url="https://pypi.org/simple",
        )


@pytest.mark.parametrize(
    ("filename", "expected_target"),
    (
        pytest.param("pkg-1.0.tar.gz", "sdist", id="tar-gz"),
        pytest.param("pkg-1.0.tar.bz2", "sdist", id="tar-bz2"),
        pytest.param("pkg-1.0.tar.xz", "sdist", id="tar-xz"),
        pytest.param("pkg-1.0.zip", "sdist", id="zip"),
        pytest.param("pkg-1.0-py3-none-any.whl", "wheel", id="wheel"),
    ),
)
def test_assign_dist_files_classifies_known_formats(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    filename: str,
    expected_target: str,
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    cls = PackageWheel if filename.endswith(".whl") else PackageSdist
    dist_files: list[PackageWheel | PackageSdist] = [
        cls(
            url=f"https://example.com/{filename}",
            name=filename,
            hashes={"sha256": "abc"},
        )
    ]
    pkg = make_pkg(
        requirement,
        dist_files=dist_files,
        index_url="https://pypi.org/simple",
    )
    if expected_target == "sdist":
        assert pkg.sdist is not None
        assert pkg.wheels is None
    else:
        assert pkg.sdist is None
        assert pkg.wheels is not None


def test_build_pylock_package_index_no_sdist(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(name="pure-whl", version="1.0")
    dist_files = [
        PackageWheel(
            url="https://pypi.org/packages/pure_whl-1.0-py3-none-any.whl",
            name="pure_whl-1.0-py3-none-any.whl",
            hashes={"sha256": "abc"},
        ),
    ]
    pkg = make_pkg(
        requirement,
        dist_files=dist_files,
        index_url="https://pypi.org/simple",
    )
    assert pkg.sdist is None
    assert pkg.wheels is not None
    assert len(pkg.wheels) == 1


def test_build_pylock_package_with_marker(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    stub_sdist: list[PackageSdist],
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    pkg = make_pkg(
        requirement,
        dist_files=stub_sdist,
        marker="sys_platform == 'win32'",
    )
    assert str(pkg.marker) == 'sys_platform == "win32"'


def test_build_pylock_package_dependencies_sorted(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    stub_sdist: list[PackageSdist],
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    pkg = make_pkg(
        requirement,
        dist_files=stub_sdist,
        dependencies=[{"name": n} for n in sorted({"werkzeug", "click", "jinja2"})],
    )
    assert pkg.dependencies is not None
    dep_names = [d["name"] for d in pkg.dependencies]
    assert dep_names == ["click", "jinja2", "werkzeug"]


@pytest.mark.parametrize(
    ("requires_python", "expected"),
    (
        pytest.param(">=3.9", ">=3.9", id="set"),
        pytest.param(None, None, id="default-none"),
    ),
)
def test_build_pylock_package_requires_python(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    stub_sdist: list[PackageSdist],
    requires_python: str | None,
    expected: str | None,
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    pkg = make_pkg(
        requirement,
        dist_files=stub_sdist,
        requires_python=requires_python,
    )
    assert pkg.requires_python == expected


def test_assign_dist_files_sorts_wheels_and_picks_first_sdist(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(name="pkg", version="1.0")
    dist_files: list[PackageWheel | PackageSdist] = [
        PackageWheel(
            url="https://example.com/pkg-1.0-py3-none-win_amd64.whl",
            name="pkg-1.0-py3-none-win_amd64.whl",
            hashes={"sha256": "w"},
        ),
        PackageWheel(
            url="https://example.com/pkg-1.0-py3-none-any.whl",
            name="pkg-1.0-py3-none-any.whl",
            hashes={"sha256": "a"},
        ),
        PackageSdist(
            url="https://example.com/pkg-1.0.zip",
            name="pkg-1.0.zip",
            hashes={"sha256": "z"},
        ),
        PackageSdist(
            url="https://example.com/pkg-1.0.tar.gz",
            name="pkg-1.0.tar.gz",
            hashes={"sha256": "t"},
        ),
    ]
    pkg = make_pkg(
        requirement,
        dist_files=dist_files,
        index_url="https://pypi.org/simple",
    )
    assert pkg.wheels is not None
    assert [w.name for w in pkg.wheels] == [
        "pkg-1.0-py3-none-any.whl",
        "pkg-1.0-py3-none-win_amd64.whl",
    ]
    assert pkg.sdist is not None
    assert pkg.sdist.name == "pkg-1.0.tar.gz"


def test_requirement_version_returns_specifier_version(
    make_requirement: RequirementFactory,
) -> None:
    assert requirement_version(make_requirement(version="2.5.1")) == "2.5.1"


def test_requirement_version_returns_none_for_empty_specifier(
    mocker: MockerFixture,
) -> None:
    requirement = mocker.MagicMock(
        specifier=mocker.MagicMock(__iter__=lambda _self: iter([]))
    )
    assert requirement_version(requirement) is None


def test_validate_dist_filenames_derives_name_from_path() -> None:
    # PEP 751 lets path-only entries omit ``name``; the validator derives
    # the name from the path's last component so a malicious mirror serving
    # a ``name=None`` entry can't slip through the consistency check.
    bad_dist = PackageSdist(
        name=None, path="src/wrong-1.0.tar.gz", hashes={"sha256": "x" * 64}
    )
    with pytest.raises(PipToolsError, match="Index returned"):
        _validate_dist_filenames("expected", Version("1.0"), [bad_dist])


def _wheel(name: str) -> PackageWheel:
    return PackageWheel(name=name, url=f"https://e/{name}", hashes={"sha256": "x" * 64})


@pytest.mark.parametrize(
    ("wheels", "expected_order"),
    (
        pytest.param(
            [
                "numpy-2.1.0-cp311-cp311-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp312-cp312-manylinux_2_17_x86_64.whl",
            ],
            [
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp312-cp312-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp311-cp311-manylinux_2_17_x86_64.whl",
            ],
            id="newest-cpython-first",
        ),
        pytest.param(
            [
                "numpy-2.1.0-cp313-cp313-musllinux_1_2_x86_64.whl",
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_aarch64.whl",
            ],
            [
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_aarch64.whl",
                "numpy-2.1.0-cp313-cp313-manylinux_2_17_x86_64.whl",
                "numpy-2.1.0-cp313-cp313-musllinux_1_2_x86_64.whl",
            ],
            id="same-python-stable-by-platform",
        ),
        pytest.param(
            [
                "anyio-3.7.0-py3-none-any.whl",
                "anyio-3.7.0-pp310-pypy310_pp73-manylinux_2_17_x86_64.whl",
                "anyio-3.7.0-cp313-cp313-manylinux_2_17_x86_64.whl",
            ],
            [
                "anyio-3.7.0-cp313-cp313-manylinux_2_17_x86_64.whl",
                "anyio-3.7.0-pp310-pypy310_pp73-manylinux_2_17_x86_64.whl",
                "anyio-3.7.0-py3-none-any.whl",
            ],
            id="cpython-before-pypy-before-py3",
        ),
        pytest.param(
            ["not-a-real-wheel.whl"],
            ["not-a-real-wheel.whl"],
            id="unparseable-fallback",
        ),
    ),
)
def test_wheel_sort_key_orders_newest_python_first(
    wheels: list[str], expected_order: list[str]
) -> None:
    sorted_wheels = sorted((_wheel(name) for name in wheels), key=_wheel_sort_key)
    assert [w.name for w in sorted_wheels] == expected_order


def _sdist(name: str) -> PackageSdist:
    return PackageSdist(name=name, url=f"https://e/{name}", hashes={"sha256": "x" * 64})


@pytest.mark.parametrize(
    ("input_names", "expected_first"),
    (
        pytest.param(
            ["pkg-1.0.zip", "pkg-1.0.tar.gz"], "pkg-1.0.tar.gz", id="tar-gz-wins"
        ),
        pytest.param(["pkg-1.0.tar.gz"], "pkg-1.0.tar.gz", id="only-tar-gz"),
        pytest.param(["pkg-1.0.zip"], "pkg-1.0.zip", id="only-zip"),
    ),
)
def test_build_index_source_prefers_tar_gz_over_zip(
    input_names: list[str], expected_first: str
) -> None:
    sdist, _ = build_index_source(
        "pkg",
        Version("1.0"),
        [_sdist(name) for name in input_names],
        lock_dir=None,
    )
    assert sdist is not None
    assert sdist.name == expected_first


def test_build_index_source_warns_when_dropping_extra_sdist(
    capsys: pytest.CaptureFixture[str],
) -> None:
    build_index_source(
        "pkg",
        Version("1.0"),
        [_sdist("pkg-1.0.tar.gz"), _sdist("pkg-1.0.zip")],
        lock_dir=None,
    )
    captured = capsys.readouterr()
    assert "Multiple sdists for pkg==1.0" in captured.err
    assert "pkg-1.0.zip" in captured.err
