from __future__ import annotations

import sys
from io import BytesIO

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib  # type: ignore[no-redef]
from datetime import datetime, timezone

from packaging.pylock import (
    Package,
    PackageArchive,
    PackageDirectory,
    PackageSdist,
    PackageVcs,
    PackageWheel,
    Pylock,
)
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import Version

from piptools.pylock.cli._file_io import _render


def _round_trip(doc: Pylock) -> Pylock:
    """Render ``doc`` then re-parse via ``Pylock.from_dict`` for typed access.

    Routing every assertion through ``Pylock.from_dict`` doubles as a
    spec-conformance check: anything we emit that ``packaging`` rejects
    surfaces as a ``PylockValidationError`` here instead of in production.
    """
    rendered = _render(doc)
    return Pylock.from_dict(tomllib.load(BytesIO(rendered)))


def test_minimal_document_round_trips_through_packaging() -> None:
    doc = Pylock(
        lock_version=Version("1.0"),
        created_by="pip-tools",
        requires_python=SpecifierSet(">=3.9"),
        packages=[
            Package(
                name=canonicalize_name("typing-extensions"),
                version=Version("4.10.0"),
                index="https://pypi.org/simple",
                sdist=PackageSdist(
                    name="typing_extensions-4.10.0.tar.gz",
                    url="https://example.com/typing_extensions-4.10.0.tar.gz",
                    hashes={"sha256": "a" * 64},
                ),
            ),
        ],
    )
    reparsed = _round_trip(doc)
    assert reparsed.created_by == "pip-tools"
    assert reparsed.requires_python == SpecifierSet(">=3.9")
    assert len(reparsed.packages) == 1
    package = reparsed.packages[0]
    assert package.name == "typing-extensions"
    assert package.version == Version("4.10.0")
    assert package.index == "https://pypi.org/simple"


def test_full_index_package_round_trip() -> None:
    upload_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    doc = Pylock(
        lock_version=Version("1.0"),
        created_by="pip-tools",
        packages=[
            Package(
                name=canonicalize_name("anyio"),
                version=Version("3.7.0"),
                index="https://pypi.org/simple",
                dependencies=[{"name": "idna"}, {"name": "sniffio"}],
                sdist=PackageSdist(
                    name="anyio-3.7.0.tar.gz",
                    url="https://example.com/anyio-3.7.0.tar.gz",
                    hashes={"sha256": "a" * 64},
                    size=142737,
                    upload_time=upload_time,
                ),
                wheels=[
                    PackageWheel(
                        name="anyio-3.7.0-py3-none-any.whl",
                        url="https://example.com/anyio-3.7.0-py3-none-any.whl",
                        hashes={"sha256": "b" * 64},
                        size=80873,
                        upload_time=upload_time,
                    ),
                ],
            ),
        ],
    )
    reparsed = _round_trip(doc)
    package = reparsed.packages[0]
    assert package.dependencies is not None
    assert [d["name"] for d in package.dependencies] == ["idna", "sniffio"]
    assert package.sdist is not None
    assert package.sdist.size == 142737
    assert package.wheels is not None
    assert package.wheels[0].upload_time == upload_time


def test_vcs_directory_archive_packages_round_trip() -> None:
    sha = "a" * 40
    doc = Pylock(
        lock_version=Version("1.0"),
        created_by="pip-tools",
        packages=[
            Package(
                name=canonicalize_name("my-vcs-pkg"),
                vcs=PackageVcs(
                    type="git",
                    url="https://example.com/repo.git",
                    commit_id=sha,
                ),
            ),
            Package(
                name=canonicalize_name("my-dir-pkg"),
                directory=PackageDirectory(path="/tmp/pkg", editable=True),
            ),
            Package(
                name=canonicalize_name("my-archive-pkg"),
                archive=PackageArchive(
                    url="https://example.com/pkg-1.0.tar.gz",
                    hashes={"sha256": "b" * 64},
                ),
            ),
        ],
    )
    reparsed = _round_trip(doc)
    by_name = {p.name: p for p in reparsed.packages}
    vcs_package = by_name[canonicalize_name("my-vcs-pkg")]
    assert vcs_package.vcs is not None
    assert vcs_package.vcs.commit_id == sha
    dir_package = by_name[canonicalize_name("my-dir-pkg")]
    assert dir_package.directory is not None
    assert dir_package.directory.editable is True
    archive_package = by_name[canonicalize_name("my-archive-pkg")]
    assert archive_package.archive is not None
    assert archive_package.archive.url is not None
    assert archive_package.archive.url.endswith("pkg-1.0.tar.gz")


def test_tool_block_passes_through() -> None:
    doc = Pylock(
        lock_version=Version("1.0"),
        created_by="pip-tools",
        packages=[],
        tool={"pip-tools": {"version": "0.1.0", "command": ["pip-lock"]}},
    )
    reparsed = _round_trip(doc)
    assert reparsed.tool is not None
    pip_tools = reparsed.tool["pip-tools"]
    assert pip_tools["version"] == "0.1.0"
    assert pip_tools["command"] == ["pip-lock"]
