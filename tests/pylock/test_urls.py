from __future__ import annotations

import pytest

from piptools.pylock._urls import (
    index_match_key,
    normalize_for_compare,
    split_revision,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        pytest.param("", "", id="empty-string"),
        pytest.param(None, None, id="none"),
        pytest.param(
            "https://USER:secret@HOST.example.com/pkg/",
            "https://host.example.com/pkg",
            id="userinfo-uppercase-trailing-slash",
        ),
        pytest.param(
            "HTTPS://example.com/foo",
            "https://example.com/foo",
            id="uppercase-scheme",
        ),
        pytest.param(
            "https://example.com:8080/foo/",
            "https://example.com:8080/foo",
            id="port-preserved",
        ),
    ),
)
def test_normalize_for_compare(url: str | None, expected: str | None) -> None:
    assert normalize_for_compare(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        pytest.param(
            "ssh://git@github.com/owner/repo.git",
            ("ssh://git@github.com/owner/repo.git", None),
            id="userinfo-only-no-revision",
        ),
        pytest.param(
            "https://github.com/owner/repo.git@main",
            ("https://github.com/owner/repo.git", "main"),
            id="path-revision",
        ),
        pytest.param(
            "ssh://git@github.com/owner/repo.git@v1.2.3",
            ("ssh://git@github.com/owner/repo.git", "v1.2.3"),
            id="userinfo-and-revision",
        ),
        pytest.param(
            "https://example.com/foo#egg=bar",
            ("https://example.com/foo", None),
            id="fragment-stripped",
        ),
    ),
)
def test_split_revision(url: str, expected: tuple[str, str | None]) -> None:
    assert split_revision(url) == expected


def test_index_match_key_ignores_userinfo() -> None:
    # Index-URL equality has to ignore ``user:pw@`` so a token-bearing
    # candidate URL still matches the configured token-less index URL for
    # the same logical host.
    assert index_match_key("https://token@host.com/simple/") == index_match_key(
        "https://host.com/simple/other"
    )


def test_index_match_key_distinguishes_ports() -> None:
    # Port is part of the identity; a private mirror on ``:8443`` is a
    # different host from public PyPI on ``:443``.
    assert index_match_key("https://host.com:8443/simple/") != index_match_key(
        "https://host.com/simple/"
    )
