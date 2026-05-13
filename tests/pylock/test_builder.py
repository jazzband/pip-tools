from __future__ import annotations

import typing as _t

import pytest
from packaging.pylock import Package, PackageSdist, Pylock
from packaging.utils import canonicalize_name
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.exceptions import PipToolsError
from piptools.pylock._inputs import (
    LockInputs,
    LockSelection,
    LockTargets,
    ResolverOptions,
    ToolMetadataOptions,
    WorkerSpec,
)
from piptools.pylock._merge import ResolvedEntry
from piptools.pylock.builder import (
    _build_package_dependencies,
    _index_for_entry,
    build_pylock_document,
)
from piptools.pylock.platforms import PLATFORM_ENVIRONMENTS, build_target_environments
from piptools.repositories import PyPIRepository

_STUB_SDIST = PackageSdist(
    url="https://example.com/x.tar.gz", name="x.tar.gz", hashes={"sha256": "x"}
)


class _IndexIreqFactory(_t.Protocol):
    def __call__(
        self,
        name: str,
        version: str,
        *,
        link_url: str | None = ...,
        comes_from: str | None = ...,
    ) -> InstallRequirement: ...


@pytest.fixture
def make_index_ireq(mocker: MockerFixture) -> _IndexIreqFactory:
    def _factory(
        name: str,
        version: str,
        *,
        link_url: str | None = None,
        comes_from: str | None = None,
    ) -> InstallRequirement:
        link = (
            mocker.MagicMock(url=link_url, comes_from=comes_from)
            if link_url is not None
            else None
        )
        ireq = mocker.create_autospec(
            InstallRequirement,
            instance=True,
            editable=False,
            original_link=None,
            link=link,
        )
        # ``name=`` as a constructor kwarg would set MagicMock's display name, not
        # the attribute the code under test reads.
        ireq.name = name
        ireq.specifier = mocker.MagicMock(
            __iter__=lambda _self: iter([mocker.MagicMock(version=version)])
        )
        return ireq

    return _factory


_DEFAULT_TARGETS = LockTargets(
    target_envs=build_target_environments(("linux-x86_64", "windows-amd64"), ("3.12",)),
    platforms=(),
    python_versions=(),
    no_universal=False,
    discover_envs=False,
)
_DEFAULT_SELECTION = LockSelection(
    extras=(), all_extras=False, groups=(), all_groups=False
)
_DEFAULT_OPTIONS = ResolverOptions(
    prereleases=False,
    rebuild=False,
    allow_unsafe=False,
    unsafe_packages=frozenset(),
    max_rounds=10,
    cache_dir="/tmp",
    pre=False,
)
_DEFAULT_METADATA = ToolMetadataOptions(no_metadata=True, skip_metadata_fields=())


def _build_document(
    mocker: MockerFixture,
    *,
    merged: dict[str, list[ResolvedEntry]],
    forward_deps: dict[str, set[str]],
    files_by_ireq: dict[int, list[PackageSdist]] | None = None,
    requires_python_by_ireq: dict[int, str | None] | None = None,
    index_urls: tuple[str, ...] = (),
    selection: LockSelection = _DEFAULT_SELECTION,
    targets: LockTargets = _DEFAULT_TARGETS,
    options: ResolverOptions = _DEFAULT_OPTIONS,
    metadata: ToolMetadataOptions = _DEFAULT_METADATA,
) -> Pylock:
    files = files_by_ireq or {}
    reqpy = requires_python_by_ireq or {}
    mocker.patch("piptools.pylock.builder.resolve", return_value=(merged, forward_deps))
    repository = mocker.create_autospec(PyPIRepository, instance=True)
    repository.get_distribution_files.side_effect = lambda req: files.get(id(req), [])
    repository.get_requires_python.side_effect = lambda req: reqpy.get(id(req))
    repository.allow_all_wheels.return_value.__enter__ = lambda self: None
    repository.allow_all_wheels.return_value.__exit__ = lambda self, *a: False
    repository.finder.index_urls = list(index_urls)
    mocker.patch(
        "piptools.pylock.builder.ensure_marker_disjointness", return_value=None
    )
    mocker.patch("piptools.pylock.builder.extract_requires_python", return_value=None)
    return build_pylock_document(
        src_files=(),
        repository=repository,
        inputs=LockInputs(raw_constraints=[], conflicts=[], group_constraints={}),
        selection=selection,
        targets=targets,
        options=options,
        workers=WorkerSpec(jobs=1, pip_args=()),
        metadata=metadata,
    )


def _entries_by_version(doc: Pylock, name: str) -> dict[str | None, Package]:
    return {
        str(pkg.version) if pkg.version is not None else None: pkg
        for pkg in doc.packages
        if pkg.name == name
    }


def test_top_level_environments_use_full_version_when_patch_supplied(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # When the user passes ``--python-version 3.12.5``, per-package markers
    # already use ``python_full_version``; the top-level ``environments``
    # clause must mirror that, otherwise a 3.12.0 installer passes the
    # top-level check then fails every per-package check.
    parent_ireq = make_index_ireq("pkg", "1.0")
    target_envs = build_target_environments(("linux-x86_64",), ("3.12.5",))
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=parent_ireq,
                    version="1.0",
                    environments={"linux-x86_64-3.12.5-cpython"},
                )
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(parent_ireq): [_STUB_SDIST]},
        targets=LockTargets(
            target_envs=target_envs,
            platforms=("linux-x86_64",),
            python_versions=("3.12.5",),
            no_universal=False,
            discover_envs=False,
        ),
    )
    assert doc.environments is not None
    assert any(
        'python_full_version == "3.12.5"' in str(env) for env in doc.environments
    )


def test_index_field_uses_candidate_host_for_extra_index(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # Defaulting every index-source package to ``finder.index_urls[0]`` leaks
    # internal-index resolutions back to public PyPI when the lockfile is
    # honored later; installers may try to fetch private packages from PyPI.
    public_url = "https://pypi.org/simple"
    private_url = "https://internal.example.com/simple"
    public_pkg = make_index_ireq(
        "public",
        "1.0",
        link_url="https://files.pythonhosted.org/p/p-1.0.whl",
        comes_from="https://pypi.org/simple/public/",
    )
    private_pkg = make_index_ireq(
        "private",
        "1.0",
        link_url="https://internal.example.com/p/private-1.0.whl",
        comes_from="https://internal.example.com/simple/private/",
    )
    sdist = _STUB_SDIST
    merged = {
        "public": [
            ResolvedEntry(
                requirement=public_pkg,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ],
        "private": [
            ResolvedEntry(
                requirement=private_pkg,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"public": set(), "private": set()},
        files_by_ireq={id(public_pkg): [sdist], id(private_pkg): [sdist]},
        index_urls=(public_url, private_url),
    )
    by_name = {pkg.name: pkg for pkg in doc.packages}
    assert by_name[canonicalize_name("public")].index == public_url
    assert by_name[canonicalize_name("private")].index == private_url


def test_index_field_omitted_when_no_host_match(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # ``--find-links`` and similar configurations can serve a package from a
    # host that no configured index covers; emitting the wrong index would
    # mislead the installer, so omit it.
    findlinks_pkg = make_index_ireq(
        "fl-pkg",
        "1.0",
        link_url="https://files.example.org/fl-pkg-1.0.whl",
        comes_from="https://files.example.org/find-links/",
    )
    sdist = _STUB_SDIST
    merged = {
        "fl-pkg": [
            ResolvedEntry(
                requirement=findlinks_pkg,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ]
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"fl-pkg": set()},
        files_by_ireq={id(findlinks_pkg): [sdist]},
        index_urls=("https://pypi.org/simple",),
    )
    pkg = next(p for p in doc.packages if p.name == canonicalize_name("fl-pkg"))
    assert pkg.index is None


def test_multi_version_entries_get_per_release_dist_files(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # Keying dist-file lookup by name alone copied ``entries[0]``'s files onto
    # every release of the same package; so ``2.0`` would publish ``1.0``'s
    # wheels, exactly the case the cohort/partition machinery exists to enable.
    ireq_v1 = make_index_ireq("pkg", "1.0")
    ireq_v2 = make_index_ireq("pkg", "2.0")
    merged = {
        "pkg": [
            ResolvedEntry(
                requirement=ireq_v1,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
                marker="sys_platform == 'linux'",
            ),
            ResolvedEntry(
                requirement=ireq_v2,
                version="2.0",
                environments={"windows-amd64-3.12-cpython"},
                marker="sys_platform == 'win32'",
            ),
        ]
    }
    sdist_v1 = PackageSdist(
        url="https://example.com/pkg-1.0.tar.gz",
        name="pkg-1.0.tar.gz",
        hashes={"sha256": "v1"},
    )
    sdist_v2 = PackageSdist(
        url="https://example.com/pkg-2.0.tar.gz",
        name="pkg-2.0.tar.gz",
        hashes={"sha256": "v2"},
    )
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq_v1): [sdist_v1], id(ireq_v2): [sdist_v2]},
        requires_python_by_ireq={id(ireq_v1): ">=3.9", id(ireq_v2): ">=3.12"},
    )

    pkgs = _entries_by_version(doc, "pkg")
    assert pkgs["1.0"].sdist == sdist_v1
    assert pkgs["2.0"].sdist == sdist_v2
    assert pkgs["1.0"].requires_python == ">=3.9"
    assert pkgs["2.0"].requires_python == ">=3.12"


def test_dependency_reference_disambiguates_multi_version_target(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # A bare ``{name = "child"}`` reference is ambiguous when ``child`` has two
    # ``[[packages]]`` entries; the spec requires the minimum disambiguating
    # info so the installer can pick a candidate deterministically.
    parent_ireq = make_index_ireq("parent", "1.0")
    child_v1 = make_index_ireq("child", "1.0")
    child_v2 = make_index_ireq("child", "2.0")
    sdist = _STUB_SDIST
    files_by_ireq = {
        id(parent_ireq): [sdist],
        id(child_v1): [sdist],
        id(child_v2): [sdist],
    }
    merged = {
        "parent": [
            ResolvedEntry(
                requirement=parent_ireq,
                version="1.0",
                environments={
                    "linux-x86_64-3.12-cpython",
                    "windows-amd64-3.12-cpython",
                },
                marker=None,
            )
        ],
        "child": [
            ResolvedEntry(
                requirement=child_v1,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
                marker="sys_platform == 'linux'",
            ),
            ResolvedEntry(
                requirement=child_v2,
                version="2.0",
                environments={"windows-amd64-3.12-cpython"},
                marker="sys_platform == 'win32'",
            ),
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"parent": {"child"}, "child": set()},
        files_by_ireq=files_by_ireq,
    )
    parent_pkg = next(p for p in doc.packages if p.name == canonicalize_name("parent"))
    assert parent_pkg.dependencies is not None
    child_refs = [
        (d["name"], d.get("version"))
        for d in parent_pkg.dependencies
        if d["name"] == "child"
    ]
    assert sorted(child_refs) == [("child", "1.0"), ("child", "2.0")]


def test_dependency_reference_falls_back_when_no_env_overlap(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # Parent depends on ``child`` but has no overlap with any child entry's
    # ``environments``; bail out to the name-only reference rather than emit a
    # spec-invalid empty-version field.
    parent_ireq = make_index_ireq("parent", "1.0")
    child_v1 = make_index_ireq("child", "1.0")
    child_v2 = make_index_ireq("child", "2.0")
    sdist = _STUB_SDIST
    merged = {
        "parent": [
            ResolvedEntry(
                requirement=parent_ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ],
        "child": [
            ResolvedEntry(
                requirement=child_v1,
                version="1.0",
                environments={"windows-amd64-3.12-cpython"},
            ),
            ResolvedEntry(
                requirement=child_v2,
                version="2.0",
                environments={"macos-arm64-3.12-cpython"},
            ),
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"parent": {"child"}, "child": set()},
        files_by_ireq={
            id(parent_ireq): [sdist],
            id(child_v1): [sdist],
            id(child_v2): [sdist],
        },
    )
    parent_pkg = next(p for p in doc.packages if p.name == canonicalize_name("parent"))
    assert parent_pkg.dependencies is not None
    child_refs = [d for d in parent_pkg.dependencies if d["name"] == "child"]
    assert len(child_refs) == 1
    assert child_refs[0].get("version") is None


def test_dependency_reference_raises_for_unidisambiguable_vcs_targets(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # PEP 751 lets ``vcs``/``directory`` entries omit ``version`` and pip-tools
    # has no other minimal-and-stable field to disambiguate two same-name VCS
    # variants; emitting bare ``{name = "X"}`` for each would produce a dep
    # list that identifies zero specific candidate. Surface a clear error so
    # the user collapses the inputs themselves rather than shipping an
    # unusable lockfile.
    parent_ireq = make_index_ireq("parent", "1.0")
    sdist = _STUB_SDIST
    full_sha = "a" * 40
    vcs_link = mocker.MagicMock(
        url=f"git+https://example.com/repo@{full_sha}",
        url_without_fragment=f"git+https://example.com/repo@{full_sha}",
        scheme="git+https",
        is_vcs=True,
        is_file=False,
        subdirectory_fragment=None,
    )
    vcs_link.is_existing_dir.return_value = False
    child_vcs1 = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        original_link=vcs_link,
        link=vcs_link,
    )
    child_vcs1.name = "child"
    child_vcs2 = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        original_link=vcs_link,
        link=vcs_link,
    )
    child_vcs2.name = "child"
    merged = {
        "parent": [
            ResolvedEntry(
                requirement=parent_ireq,
                version="1.0",
                environments={
                    "linux-x86_64-3.12-cpython",
                    "windows-amd64-3.12-cpython",
                },
            )
        ],
        "child": [
            ResolvedEntry(
                requirement=child_vcs1,
                version="",
                environments={
                    "linux-x86_64-3.12-cpython",
                    "windows-amd64-3.12-cpython",
                },
            ),
            ResolvedEntry(
                requirement=child_vcs2,
                version="",
                environments={
                    "linux-x86_64-3.12-cpython",
                    "windows-amd64-3.12-cpython",
                },
            ),
        ],
    }
    with pytest.raises(PipToolsError, match="multiple vcs/directory variants"):
        _build_document(
            mocker,
            merged=merged,
            forward_deps={"parent": {"child"}, "child": set()},
            files_by_ireq={id(parent_ireq): [sdist]},
        )


def test_dependency_reference_omits_version_for_single_target(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # PEP 751 calls for the *minimum* disambiguating info; when the target has
    # one entry there is nothing to disambiguate, so adding ``version`` would be
    # gratuitous churn against uv's output for the common case.
    parent_ireq = make_index_ireq("parent", "1.0")
    child_ireq = make_index_ireq("child", "1.0")
    sdist = _STUB_SDIST
    merged = {
        "parent": [
            ResolvedEntry(
                requirement=parent_ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ],
        "child": [
            ResolvedEntry(
                requirement=child_ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            )
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"parent": {"child"}, "child": set()},
        files_by_ireq={id(parent_ireq): [sdist], id(child_ireq): [sdist]},
    )
    parent_pkg = next(p for p in doc.packages if p.name == canonicalize_name("parent"))
    assert parent_pkg.dependencies is not None
    child_refs = [d for d in parent_pkg.dependencies if d["name"] == "child"]
    assert len(child_refs) == 1
    assert child_refs[0].get("version") is None


def test_index_field_strips_basic_auth_credentials(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # ``--index-url https://user:token@private/simple/`` would otherwise pin the
    # token verbatim into ``packages[].index``. Strip userinfo so the lockfile
    # is safe to commit while still naming the right host for an installer that
    # resupplies the credential.
    ireq = make_index_ireq(
        "pkg",
        "1.0",
        link_url="https://files.private/pkg-1.0.whl",
        comes_from="https://user:secret@private/simple/pkg/",
    )
    sdist = PackageSdist(
        url="https://example.com/pkg.tar.gz",
        name="pkg-1.0.tar.gz",
        hashes={"sha256": "x"},
    )
    merged = {
        "pkg": [
            ResolvedEntry(
                requirement=ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            ),
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [sdist]},
        index_urls=("https://user:secret@private/simple",),
    )
    pkg = next(p for p in doc.packages if p.name == canonicalize_name("pkg"))
    assert pkg.index is not None
    assert "secret" not in pkg.index
    assert pkg.index.endswith("@private/simple")


def test_index_field_omitted_when_link_is_missing(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # When ``link`` is unset we cannot prove which index served the candidate;
    # guessing ``index_urls[0]`` would name a public index for a private-source
    # package (or vice versa). PEP 751 treats absent ``index`` as "don't
    # constrain installer fallback", which is the safe behavior.
    ireq = make_index_ireq("pkg", "1.0", link_url=None)
    sdist = PackageSdist(
        url="https://example.com/pkg.tar.gz",
        name="pkg-1.0.tar.gz",
        hashes={"sha256": "x"},
    )
    merged = {
        "pkg": [
            ResolvedEntry(
                requirement=ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            ),
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [sdist]},
        index_urls=("https://pypi.org/simple",),
    )
    pkg = next(p for p in doc.packages if p.name == canonicalize_name("pkg"))
    assert pkg.index is None


def test_index_field_falls_back_to_netloc_match(
    make_index_ireq: _IndexIreqFactory, mocker: MockerFixture
) -> None:
    # Indexes that don't surface a ``comes_from`` (e.g. devpi, simple mirrors
    # that strip the trailing slash) still tag candidates with a ``link.url``
    # whose host matches the configured index; netloc-equality is the last
    # resort before giving up and emitting no ``index``.
    ireq = make_index_ireq(
        "pkg",
        "1.0",
        link_url="https://mirror.example.com/files/pkg-1.0.whl",
        comes_from=None,
    )
    sdist = _STUB_SDIST
    merged = {
        "pkg": [
            ResolvedEntry(
                requirement=ireq,
                version="1.0",
                environments={"linux-x86_64-3.12-cpython"},
            ),
        ],
    }
    doc = _build_document(
        mocker,
        merged=merged,
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [sdist]},
        index_urls=("https://mirror.example.com/simple",),
    )
    pkg = next(p for p in doc.packages if p.name == canonicalize_name("pkg"))
    assert pkg.index == "https://mirror.example.com/simple"


def test_tool_metadata_includes_resolver_options(
    make_index_ireq: _IndexIreqFactory, mocker: MockerFixture
) -> None:
    # The ``[tool.pip-tools]`` block surfaces the resolver options the user
    # picked so the lockfile is reproducible without inspecting the CLI;
    # every non-default flag (pre, allow_unsafe, rebuild, all_*) must round-trip.
    ireq = make_index_ireq("pkg", "1.0")
    target_envs = build_target_environments(
        ("linux-x86_64", "windows-amd64"), ("3.12",)
    )
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=ireq,
                    version="1.0",
                    environments={"linux-x86_64-3.12-cpython"},
                ),
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [_STUB_SDIST]},
        selection=LockSelection(
            extras=("e1",), all_extras=True, groups=("g1",), all_groups=True
        ),
        targets=LockTargets(
            target_envs=target_envs,
            platforms=("linux-x86_64",),
            python_versions=("3.12",),
            no_universal=True,
            discover_envs=False,
        ),
        options=ResolverOptions(
            prereleases=True,
            rebuild=True,
            allow_unsafe=True,
            unsafe_packages=frozenset(),
            max_rounds=10,
            cache_dir="/tmp",
            pre=True,
        ),
        metadata=ToolMetadataOptions(no_metadata=False, skip_metadata_fields=()),
    )
    assert doc.tool is not None
    pip_tools = doc.tool["pip-tools"]
    assert pip_tools["pre"] is True
    assert pip_tools["allow-unsafe"] is True
    assert pip_tools["rebuild"] is True
    assert pip_tools["all-extras"] is True
    assert pip_tools["all-groups"] is True
    assert pip_tools["no-universal"] is True
    assert pip_tools["platforms"] == ["linux-x86_64"]
    assert pip_tools["python-versions"] == ["3.12"]
    assert pip_tools["extras"] == ["e1"]
    assert pip_tools["groups"] == ["g1"]


@pytest.mark.parametrize(
    ("default_groups", "expected"),
    (
        pytest.param((), None, id="absent-when-unset"),
        pytest.param(("test",), ["test"], id="single"),
        pytest.param(
            ("Test", "test-extra"), ["test", "test-extra"], id="canonicalised"
        ),
    ),
)
def test_pylock_default_groups_field(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
    default_groups: tuple[str, ...],
    expected: list[str] | None,
) -> None:
    # ``Pylock.default_groups`` echoes ``[dependency-groups].default-groups``
    # so a downstream installer picks the right set when ``--group`` is
    # omitted; the field is absent when the project declares no defaults.
    parent_ireq = make_index_ireq("pkg", "1.0")
    sdist = _STUB_SDIST
    target_envs = build_target_environments(("linux-x86_64",), ("3.12",))
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=parent_ireq,
                    version="1.0",
                    environments=set(target_envs),
                )
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(parent_ireq): [sdist]},
        selection=LockSelection(
            extras=(),
            all_extras=False,
            groups=(),
            all_groups=False,
            default_groups=default_groups,
        ),
        targets=LockTargets(
            target_envs=target_envs,
            platforms=("linux-x86_64",),
            python_versions=("3.12",),
            no_universal=False,
            discover_envs=False,
        ),
    )
    assert doc.default_groups == expected


def test_top_level_environments_include_implementation_clause_when_multiple(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # Multi-implementation locks need the impl clause on every top-level
    # entry so a PyPy installer doesn't pick the CPython entry's marker.
    parent_ireq = make_index_ireq("pkg", "1.0")
    target_envs = build_target_environments(
        ("linux-x86_64",), ("3.12",), ("cpython", "pypy")
    )
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=parent_ireq,
                    version="1.0",
                    environments=set(target_envs),
                )
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(parent_ireq): [_STUB_SDIST]},
        targets=LockTargets(
            target_envs=target_envs,
            platforms=("linux-x86_64",),
            python_versions=("3.12",),
            implementations=("cpython", "pypy"),
            no_universal=False,
            discover_envs=False,
        ),
    )
    assert doc.environments is not None
    rendered = [str(env) for env in doc.environments]
    assert any('implementation_name == "cpython"' in r for r in rendered)
    assert any('implementation_name == "pypy"' in r for r in rendered)


def test_top_level_environment_omits_platform_marker_when_universe_covered(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # When the cohort covers every supported platform for a given python
    # version, the top-level entry collapses to a bare python_version clause
    # rather than ``(any-platform-or-clause) and python_version == 'X.Y'``.
    target_envs = build_target_environments(
        tuple(PLATFORM_ENVIRONMENTS.keys()), ("3.12",)
    )
    ireq = make_index_ireq("pkg", "1.0")
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=ireq,
                    version="1.0",
                    environments=set(target_envs),
                ),
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [_STUB_SDIST]},
        targets=LockTargets(
            target_envs=target_envs,
            platforms=tuple(PLATFORM_ENVIRONMENTS.keys()),
            python_versions=("3.12",),
            no_universal=False,
            discover_envs=False,
        ),
    )
    assert doc.environments is not None
    assert all("python_version" in str(env) for env in doc.environments)
    assert all(" and " not in str(env) for env in doc.environments)


def test_index_for_entry_returns_none_when_no_configured_index_matches(
    mocker: MockerFixture,
) -> None:
    # VCS / archive / find-links artifacts whose URL host does not match any
    # configured ``--index-url`` get no attribution; the helper relies purely
    # on host/path matching so source type does not gate the decision.
    link = mocker.MagicMock(
        name="vcs_link",
        url="git+https://github.com/x/y.git@deadbeef",
        comes_from=None,
        is_vcs=True,
        is_file=False,
    )
    ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        link=link,
        original_link=link,
    )
    entry = ResolvedEntry(
        requirement=ireq, version="1.0", environments={"linux-x86_64-3.12-cpython"}
    )
    assert _index_for_entry(entry, ("https://pypi.org/simple",)) is None


def test_index_for_entry_attributes_find_links_hosted_on_index(
    mocker: MockerFixture,
) -> None:
    # A ``--find-links`` artifact whose URL host matches a configured
    # ``--index-url`` is attributable; pip-tools must not gate attribution on
    # the installer-internal source-type classification because PEP 751
    # ``packages.index`` is purely about the URL.
    link = mocker.MagicMock(
        name="find_links_link",
        url="https://internal.corp/wheels/pkg-1.0-py3-none-any.whl",
        comes_from="https://internal.corp/wheels/",
        is_vcs=False,
        is_file=False,
    )
    ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        link=link,
        original_link=link,
    )
    entry = ResolvedEntry(
        requirement=ireq, version="1.0", environments={"linux-x86_64-3.12-cpython"}
    )
    assert (
        _index_for_entry(entry, ("https://internal.corp/wheels",))
        == "https://internal.corp/wheels"
    )


def test_index_for_entry_returns_none_when_link_url_is_not_str(
    mocker: MockerFixture,
) -> None:
    # An older pip release exposed ``Link.url`` as a property that could
    # raise; today it is always a ``str`` but the helper guards the type so
    # a future regression cannot crash the whole lock pipeline.
    link = mocker.MagicMock(comes_from=None, url=None)
    ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        link=link,
        original_link=None,
    )
    entry = ResolvedEntry(
        requirement=ireq, version="1.0", environments={"linux-x86_64-3.12-cpython"}
    )
    assert _index_for_entry(entry, ("https://pypi.org/simple",)) is None


def test_top_level_extras_and_groups_normalize_and_dedupe(
    make_index_ireq: _IndexIreqFactory,
    mocker: MockerFixture,
) -> None:
    # PEP 503 / PEP 735 require ``Foo-bar`` and ``foo_bar`` to canonicalize to
    # the same key. Without dedup-after-canonicalise the lockfile carries
    # duplicate ``foo-bar`` entries; without canonicalise-at-all, groups
    # violate PEP 735.
    ireq = make_index_ireq("pkg", "1.0")
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=ireq,
                    version="1.0",
                    environments={"linux-x86_64-3.12-cpython"},
                ),
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [_STUB_SDIST]},
        selection=LockSelection(
            extras=("Foo-Bar", "foo_bar"),
            all_extras=False,
            groups=("Dev", "dev"),
            all_groups=False,
        ),
    )
    assert doc.extras == ["foo-bar"]
    assert doc.dependency_groups == ["dev"]


def test_tool_metadata_skip_fields_drops_each_option(
    make_index_ireq: _IndexIreqFactory, mocker: MockerFixture
) -> None:
    # ``--skip-metadata-fields`` lets the user blank out individual entries;
    # each guarded ``if opts.X is not None`` branch must skip cleanly when
    # the field was opted out of (vs. still emitting a default value).
    ireq = make_index_ireq("pkg", "1.0")
    target_envs = build_target_environments(
        ("linux-x86_64", "windows-amd64"), ("3.12",)
    )
    skip_fields = (
        "platforms",
        "python-versions",
        "target-environments",
        "no-universal",
        "extras",
        "all-extras",
        "groups",
        "all-groups",
        "pre",
        "allow-unsafe",
        "rebuild",
        "pip-version",
        "command",
        "generated-at",
    )
    doc = _build_document(
        mocker,
        merged={
            "pkg": [
                ResolvedEntry(
                    requirement=ireq,
                    version="1.0",
                    environments={"linux-x86_64-3.12-cpython"},
                ),
            ],
        },
        forward_deps={"pkg": set()},
        files_by_ireq={id(ireq): [_STUB_SDIST]},
        targets=LockTargets(
            target_envs=target_envs,
            platforms=("linux-x86_64",),
            python_versions=("3.12",),
            no_universal=False,
            discover_envs=False,
        ),
        metadata=ToolMetadataOptions(
            no_metadata=False, skip_metadata_fields=skip_fields
        ),
    )
    assert doc.tool is not None
    pip_tools = doc.tool["pip-tools"]
    for key in skip_fields:
        assert key not in pip_tools, key


def test_build_package_dependencies_emits_marker_for_tied_versions(
    mocker: MockerFixture,
) -> None:
    # When two same-name dep candidates share a version (one for py3.12, one
    # for py3.13), the disambiguator can't distinguish them on version alone
    # ; PEP 751 demands the ``marker`` field be added to each.
    mocker.patch("piptools.pylock.builder.detect_source_type", return_value="index")
    parent_req = mocker.create_autospec(InstallRequirement, instance=True)
    parent_req.name = "parent"
    parent = ResolvedEntry(requirement=parent_req, version="1.0", marker=None)
    a = ResolvedEntry(
        requirement=mocker.create_autospec(InstallRequirement, instance=True),
        version="1.0",
        marker="python_version == '3.12'",
    )
    b = ResolvedEntry(
        requirement=mocker.create_autospec(InstallRequirement, instance=True),
        version="1.0",
        marker="python_version == '3.13'",
    )
    deps = _build_package_dependencies(parent, {"shared"}, {"shared": [a, b]})
    assert len(deps) == 2
    assert all("marker" in d for d in deps)


@pytest.mark.parametrize(
    ("raw_marker", "canonical"),
    (
        pytest.param(
            "python_version=='3.12'",
            'python_version == "3.12"',
            id="whitespace-and-quotes",
        ),
        pytest.param(
            "(python_version  ==  '3.12')",
            'python_version == "3.12"',
            id="redundant-parens",
        ),
    ),
)
def test_build_package_dependencies_canonicalizes_pass_through_markers(
    mocker: MockerFixture, raw_marker: str, canonical: str
) -> None:
    # Pass-through dep markers must reach the dict in the same shape Marker
    # serialises: stable diff across regenerates regardless of input.
    mocker.patch("piptools.pylock.builder.detect_source_type", return_value="index")
    parent_requirement = mocker.create_autospec(InstallRequirement, instance=True)
    parent_requirement.name = "parent"
    parent = ResolvedEntry(requirement=parent_requirement, version="1.0", marker=None)
    py312_entry = ResolvedEntry(
        requirement=mocker.create_autospec(InstallRequirement, instance=True),
        version="1.0",
        marker=raw_marker,
    )
    py313_entry = ResolvedEntry(
        requirement=mocker.create_autospec(InstallRequirement, instance=True),
        version="1.0",
        marker="python_version == '3.13'",
    )
    deps = _build_package_dependencies(
        parent, {"shared"}, {"shared": [py312_entry, py313_entry]}
    )
    rendered_markers = {dep["marker"] for dep in deps}
    assert canonical in rendered_markers


def test_index_for_entry_skips_index_with_mismatched_path(
    mocker: MockerFixture,
) -> None:
    # Two indexes share scheme+netloc; only the one whose path actually
    # prefixes ``comes_from`` may claim the candidate, the other has to be
    # skipped so a same-host neighbour doesn't steal the attribution.
    link = mocker.MagicMock(
        url="https://pypi.org/simple/pkg-1.0.tar.gz",
        comes_from="https://pypi.org/simple/pkg/",
        is_vcs=False,
        is_file=False,
    )
    ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        editable=False,
        link=link,
        original_link=None,
    )
    entry = ResolvedEntry(
        requirement=ireq, version="1.0", environments={"linux-x86_64-3.12-cpython"}
    )
    selected = _index_for_entry(
        entry,
        (
            "https://pypi.org/other/simple/",
            "https://pypi.org/simple/",
        ),
    )
    assert selected == "https://pypi.org/simple/"


def test_build_package_dependencies_omits_version_for_non_vcs_without_version(
    mocker: MockerFixture,
) -> None:
    # An archive/index candidate that lands here without a version (e.g.
    # because pip surfaced an unparsed sdist) must not poison the dep ref
    # with a ``"version": ""`` entry that PEP 751 readers would reject.
    parent_req = mocker.create_autospec(InstallRequirement, instance=True)
    parent_req.name = "parent"
    archive_req = mocker.create_autospec(InstallRequirement, instance=True)
    sibling_req = mocker.create_autospec(InstallRequirement, instance=True)
    type_by_req = {
        id(parent_req): "index",
        id(archive_req): "archive",
        id(sibling_req): "index",
    }
    mocker.patch(
        "piptools.pylock.builder.detect_source_type",
        side_effect=lambda req: type_by_req[id(req)],
    )
    parent = ResolvedEntry(requirement=parent_req, version="1.0", marker=None)
    unversioned = ResolvedEntry(requirement=archive_req, version="", marker=None)
    sibling = ResolvedEntry(requirement=sibling_req, version="2.0", marker=None)
    deps = _build_package_dependencies(
        parent, {"shared"}, {"shared": [unversioned, sibling]}
    )
    by_version = {d.get("version") for d in deps}
    assert by_version == {None, "2.0"}


def test_build_package_dependencies_omits_version_for_vcs_in_mixed_set(
    mocker: MockerFixture,
) -> None:
    # ``vcs``/``directory`` entries have no PEP 440 version; PEP 751 lets the
    # parent's marker disambiguate. When the matching set mixes a vcs entry
    # with an index entry, the vcs reference must omit the ``version`` field
    # so installers don't reject the bare-but-versioned ref.
    parent_req = mocker.create_autospec(InstallRequirement, instance=True)
    parent_req.name = "parent"
    vcs_req = mocker.create_autospec(InstallRequirement, instance=True)
    index_req = mocker.create_autospec(InstallRequirement, instance=True)
    type_by_req = {id(parent_req): "index", id(vcs_req): "vcs", id(index_req): "index"}
    mocker.patch(
        "piptools.pylock.builder.detect_source_type",
        side_effect=lambda req: type_by_req[id(req)],
    )
    parent = ResolvedEntry(requirement=parent_req, version="1.0", marker=None)
    vcs_child = ResolvedEntry(requirement=vcs_req, version="", marker=None)
    index_child = ResolvedEntry(requirement=index_req, version="2.0", marker=None)
    deps = _build_package_dependencies(
        parent, {"shared"}, {"shared": [vcs_child, index_child]}
    )
    by_version = {d.get("version") for d in deps}
    assert by_version == {None, "2.0"}
