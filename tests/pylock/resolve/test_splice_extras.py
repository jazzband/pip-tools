from __future__ import annotations

import typing as _t

import pytest
from packaging.markers import Marker
from packaging.specifiers import SpecifierSet
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.pylock._merge import VariantKey
from piptools.pylock.resolve._splice_extras import (
    _bfs_forward,
    _classify_extras_roots,
    _collect_base_constraints,
    splice_combined_extras,
)

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock


class IreqFactory(_t.Protocol):
    def __call__(self, name: str, marker: str | None = ...) -> InstallRequirement: ...


class IreqWithSpecFactory(_t.Protocol):
    def __call__(
        self, name: str, specifier: str, *, constraint: bool = ...
    ) -> InstallRequirement: ...


class IreqWithLinkFactory(_t.Protocol):
    def __call__(self, name: str, url: str) -> InstallRequirement: ...


@pytest.fixture
def make_ireq(mocker: MockerFixture) -> IreqFactory:
    def _factory(name: str, marker: str | None = None) -> InstallRequirement:
        req_mock = mocker.MagicMock()
        req_mock.name = name
        return mocker.create_autospec(
            InstallRequirement,
            instance=True,
            markers=Marker(marker) if marker else None,
            req=req_mock,
        )

    return _factory


@pytest.fixture
def make_ireq_with_spec(mocker: MockerFixture) -> IreqWithSpecFactory:
    def _factory(
        name: str, specifier: str, *, constraint: bool = False
    ) -> InstallRequirement:
        req_mock = mocker.MagicMock()
        req_mock.name = name
        return mocker.create_autospec(
            InstallRequirement,
            instance=True,
            markers=None,
            req=req_mock,
            specifier=SpecifierSet(specifier),
            constraint=constraint,
            original_link=None,
            link=None,
        )

    return _factory


@pytest.fixture
def make_ireq_with_link(mocker: MockerFixture) -> IreqWithLinkFactory:
    def _factory(name: str, url: str) -> InstallRequirement:
        req_mock = mocker.MagicMock()
        req_mock.name = name
        link = mocker.MagicMock()
        link.url_without_fragment = url
        return mocker.create_autospec(
            InstallRequirement,
            instance=True,
            markers=None,
            req=req_mock,
            specifier=SpecifierSet(),
            constraint=False,
            original_link=link,
            link=None,
        )

    return _factory


def test_bfs_forward_visits_transitive_descendants() -> None:
    forward_deps = {
        "a": {"b", "c"},
        "b": {"d"},
        "c": {"d", "e"},
        "f": {"g"},
    }
    assert _bfs_forward(forward_deps, {"a"}) == {"a", "b", "c", "d", "e"}
    assert _bfs_forward(forward_deps, {"f"}) == {"f", "g"}
    assert _bfs_forward(forward_deps, set()) == set()


def test_classify_extras_roots_separates_base_from_extras(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    constraints = [
        make_ireq("requests"),
        make_ireq("pytest", marker="extra == 'test'"),
        make_ireq("ruff", marker="extra == 'lint' or extra == 'dev'"),
        make_ireq("tomli", marker="python_version < '3.11'"),
    ]
    base, per_extra = _classify_extras_roots(constraints, ("test", "lint", "dev"))
    # `requests` has no marker; `tomli`'s `python_version` marker still
    # admits the empty-extras context, so both belong to the base set.
    assert base == {"requests", "tomli"}
    assert per_extra["test"] == {"pytest"}
    assert per_extra["lint"] == {"ruff"}
    assert per_extra["dev"] == {"ruff"}


def test_classify_extras_roots_handles_reversed_comparison(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    # PEP 508 marker comparisons go either direction; the AST walker has to
    # match both orderings so a constraint written ``'dev' == extra`` does not
    # leak into base and lose its ``'dev' in extras`` marker on the lockfile.
    constraints = [
        make_ireq("pytest", marker="'test' == extra"),
        make_ireq("ruff", marker="extra == 'lint' or 'dev' == extra"),
    ]
    base, per_extra = _classify_extras_roots(constraints, ("test", "lint", "dev"))
    assert base == set()
    assert per_extra["test"] == {"pytest"}
    assert per_extra["lint"] == {"ruff"}
    assert per_extra["dev"] == {"ruff"}


def test_classify_extras_roots_descends_into_parenthesized_marker(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    # Parenthesised markers parse as nested AST lists; the extras walker must
    # recurse into them, otherwise an extras-conditional dep written
    # ``(extra == 'dev' or extra == 'test')`` would slip into base.
    constraints = [
        make_ireq("ruff", marker="(extra == 'dev' or extra == 'test')"),
    ]
    base, per_extra = _classify_extras_roots(constraints, ("dev", "test"))
    assert base == set()
    assert per_extra["dev"] == {"ruff"}
    assert per_extra["test"] == {"ruff"}


def test_classify_extras_roots_skips_constraints_without_name(
    mocker: MockerFixture,
) -> None:
    no_req = mocker.create_autospec(InstallRequirement, instance=True, req=None)
    nameless_req = mocker.MagicMock()
    nameless_req.name = None
    no_name = mocker.create_autospec(
        InstallRequirement, instance=True, req=nameless_req
    )
    base, per_extra = _classify_extras_roots([no_req, no_name], ("ext",))
    assert base == set()
    assert per_extra == {"ext": set()}


def test_splice_combined_extras_moves_extras_only_packages(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    constraints = [
        make_ireq("requests"),
        make_ireq("pytest", marker="extra == 'test'"),
    ]
    forward_deps = {
        "requests": {"urllib3"},
        "pytest": {"pluggy"},
    }
    env_key = "linux-x86_64-3.12-cpython"
    base_variant = VariantKey(env=env_key, extra=None, group=None)
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        base_variant: {
            "requests": (
                "2.31.0",
                mocker.create_autospec(InstallRequirement, instance=True),
            ),
            "urllib3": (
                "2.0.0",
                mocker.create_autospec(InstallRequirement, instance=True),
            ),
            "pytest": (
                "8.0.0",
                mocker.create_autospec(InstallRequirement, instance=True),
            ),
            "pluggy": (
                "1.4.0",
                mocker.create_autospec(InstallRequirement, instance=True),
            ),
        },
    }

    splice_combined_extras(
        cohort_envs=[env_key],
        raw_constraints=constraints,
        combined_extras=("test",),
        forward_deps=forward_deps,
        per_variant=per_variant,
    )

    test_variant = VariantKey(env=env_key, extra="test", group=None)
    # base keeps only the packages reachable from base roots
    assert set(per_variant[base_variant]) == {"requests", "urllib3"}
    # extras-only packages move into the per-extra slot
    assert set(per_variant[test_variant]) == {"pytest", "pluggy"}


def test_splice_combined_extras_skips_envs_with_empty_base(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    constraints = [make_ireq("pytest", marker="extra == 'test'")]
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        VariantKey(env="missing", extra=None, group=None): {},
    }
    splice_combined_extras(
        cohort_envs=["missing"],
        raw_constraints=constraints,
        combined_extras=("test",),
        forward_deps={"pytest": set()},
        per_variant=per_variant,
    )
    # Empty base variant short-circuits; no per-extra entry is synthesized.
    assert VariantKey(env="missing", extra="test", group=None) not in per_variant


def test_splice_combined_extras_skips_extra_with_no_new_packages(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
) -> None:
    # If an extra's roots don't add any packages beyond base (e.g. the
    # extra was empty or all its deps are already required by base), the
    # splice must skip creating a per-extra variant; leaving the only
    # entry in `per_variant` would lock the package as if `'X' in extras`
    # were required.
    base_req = make_ireq("requests")
    ext_req = make_ireq("requests", marker="extra == 'mirror'")
    env_key = "linux-x86_64-3.12-cpython"
    base_variant = VariantKey(env=env_key, extra=None, group=None)
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        base_variant: {
            "requests": (
                "2.31.0",
                mocker.create_autospec(InstallRequirement, instance=True),
            )
        },
    }

    splice_combined_extras(
        cohort_envs=[env_key],
        raw_constraints=[base_req, ext_req],
        combined_extras=("mirror",),
        forward_deps={"requests": set()},
        per_variant=per_variant,
    )
    # No per-extra variant created because `mirror`'s only root is also
    # base; subtracting base leaves an empty set.
    assert VariantKey(env=env_key, extra="mirror", group=None) not in per_variant


def test_collect_base_constraints_skips_seeded_constraint_pins(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
    make_ireq_with_spec: IreqWithSpecFactory,
) -> None:
    # ``constraint=True`` ireqs come from seeded ``name==<old>`` pins. Treating
    # them as base specs would fire a spurious "widened" warning whenever the
    # new resolution legitimately picks a newer version, since the seeded ``==``
    # would no longer contain it.
    seeded = make_ireq_with_spec("requests", "==2.30.0", constraint=True)
    user = make_ireq_with_spec("click", ">=8")
    base_specs, base_links = _collect_base_constraints([seeded, user], ())
    assert "requests" not in base_specs
    assert "click" in base_specs
    assert base_links == {}


def test_collect_base_constraints_records_direct_url(
    mocker: MockerFixture,
    make_ireq_with_link: IreqWithLinkFactory,
) -> None:
    # Direct-URL pins (``pkg @ https://...``) carry no SpecifierSet, but the
    # splice still needs to detect when extras swap the URL out.
    url = "https://example.com/pkg-1.0.tar.gz"
    direct = make_ireq_with_link("pkg", url)
    base_specs, base_links = _collect_base_constraints([direct], ())
    assert base_specs == {}
    assert base_links == {"pkg": url}


def test_splice_combined_extras_warns_on_widened_pin(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
    make_ireq_with_spec: IreqWithSpecFactory,
) -> None:
    base_req = make_ireq_with_spec("requests", "<3")
    ext_req = make_ireq("pytest", marker="extra == 'test'")
    env_key = "linux-x86_64-3.12-cpython"
    base_variant = VariantKey(env=env_key, extra=None, group=None)
    upgraded_ireq = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=None, link=None
    )
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        base_variant: {"requests": ("3.0.0", upgraded_ireq)},
    }
    log_warning = mocker.patch("piptools.pylock.resolve._splice_extras.log.warning")
    splice_combined_extras(
        cohort_envs=[env_key],
        raw_constraints=[base_req, ext_req],
        combined_extras=("test",),
        forward_deps={"requests": set()},
        per_variant=per_variant,
    )
    log_warning.assert_called_once()
    # Same (name, version) firing on a second cohort env stays deduped; only
    # one warning surfaces even when the cohort has 17 envs.


def test_splice_combined_extras_warns_on_link_swap(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
    make_ireq_with_link: IreqWithLinkFactory,
) -> None:
    base_url = "https://example.com/pkg-1.0.tar.gz"
    base_req = make_ireq_with_link("pkg", base_url)
    ext_req = make_ireq("side", marker="extra == 'gpu'")
    env_key = "linux-x86_64-3.12-cpython"
    base_variant = VariantKey(env=env_key, extra=None, group=None)
    swapped_link = mocker.MagicMock()
    swapped_link.url_without_fragment = "https://example.com/pkg-2.0.tar.gz"
    swapped_ireq = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=swapped_link, link=None
    )
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        base_variant: {"pkg": ("2.0.0", swapped_ireq)},
    }
    log_warning = mocker.patch("piptools.pylock.resolve._splice_extras.log.warning")
    splice_combined_extras(
        cohort_envs=[env_key],
        raw_constraints=[base_req, ext_req],
        combined_extras=("gpu",),
        forward_deps={"pkg": set()},
        per_variant=per_variant,
    )
    log_warning.assert_called_once()


def test_splice_combined_extras_no_warn_when_link_unchanged(
    mocker: MockerFixture,
    make_ireq: IreqFactory,
    make_ireq_with_link: IreqWithLinkFactory,
) -> None:
    # The widening / link-swap warnings should stay quiet when the resolved
    # link matches the base spec. Covers the ``no swap detected`` branch so a
    # future change can't silently flip the comparison logic.
    base_url = "https://example.com/pkg-1.0.tar.gz"
    base_req = make_ireq_with_link("pkg", base_url)
    ext_req = make_ireq("side", marker="extra == 'gpu'")
    env_key = "linux-x86_64-3.12-cpython"
    base_variant = VariantKey(env=env_key, extra=None, group=None)
    same_link = mocker.MagicMock()
    same_link.url_without_fragment = base_url
    same_ireq = mocker.create_autospec(
        InstallRequirement, instance=True, original_link=same_link, link=None
    )
    per_variant: dict[VariantKey, dict[str, tuple[str, MagicMock]]] = {
        base_variant: {"pkg": ("1.0.0", same_ireq)},
    }
    log_warning = mocker.patch("piptools.pylock.resolve._splice_extras.log.warning")
    splice_combined_extras(
        cohort_envs=[env_key],
        raw_constraints=[base_req, ext_req],
        combined_extras=("gpu",),
        forward_deps={"pkg": set()},
        per_variant=per_variant,
    )
    log_warning.assert_not_called()


def test_collect_base_constraints_skips_nameless_requirements(
    mocker: MockerFixture,
) -> None:
    # ``InstallRequirement`` can land here with ``req=None`` (the
    # ``-e <directory>`` and ``<url>`` shapes pre-resolution); the helper
    # must skip those rather than crash trying to read ``req.name``.
    nameless = mocker.create_autospec(InstallRequirement, instance=True, req=None)
    base_specs, base_links = _collect_base_constraints([nameless], ())
    assert base_specs == {}
    assert base_links == {}


def test_collect_base_constraints_skips_link_without_url_without_fragment(
    mocker: MockerFixture,
) -> None:
    # A link missing ``url_without_fragment`` must not poison ``base_links``.
    req_mock = mocker.MagicMock()
    req_mock.name = "pkg"
    link = mocker.MagicMock(spec=[])
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        markers=None,
        req=req_mock,
        specifier=SpecifierSet(),
        constraint=False,
        original_link=link,
        link=None,
    )
    base_specs, base_links = _collect_base_constraints([requirement], ())
    assert base_links == {}
