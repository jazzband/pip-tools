from __future__ import annotations

import typing as _t

import pytest
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.exceptions import PipToolsError
from piptools.pylock._merge import (
    ResolvedEntry,
    VariantKey,
    _widen_base_marker_against_overrides,
    merge_resolutions,
)

IreqFactory = _t.Callable[[], InstallRequirement]
PerVariantFactory = _t.Callable[
    [IreqFactory],
    "dict[VariantKey, dict[str, tuple[str, InstallRequirement]]]",
]


@pytest.fixture
def make_ireq(
    mocker: MockerFixture,
) -> _t.Callable[[], InstallRequirement]:
    def _factory() -> InstallRequirement:
        return mocker.create_autospec(InstallRequirement, instance=True)

    return _factory


@pytest.mark.parametrize(
    ("per_variant_factory", "all_envs", "expected_markers"),
    (
        pytest.param(
            lambda make: {
                VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", make())},
                VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", make())},
            },
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"pkg": None},
            id="same-version-all-envs-no-marker",
        ),
        pytest.param(
            lambda make: {
                VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", make())},
                VariantKey(env="windows-amd64-3.12-cpython"): {},
            },
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {"pkg": "sys_platform == 'linux'"},
            id="package-only-on-linux",
        ),
        pytest.param(
            lambda make: {
                VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", make())},
                VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("2.0", make())},
            },
            {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"},
            {
                ("pkg", "1.0"): "sys_platform == 'linux'",
                ("pkg", "2.0"): "sys_platform == 'win32'",
            },
            id="version-conflict-split-entries",
        ),
        pytest.param(
            lambda make: {
                VariantKey(env="linux-x86_64-3.12-cpython"): {
                    "base-pkg": ("1.0", make()),
                },
                VariantKey(env="linux-x86_64-3.12-cpython", extra="dev"): {
                    "base-pkg": ("1.0", make()),
                    "dev-pkg": ("2.0", make()),
                },
            },
            {"linux-x86_64-3.12-cpython"},
            {"base-pkg": None, "dev-pkg": "'dev' in extras"},
            id="extra-only-package-gets-extras-marker",
        ),
        pytest.param(
            lambda make: {
                VariantKey(env="linux-x86_64-3.12-cpython", extra="gpu"): {
                    "torch": ("2.0", make()),
                },
                VariantKey(env="linux-x86_64-3.12-cpython", extra="cpu"): {
                    "numpy": ("1.0", make()),
                },
                VariantKey(env="linux-x86_64-3.12-cpython"): {},
            },
            {"linux-x86_64-3.12-cpython"},
            {
                "torch": "'gpu' in extras",
                "numpy": "'cpu' in extras",
            },
            id="different-extras-different-packages",
        ),
    ),
)
def test_merge_resolutions(
    per_variant_factory: PerVariantFactory,
    all_envs: set[str],
    expected_markers: dict[str | tuple[str, str], str | None],
    make_ireq: IreqFactory,
) -> None:
    result = merge_resolutions(per_variant_factory(make_ireq), all_envs)

    for key, expected_marker in expected_markers.items():
        if isinstance(key, tuple):
            name, version = key
            matches = [e for e in result[name] if e.version == version]
            assert len(matches) == 1
            assert matches[0].marker == expected_marker
        else:
            assert len(result[key]) == 1
            assert result[key][0].marker == expected_marker


def test_merge_resolutions_orders_versions_by_pep440(
    make_ireq: IreqFactory,
) -> None:
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython", extra="x"): {
            "pkg": ("1.10.0", make_ireq())
        },
        VariantKey(env="linux-x86_64-3.12-cpython", extra="y"): {
            "pkg": ("1.2.0", make_ireq())
        },
    }
    result = merge_resolutions(per_variant, {"linux-x86_64-3.12-cpython"})
    assert [entry.version for entry in result["pkg"]] == ["1.2.0", "1.10.0"]


def test_merge_resolutions_prefers_ireq_with_original_link(
    mocker: MockerFixture,
) -> None:
    plain_ireq = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    url_ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(),  # truthy
    )
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", plain_ireq)},
        VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", url_ireq)},
    }
    result = merge_resolutions(
        per_variant, {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"}
    )
    assert result["pkg"][0].requirement is url_ireq


def test_merge_resolutions_keeps_link_when_later_variant_has_no_link(
    mocker: MockerFixture,
) -> None:
    # A later index-only resolution does not displace the linked ireq
    # already kept.
    url_ireq = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url="https://example.com/pkg-1.0.tar.gz"),
    )
    plain_ireq = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", url_ireq)},
        VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", plain_ireq)},
    }
    result = merge_resolutions(
        per_variant, {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"}
    )
    assert result["pkg"][0].requirement is url_ireq


def test_merge_resolutions_raises_on_conflicting_direct_urls(
    mocker: MockerFixture,
) -> None:
    left = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url="https://example.com/a.tar.gz"),
    )
    right = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url="https://example.com/b.tar.gz"),
    )
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", left)},
        VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", right)},
    }
    with pytest.raises(PipToolsError, match="Conflicting direct-URL pins"):
        merge_resolutions(
            per_variant, {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"}
        )


def test_merge_resolutions_keeps_first_when_direct_urls_match(
    mocker: MockerFixture,
) -> None:
    # Two variants resolving to the same direct-URL pin (the common case
    # for ``--platform`` matrices) merge into one entry rather than raise
    # the conflicting-URL error reserved for divergence.
    shared_url = "https://example.com/pkg-1.0.tar.gz"
    first = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url=shared_url),
    )
    second = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url=shared_url),
    )
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", first)},
        VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", second)},
    }
    result = merge_resolutions(
        per_variant, {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"}
    )
    assert result["pkg"][0].requirement is first


def test_merge_resolutions_negates_overriding_group_in_base_marker(
    mocker: MockerFixture,
) -> None:
    # When a conflict-group resolution pins a different version than
    # base, the two entries collide unless base's marker excludes that
    # group. Without the negation, ``ensure_marker_disjointness``
    # rejects the lock under ``--group black24`` because both entries
    # match.
    base_req = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    other_req = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    env = "linux-x86_64-3.12-cpython"
    per_variant = {
        VariantKey(env=env): {"black": ("26.3.1", base_req)},
        VariantKey(env=env, group="black24"): {"black": ("24.1.0", other_req)},
    }
    result = merge_resolutions(per_variant, {env})
    base_entry = next(
        e
        for e in result["black"]
        if e.extras_needed is None and e.groups_needed is None
    )
    assert base_entry.marker is not None
    assert "'black24' not in dependency_groups" in base_entry.marker


def test_merge_resolutions_no_negation_when_base_and_group_share_version(
    mocker: MockerFixture,
) -> None:
    # If base and group-only variants pin the same version they collapse
    # onto one entry (variants merged); no second entry exists to collide
    # with, so the negation does not fire on a unique-version case.
    req = mocker.create_autospec(InstallRequirement, instance=True, original_link=None)
    env = "linux-x86_64-3.12-cpython"
    per_variant = {
        VariantKey(env=env): {"pkg": ("1.0", req)},
        VariantKey(env=env, group="dev"): {"pkg": ("1.0", req)},
    }
    result = merge_resolutions(per_variant, {env})
    # One entry, marker ``None``: variants merged at the same pin.
    assert len(result["pkg"]) == 1
    assert result["pkg"][0].marker is None


def test_merge_resolutions_negates_extras_when_base_version_differs(
    mocker: MockerFixture,
) -> None:
    # Same logic on the extras axis: a base+extra pass picking different
    # versions yields a base entry whose marker excludes that extra.
    base_req = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    extra_req = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None
    )
    env = "linux-x86_64-3.12-cpython"
    per_variant = {
        VariantKey(env=env): {"pkg": ("2.0", base_req)},
        VariantKey(env=env, extra="legacy"): {"pkg": ("1.0", extra_req)},
    }
    result = merge_resolutions(per_variant, {env})
    base_entry = next(
        e for e in result["pkg"] if e.extras_needed is None and e.groups_needed is None
    )
    assert base_entry.marker is not None
    assert "'legacy' not in extras" in base_entry.marker


def test_merge_resolutions_normalises_direct_url_compare(
    mocker: MockerFixture,
) -> None:
    # Two cohorts pinning the same logical URL (with case, userinfo, or
    # trailing-slash differences) merge cleanly. pip's ``Link``
    # normalizes the candidate URL while the user-supplied input
    # preserves the original spelling, and a byte-exact compare
    # false-fired the conflicting-direct-URL error.
    base_url = "HTTPS://USER:tok@host.com/path/"
    norm_url = "https://host.com/path"
    left = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url=base_url),
    )
    right = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url=norm_url),
    )
    per_variant = {
        VariantKey(env="linux-x86_64-3.12-cpython"): {"pkg": ("1.0", left)},
        VariantKey(env="windows-amd64-3.12-cpython"): {"pkg": ("1.0", right)},
    }
    result = merge_resolutions(
        per_variant, {"linux-x86_64-3.12-cpython", "windows-amd64-3.12-cpython"}
    )
    assert len(result["pkg"]) == 1


def test_widen_base_marker_wraps_or_marker(
    mocker: MockerFixture,
) -> None:
    # If the base entry already carries a marker with ``or``, the
    # trailing ``and 'X' not in dependency_groups`` would bind to a
    # single disjunct without the wrapping parens, changing the marker's
    # truth set.
    req = mocker.create_autospec(InstallRequirement, instance=True)
    base = ResolvedEntry(
        requirement=req,
        version="2.0",
        marker="sys_platform == 'linux' or sys_platform == 'darwin'",
    )
    other = ResolvedEntry(
        requirement=req,
        version="1.0",
        groups_needed={"legacy"},
        marker="'legacy' in dependency_groups",
    )
    entries = [base, other]
    _widen_base_marker_against_overrides(entries)
    rewritten = entries[0].marker
    assert rewritten is not None
    assert rewritten.startswith("(")
    assert ") and " in rewritten
    assert "'legacy' not in dependency_groups" in rewritten


def test_merge_resolutions_constraint_flip_keeps_non_constraint(
    mocker: MockerFixture,
) -> None:
    # When two variants both pin ``(name, version)`` with no
    # ``original_link``, the merge prefers the non-constraint requirement
    # so the kept ireq carries extras and hash info that the bare ``-c``
    # reference lacks.
    seeded = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None, constraint=True
    )
    user = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None, constraint=False
    )
    env_a = "linux-x86_64-3.12-cpython"
    env_b = "windows-amd64-3.12-cpython"
    per_variant = {
        VariantKey(env=env_a): {"pkg": ("1.0", seeded)},
        VariantKey(env=env_b): {"pkg": ("1.0", user)},
    }
    result = merge_resolutions(per_variant, {env_a, env_b})
    assert result["pkg"][0].requirement is user
