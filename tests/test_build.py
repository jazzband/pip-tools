from __future__ import annotations

import pathlib
import shutil

import pytest

from piptools.build import build_project_metadata
from tests.constants import PACKAGES_PATH


@pytest.mark.network
def test_build_project_metadata_resolved_correct_build_dependencies(
    fake_dists_with_build_deps, tmp_path, monkeypatch
):
    """Test that the resolved build dependencies are correct.

    Because this is a slow process we test it only for one build target and rely
    on ``test_all_extras_and_all_build_deps`` to test that it works with multiple build
    targets.
    """
    # When used as argument to the runner it is not passed to pip
    monkeypatch.setenv("PIP_FIND_LINKS", fake_dists_with_build_deps)
    src_pkg_path = pathlib.Path(PACKAGES_PATH) / "small_fake_with_build_deps"
    shutil.copytree(src_pkg_path, tmp_path, dirs_exist_ok=True)
    src_file = tmp_path / "setup.py"
    metadata = build_project_metadata(
        src_file, ("editable",), isolated=True, quiet=False
    )
    build_requirements = sorted(r.name for r in metadata.build_requirements)
    assert build_requirements == [
        "fake_dynamic_build_dep_for_all",
        "fake_dynamic_build_dep_for_editable",
        "fake_static_build_dep",
        "setuptools",
        "wheel",
    ]
