from __future__ import annotations

import pytest

from piptools.exceptions import PipToolsError

from .conftest import FULL_SHA, PylockPackageFactory, RequirementFactory


def test_build_pylock_package_vcs(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="my-lib",
        version="0.1.0",
        link_url=f"git+https://github.com/user/repo@{FULL_SHA}#egg=my-lib",
        is_vcs=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.name == "my-lib"
    assert pkg.version is None
    assert pkg.vcs is not None
    assert pkg.vcs.type == "git"
    assert pkg.vcs.commit_id == FULL_SHA
    assert "github.com/user/repo" in (pkg.vcs.url or "")
    assert pkg.vcs.requested_revision is None


@pytest.mark.parametrize(
    ("scheme_prefix", "host_path", "revision", "expected_type", "expected_commit"),
    (
        pytest.param(
            "git+",
            "https://example.com/r.git",
            FULL_SHA,
            "git",
            FULL_SHA,
            id="git",
        ),
        pytest.param(
            "hg+",
            "https://example.com/r",
            FULL_SHA,
            "hg",
            FULL_SHA,
            id="hg",
        ),
        pytest.param(
            "svn+",
            "https://example.com/r",
            "12345",
            "svn",
            "12345",
            id="svn",
        ),
        pytest.param(
            "bzr+",
            "https://example.com/r",
            # Bazaar revision-ids carry ``@``, which collides with pip's
            # ``url@rev`` split; users pin to the trailing hash form.
            # pip-tools rejects pure-numeric revnos (mutable per-branch)
            # and accepts anything else.
            "20100308131600-abcd1234",
            "bzr",
            "20100308131600-abcd1234",
            id="bzr-revision-id",
        ),
        pytest.param(
            "",
            "https://example.com/r",
            FULL_SHA,
            "git",
            FULL_SHA,
            id="unknown-scheme-falls-back-to-git",
        ),
    ),
)
def test_build_pylock_package_vcs_type_per_scheme(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    scheme_prefix: str,
    host_path: str,
    revision: str,
    expected_type: str,
    expected_commit: str,
) -> None:
    # PEP 751's commit-id rule requires the registered VCS's hash form
    # when one exists but does not impose git's shape on backends with
    # their own conventions; svn integers and bzr arbitrary revision IDs
    # both belong.
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url=f"{scheme_prefix}{host_path}@{revision}",
        is_vcs=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.vcs is not None
    assert pkg.vcs.type == expected_type
    assert pkg.vcs.url == host_path
    assert pkg.vcs.commit_id == expected_commit


def test_build_pylock_package_git_uppercase_sha_is_normalised(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    # An ``ABCDEF...`` SHA is a SHA; rejecting it because of case forced
    # users to lowercase by hand. Accept either case and normalize to
    # lower so the on-disk lockfile is byte-stable across input formats.
    requirement = make_requirement(
        name="lib",
        version="0.1.0",
        link_url=f"git+https://github.com/user/repo@{FULL_SHA.upper()}",
        is_vcs=True,
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.vcs is not None
    assert pkg.vcs.commit_id == FULL_SHA


@pytest.mark.parametrize(
    ("scheme_prefix", "revision"),
    (
        pytest.param("git+", None, id="git-no-revision"),
        pytest.param("git+", "main", id="git-branch"),
        pytest.param("git+", "v1.2.3", id="git-tag"),
        pytest.param("git+", "a1b2c3d", id="git-short-sha"),
        pytest.param("git+", "a" * 39, id="git-too-short"),
        pytest.param("git+", "a" * 41, id="git-too-long"),
        pytest.param("git+", "g" * 40, id="git-non-hex"),
        pytest.param("hg+", "tip", id="hg-named-rev"),
        pytest.param("svn+", None, id="svn-no-revision"),
        pytest.param("svn+", "trunk", id="svn-non-integer"),
        pytest.param("svn+", "abc123", id="svn-hex-not-integer"),
        pytest.param("svn+", "HEAD", id="svn-head"),
        pytest.param("svn+", "BASE", id="svn-base"),
        pytest.param("svn+", "PREV", id="svn-prev"),
        pytest.param("svn+", "{2024-01-01}", id="svn-date"),
        pytest.param("hg+", "feature-branch", id="hg-branch-name"),
        pytest.param("hg+", "v1.0", id="hg-tag-name"),
        pytest.param("hg+", "@", id="hg-bookmark"),
        pytest.param("bzr+", None, id="bzr-no-revision"),
        pytest.param("bzr+", "revno:42", id="bzr-revno-prefix"),
        pytest.param("bzr+", "tag:v1.0", id="bzr-tag-prefix"),
        pytest.param("bzr+", "last:1", id="bzr-last-prefix"),
        pytest.param("bzr+", "branch:lp:repo", id="bzr-branch-prefix"),
        pytest.param("bzr+", "before:20100308131600-abc", id="bzr-before-prefix"),
    ),
)
def test_build_pylock_package_vcs_rejects_non_pinned_revision(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    scheme_prefix: str,
    revision: str | None,
) -> None:
    # Per-VCS validation refuses inputs the chosen backend cannot prove
    # immutable. PEP 751 forbids emitting an empty ``commit-id``, so the
    # sound action is to raise.
    suffix = f"@{revision}" if revision is not None else ""
    requirement = make_requirement(
        name="lib",
        version="0.1.0",
        link_url=f"{scheme_prefix}https://example.com/repo{suffix}",
        is_vcs=True,
    )
    with pytest.raises(PipToolsError, match="commit-id"):
        make_pkg(
            requirement,
        )


@pytest.mark.parametrize(
    ("link_url", "expected_url"),
    (
        pytest.param(
            f"git+ssh://git@github.com/user/repo.git@{FULL_SHA}",
            "ssh://****@github.com/user/repo.git",
            id="ssh-userinfo-with-rev",
        ),
        pytest.param(
            f"git+https://user:token@example.com/repo@{FULL_SHA}",
            "https://user:****@example.com/repo",
            id="https-userinfo-with-rev",
        ),
    ),
)
def test_build_pylock_package_vcs_userinfo_does_not_confuse_revision_split(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
    link_url: str,
    expected_url: str,
) -> None:
    requirement = make_requirement(
        name="lib", version="1.0", link_url=link_url, is_vcs=True
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.vcs is not None
    assert pkg.vcs.url == expected_url
    assert pkg.vcs.commit_id == FULL_SHA
    assert pkg.vcs.requested_revision is None


def test_build_pylock_package_vcs_carries_subdirectory(
    make_requirement: RequirementFactory,
    make_pkg: PylockPackageFactory,
) -> None:
    requirement = make_requirement(
        name="lib",
        version="1.0",
        link_url=f"git+https://github.com/u/r.git@{FULL_SHA}#subdirectory=packages/lib",
        is_vcs=True,
        subdirectory_fragment="packages/lib",
    )
    pkg = make_pkg(
        requirement,
    )
    assert pkg.vcs is not None
    assert pkg.vcs.subdirectory == "packages/lib"
