from __future__ import annotations

import pytest
from pip._vendor.requests import RequestException

from piptools._internal import _pip_api
from piptools.repositories import PyPIRepository


@pytest.fixture
def finder_with_pre(tmp_path):
    # PyPIRepository init is the primary way that a PackageFinder gets build
    # in piptools, so we use it for this fixture
    repo = PyPIRepository(["--pre"], cache_dir=tmp_path / "cache_dir")
    return repo._finder


def test_finder_with_pre_allows_all_prereleases(finder_with_pre):
    assert _pip_api.finder_allows_all_prereleases(finder_with_pre)


def test_finder_with_pre_allows_specific_package_prereleases(finder_with_pre):
    req = _pip_api.create_install_requirement_from_line("foolib>1")
    assert _pip_api.finder_allows_prereleases_of_req(finder_with_pre, req)


def test_get_request_exc_types_always_provides_tuple_with_base_request_exc_type():
    # Always clear cache before exercising this test, so that we're really calling the
    # function. This ensures that if there is breakage inside of the cached function, we
    # will get it reported as a failure here. That helps us to isolate the issue.
    _pip_api.get_pip_request_failed_exception_types.cache_clear()

    exc_types = _pip_api.get_pip_request_failed_exception_types()
    assert isinstance(exc_types, tuple)
    assert len(exc_types) >= 1
    assert RequestException in exc_types
