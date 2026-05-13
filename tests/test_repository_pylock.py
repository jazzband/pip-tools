from __future__ import annotations

import contextlib
from collections.abc import Callable, Iterator
from io import BytesIO
from pathlib import Path

import pytest
from packaging.pylock import PackageSdist, PackageWheel
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.link import Link
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools._internal import _pip_api
from piptools.exceptions import PipToolsError
from piptools.repositories import PyPIRepository
from piptools.repositories.base import BaseRepository
from piptools.repositories.local import LocalRequirementsRepository
from piptools.repositories.pypi import FileStream


def test_fake_repository_returns_file_info(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    requirement = from_line("small-fake-a==0.1")
    files = repository.get_distribution_files(requirement)
    assert len(files) == 1
    assert isinstance(files[0], (PackageSdist, PackageWheel))
    assert files[0].name == "small-fake-a-0.1.tar.gz"
    assert files[0].hashes == {"sha256": "0" * 64}
    assert files[0].size == 1000


def test_fake_repository_returns_empty_for_url_requirement(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    requirement = from_line("https://example.com/pkg.tar.gz")
    assert repository.get_distribution_files(requirement) == []


def test_base_repository_defaults_for_pylock_methods(mocker: MockerFixture) -> None:
    # Third-party ``BaseRepository`` subclasses written before pip-lock landed
    # do not override the new pylock helpers; the fallbacks must keep them
    # instantiating and surface "no dist files" / no ``Requires-Python``
    # rather than raise. Bypass abstract instantiation by calling the
    # unbound methods with a stand-in ``self``.
    fake_self = mocker.MagicMock()
    fake_ireq = mocker.MagicMock()
    assert BaseRepository.get_distribution_files(fake_self, fake_ireq) == []
    assert BaseRepository.get_requires_python(fake_self, fake_ireq) is None


def test_pypi_clear_caches_atomically_renames_then_removes(
    pypi_repository: PyPIRepository, tmp_path: Path
) -> None:
    # Two ``pip-lock`` processes against one cache directory must not race on
    # ``rmtree``; the rename pivots the live tree out before deletion so a
    # concurrent reader either sees the old directory or none at all, never a
    # half-deleted one.
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    (download_dir / "marker").write_text("data")
    pypi_repository._download_dir = str(download_dir)

    pypi_repository.clear_caches()

    assert not download_dir.exists()
    assert not list(tmp_path.glob("downloads.stale-*"))


def test_pypi_clear_caches_skips_when_rename_fails(
    pypi_repository: PyPIRepository, tmp_path: Path, mocker: MockerFixture
) -> None:
    # The rename can fail on locked files (Windows) or cross-device moves;
    # the cleanup is best-effort so the caller continues rather than crash.
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    pypi_repository._download_dir = str(download_dir)
    mocker.patch("piptools.repositories.pypi.os.replace", side_effect=OSError("locked"))

    pypi_repository.clear_caches()

    assert download_dir.exists()


def test_local_repository_delegates(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    local = LocalRequirementsRepository({}, repository)
    files = local.get_distribution_files(from_line("small-fake-a==0.1"))
    assert len(files) == 1
    assert files[0].name == "small-fake-a-0.1.tar.gz"


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_pypi_repository_falls_back_to_candidates(
    pypi_repository: PyPIRepository,
) -> None:
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    with pypi_repository.allow_all_wheels():
        files = pypi_repository.get_distribution_files(requirement)
    assert len(files) >= 1
    for f in files:
        assert isinstance(f, (PackageSdist, PackageWheel))
        assert f.url
        assert f.name
        assert f.hashes


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_pypi_repository_returns_empty_for_vcs(
    pypi_repository: PyPIRepository,
) -> None:
    requirement = _pip_api.create_install_requirement_from_line(
        "git+https://github.com/jazzband/pip-tools@main#egg=pip-tools"
    )
    assert pypi_repository.get_distribution_files(requirement) == []


@pytest.mark.usefixtures("pip_conf")
def test_pypi_repository_returns_empty_for_url_req(
    pypi_repository: PyPIRepository,
) -> None:
    """URL requirements skip the index lookup and return an empty list."""
    requirement = _pip_api.create_install_requirement_from_line(
        "https://example.com/pkg-1.0.tar.gz"
    )
    assert pypi_repository.get_distribution_files(requirement) == []


@pytest.mark.network
@pytest.mark.usefixtures("pip_conf")
def test_pypi_repository_raises_for_unpinned(
    pypi_repository: PyPIRepository,
) -> None:
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a")
    with pytest.raises(TypeError, match="Expected pinned requirement"):
        pypi_repository.get_distribution_files(requirement)


@pytest.mark.usefixtures("pip_conf")
def test_pypi_repository_raises_for_unpinned_non_network(
    pypi_repository: PyPIRepository,
) -> None:
    """Unpinned requirements raise TypeError before any network call."""
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a")
    with pytest.raises(TypeError, match="Expected pinned requirement"):
        pypi_repository.get_distribution_files(requirement)


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_falls_back_when_project_is_none(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    """When _get_project returns None, fallback to _get_distribution_files_from_candidates."""
    mocker.patch.object(pypi_repository, "_get_project", return_value=None)
    mock_fallback = mocker.patch.object(
        pypi_repository,
        "_get_distribution_files_from_candidates",
        return_value=[],
    )
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    result = pypi_repository.get_distribution_files(requirement)
    mock_fallback.assert_called_once_with(requirement)
    assert result == []


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_from_json_api(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/small-fake-a-0.1.tar.gz",
                    "filename": "small-fake-a-0.1.tar.gz",
                    "digests": {"sha256": "abc123", "md5": "def456"},
                    "size": 12345,
                    "upload_time_iso_8601": "2024-01-15T10:30:00.000000Z",
                    "packagetype": "sdist",
                },
                {
                    "url": "https://example.com/small_fake_a-0.1-py3-none-any.whl",
                    "filename": "small_fake_a-0.1-py3-none-any.whl",
                    "digests": {"sha256": "whl789"},
                    "size": 5000,
                    "upload_time_iso_8601": "2024-01-15T10:31:00.000000Z",
                    "packagetype": "bdist_wheel",
                },
                {
                    "url": "https://example.com/small-fake-a-0.1.exe",
                    "filename": "small-fake-a-0.1.exe",
                    "digests": {"sha256": "exe000"},
                    "size": 99999,
                    "packagetype": "bdist_wininst",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)

    assert len(files) == 2
    sdist = files[0]
    assert sdist.name == "small-fake-a-0.1.tar.gz"
    # md5 is dropped: PEP 751 wants "at least one secure algorithm" and md5
    # only satisfies pip's checks, not the spec's intent.
    assert sdist.hashes == {"sha256": "abc123"}
    assert sdist.size == 12345
    assert sdist.upload_time is not None

    wheel = files[1]
    assert wheel.name == "small_fake_a-0.1-py3-none-any.whl"
    assert wheel.hashes == {"sha256": "whl789"}


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_json_missing_release(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    mocker.patch.object(pypi_repository, "_get_project", return_value={"releases": {}})
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    with pypi_repository.allow_all_wheels():
        files = pypi_repository.get_distribution_files(requirement)
    assert len(files) >= 1


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_json_missing_digests(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg.tar.gz",
                    "filename": "pkg.tar.gz",
                    "size": 100,
                    "packagetype": "sdist",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)
    assert files == []


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_streams_sha256_when_only_weak_digests(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    # md5 satisfies pip's permissive guaranteed-algorithms check but PEP 751
    # treats it as insecure; the fallback streams the file for a real sha256
    # rather than emit an md5-only ``hashes`` table.
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg.tar.gz",
                    "filename": "pkg.tar.gz",
                    "digests": {"md5": "deadbeef"},
                    "size": 100,
                    "packagetype": "sdist",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    mocker.patch.object(
        pypi_repository,
        "_get_file_hash_and_size",
        return_value=("sha256:" + "f" * 64, 4096),
    )
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)
    assert len(files) == 1
    assert files[0].hashes == {"sha256": "f" * 64}
    # JSON ``size`` was supplied (100), so the cached value beats the
    # streamed byte count; the lockfile records the index-reported size.
    assert files[0].size == 100


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_uses_streamed_size_when_json_omits(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    # When JSON omits ``size`` and the streamer fills it in, the lockfile
    # carries the count of bytes hashed; without the substitution
    # ``packages.size`` would be absent only on private mirrors that don't
    # expose digests, producing a noisy diff between PyPI and mirror locks.
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg.tar.gz",
                    "filename": "pkg.tar.gz",
                    "digests": {"md5": "deadbeef"},
                    "packagetype": "sdist",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    mocker.patch.object(
        pypi_repository,
        "_get_file_hash_and_size",
        return_value=("sha256:" + "f" * 64, 4096),
    )
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)
    assert len(files) == 1
    assert files[0].size == 4096


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_falls_back_when_filtered_digests_empty(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    # PyPI reports only `crc32`, which is neither in the secure-algorithms
    # allowlist nor a known integrity primitive; stream sha256 instead.
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg.tar.gz",
                    "filename": "pkg.tar.gz",
                    "digests": {"crc32": "deadbeef"},
                    "size": 100,
                    "packagetype": "sdist",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    mocker.patch.object(
        pypi_repository,
        "_get_file_hash_and_size",
        return_value=("sha256:" + "f" * 64, 4096),
    )
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)
    assert len(files) == 1
    assert files[0].hashes == {"sha256": "f" * 64}


@pytest.mark.usefixtures("pip_conf")
def test_pypi_candidate_path_caches_streamed_sha256(
    pypi_repository: PyPIRepository, mocker: MockerFixture, tmp_path: Path
) -> None:
    # When the index doesn't expose digests, pip-tools streams each wheel
    # through sha256 on every run. With an on-disk cache the second run reuses
    # the digest and skips the hash loop; noticeable on 200+ package locks.
    mocker.patch.object(pypi_repository, "_get_project", return_value=None)
    candidate = mocker.MagicMock()
    # The hash cache only stores ``files.pythonhosted.org`` URLs (the only
    # content-addressable host); a private-index URL would bypass the cache
    # so this test would never observe the second-run hit.
    candidate.link.url_without_fragment = (
        "https://files.pythonhosted.org/packages/abc/pkg-1.0.tar.gz"
    )
    candidate.link.filename = "pkg-1.0.tar.gz"
    mocker.patch.object(
        pypi_repository, "_get_matching_candidates", return_value=[candidate]
    )
    pypi_repository._options.cache_dir = str(tmp_path)
    file_hash = mocker.patch.object(
        pypi_repository,
        "_get_file_hash_and_size",
        return_value=("sha256:" + "a" * 64, 2048),
    )
    requirement = _pip_api.create_install_requirement_from_line("pkg==1.0")

    first = pypi_repository.get_distribution_files(requirement)
    second = pypi_repository.get_distribution_files(requirement)

    assert first == second
    assert file_hash.call_count == 1


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_distribution_files_no_upload_time(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    fake_release = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg.tar.gz",
                    "filename": "pkg.tar.gz",
                    "digests": {"sha256": "abc"},
                    "size": 100,
                    "packagetype": "sdist",
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=fake_release)
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    files = pypi_repository.get_distribution_files(requirement)
    assert len(files) == 1
    assert files[0].upload_time is None


@pytest.mark.usefixtures("pip_conf")
@pytest.mark.parametrize(
    ("project_data", "expected"),
    (
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {
                            "url": "https://example.com/pkg-0.1.tar.gz",
                            "filename": "pkg-0.1.tar.gz",
                            "digests": {"sha256": "abc"},
                            "size": 100,
                            "packagetype": "sdist",
                            "requires_python": ">=3.9",
                        }
                    ]
                }
            },
            ">=3.9",
            id="present",
        ),
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {
                            "url": "https://example.com/pkg-0.1.tar.gz",
                            "filename": "pkg-0.1.tar.gz",
                            "digests": {"sha256": "abc"},
                            "size": 100,
                            "packagetype": "sdist",
                        }
                    ]
                }
            },
            None,
            id="missing-field",
        ),
        pytest.param(None, None, id="no-project"),
    ),
)
def test_pypi_get_requires_python(
    pypi_repository: PyPIRepository,
    mocker: MockerFixture,
    project_data: dict[str, object] | None,
    expected: str | None,
) -> None:
    mocker.patch.object(pypi_repository, "_get_project", return_value=project_data)
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    assert pypi_repository.get_requires_python(requirement) == expected


@pytest.mark.usefixtures("pip_conf")
@pytest.mark.parametrize(
    ("first_rp", "second_rp", "expected_substrings"),
    (
        pytest.param(">=3.9", ">=3.9", (">=3.9",), id="agreeing-files"),
        pytest.param(">=3.9", ">=3.10", (">=3.9", ">=3.10"), id="conflicting-files"),
        pytest.param(">=3.9", "not-a-spec", (">=3.9",), id="invalid-second-skipped"),
    ),
)
def test_pypi_get_requires_python_intersects_per_file_specifiers(
    pypi_repository: PyPIRepository,
    mocker: MockerFixture,
    first_rp: str,
    second_rp: str,
    expected_substrings: tuple[str, ...],
) -> None:
    project_data = {
        "releases": {
            "0.1": [
                {
                    "url": "https://example.com/pkg-0.1.tar.gz",
                    "filename": "pkg-0.1.tar.gz",
                    "digests": {"sha256": "abc"},
                    "size": 100,
                    "packagetype": "sdist",
                    "requires_python": first_rp,
                },
                {
                    "url": "https://example.com/pkg-0.1-py3-none-any.whl",
                    "filename": "pkg-0.1-py3-none-any.whl",
                    "digests": {"sha256": "def"},
                    "size": 100,
                    "packagetype": "bdist_wheel",
                    "requires_python": second_rp,
                },
            ]
        }
    }
    mocker.patch.object(pypi_repository, "_get_project", return_value=project_data)
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    result = pypi_repository.get_requires_python(requirement)
    assert result is not None
    for substr in expected_substrings:
        assert substr in result


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_requires_python_returns_none_for_url_req(
    pypi_repository: PyPIRepository,
) -> None:
    requirement = _pip_api.create_install_requirement_from_line(
        "https://example.com/pkg-1.0.tar.gz"
    )
    assert pypi_repository.get_requires_python(requirement) is None


def test_fake_repository_get_requires_python(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    requirement = from_line("small-fake-a==0.1")
    assert repository.get_requires_python(requirement) is None


def test_local_repository_delegates_requires_python(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    local = LocalRequirementsRepository({}, repository)
    requirement = from_line("small-fake-a==0.1")
    assert local.get_requires_python(requirement) is None


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_requires_python_returns_none_for_unpinned(
    pypi_repository: PyPIRepository,
) -> None:
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a")
    assert pypi_repository.get_requires_python(requirement) is None


def test_local_repository_clear_caches_delegates(
    repository: BaseRepository, mocker: MockerFixture
) -> None:
    local = LocalRequirementsRepository({}, repository)
    clear_caches_mock = mocker.patch.object(repository, "clear_caches")
    local.clear_caches()
    clear_caches_mock.assert_called_once_with()


@pytest.mark.usefixtures("pip_conf")
def test_local_repository_get_hashes_falls_back_when_no_hexdigests(
    from_line: Callable[..., InstallRequirement], repository: BaseRepository
) -> None:
    """Empty hexdigests fall through to the repository's default hash path."""
    req = from_line("small-fake-a==0.1", hash_options={"sha256": []})
    existing_pins = {req.name: req}
    local = LocalRequirementsRepository(existing_pins, repository)
    # The existing pin has no hexdigests, so get_hashes falls back to the proxied repo.
    hashes = local.get_hashes(from_line("small-fake-a==0.1"))
    assert isinstance(hashes, set)


@pytest.mark.usefixtures("pip_conf")
def test_pypi_clear_finder_cache_old_pip(
    pypi_repository: PyPIRepository,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lines 133-134: else branch when pip < 25.1 uses cache_clear()."""
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (24, 0))
    mock_find_all = mocker.MagicMock()
    mock_find_best = mocker.MagicMock()
    monkeypatch.setattr(pypi_repository.finder, "find_all_candidates", mock_find_all)
    monkeypatch.setattr(pypi_repository.finder, "find_best_candidate", mock_find_best)
    pypi_repository._clear_finder_cache()
    mock_find_all.cache_clear.assert_called_once_with()
    mock_find_best.cache_clear.assert_called_once_with()


@pytest.mark.usefixtures("pip_conf")
def test_pypi_clear_finder_cache_drops_available_candidates(
    pypi_repository: PyPIRepository,
) -> None:
    pypi_repository._available_candidates_cache["fake"] = ["sentinel"]
    pypi_repository._clear_finder_cache()
    assert pypi_repository._available_candidates_cache == {}


@pytest.mark.usefixtures("pip_conf")
def test_pypi_clear_finder_cache_new_pip(
    pypi_repository: PyPIRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pip 25.1 swapped lru_cache decoration for instance-level dicts; the
    # else-branch above already covers `cache_clear`, this exercises the
    # dict-clear path so both pip eras stay green.
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (26, 0))
    pypi_repository.finder._all_candidates = {"foo": ["sentinel"]}
    pypi_repository.finder._best_candidates = {"foo": ["sentinel"]}
    pypi_repository._clear_finder_cache()
    assert pypi_repository.finder._all_candidates == {}
    assert pypi_repository.finder._best_candidates == {}


@pytest.mark.usefixtures("pip_conf")
def test_pypi_get_dependencies_calls_get_dist_for_when_not_prepared(
    pypi_repository: PyPIRepository,
    mocker: MockerFixture,
) -> None:
    # Without the `_get_dist_for(requirement)` call the dependencies set comes
    # back empty whenever pip's resolver leaves `requirement.prepared` False
    # after `_resolve_one`, which the resolver does for editable installs
    # and for a few VCS shapes. Drive a sentinel exception out of the
    # mock so we hit the call-site exactly once and exit the function
    # cleanly without depending on whatever pip's later code paths do
    # with the (mocked) returned dist.
    requirement = _pip_api.create_install_requirement_from_line("small-fake-a==0.1")
    mock_resolver = mocker.MagicMock()
    mock_resolver._resolve_one.return_value = []
    mock_resolver._get_dist_for.side_effect = StopIteration("test sentinel")
    mocker.patch.object(
        pypi_repository.command, "make_resolver", return_value=mock_resolver
    )
    requirement.prepared = False
    with pytest.raises(StopIteration, match="test sentinel"):
        pypi_repository.get_dependencies(requirement)
    mock_resolver._get_dist_for.assert_called_once_with(requirement)


def test_get_file_hash_and_size_refuses_truncated_stream(
    pypi_repository: PyPIRepository, mocker: MockerFixture
) -> None:
    # If a transparent proxy truncates mid-stream, the sha256 still computes
    # validly over the truncated bytes; recording it as authoritative would
    # lock a corrupt artifact. Cross-check Content-Length and refuse.
    fake_stream = FileStream(stream=BytesIO(b"abc"), size=99)

    @contextlib.contextmanager
    def fake_open(link: Link, session: object) -> Iterator[FileStream]:
        yield fake_stream

    mocker.patch("piptools.repositories.pypi.open_local_or_remote_file", fake_open)
    with pytest.raises(PipToolsError, match="truncated"):
        pypi_repository._get_file_hash_and_size(Link("https://example.com/pkg.tar.gz"))


@pytest.fixture
def candidate_factory(
    mocker: MockerFixture,
) -> Callable[[str, str], InstallationCandidate]:
    def _make(url: str, filename: str) -> InstallationCandidate:
        candidate = mocker.create_autospec(InstallationCandidate, instance=True)
        candidate.link = mocker.create_autospec(Link, instance=True)
        candidate.link.url_without_fragment = url
        candidate.link.filename = filename
        return candidate

    return _make


@pytest.fixture
def from_candidates_repository(
    pypi_repository: PyPIRepository,
    candidate_factory: Callable[[str, str], InstallationCandidate],
    mocker: MockerFixture,
) -> Callable[[str, str], PyPIRepository]:
    def _setup(url: str, filename: str) -> PyPIRepository:
        candidate = candidate_factory(url, filename)
        mocker.patch.object(pypi_repository, "_get_project", return_value=None)
        mocker.patch.object(
            pypi_repository, "_get_matching_candidates", return_value=[candidate]
        )
        return pypi_repository

    return _setup


@pytest.mark.parametrize(
    ("url", "filename"),
    (
        pytest.param(
            "http://example.com/pkg-1.0.tar.gz",
            "pkg-1.0.tar.gz",
            id="plain-http",
        ),
        pytest.param(
            "ftp://example.com/pkg-1.0.tar.gz",
            "pkg-1.0.tar.gz",
            id="ftp",
        ),
    ),
)
def test_get_distribution_files_from_candidates_refuses_insecure_scheme(
    from_candidates_repository: Callable[[str, str], PyPIRepository],
    url: str,
    filename: str,
) -> None:
    # PEP 751 hashes are authoritative; recording a streamed hash from a
    # non-TLS transport would let a man-in-the-middle's bytes become the
    # lockfile's source of truth. The check refuses every scheme except
    # ``https://`` and ``file://``.
    repository = from_candidates_repository(url, filename)
    requirement = _pip_api.create_install_requirement_from_line("pkg==1.0")
    with pytest.raises(PipToolsError, match="streamed hash"):
        repository.get_distribution_files(requirement)


def test_get_distribution_files_skips_hash_cache_for_non_sha256(
    from_candidates_repository: Callable[[str, str], PyPIRepository],
    mocker: MockerFixture,
) -> None:
    # ``_hash_cache.store`` is keyed on sha256 digests so a non-sha256 result
    # from ``_get_file_hash_and_size`` (a future ``FAVORITE_HASH`` swap, or a
    # mirror that hashed with ``sha512`` directly) bypasses the cache write
    # without dropping the digest from the recorded lockfile entry.
    repository = from_candidates_repository(
        "https://example.com/pkg-1.0.tar.gz", "pkg-1.0.tar.gz"
    )
    mocker.patch.object(
        repository,
        "_get_file_hash_and_size",
        return_value=("sha512:" + "a" * 128, 4096),
    )
    hash_cache_load = mocker.patch(
        "piptools.repositories.pypi._hash_cache.load", return_value=None
    )
    hash_cache_store = mocker.patch("piptools.repositories.pypi._hash_cache.store")
    requirement = _pip_api.create_install_requirement_from_line("pkg==1.0")
    files = repository.get_distribution_files(requirement)
    hash_cache_load.assert_called_once()
    hash_cache_store.assert_not_called()
    assert len(files) == 1
    assert files[0].hashes == {"sha512": "a" * 128}
    assert files[0].size == 4096
