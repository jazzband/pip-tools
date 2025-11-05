from __future__ import annotations

import pathlib
import shutil
import textwrap

import pytest
from build import BuildBackendException

from piptools.build import (
    ProjectMetadata,
    StaticProjectMetadata,
    build_project_metadata,
    maybe_statically_parse_project_metadata,
)
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
        ("fake_direct_extra_runtime_dep", {"with_its_own_extra"}, 'extra == "x"'),
        ("fake_direct_runtime_dep", set(), "None"),
    ]
    assert metadata.extras == ("x",)


def test_build_project_metadata_raises_error(tmp_path):
    src_pkg_path = pathlib.Path(PACKAGES_PATH) / "small_fake_with_build_deps"
    shutil.copytree(src_pkg_path, tmp_path, dirs_exist_ok=True)
    src_file = tmp_path / "setup.py"
    with pytest.raises(
        ValueError, match="Cannot execute the PEP 517 optional.* hooks statically"
    ):
        build_project_metadata(
            src_file,
            ("editable",),
            attempt_static_parse=True,
            isolated=True,
            quiet=False,
        )


def test_build_project_metadata_upgrading_raises_error(tmp_path):
    """Test build_project_metadata doesn't swallow error."""
    src_file = tmp_path / "pyproject.toml"
    src_file.write_text(
        textwrap.dedent(
            """
            [project]
            # missing name
            version = "0.1"
            dependencies=["test_dep"]
            """
        ),
    )
    with pytest.raises(
        BuildBackendException,
        match=(
            "Backend subprocess exited when trying to invoke "
            "get_requires_for_build_wheel"
        ),
    ):
        build_project_metadata(
            src_file,
            (),
            attempt_static_parse=False,
            isolated=True,
            quiet=False,
            upgrade_packages=["test_dep"],
        )


def test_static_parse_valid(tmp_path):
    src_file = tmp_path / "pyproject.toml"

    valid = """
[project]
name = "foo"
version = "0.1.0"
dependencies = ["bar>=1"]
[project.optional-dependencies]
baz = ["qux[extra]"]
"""
    src_file.write_text(valid)
    metadata = maybe_statically_parse_project_metadata(src_file)
    assert isinstance(metadata, StaticProjectMetadata)
    assert [str(r.req) for r in metadata.requirements] == ["bar>=1", "qux[extra]"]
    assert metadata.extras == ("baz",)


@pytest.mark.parametrize(
    "input_path_is_absolute",
    (True, False),
    ids=("absolute-input", "relative-input"),
)
def test_static_parse_of_self_referential_extra(
    tmp_path, monkeypatch, input_path_is_absolute
):
    monkeypatch.chdir(tmp_path)

    src_file = tmp_path / "pyproject.toml"
    src_file.write_text(
        textwrap.dedent(
            """
            [project]
            name = "foo"
            version = "0.1.0"
            [project.optional-dependencies]
            ext1 = ["bar"]
            ext2 = ["foo[ext1]"]
            """
        )
    )

    if input_path_is_absolute:
        parse_path = src_file
    else:
        parse_path = src_file.relative_to(tmp_path)

    metadata = maybe_statically_parse_project_metadata(parse_path)
    assert isinstance(metadata, StaticProjectMetadata)
    assert metadata.extras == ("ext1", "ext2")
    assert len(metadata.requirements) == 2

    assert [r.name for r in metadata.requirements] == ["bar", "foo"]
    assert [r.comes_from for r in metadata.requirements] == [
        f"foo ({parse_path.as_posix()})"
    ] * 2

    foo_req = metadata.requirements[1]
    assert foo_req.extras == {"ext1"}
    assert foo_req.link.url == tmp_path.as_uri()


def test_static_parse_invalid(tmp_path):
    src_file = tmp_path / "pyproject.toml"

    invalid_toml = """this is not valid toml"""
    src_file.write_text(invalid_toml)
    assert maybe_statically_parse_project_metadata(src_file) is None

    no_pep621 = """
[build-system]
requires = ["setuptools"]
"""
    src_file.write_text(no_pep621)
    assert maybe_statically_parse_project_metadata(src_file) is None

    invalid_pep621 = """
[project]
# no name
version = "0.1.0"
"""
    src_file.write_text(invalid_pep621)
    assert maybe_statically_parse_project_metadata(src_file) is None

    dynamic_deps = """
[project]
name = "foo"
dynamic = ["dependencies"]
"""
    src_file.write_text(dynamic_deps)
    assert maybe_statically_parse_project_metadata(src_file) is None

    dynamic_optional_deps = """
[project]
name = "foo"
dynamic = ["optional-dependencies"]
"""
    src_file.write_text(dynamic_optional_deps)
    assert maybe_statically_parse_project_metadata(src_file) is None

    src_file = tmp_path / "setup.py"
    src_file.write_text("print('hello')")
    assert maybe_statically_parse_project_metadata(src_file) is None


@pytest.mark.network
def test_build_metadata_from_dynamic_dependencies(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    setuppy_file = tmp_path / "setup.py"

    pyproject_file.write_text(
        textwrap.dedent(
            """
            [project]
            name = "foo"
            version = "0.1.0"
            dynamic = ["dependencies"]
            """
        )
    )
    setuppy_file.write_text(
        textwrap.dedent(
            """\
            from setuptools import setup
            setup(install_requires=["bar > 2"])
            """
        )
    )

    metadata = build_project_metadata(
        pyproject_file, (), attempt_static_parse=True, isolated=True, quiet=False
    )
    assert isinstance(metadata, ProjectMetadata)
    assert [str(r.req) for r in metadata.requirements] == ["bar>2"]
    assert [r.comes_from for r in metadata.requirements] == [
        f"foo ({pyproject_file.as_posix()})"
    ]
