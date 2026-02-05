from __future__ import annotations

import pytest

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
