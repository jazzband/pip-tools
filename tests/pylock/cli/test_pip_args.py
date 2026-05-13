from __future__ import annotations

import pytest

from piptools._internal import _pip_api
from piptools.pylock.cli._pip_args import build_pip_args


def test_build_pip_args_all_flags() -> None:

    args = build_pip_args(
        find_links=("http://packages.example.com",),
        index_url="https://index.example.com/simple",
        no_index=False,
        extra_index_url=("https://extra.example.com",),
        cert="/path/to/cert.pem",
        client_cert="/path/to/client.pem",
        pre=True,
        trusted_host=("example.com",),
        uploaded_prior_to=None,
        build_isolation=False,
        cache_dir="/tmp/cache",
        pip_args_str="--timeout 30",
    )
    assert args[:2] == ["-f", "http://packages.example.com"]
    assert "-i" in args
    assert "https://index.example.com/simple" in args
    assert "--extra-index-url" in args
    assert "--cert" in args
    assert "/path/to/cert.pem" in args
    assert "--client-cert" in args
    assert "--pre" in args
    assert "--trusted-host" in args
    assert "example.com" in args
    assert "--no-build-isolation" in args
    assert "--cache-dir" in args
    assert "--timeout" in args


@pytest.mark.parametrize(
    ("flag", "expected"),
    (
        pytest.param("no_index", "--no-index", id="no-index"),
        pytest.param("pre", "--pre", id="pre"),
    ),
)
def test_build_pip_args_bool_flags(flag: str, expected: str) -> None:
    args = build_pip_args(
        find_links=(),
        index_url="",
        no_index=(flag == "no_index"),
        extra_index_url=(),
        cert=None,
        client_cert=None,
        pre=(flag == "pre"),
        trusted_host=(),
        uploaded_prior_to=None,
        build_isolation=True,
        cache_dir="",
        pip_args_str=None,
    )
    assert expected in args


def test_build_pip_args_uploaded_prior_to_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_pip_api, "PIP_VERSION_MAJOR_MINOR", (26, 0))
    args = build_pip_args(
        find_links=(),
        index_url="",
        no_index=False,
        extra_index_url=(),
        cert=None,
        client_cert=None,
        pre=False,
        trusted_host=(),
        uploaded_prior_to="2024-01-01T00:00:00Z",
        build_isolation=True,
        cache_dir="",
        pip_args_str=None,
    )
    assert "--uploaded-prior-to" in args
    assert "2024-01-01T00:00:00Z" in args
