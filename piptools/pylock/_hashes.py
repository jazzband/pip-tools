"""PEP 751 hash-strength policy shared by the repository and the collector."""

from __future__ import annotations

PREFERRED_HASH_ALGORITHMS: frozenset[str] = frozenset(
    {"sha256", "sha384", "sha512", "blake2b", "blake2s"}
)


def is_secure_hash_name(algo: str) -> bool:
    """Return whether ``algo`` is on PEP 751's strong-hash allowlist.

    :param algo: Hash algorithm name as reported by the index or wheel metadata.
    :returns: ``True`` when the algorithm meets the spec's strength bar.
    """
    return algo in PREFERRED_HASH_ALGORITHMS


__all__ = [
    "PREFERRED_HASH_ALGORITHMS",
    "is_secure_hash_name",
]
