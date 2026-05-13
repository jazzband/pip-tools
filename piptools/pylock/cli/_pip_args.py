"""Translate ``pip-lock`` flags into the underlying pip CLI arguments.

The resolver delegates index discovery, certificate handling, and
build isolation to pip; this module rewrites the click-level flags into
the equivalent argv list pip expects.
"""

from __future__ import annotations

from os import name as os_name
from shlex import split as shlex_split

from click import BadParameter

from ..._internal import _pip_api
from ...scripts._deprecations import filter_deprecated_pip_args


def build_pip_args(
    find_links: tuple[str, ...],
    index_url: str,
    no_index: bool,
    extra_index_url: tuple[str, ...],
    cert: str | None,
    client_cert: str | None,
    pre: bool,
    trusted_host: tuple[str, ...],
    uploaded_prior_to: str | None,
    build_isolation: bool,
    cache_dir: str,
    pip_args_str: str | None,
) -> list[str]:
    """Translate CLI flags into the argv list pip's discovery layer expects.

    :param find_links: Local or URL-based wheel finders for offline locking.
    :param index_url: Primary package index URL.
    :param no_index: Disable index discovery entirely.
    :param extra_index_url: Additional package indexes consulted in order.
    :param cert: Certificate bundle path for HTTPS verification.
    :param client_cert: Client certificate path for mutual TLS.
    :param pre: Allow pre-release candidates in resolution.
    :param trusted_host: Hostnames whose TLS errors should be ignored.
    :param uploaded_prior_to: Cut-off timestamp for index-side filtering.
    :param build_isolation: Whether to invoke build backends in isolation.
    :param cache_dir: Cache directory pip should reuse.
    :param pip_args_str: Free-form extra pip arguments tokenised before append.
    :returns: A pip-compatible argv list with deprecated tokens stripped.
    :raises click.BadParameter: When ``--uploaded-prior-to`` is set on a pip too old to honour it.
    """
    pip_args: list[str] = []
    for link in find_links:
        pip_args.extend(["-f", link])
    if index_url:
        pip_args.extend(["-i", index_url])
    if no_index:
        pip_args.extend(["--no-index"])
    for extra_index in extra_index_url:
        pip_args.extend(["--extra-index-url", extra_index])
    if cert:
        pip_args.extend(["--cert", cert])
    if client_cert:
        pip_args.extend(["--client-cert", client_cert])
    if pre:
        pip_args.extend(["--pre"])
    for host in trusted_host:
        pip_args.extend(["--trusted-host", host])
    if uploaded_prior_to:
        if _pip_api.PIP_VERSION_MAJOR_MINOR < (26, 0):
            raise BadParameter(
                "--uploaded-prior-to requires pip >= 26.0, "
                f"but you have pip {_pip_api.PIP_VERSION}",
                param_hint="--uploaded-prior-to",
            )
        pip_args.extend(["--uploaded-prior-to", uploaded_prior_to])
    if not build_isolation:
        pip_args.append("--no-build-isolation")
    if cache_dir:
        pip_args.extend(["--cache-dir", cache_dir])
    # ``shlex.split`` is POSIX by default, so a Windows user's
    # ``--pip-args="--cert C:\\Users\\me\\cert"`` would have its backslashes
    # mangled. ``posix=False`` keeps Windows-flavoured paths intact while
    # tokenizing on whitespace.
    pip_args.extend(shlex_split(pip_args_str or "", posix=os_name != "nt"))
    return filter_deprecated_pip_args(pip_args)


__all__ = [
    "build_pip_args",
]
