from __future__ import annotations

import pytest

from piptools.repositories.pypi import _get_true_base_from_index_url


@pytest.mark.parametrize(
    "url",
    (
        "https://pypi.org/",
        "https://test.pypi.org/",
        "https://my-pypi-mirror.example.org/",
    ),
)
def test_true_base_url_no_change(url: str) -> None:
    assert _get_true_base_from_index_url(url) == url


@pytest.mark.parametrize(
    ("url", "expect_result"),
    (
        ("https://pypi.org/simple", "https://pypi.org/"),
        ("https://pypi.org/simple/", "https://pypi.org/"),
        # custom index gets the same treatment
        (
            "https://my-pypi-mirror.example.org/simple",
            "https://my-pypi-mirror.example.org/",
        ),
        # an extreme case: pypi.org is being presented via some proxy,
        # which we want to preserve, *and* simple is used repeatedly in the URL
        # -- we only strip one copy of "simple", as this provides an escape hatch
        # for anyone with a particularly weird proxy setup
        (
            "https://pypi.org/my-proxy/simple/simple",
            "https://pypi.org/my-proxy/simple/",
        ),
    ),
)
def test_true_base_url_strips_simple_suffix(url: str, expect_result: str) -> None:
    assert _get_true_base_from_index_url(url) == expect_result
