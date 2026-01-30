"""
Utilities for working with pip InstallRequirement and related types.

This module provides functions for converting, formatting, and checking
requirements in a way that abstracts over pip's internal APIs.
"""

from __future__ import annotations

import copy
import re
import typing as _t

from pip._internal.req import InstallRequirement
from pip._internal.resolution.resolvelib.base import Requirement as PipRequirement
from pip._internal.utils.misc import redact_auth_from_url
from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.utils import canonicalize_name


def key_from_ireq(ireq: InstallRequirement) -> str:
    """Get a standardized key for an InstallRequirement."""
    if ireq.req is None and ireq.link is not None:
        return str(ireq.link)
    else:
        return key_from_req(ireq.req)


def key_from_req(req: InstallRequirement | Requirement | PipRequirement) -> str:
    """
    Get an all-lowercase version of the requirement's name.

    **Note:** If the argument is an instance of
    ``pip._internal.resolution.resolvelib.base.Requirement`` (like
    ``pip._internal.resolution.resolvelib.requirements.SpecifierRequirement``),
    then the name might include an extras specification.
    Apply :py:func:`strip_extras` to the result of this function if you need
    the package name only.

    :param req: the requirement the key is computed for
    :return: the canonical name of the requirement
    """
    return canonicalize_name(req.name)


def is_url_requirement(ireq: InstallRequirement) -> bool:
    """
    Return :py:data:`True` if requirement was specified as a path or URL.

    ``ireq.original_link`` will have been set by ``InstallRequirement.__init__``
    """
    return bool(ireq.original_link)


def is_pinned_requirement(ireq: InstallRequirement) -> bool:
    """
    Return whether an InstallRequirement is a "pinned" requirement.

    An InstallRequirement is considered pinned if:

    - Is not editable
    - It has exactly one specifier
    - That specifier is "==" or "==="
    - The version does not contain a wildcard

    Examples:
        django==1.8   # pinned
        django>1.8    # NOT pinned
        django~=1.8   # NOT pinned
        django==1.*   # NOT pinned
    """
    if ireq.editable:
        return False

    if ireq.req is None or len(ireq.specifier) != 1:
        return False

    spec = next(iter(ireq.specifier))
    return spec.operator in {"==", "==="} and not spec.version.endswith(".*")


def format_requirement(
    ireq: InstallRequirement,
    marker: Marker | None = None,
    hashes: set[str] | None = None,
) -> str:
    """
    Generic formatter for pretty printing InstallRequirements to the terminal
    in a less verbose way than using its ``__str__`` method.
    """
    if ireq.editable:
        line = f"-e {ireq.link.url}"
    elif is_url_requirement(ireq):
        line = _build_direct_reference_best_efforts(ireq)
    else:
        # Canonicalize the requirement name
        # https://packaging.pypa.io/en/latest/utils.html#packaging.utils.canonicalize_name
        req = copy.copy(ireq.req)
        req.name = canonicalize_name(req.name)
        line = str(req)

    if marker:
        line = f"{line} ; {marker}"

    if hashes:
        for hash_ in sorted(hashes):
            line += f" \\\n    --hash={hash_}"

    return line


def _build_direct_reference_best_efforts(ireq: InstallRequirement) -> str:
    """
    Return a string of a direct reference URI, whenever possible.

    See https://www.python.org/dev/peps/pep-0508/
    """
    # If the requirement has no name then we cannot build a direct reference.
    if not ireq.name:
        return _t.cast(str, ireq.link.url)

    # Look for a relative file path, the direct reference currently does not work with it.
    if ireq.link.is_file and not ireq.link.path.startswith("/"):
        return _t.cast(str, ireq.link.url)

    # If we get here then we have a requirement that supports direct reference.
    # We need to remove the egg if it exists and keep the rest of the fragments.
    lowered_ireq_name = canonicalize_name(ireq.name)
    extras = f"[{','.join(sorted(ireq.extras))}]" if ireq.extras else ""
    direct_reference = f"{lowered_ireq_name}{extras} @ {ireq.link.url_without_fragment}"
    fragments = []

    # Check if there is any fragment to add to the URI.
    if ireq.link.subdirectory_fragment:
        fragments.append(f"subdirectory={ireq.link.subdirectory_fragment}")
    if ireq.link.has_hash:
        fragments.append(f"{ireq.link.hash_name}={ireq.link.hash}")

    # Then add the fragments into the URI, if any.
    if fragments:
        direct_reference += f"#{'&'.join(fragments)}"

    return direct_reference


def format_specifier(ireq: InstallRequirement) -> str:
    """
    Format the specifier of an InstallRequirement.

    Return a user-friendly representation of the requirement specifier.
    If the requirement has no specifier, returns 'any'.
    """
    specs = ireq.specifier
    if specs:
        return ",".join(sorted(str(s) for s in specs))
    return "any"


_strip_extras_re = re.compile(r"\[.+?\]")


def strip_extras(name: str) -> str:
    """Strip extras from package name, e.g. pytest[testing] -> pytest."""
    return re.sub(_strip_extras_re, "", name)
