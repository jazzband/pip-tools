from __future__ import annotations

import functools
import sys
import typing as _t
from pathlib import Path

import pytest
from packaging import utils as _packaging_utils
from pip._internal.exceptions import MetadataInconsistent
from pip._internal.index import package_finder as _pkgfinder
from pip._internal.index.collector import LinkCollector as _LinkCollector
from pip._internal.models import wheel as _wheel
from pip._internal.operations.prepare import RequirementPreparer as _RequirementPreparer
from pytest_mock import MockerFixture

from piptools._internal import _pip_caches
from piptools._internal._pip_caches import _InMemoryImportlibDistribution
from piptools.logging import log as _piptools_log

if _t.TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def _reset_cache_state(mocker: MockerFixture) -> _t.Iterator[None]:
    # Each test starts with a clean install slate; `uninstall` would
    # otherwise carry the state of the previous test forward and trip the
    # idempotency guard. `create=True` keeps the restoration uniform across
    # pip versions where the underlying symbols may or may not exist (e.g.
    # `parse_wheel_filename` joined `Wheel` in pip 25,
    # `_fetch_metadata_using_link_data_attr` joined the preparer in 23.2)
    # so the fixture itself stays branch-free.
    mocker.patch.object(_pip_caches, "_installed", False)
    mocker.patch.object(_pkgfinder, "parse_links", _pip_caches._original_parse_links)
    mocker.patch.object(
        _packaging_utils,
        "parse_wheel_filename",
        _pip_caches._original_parse_wheel_filename,
    )
    mocker.patch.object(
        _wheel,
        "parse_wheel_filename",
        _pip_caches._original_parse_wheel_filename,
        create=True,
    )
    mocker.patch.object(
        _LinkCollector, "fetch_response", _pip_caches._original_fetch_response
    )
    mocker.patch.object(
        _RequirementPreparer,
        "_fetch_metadata_using_link_data_attr",
        _pip_caches._original_fetch_metadata_using_link_data_attr,
        create=True,
    )
    _pip_caches.clear()
    yield
    # Tests that called `install()` (or used `scope()`) leave a real patch
    # on `_installed=True`; `mocker.patch.object` only undoes its own
    # changes, so explicitly drop the flag too.
    _pip_caches._installed = False


def _page(mocker: MockerFixture, url: str) -> MagicMock:
    page: MagicMock = mocker.MagicMock()
    page.url = url
    return page


def test_install_replaces_parse_links() -> None:
    before = _pkgfinder.parse_links
    _pip_caches.install()
    assert _pkgfinder.parse_links is not before
    assert _pkgfinder.parse_links is _pip_caches._cached_parse_links


def test_install_skips_metadata_attr_when_pip_lacks_it(
    mocker: MockerFixture,
) -> None:
    # pip 22.2 shipped a different metadata flow without
    # ``_fetch_metadata_using_link_data_attr``; capturing whatever the
    # preparer exposes at import time lets ``install`` / ``uninstall`` skip
    # the patch cleanly on those releases instead of crashing.
    mocker.patch.object(
        _pip_caches, "_original_fetch_metadata_using_link_data_attr", None
    )
    _pip_caches.install()
    _pip_caches.uninstall()


def test_install_is_idempotent() -> None:
    _pip_caches.install()
    after_first = _pkgfinder.parse_links
    _pip_caches.install()
    assert _pkgfinder.parse_links is after_first


def test_cached_parse_links_calls_pip_once_per_url(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_links",
        side_effect=lambda page: iter([f"link-for-{page.url}"]),
    )
    page = _page(mocker, "https://pypi.org/simple/foo/")

    first = _pip_caches._cached_parse_links(page)
    second = _pip_caches._cached_parse_links(page)

    assert first == ["link-for-https://pypi.org/simple/foo/"]
    assert second == first
    assert fake.call_count == 1


def test_cached_parse_links_distinguishes_urls(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_links",
        side_effect=lambda page: iter([page.url]),
    )

    foo = _pip_caches._cached_parse_links(_page(mocker, "https://pypi.org/simple/foo/"))
    bar = _pip_caches._cached_parse_links(_page(mocker, "https://pypi.org/simple/bar/"))

    assert foo == ["https://pypi.org/simple/foo/"]
    assert bar == ["https://pypi.org/simple/bar/"]
    assert fake.call_count == 2


def test_clear_drops_cached_parses(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_links",
        side_effect=lambda page: iter([page.url]),
    )
    page = _page(mocker, "https://pypi.org/simple/foo/")
    _pip_caches._cached_parse_links(page)
    _pip_caches.clear()
    _pip_caches._cached_parse_links(page)
    assert fake.call_count == 2


def test_install_rebinds_parse_wheel_filename_in_consumers() -> None:
    # `_rebind_everywhere` walks `sys.modules` so the hot consumer
    # (`pip._internal.models.wheel`) sees the cache too; without that
    # walk, `Wheel.__init__` keeps calling the unwrapped function via
    # its module-local reference and the cache silently does nothing.
    # Pip 22.2's `Wheel.__init__` is regex-based and never imports
    # `parse_wheel_filename`, so the autouse fixture pre-seeds the
    # attribute (`create=True`) to keep this test exercising the
    # rebind path on every pip in the matrix.
    before = _wheel.parse_wheel_filename
    _pip_caches.install()
    assert (
        _packaging_utils.parse_wheel_filename
        is _pip_caches._cached_parse_wheel_filename
    )
    assert _wheel.parse_wheel_filename is _pip_caches._cached_parse_wheel_filename
    assert _wheel.parse_wheel_filename is not before


def test_cached_parse_wheel_filename_calls_pip_once_per_filename(
    mocker: MockerFixture,
) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_wheel_filename",
        side_effect=lambda fn: ("pkg", "1.0", (), frozenset()),
    )
    _pip_caches.clear()
    filename = "foo-1.0-py3-none-any.whl"
    first = _pip_caches._cached_parse_wheel_filename(filename)
    second = _pip_caches._cached_parse_wheel_filename(filename)
    assert first is second
    assert fake.call_count == 1


def test_clear_drops_cached_wheel_filenames(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_wheel_filename",
        side_effect=lambda fn: ("pkg", "1.0", (), frozenset()),
    )
    _pip_caches.clear()
    _pip_caches._cached_parse_wheel_filename("foo-1.0-py3-none-any.whl")
    _pip_caches.clear()
    _pip_caches._cached_parse_wheel_filename("foo-1.0-py3-none-any.whl")
    assert fake.call_count == 2


def test_cached_parse_wheel_filename_is_bounded() -> None:
    # Without a bound the dict could grow without limit on monorepos with
    # thousands of distinct wheel filenames or in long-lived ``--jobs auto``
    # workers; the explicit ``OrderedDict`` LRU puts a known ceiling on the
    # working set so reasoning about lifetime stays in this module.
    assert _pip_caches._PARSED_WHEEL_FILENAME_BOUND == 10_000


def test_cached_parse_wheel_filename_evicts_oldest_when_bounded(
    mocker: MockerFixture,
) -> None:
    # The LRU eviction is what keeps the cache bounded in long-lived workers;
    # without it, ``--jobs auto`` against a monorepo would push the working
    # set past tens of megabytes. Patch the bound low to exercise the
    # eviction without populating 10k entries.
    mocker.patch.object(_pip_caches, "_PARSED_WHEEL_FILENAME_BOUND", 2)
    _pip_caches._parsed_wheel_filename_cache.clear()
    mocker.patch.object(
        _pip_caches,
        "_original_parse_wheel_filename",
        side_effect=lambda f: ("name", "1.0", (), frozenset()),
    )
    _pip_caches._cached_parse_wheel_filename("a-1-py3-none-any.whl")
    _pip_caches._cached_parse_wheel_filename("b-1-py3-none-any.whl")
    _pip_caches._cached_parse_wheel_filename("c-1-py3-none-any.whl")
    assert "a-1-py3-none-any.whl" not in _pip_caches._parsed_wheel_filename_cache
    assert "b-1-py3-none-any.whl" in _pip_caches._parsed_wheel_filename_cache
    assert "c-1-py3-none-any.whl" in _pip_caches._parsed_wheel_filename_cache


def test_install_replaces_fetch_response() -> None:
    before = _LinkCollector.fetch_response
    _pip_caches.install()
    assert _LinkCollector.fetch_response is not before
    assert _LinkCollector.fetch_response is _pip_caches._cached_fetch_response


def test_cached_fetch_response_calls_pip_once_per_url(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_fetch_response",
        side_effect=lambda self, location: f"content-for-{location.url}",
    )
    collector = mocker.create_autospec(_LinkCollector, instance=True)
    location = mocker.MagicMock()
    location.url = "https://pypi.org/simple/foo/"

    first = _pip_caches._cached_fetch_response(collector, location)
    second = _pip_caches._cached_fetch_response(collector, location)

    assert first == "content-for-https://pypi.org/simple/foo/"
    assert second == first
    assert fake.call_count == 1


def test_cached_fetch_response_caches_none_results(mocker: MockerFixture) -> None:
    # `fetch_response` returns None when pip can't reach the index;
    # caching that None too avoids retrying the failing fetch every pass.
    fake = mocker.patch.object(
        _pip_caches, "_original_fetch_response", return_value=None
    )
    collector = mocker.create_autospec(_LinkCollector, instance=True)
    location = mocker.MagicMock()
    location.url = "https://pypi.org/simple/missing/"

    assert _pip_caches._cached_fetch_response(collector, location) is None
    assert _pip_caches._cached_fetch_response(collector, location) is None
    assert fake.call_count == 1


def test_clear_drops_cached_fetch_responses(mocker: MockerFixture) -> None:
    fake = mocker.patch.object(
        _pip_caches,
        "_original_fetch_response",
        side_effect=lambda self, location: f"x-{location.url}",
    )
    collector = mocker.create_autospec(_LinkCollector, instance=True)
    location = mocker.MagicMock()
    location.url = "https://pypi.org/simple/foo/"
    _pip_caches._cached_fetch_response(collector, location)
    _pip_caches.clear()
    _pip_caches._cached_fetch_response(collector, location)
    assert fake.call_count == 2


def test_cached_fetch_metadata_returns_none_when_link_has_no_metadata_link(
    mocker: MockerFixture,
) -> None:
    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    req = mocker.MagicMock()
    req.link.metadata_link.return_value = None
    req.req = mocker.MagicMock()
    get_http = mocker.patch(
        "pip._internal.operations.prepare.get_http_url", create=True
    )
    assert (
        _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req) is None
    )
    # When there is no metadata_link, no HTTP call should fire.
    assert get_http.call_count == 0


def test_cached_fetch_metadata_returns_none_when_req_link_is_none(
    mocker: MockerFixture,
) -> None:
    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    req = mocker.MagicMock()
    req.link = None
    req.req = mocker.MagicMock()
    assert (
        _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req) is None
    )


def test_cached_fetch_metadata_caches_distribution_across_calls(
    mocker: MockerFixture, tmp_path: object
) -> None:
    # The cache is keyed by metadata-link URL and stores the parsed
    # Distribution. Repeated calls for the same URL must return the same
    # Distribution instance and re-read neither HTTP nor the byte cache.
    metadata = b"Metadata-Version: 2.1\nName: foo\nVersion: 1.0\n\n"
    metadata_path = Path(str(tmp_path)) / "METADATA"
    metadata_path.write_bytes(metadata)
    fetched_file = mocker.MagicMock()
    fetched_file.path = str(metadata_path)

    get_http = mocker.patch(
        "pip._internal.operations.prepare.get_http_url",
        create=True,
        return_value=fetched_file,
    )

    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    preparer._download = mocker.MagicMock()
    metadata_link = mocker.MagicMock()
    metadata_link.url = "https://example.com/foo-1.0-py3-none-any.whl.metadata"
    metadata_link.as_hashes.return_value = mocker.MagicMock()
    req = mocker.MagicMock()
    req.link.metadata_link.return_value = metadata_link
    req.link.filename = "foo-1.0-py3-none-any.whl"
    req.req = mocker.MagicMock()
    req.req.name = "foo"

    first = _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req)
    second = _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req)

    assert first is not None
    assert second is not None
    assert first is second
    assert first.raw_name == "foo"
    assert get_http.call_count == 1


def test_cached_fetch_metadata_distribution_survives_temp_dir_teardown(
    mocker: MockerFixture, tmp_path: object
) -> None:
    # The cached Distribution must keep working after the temp dir backing
    # the original metadata file is gone — that's the failure mode the
    # in-memory reader exists to prevent. Read every field the lock pipeline
    # touches before deleting the temp file.
    metadata = (
        b"Metadata-Version: 2.1\nName: foo\nVersion: 1.0\n"
        b"Requires-Python: >=3.10\nRequires-Dist: bar>=2\n\n"
    )
    metadata_path = Path(str(tmp_path)) / "METADATA"
    metadata_path.write_bytes(metadata)
    fetched_file = mocker.MagicMock()
    fetched_file.path = str(metadata_path)

    mocker.patch(
        "pip._internal.operations.prepare.get_http_url",
        create=True,
        return_value=fetched_file,
    )

    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    preparer._download = mocker.MagicMock()
    metadata_link = mocker.MagicMock()
    metadata_link.url = "https://example.com/foo-1.0-py3-none-any.whl.metadata"
    metadata_link.as_hashes.return_value = mocker.MagicMock()
    req = mocker.MagicMock()
    req.link.metadata_link.return_value = metadata_link
    req.link.filename = "foo-1.0-py3-none-any.whl"
    req.req = mocker.MagicMock()
    req.req.name = "foo"

    dist = _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req)
    assert dist is not None

    metadata_path.unlink()

    assert dist.raw_name == "foo"
    assert str(dist.version) == "1.0"
    assert str(dist.requires_python) == ">=3.10"
    assert [str(r) for r in dist.iter_dependencies()] == ["bar>=2"]


def test_cached_fetch_metadata_raises_on_name_mismatch(
    mocker: MockerFixture, tmp_path: object
) -> None:
    # METADATA bytes declare a different Name than the requirement claims;
    # the wrapper must surface this as ``MetadataInconsistent`` and skip the
    # cache so a corrected re-fetch can succeed on a later invocation.
    metadata = b"Metadata-Version: 2.1\nName: bar\nVersion: 1.0\n\n"
    metadata_path = Path(str(tmp_path)) / "METADATA"
    metadata_path.write_bytes(metadata)
    fetched_file = mocker.MagicMock()
    fetched_file.path = str(metadata_path)

    mocker.patch(
        "pip._internal.operations.prepare.get_http_url",
        create=True,
        return_value=fetched_file,
    )

    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    preparer._download = mocker.MagicMock()
    metadata_link = mocker.MagicMock()
    metadata_link.url = "https://example.com/foo.whl.metadata"
    metadata_link.as_hashes.return_value = mocker.MagicMock()
    req = mocker.MagicMock()
    req.link.metadata_link.return_value = metadata_link
    req.link.filename = "foo-1.0-py3-none-any.whl"
    req.req = mocker.MagicMock()
    req.req.name = "foo"

    with pytest.raises(MetadataInconsistent):
        _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req)
    assert metadata_link.url not in _pip_caches._metadata_dist_by_url


def test_cached_fetch_metadata_returns_cached_none(mocker: MockerFixture) -> None:
    # When pip's PEP 658 fetch returned None for a URL on a previous call,
    # later calls must short-circuit without re-attempting the fetch; both
    # to amortize the failure and to leave pip's HTTP cache state alone.
    metadata_link = mocker.MagicMock()
    metadata_link.url = "https://example.com/missing.whl.metadata"
    req = mocker.MagicMock()
    req.link.metadata_link.return_value = metadata_link
    req.req = mocker.MagicMock()
    preparer = mocker.create_autospec(_RequirementPreparer, instance=True)
    get_http = mocker.patch(
        "pip._internal.operations.prepare.get_http_url",
        create=True,
    )
    # The wrapper imports `get_metadata_distribution` lazily (pip 23.2+);
    # `create=True` adds the symbol on pip 22.2 too so the test still
    # reaches the cached-None branch on every supported pip.
    mocker.patch(
        "pip._internal.metadata.get_metadata_distribution",
        create=True,
    )
    _pip_caches._metadata_bytes_by_url[metadata_link.url] = None
    try:
        assert (
            _pip_caches._cached_fetch_metadata_using_link_data_attr(preparer, req)
            is None
        )
    finally:
        _pip_caches._metadata_bytes_by_url.pop(metadata_link.url, None)
    assert get_http.call_count == 0


def test_install_replaces_fetch_metadata_when_original_present(
    mocker: MockerFixture,
) -> None:
    # Pip 22.2 lacks `_fetch_metadata_using_link_data_attr` so install()
    # short-circuits there. Inject a sentinel so install() takes the
    # replace branch on every supported pip and the wrap is exercised
    # in coverage.
    fake_original = mocker.MagicMock()
    mocker.patch.object(
        _pip_caches,
        "_original_fetch_metadata_using_link_data_attr",
        fake_original,
    )
    mocker.patch.object(
        _RequirementPreparer,
        "_fetch_metadata_using_link_data_attr",
        fake_original,
        create=True,
    )
    _pip_caches.install()
    assert (
        _RequirementPreparer._fetch_metadata_using_link_data_attr
        is _pip_caches._cached_fetch_metadata_using_link_data_attr
    )


def test_rebind_everywhere_only_touches_modules_holding_original() -> None:
    sentinel_orig = functools.partial(str, "orig")
    sentinel_new = functools.partial(str, "new")
    source = sys.modules[__name__]
    source.__dict__["_probe"] = sentinel_orig
    other = sys.modules[_pip_caches.__name__]
    other.__dict__["_probe"] = sentinel_orig
    try:
        _pip_caches._rebind_everywhere(source, "_probe", sentinel_orig, sentinel_new)
        assert source._probe is sentinel_new
        assert other._probe is sentinel_new
    finally:
        source.__dict__.pop("_probe", None)
        other.__dict__.pop("_probe", None)


def test_scope_installs_on_enter_and_reverts_on_exit() -> None:
    # The recommended public API: enter swaps in the cached variants,
    # exit restores the originals so successive pip-tools invocations
    # don't inherit each other's monkeypatches.
    before = _pkgfinder.parse_links
    with _pip_caches.scope():
        assert _pkgfinder.parse_links is _pip_caches._cached_parse_links
    assert _pkgfinder.parse_links is before
    assert _pkgfinder.parse_links is _pip_caches._original_parse_links


def test_scope_clears_state_on_exit(mocker: MockerFixture) -> None:
    # Cached parses must not leak past the scope; otherwise tests and
    # successive lock commands would see each other's results.
    fake = mocker.patch.object(
        _pip_caches,
        "_original_parse_links",
        side_effect=lambda page: iter([page.url]),
    )
    page = _page(mocker, "https://pypi.org/simple/foo/")
    with _pip_caches.scope():
        _pip_caches._cached_parse_links(page)
        assert fake.call_count == 1
    with _pip_caches.scope():
        _pip_caches._cached_parse_links(page)
    assert fake.call_count == 2


def test_scope_is_reentrant() -> None:
    # Nested entries are no-ops: only the outermost ``scope()`` owns
    # the install/uninstall pair, so a programmatic caller that already
    # entered ``scope`` and then invoked ``build_pylock_document``
    # doesn't double-revert.
    with _pip_caches.scope():
        assert _pip_caches._installed is True
        with _pip_caches.scope():
            assert _pip_caches._installed is True
        assert _pip_caches._installed is True
    assert _pip_caches._installed is False


def _enter_scope_and_raise() -> None:
    with _pip_caches.scope():
        raise RuntimeError("boom")


def test_scope_reverts_even_when_body_raises() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        _enter_scope_and_raise()
    assert _pip_caches._installed is False
    assert _pkgfinder.parse_links is _pip_caches._original_parse_links


def test_uninstall_restores_originals() -> None:
    # The lower-level uninstall path is what `scope.__exit__` calls; cover
    # it directly so the ProcessPool worker case (which uses ``install``
    # without a paired uninstall) is the only documented one-way use.
    _pip_caches.install()
    assert _pkgfinder.parse_links is _pip_caches._cached_parse_links
    _pip_caches.uninstall()
    assert _pkgfinder.parse_links is _pip_caches._original_parse_links
    assert _pip_caches._installed is False


def test_uninstall_when_not_installed_is_a_noop() -> None:
    assert _pip_caches._installed is False
    _pip_caches.uninstall()  # must not raise
    assert _pip_caches._installed is False


def test_parsed_wheel_filename_cache_warns_on_eviction(
    mocker: MockerFixture,
) -> None:
    # Once the LRU evicts more than ~1% of capacity in one resolution pass
    # the user is parsing the same filenames over and over; surface a
    # one-time hint so they can lift the bound. Without the hint the only
    # signal is "this lock is unexpectedly slow".
    mocker.patch.object(_pip_caches, "_PARSED_WHEEL_FILENAME_BOUND", 4)
    mocker.patch.object(_pip_caches, "_EVICTION_WARN_THRESHOLD", 1)
    _pip_caches.clear()
    log_info = mocker.patch.object(_piptools_log, "info")
    real_parse = _pip_caches._original_parse_wheel_filename
    fake_parse = mocker.patch.object(_pip_caches, "_original_parse_wheel_filename")
    fake_parse.side_effect = real_parse
    for i in range(10):
        _pip_caches._cached_parse_wheel_filename(f"pkg{i}-1.0-py3-none-any.whl")
    log_info.assert_called_once()
    # The hint mentions the env var so users can act on it.
    assert "PIP_TOOLS_PARSED_WHEEL_FILENAME_BOUND" in log_info.call_args.args[0]


def test_in_memory_distribution_locate_file_returns_path() -> None:
    # Without this, ``importlib.metadata.Distribution``'s abstract
    # ``locate_file`` would leave the class abstract and pip's metadata
    # backend would fail with a ``TypeError`` instead of using the
    # in-memory bytes the cache stores.
    distribution = _InMemoryImportlibDistribution(b"Name: foo\n")
    assert distribution.locate_file("egg-info/METADATA") == Path("egg-info/METADATA")
