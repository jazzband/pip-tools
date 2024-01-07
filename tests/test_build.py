from __future__ import annotations

import pathlib
import shutil

import pytest

from piptools.build import StaticProjectMetadata, ProjectMetadata, build_project_metadata
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
        src_file, ("editable",), attempt_static_parse=False, isolated=True, quiet=False
    )
    assert isinstance(metadata, ProjectMetadata)
    build_requirements = sorted(r.name for r in metadata.build_requirements)
    assert build_requirements == [
        "fake_dynamic_build_dep_for_all",
        "fake_dynamic_build_dep_for_editable",
        "fake_static_build_dep",
        "setuptools",
        "wheel",
    ]


def test_build_project_metadata_static(tmp_path):
    """Test static parsing branch of build_project_metadata"""
    src_pkg_path = pathlib.Path(PACKAGES_PATH) / "small_fake_with_pyproject"
    shutil.copytree(src_pkg_path, tmp_path, dirs_exist_ok=True)
    src_file = tmp_path / "pyproject.toml"
    metadata = build_project_metadata(
        src_file, (), attempt_static_parse=True, isolated=True, quiet=False
    )
    assert isinstance(metadata, StaticProjectMetadata)
    requirements = [(r.name, r.extras, str(r.markers)) for r in metadata.requirements]
    requirements.sort(key=lambda x: x[0])
    assert requirements == [
        ('fake_direct_extra_runtime_dep', {"with_its_own_extra"}, 'extra == "x"'),
        ('fake_direct_runtime_dep', set(), 'None')
    ]
    assert metadata.extras == ("x",)
