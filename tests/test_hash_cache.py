from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from piptools.repositories._hash_cache import _FILENAME_VERSION, cache_path, load, store


def test_load_returns_cached_value_with_size(tmp_path: Path) -> None:
    # ``files.pythonhosted.org`` (PyPI's content-addressable host) is
    # cacheable; a non-Warehouse URL would bypass the cache and return a
    # stale value forever.
    url = "https://files.pythonhosted.org/packages/abc/pkg-1.0.tar.gz"
    store(str(tmp_path), url, "abc123", 4096)
    assert load(str(tmp_path), url) == ("abc123", 4096)


def test_load_returns_cached_value_with_unknown_size(tmp_path: Path) -> None:
    # ``size`` is optional; persisting ``None`` lets the cache stay useful for
    # callers that have a digest but no byte count to record.
    url = "https://files.pythonhosted.org/packages/abc/pkg-1.0.tar.gz"
    store(str(tmp_path), url, "abc123", None)
    assert load(str(tmp_path), url) == ("abc123", None)


def test_load_skips_non_pythonhosted_urls(tmp_path: Path) -> None:
    # Private indexes can re-publish the same URL with different bytes;
    # caching their hashes would encode stale bytes into the lockfile.
    # The cache neither stores nor returns values for those hosts.
    url = "https://private.example.com/pkg-1.0.tar.gz"
    store(str(tmp_path), url, "abc123", 1)
    assert load(str(tmp_path), url) is None


_PYTHONHOSTED = "https://files.pythonhosted.org/packages/abc/pkg-1.0.tar.gz"


@pytest.mark.parametrize(
    "data",
    (
        pytest.param(
            {"v": 999, "url": _PYTHONHOSTED, "sha256": "x", "size": 1},
            id="wrong-version",
        ),
        pytest.param(
            {"v": _FILENAME_VERSION, "url": "other", "sha256": "x", "size": 1},
            id="url-mismatch",
        ),
        pytest.param(
            {"v": _FILENAME_VERSION, "url": _PYTHONHOSTED, "sha256": 42, "size": 1},
            id="non-string-sha",
        ),
    ),
)
def test_load_rejects_invalid_payload(tmp_path: Path, data: dict[str, object]) -> None:
    # The cache is keyed by ``hash(url)`` so a collision or stale-format
    # payload could otherwise bleed across URLs; reject anything whose
    # envelope does not match the current schema.
    path = cache_path(str(tmp_path), _PYTHONHOSTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    assert load(str(tmp_path), _PYTHONHOSTED) is None


def test_load_treats_non_int_size_as_unknown(tmp_path: Path) -> None:
    # A v2 payload whose ``size`` field is corrupt (string, float, bool)
    # does not raise; the loader degrades to "unknown size" so a re-stream
    # can populate it on the next call rather than abort the lock.
    path = cache_path(str(tmp_path), _PYTHONHOSTED)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "v": _FILENAME_VERSION,
                "url": _PYTHONHOSTED,
                "sha256": "abc",
                "size": "not-an-int",
            }
        )
    )
    assert load(str(tmp_path), _PYTHONHOSTED) == ("abc", None)


def test_load_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert load(str(tmp_path), _PYTHONHOSTED) is None


def test_store_swallows_oserror(tmp_path: Path, mocker: MockerFixture) -> None:
    # The cache is opportunistic; a read-only volume or a permission
    # error does not abort the lock. A missing entry means the next run
    # rehashes.
    mocker.patch(
        "piptools.repositories._hash_cache.Path.write_text",
        side_effect=OSError("read-only"),
    )
    store(str(tmp_path), _PYTHONHOSTED, "abc", 1)
    assert load(str(tmp_path), _PYTHONHOSTED) is None
