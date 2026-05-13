from __future__ import annotations

import typing as _t

import pytest
from packaging.markers import Marker
from pip._internal.req import InstallRequirement
from pytest_mock import MockerFixture

from piptools.pylock._merge import VariantKey
from piptools.pylock.platforms import TargetEnvironment
from piptools.pylock.resolve import _worker
from piptools.pylock.resolve._state import ResolverInputs
from piptools.pylock.resolve._worker import (
    _lite_requirement,
    _strip_per_variant_for_pickle,
    init_worker_repository,
    resolve_cohort_in_worker,
)
from piptools.repositories import PyPIRepository

from .conftest import _OptionsFactory


def test_init_worker_repository_sets_module_global(
    mocker: MockerFixture,
) -> None:
    # The ProcessPool initializer caches the per-worker repository on a
    # module-global so subsequent task pickles do not ferry one across the
    # IPC boundary on every call.
    repo_cls = mocker.patch("piptools.pylock.resolve._worker.PyPIRepository")
    mocker.patch.object(_worker, "_WORKER_REPOSITORY", None)

    init_worker_repository(["--index-url", "x"], "/cache")

    repo_cls.assert_called_once_with(["--index-url", "x"], cache_dir="/cache")
    assert _worker._WORKER_REPOSITORY is repo_cls.return_value


def test_resolve_class_in_worker_delegates_to_cohort_work(
    mocker: MockerFixture,
    empty_inputs: ResolverInputs,
    make_options: _OptionsFactory,
) -> None:
    # The worker entrypoint injects the cached repository into
    # ``resolve_cohort_work`` and returns its result through the
    # pickle-safe stripper; otherwise the parent process cannot
    # reconstruct the requirements.
    sentinel_repo = mocker.create_autospec(PyPIRepository, instance=True)
    mocker.patch.object(_worker, "_WORKER_REPOSITORY", sentinel_repo)
    variant = VariantKey(env="a", extra=None, group=None)
    raw_per_variant: dict[VariantKey, dict[str, tuple[str, InstallRequirement]]] = {
        variant: {}
    }
    stripped_per_variant: dict[
        VariantKey, dict[str, tuple[str, InstallRequirement]]
    ] = {variant: {}}
    work = mocker.patch(
        "piptools.pylock.resolve._worker.resolve_cohort_work",
        return_value=(raw_per_variant, {"name": {"dep"}}),
    )
    strip = mocker.patch(
        "piptools.pylock.resolve._worker._strip_per_variant_for_pickle",
        return_value=stripped_per_variant,
    )

    result = resolve_cohort_in_worker(
        cohort_envs=["a"],
        target_envs=_t.cast("dict[str, TargetEnvironment]", {"a": {}}),
        inputs=empty_inputs,
        options=make_options(),
    )

    assert work.call_args.kwargs["repository"] is sentinel_repo
    strip.assert_called_once_with(raw_per_variant)
    assert result == (stripped_per_variant, {"name": {"dep"}})


def test_strip_per_variant_rebuilds_every_requirement(mocker: MockerFixture) -> None:
    # The stripper rebuilds via ``_lite_requirement`` for every entry.
    # pip's resolved requirements carry state that does not survive
    # ProcessPool's pickle transport on Python 3.14, and the lockfile
    # consumes name, version, link, and editable, so the loss of fidelity
    # is harmless and buys a clean cross-process boundary.
    original = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras=set()),
        editable=False,
    )
    variant = VariantKey(env="env", extra=None, group=None)
    cleaned = _strip_per_variant_for_pickle(
        {variant: {"requests": ("2.31.0", original)}}
    )
    rebuilt = cleaned[variant]["requests"][1]
    assert rebuilt is not original
    assert rebuilt.req is not None
    assert rebuilt.req.name == "requests"
    assert str(rebuilt.req.specifier) == "==2.31.0"


def test_lite_requirement_uses_original_link_url_when_available(
    mocker: MockerFixture,
) -> None:
    # VCS and direct-URL requirements lose their identity if rebuilt from
    # a ``name==version`` spec; keep the original link URL so reinstalls
    # hit the same archive instead of whatever the index serves for that pin.
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url="https://example.com/pkg.tar.gz"),
        req=mocker.MagicMock(extras=set()),
        editable=False,
    )
    fresh = _lite_requirement(requirement, "pkg", "1.0")
    assert fresh.link is not None
    assert fresh.link.url == "https://example.com/pkg.tar.gz"
    # PEP 508 direct-URL round-trip preserves the canonical name; without
    # it the worker pickle path produced ``req=None`` and the lockfile
    # wrote ``name = ""`` for any VCS, archive, or directory requirement
    # under ``--jobs > 1``.
    assert fresh.req is not None
    assert fresh.req.name == "pkg"


@pytest.mark.parametrize(
    ("link_url", "kind"),
    (
        pytest.param(
            "git+https://example.com/repo.git@" + "a" * 40,
            "vcs",
            id="vcs",
        ),
        pytest.param(
            "https://example.com/pkg-1.0.tar.gz#sha256=" + "a" * 64,
            "archive",
            id="archive",
        ),
        pytest.param("file:///tmp/pkg-src", "directory", id="directory"),
    ),
)
def test_lite_requirement_round_trips_canonical_name(
    mocker: MockerFixture, link_url: str, kind: str
) -> None:
    # Regression for the worker pickle path; the bare-URL line shape
    # produced a nameless ``InstallRequirement`` for every direct-URL
    # source group, which the writer surfaced as ``name = ""`` in the
    # lockfile. PEP 751 names are mandatory, so the rebuild puts the
    # canonical name back.
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=mocker.MagicMock(url=link_url),
        req=mocker.MagicMock(extras=set()),
        editable=(kind == "directory"),
    )
    fresh = _lite_requirement(requirement, "my-lib", "")
    assert fresh.req is not None
    assert fresh.req.name == "my-lib"


def test_lite_requirement_uses_name_version_pin_when_no_link(
    mocker: MockerFixture,
) -> None:
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras=set()),
        editable=False,
    )
    fresh = _lite_requirement(requirement, "requests", "2.31.0")
    assert fresh.req is not None
    assert fresh.req.name == "requests"
    assert str(fresh.req.specifier) == "==2.31.0"


def test_lite_requirement_falls_back_to_name_only_without_version(
    mocker: MockerFixture,
) -> None:
    # Editable and VCS-without-tag requirements can resolve to a blank
    # version; the stripper avoids emitting ``name==`` (an invalid PEP 440
    # spec that ``Requirement`` rejects as malformed).
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras=set()),
        editable=True,
    )
    fresh = _lite_requirement(requirement, "mypkg", "")
    assert fresh.req is not None
    assert fresh.req.name == "mypkg"
    assert str(fresh.req.specifier) == ""
    assert fresh.editable is True


def test_lite_requirement_preserves_extras_in_pin(mocker: MockerFixture) -> None:
    # Extras survive the rebuild so the per-variant spec matches the
    # resolver's view; otherwise ``requests[security]==2.31.0`` would
    # round-trip into a plain ``requests==2.31.0`` and change the install
    # set without flagging it.
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras={"security", "socks"}),
        editable=False,
    )
    fresh = _lite_requirement(requirement, "requests", "2.31.0")
    assert fresh.req is not None
    assert fresh.extras == {"security", "socks"}


def test_lite_requirement_preserves_user_supplied_hash_options(
    mocker: MockerFixture,
) -> None:
    # ``--hash=sha256:…`` in a requirements file populates
    # ``hash_options``, which the bare ``name @ url`` round-trip in
    # ``_lite_requirement`` discards. PEP 751 treats user-supplied hashes
    # as authoritative; the strip-and-rebuild path under ``--jobs > 1``
    # re-attaches them, otherwise the lockfile's hash source-of-truth
    # shifts to whatever the index served.
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras=set()),
        editable=False,
        markers=None,
        hash_options={"sha256": ["a" * 64]},
    )
    fresh = _lite_requirement(requirement, "pkg", "1.0")
    assert fresh.hash_options == {"sha256": ["a" * 64]}


def test_lite_requirement_preserves_user_supplied_markers(
    mocker: MockerFixture,
) -> None:
    # PEP 508 markers do not survive a bare ``name @ url``
    # ``install_req_from_line`` round-trip; without re-attaching them, the
    # per-extra attribution that ``splice_combined_extras`` relies on
    # would collapse without warning.
    marker = Marker("python_version >= '3.10'")
    requirement = mocker.create_autospec(
        InstallRequirement,
        instance=True,
        original_link=None,
        req=mocker.MagicMock(extras=set()),
        editable=False,
        markers=marker,
        hash_options={},
    )
    fresh = _lite_requirement(requirement, "pkg", "1.0")
    assert fresh.markers is marker
