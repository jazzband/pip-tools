"""URL helpers shared across the pylock pipeline.

Three call sites (``builder._index_for_entry``, ``sources.build_vcs_source``,
``resolve._splice_extras``) each run their own ``urlsplit``-and-normalize
pass for different reasons. Centralizing the helpers here means the next
pip ``Link`` semantics shift lands in one file; the docstrings record what
each helper keeps and drops so a future maintainer can pick the right one.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit


def normalize_for_compare(url: str | None) -> str | None:
    """Return a canonical URL form for direct-URL equality comparisons.

    Lower-cases scheme and host, drops userinfo, and trims trailing slashes
    so equivalent direct-URL pins compare equal even when one side preserves
    incidental differences that pip's ``Link`` normalisation hides.

    :param url: The URL to normalise, or ``None`` to short-circuit.
    :returns: The canonical form of ``url`` or ``None`` when ``url`` is empty.
    """
    if not url:
        return url
    parts = urlsplit(url)
    netloc = (parts.hostname or "").lower()
    if parts.port is not None:
        netloc = f"{netloc}:{parts.port}"
    return urlunsplit(
        (parts.scheme.lower(), netloc, parts.path.rstrip("/"), parts.query, "")
    )


def split_revision(url: str) -> tuple[str, str | None]:
    """Separate the ``@<rev>`` suffix from a VCS URL.

    Splits on the path component so the ``user@host`` segment of a URL such
    as ``ssh://git@github.com/repo.git`` survives untouched. Drops the URL
    fragment so the caller does not lose it without noticing.

    :param url: VCS URL carrying a trailing ``@<revision>`` segment.
    :returns: A pair of ``(url without revision, revision or None)``.
    """
    parsed = urlsplit(url)
    if "@" not in parsed.path:
        return (
            urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")),
            None,
        )
    path, revision = parsed.path.rsplit("@", 1)
    cleaned = urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))
    return cleaned, revision


def index_match_key(url: str) -> tuple[str, str | None, int | None]:
    """Return the ``(scheme, hostname, port)`` key for index-URL matching.

    Strips userinfo so a candidate URL bearing an auth token matches a
    configured index URL that omits it.

    :param url: URL whose authority portion the comparison uses.
    :returns: A tuple of ``(scheme, hostname, port)`` suitable for equality.
    """
    parts = urlsplit(url)
    return (parts.scheme, parts.hostname, parts.port)


__all__ = [
    "index_match_key",
    "normalize_for_compare",
    "split_revision",
]
