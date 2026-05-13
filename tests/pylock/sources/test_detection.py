from __future__ import annotations

from piptools.pylock.sources import detect_source_type

from .conftest import RequirementFactory


def test_detect_source_type_editable(make_requirement: RequirementFactory) -> None:
    assert (
        detect_source_type(make_requirement(editable=True, link_url="file:///p"))
        == "directory"
    )


def test_detect_source_type_vcs(make_requirement: RequirementFactory) -> None:
    assert (
        detect_source_type(
            make_requirement(link_url="git+https://g/r@main", is_vcs=True)
        )
        == "vcs"
    )


def test_detect_source_type_local_directory(
    make_requirement: RequirementFactory,
) -> None:
    assert (
        detect_source_type(
            make_requirement(
                link_url="file:///local/p", is_file=True, is_existing_dir=True
            )
        )
        == "directory"
    )


def test_detect_source_type_direct_url(make_requirement: RequirementFactory) -> None:
    assert (
        detect_source_type(make_requirement(link_url="https://e.com/p-1.0.whl"))
        == "archive"
    )


def test_detect_source_type_index(make_requirement: RequirementFactory) -> None:
    assert detect_source_type(make_requirement()) == "index"
