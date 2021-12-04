import os
from unittest import mock

import pytest
from pip._internal.models.link import Link
from pip._internal.utils.urls import path_to_url
from pip._vendor.requests import HTTPError, Session

from piptools.repositories import PyPIRepository
from piptools.repositories.pypi import open_local_or_remote_file


def test_generate_hashes_all_platforms(capsys, pip_conf, from_line, pypi_repository):
    expected = {
        "sha256:8d4d131cd05338e09f461ad784297efea3652e542c5fabe04a62358429a6175e",
        "sha256:ad05e1371eb99f257ca00f791b755deb22e752393eb8e75bc01d651715b02ea9",
        "sha256:24afa5b317b302f356fd3fc3b1cfb0aad114d509cf635ea9566052424191b944",
        "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }

    ireq = from_line("small-fake-multi-arch==0.1")

    # pip caches the candidates for the current system, which means
    # allow_all_wheels won't have the desired effect unless the cache is
    # cleared. See GH-1532
    assert pypi_repository.get_hashes(ireq) < expected

    with pypi_repository.allow_all_wheels():
        assert pypi_repository.get_hashes(ireq) == expected
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.network
def test_get_file_hash_without_interfering_with_each_other(from_line, pypi_repository):
    """
    The PyPIRepository._get_file_hash() used to call unpack_url(),
    when generating the hash. Unpacking both packages to the same directory
    will then fail. E.g. matplotlib-2.0.2.tar.gz has a directory named LICENSE,
    but many other packages have a file named LICENSE.

    See GH-512 and GH-544.
    """
    assert (
        pypi_repository._get_file_hash(
            Link(
                "https://files.pythonhosted.org/packages/"
                "f5/f0/9da3ef24ea7eb0ccd12430a261b66eca36b924aeef06e17147f9f9d7d310/"
                "matplotlib-2.0.2.tar.gz"
            )
        )
        == "sha256:0ffbc44faa34a8b1704bc108c451ecf87988f900ef7ce757b8e2e84383121ff1"
    )

    assert (
        pypi_repository._get_file_hash(
            Link(
                "https://files.pythonhosted.org/packages/"
                "a1/32/e3d6c3a8b5461b903651dd6ce958ed03c093d2e00128e3f33ea69f1d7965/"
                "cffi-1.9.1.tar.gz"
            )
        )
        == "sha256:563e0bd53fda03c151573217b3a49b3abad8813de9dd0632e10090f6190fdaf8"
    )


def test_get_hashes_editable_empty_set(from_editable, pypi_repository):
    ireq = from_editable("git+https://github.com/django/django.git#egg=django")
    assert pypi_repository.get_hashes(ireq) == set()


def test_get_hashes_unpinned_raises(from_line, pypi_repository):
    # Under normal pip-tools usage, get_hashes() should never be called with an
    # unpinned requirement. The TypeError represents a programming mistake.
    ireq = from_line("django")
    with pytest.raises(TypeError, match=r"^Expected pinned requirement, got django"):
        pypi_repository.get_hashes(ireq)


@pytest.mark.parametrize(("content", "content_length"), ((b"foo", 3), (b"foobar", 6)))
def test_open_local_or_remote_file__local_file(tmp_path, content, content_length):
    """
    Test the `open_local_or_remote_file` returns a context manager to a FileStream
    for a given `Link` to a local file.
    """
    local_file_path = tmp_path / "foo.txt"
    local_file_path.write_bytes(content)

    link = Link(local_file_path.as_uri())
    session = Session()

    with open_local_or_remote_file(link, session) as file_stream:
        assert file_stream.stream.read() == content
        assert file_stream.size == content_length


def test_open_local_or_remote_file__directory(tmpdir):
    """
    Test the `open_local_or_remote_file` raises a ValueError for a given `Link`
    to a directory.
    """
    link = Link(path_to_url(tmpdir.strpath))
    session = Session()

    with pytest.raises(
        ValueError, match="Cannot open directory for read"
    ), open_local_or_remote_file(link, session):
        pass  # pragma: no cover


@pytest.mark.parametrize(
    ("content", "content_length", "expected_content_length"),
    ((b"foo", 3, 3), (b"bar", None, None), (b"kek", "invalid-content-length", None)),
)
def test_open_local_or_remote_file__remote_file(
    tmp_path, content, content_length, expected_content_length
):
    """
    Test the `open_local_or_remote_file` returns a context manager to a FileStream
    for a given `Link` to a remote file.
    """
    link = Link("https://example.com/foo.txt")
    session = Session()

    response_file_path = tmp_path / "foo.txt"
    response_file_path.write_bytes(content)

    mock_response = mock.Mock()
    with response_file_path.open("rb") as fp:
        mock_response.raw = fp
        mock_response.headers = {"content-length": content_length}

        with mock.patch.object(session, "get", return_value=mock_response):
            with open_local_or_remote_file(link, session) as file_stream:
                assert file_stream.stream.read() == content
                assert file_stream.size == expected_content_length

        mock_response.close.assert_called_once()


def test_relative_path_cache_dir_is_normalized(from_line):
    relative_cache_dir = "pypi-repo-cache"
    pypi_repository = PyPIRepository([], cache_dir=relative_cache_dir)

    assert os.path.isabs(pypi_repository._cache_dir)
    assert pypi_repository._cache_dir.endswith(relative_cache_dir)


def test_relative_path_pip_cache_dir_is_normalized(from_line, tmpdir):
    relative_cache_dir = "pip-cache"
    pypi_repository = PyPIRepository(
        ["--cache-dir", relative_cache_dir], cache_dir=(tmpdir / "pypi-repo-cache")
    )

    assert os.path.isabs(pypi_repository.options.cache_dir)
    assert pypi_repository.options.cache_dir.endswith(relative_cache_dir)


def test_pip_cache_dir_is_empty(from_line, tmpdir):
    pypi_repository = PyPIRepository(
        ["--no-cache-dir"], cache_dir=(tmpdir / "pypi-repo-cache")
    )

    assert not pypi_repository.options.cache_dir


@pytest.mark.parametrize(
    ("project_data", "expected_hashes"),
    (
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {
                            "packagetype": "bdist_wheel",
                            "digests": {"sha256": "fake-hash"},
                        }
                    ]
                }
            },
            {"sha256:fake-hash"},
            id="return single hash",
        ),
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {
                            "packagetype": "bdist_wheel",
                            "digests": {"sha256": "fake-hash-number1"},
                        },
                        {
                            "packagetype": "sdist",
                            "digests": {"sha256": "fake-hash-number2"},
                        },
                    ]
                }
            },
            {"sha256:fake-hash-number1", "sha256:fake-hash-number2"},
            id="return multiple hashes",
        ),
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {
                            "packagetype": "bdist_wheel",
                            "digests": {"sha256": "fake-hash-number1"},
                        },
                        {
                            "packagetype": "sdist",
                            "digests": {"sha256": "fake-hash-number2"},
                        },
                        {
                            "packagetype": "bdist_eggs",
                            "digests": {"sha256": "fake-hash-number3"},
                        },
                    ]
                }
            },
            {"sha256:fake-hash-number1", "sha256:fake-hash-number2"},
            id="return only bdist_wheel and sdist hashes",
        ),
        pytest.param(None, None, id="not found project data"),
        pytest.param({}, None, id="not found releases key"),
        pytest.param({"releases": {}}, None, id="not found version"),
        pytest.param({"releases": {"0.1": [{}]}}, None, id="not found digests"),
        pytest.param(
            {"releases": {"0.1": [{"packagetype": "bdist_wheel", "digests": {}}]}},
            None,
            id="digests are empty",
        ),
        pytest.param(
            {
                "releases": {
                    "0.1": [
                        {"packagetype": "bdist_wheel", "digests": {"md5": "fake-hash"}}
                    ]
                }
            },
            None,
            id="not found sha256 algo",
        ),
    ),
)
def test_get_hashes_from_pypi(from_line, tmpdir, project_data, expected_hashes):
    """
    Test PyPIRepository._get_hashes_from_pypi() returns expected hashes or None.
    """

    class MockPyPIRepository(PyPIRepository):
        def _get_project(self, ireq):
            return project_data

    pypi_repository = MockPyPIRepository(
        ["--no-cache-dir"], cache_dir=(tmpdir / "pypi-repo-cache")
    )
    ireq = from_line("fake-package==0.1")

    actual_hashes = pypi_repository._get_hashes_from_pypi(ireq)
    assert actual_hashes == expected_hashes


def test_get_project__returns_data(from_line, tmpdir, monkeypatch, pypi_repository):
    """
    Test PyPIRepository._get_project() returns expected project data.
    """
    expected_data = {"releases": {"0.1": [{"digests": {"sha256": "fake-hash"}}]}}

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return expected_data

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(pypi_repository.session, "get", mock_get)
    ireq = from_line("fake-package==0.1")

    actual_data = pypi_repository._get_project(ireq)
    assert actual_data == expected_data


def test_get_project__handles_http_error(
    from_line, tmpdir, monkeypatch, pypi_repository
):
    """
    Test PyPIRepository._get_project() returns None if HTTP error is raised.
    """

    def mock_get(*args, **kwargs):
        raise HTTPError("test http error")

    monkeypatch.setattr(pypi_repository.session, "get", mock_get)
    ireq = from_line("fake-package==0.1")

    actual_data = pypi_repository._get_project(ireq)
    assert actual_data is None


def test_get_project__handles_json_decode_error(
    from_line, tmpdir, monkeypatch, pypi_repository
):
    """
    Test PyPIRepository._get_project() returns None if JSON decode error is raised.
    """

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            raise ValueError("test json error")

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(pypi_repository.session, "get", mock_get)
    ireq = from_line("fake-package==0.1")

    actual_data = pypi_repository._get_project(ireq)
    assert actual_data is None


def test_get_project__handles_404(from_line, tmpdir, monkeypatch, pypi_repository):
    """
    Test PyPIRepository._get_project() returns None if PyPI
    response's status code is 404.
    """

    class MockResponse:
        status_code = 404

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(pypi_repository.session, "get", mock_get)
    ireq = from_line("fake-package==0.1")

    actual_data = pypi_repository._get_project(ireq)
    assert actual_data is None


def test_name_collision(from_line, pypi_repository, make_package, make_sdist, tmpdir):
    """
    Test to ensure we don't fail if there are multiple URL-based requirements
    ending with the same filename where later ones depend on earlier, e.g.
    https://git.example.com/requirement1/master.zip#egg=req_package_1
    https://git.example.com/requirement2/master.zip#egg=req_package_2
    In this case, if req_package_2 depends on req_package_1 we don't want to
    fail due to issues such as caching the requirement based on filename.
    """
    packages = {
        "test_package_1": make_package("test_package_1", version="0.1"),
        "test_package_2": make_package(
            "test_package_2", version="0.1", install_requires=["test-package-1"]
        ),
    }

    for pkg_name, pkg in packages.items():
        pkg_path = tmpdir / pkg_name

        make_sdist(pkg, pkg_path, "--formats=zip")

        os.rename(
            os.path.join(pkg_path, f"{pkg_name}-0.1.zip"),
            os.path.join(pkg_path, "master.zip"),
        )

    name_collision_1 = "file://{dist_path}#egg=test_package_1".format(
        dist_path=tmpdir / "test_package_1" / "master.zip"
    )
    ireq = from_line(name_collision_1)
    deps = pypi_repository.get_dependencies(ireq)
    assert len(deps) == 0

    name_collision_2 = "file://{dist_path}#egg=test_package_2".format(
        dist_path=tmpdir / "test_package_2" / "master.zip"
    )
    ireq = from_line(name_collision_2)
    deps = pypi_repository.get_dependencies(ireq)
    assert len(deps) == 1
    assert deps.pop().name == "test-package-1"
