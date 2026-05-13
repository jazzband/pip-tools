"""Build a ``packaging.pylock.PackageVcs`` from a VCS install requirement."""

from __future__ import annotations

import typing as _t
from re import VERBOSE, Pattern
from re import compile as compile_regex

from packaging.pylock import PackageVcs
from pip._internal.req import InstallRequirement
from pip._internal.utils.misc import redact_auth_from_url
from pip._internal.vcs import vcs as _vcs_registry
from pip._internal.vcs.git import looks_like_hash as _looks_like_hash

from ...exceptions import PipToolsError
from .._urls import split_revision
from ._detection import effective_link


def build_vcs_source(requirement: InstallRequirement) -> PackageVcs:
    """Build the PEP 751 VCS source entry for a requirement pinned to a repo.

    Looks up the VCS backend for the link scheme so the entry's type matches the registered VCS
    name (``git``, ``hg``, ``svn``, or ``bzr``).

    :param requirement: The resolved requirement whose link points at a VCS source.
    :returns: The populated VCS entry with an immutable commit identifier.
    :raises PipToolsError: When the requirement does not pin to an immutable revision.
    """
    link = effective_link(requirement)
    assert link is not None

    # PEP 751 requires the registered VCS name (``git`` / ``hg`` / ...); pip stores it in the link
    # scheme as ``<vcs>+<scheme>://...``. Look up the backend rather than hardcoding ``git``, which
    # would produce a wrong type for hg/svn/bzr.
    scheme = link.scheme or ""
    backend = _vcs_registry.get_backend_for_scheme(scheme) if scheme else None
    vcs_type = backend.name if backend is not None else "git"

    url = link.url_without_fragment
    if "+" in scheme:
        url = url.split("+", 1)[1]
    url, revision = split_revision(url)
    commit_id = _resolve_commit_id(requirement, vcs_type, revision)
    # PEP 751 ``packages.vcs`` allows ``path`` for local VCS sources; pip-tools mirrors uv and
    # emits ``url`` for every VCS scheme. ``git+file://`` pins aren't portable across user
    # checkouts, so the spec's optional ``path`` field stays unset.
    return PackageVcs(
        type=vcs_type,
        url=redact_auth_from_url(url),
        commit_id=commit_id,
        # ``requested-revision`` is optional; redundant when equal to ``commit-id``, so omit it in
        # that case to keep the lockfile minimal.
        requested_revision=None if revision == commit_id else revision,
        subdirectory=link.subdirectory_fragment,
    )


def _resolve_commit_id(
    requirement: InstallRequirement, vcs_type: str, revision: str | None
) -> str:
    """Return the immutable commit identifier required by PEP 751.

    PEP 751 says the value MUST be the registered VCS's hash form when one exists. The spec does
    not impose git's shape on backends with their own revision conventions: subversion uses
    ascending integers and bazaar uses arbitrary strings. Each VCS gets its own validator so the
    rule that an immutable value is captured holds without rejecting valid svn or bzr inputs.
    """
    validator = _COMMIT_ID_VALIDATORS.get(vcs_type, _accept_any_revision)
    if revision is not None and (normalized := validator(revision)) is not None:
        return normalized
    raise PipToolsError(
        f"Cannot determine VCS commit-id for {requirement.name!r}: PEP 751 requires "
        f"an immutable commit identifier for {vcs_type!r} sources. "
        f"Pre-resolve the tag/branch to its underlying revision before locking "
        f"(e.g. ``git ls-remote <url> <tag>`` for git/hg, ``svn info <url>`` for "
        f"svn revision number, ``bzr revision-info <revid>`` for bzr revid) and "
        f"pin the requirement to that value."
    )


_SVN_REVISION_RE: _t.Final[Pattern[str]] = compile_regex(
    r"""
    ^
    [0-9]+    # svn revisions are ascending decimal integers; nothing about a
              # git/hg-shaped hash applies here
    $
    """,
    VERBOSE,
)


def _accept_full_sha(revision: str) -> str | None:
    # ``looks_like_hash`` is pip's 40-hex check; Mercurial uses the same shape, so reusing it
    # covers both ``git`` and ``hg``. Going through pip's helper keeps the validator aligned with
    # pip's installer-side checks.
    return revision.lower() if _looks_like_hash(revision) else None


def _accept_svn_revision(revision: str) -> str | None:
    return revision if _SVN_REVISION_RE.fullmatch(revision) else None


_BZR_REVID_HASH_RE: _t.Final[Pattern[str]] = compile_regex(
    r"""
    ^
    [0-9]{14}-     # ``YYYYMMDDhhmmss-`` timestamp prefix common to revids
    [a-z0-9]+      # trailing per-revision hash
    $
    """,
    VERBOSE,
)


def _accept_any_revision(revision: str) -> str | None:
    # PEP 751 wants the immutable identifier. Bazaar's stable form is the revision-id; ``revno:N``,
    # ``tag:v1.0``, ``last:1``, ``before:...``, ``branch:...`` are all mutable references the
    # lockfile must not encode as ``commit-id``. Real revids carry ``@`` which collides with pip's
    # ``url@rev`` split, so the user pins the trailing ``YYYYMMDDhhmmss-<hash>`` portion. Narrow
    # the validator to that shape so non-immutable forms surface as a "pre-resolve" error instead
    # of shipping a drifting lock.
    return revision if _BZR_REVID_HASH_RE.fullmatch(revision) else None


_COMMIT_ID_VALIDATORS: _t.Final[dict[str, _t.Callable[[str], str | None]]] = {
    "git": _accept_full_sha,
    "hg": _accept_full_sha,
    "svn": _accept_svn_revision,
    "bzr": _accept_any_revision,
}


__all__ = [
    "build_vcs_source",
]
