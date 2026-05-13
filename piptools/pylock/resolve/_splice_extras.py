"""Recover per-extra attribution from a combined-extras pass.

The orchestrator collapses every non-conflicting extra into a single resolution
to amortize the resolver cost. ``merge_resolutions`` then derives per-extra
markers from variant membership, so we have to put each package back into the
variant whose extras introduced it. This module walks the resolved dep graph
forward from each extra's roots to determine which packages came in via that
extra.
"""

from __future__ import annotations

from packaging.markers import Marker
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from pip._internal.req import InstallRequirement

from ...logging import log
from .._marker_ast import collect_extras
from .._merge import VariantKey
from .._urls import normalize_for_compare
from ..sources._detection import effective_link


def splice_combined_extras(
    *,
    cohort_envs: list[str],
    raw_constraints: list[InstallRequirement],
    combined_extras: tuple[str, ...],
    forward_deps: dict[str, set[str]],
    per_variant: dict[VariantKey, dict[str, tuple[str, InstallRequirement]]],
) -> None:
    """Re-attribute combined-pass packages back to their extras-bearing variants.

    The combined pass folds every non-conflicting extra into one resolution.
    The merge step derives ``'X' in extras`` markers from variant membership,
    so this splice walks the dependency graph forward from each extra's roots
    and restores per-extra variant entries.

    :param cohort_envs: Environments the cohort covers.
    :param raw_constraints: User constraints used to identify each extra's roots.
    :param combined_extras: Extras that landed in the combined resolution pass.
    :param forward_deps: Forward-dependency map produced by the resolution.
    :param per_variant: Variant map mutated in place with the recovered entries.
    """
    base_roots, roots_per_extra = _classify_extras_roots(
        raw_constraints, combined_extras
    )
    base_pkgs = _bfs_forward(forward_deps, base_roots)
    pkgs_per_extra = {
        extra: _bfs_forward(forward_deps, roots) - base_pkgs
        for extra, roots in roots_per_extra.items()
    }

    base_specifiers, base_links = _collect_base_constraints(
        raw_constraints, combined_extras
    )
    # Dedupe widening warnings by ``(name, version)`` so cohort envs sharing
    # a resolution emit one warning per unique pair rather than one per env.
    warned_widening: set[tuple[str, str]] = set()
    warned_link_swap: set[str] = set()

    for env_key in cohort_envs:
        base_variant = VariantKey(env=env_key, extra=None, group=None)
        combined = per_variant.get(base_variant)
        if not combined:
            continue
        for extra, pkgs in pkgs_per_extra.items():
            owned = {name: combined[name] for name in pkgs if name in combined}
            if not owned:
                continue
            ext_variant = VariantKey(env=env_key, extra=extra, group=None)
            per_variant.setdefault(ext_variant, {}).update(owned)
        spliced_base = {
            name: data for name, data in combined.items() if name in base_pkgs
        }
        per_variant[base_variant] = spliced_base
        # Combined-extras resolves base+extra in one pass; if an extra's
        # constraint widened a base package's pin, the unified solve picks
        # the wider version and the splice keeps it in base. ``pip install
        # pylock.toml`` (no extras) then installs the upgraded version
        # without notice. Warn so the user can split the resolution if
        # they wanted base unchanged.
        for name, (version, ireq) in spliced_base.items():
            base_spec = base_specifiers.get(name)
            if (
                base_spec is not None
                and not base_spec.contains(version, prereleases=True)
                and (name, version) not in warned_widening
            ):
                warned_widening.add((name, version))
                log.warning(
                    f"Combined-extras pass upgraded {name!r} to {version}; "
                    f"the base constraint {str(base_spec)!r} no longer "
                    f"matches. An extras requirement widened the pin, so "
                    f"installs without the extra will pick up the upgraded "
                    f"version."
                )
            # Direct-URL pins (``pkg @ https://...``) carry no ``SpecifierSet``,
            # so the widening check above never fires on them. Compare the
            # resolved link's URL against the base requirement's link instead;
            # an extras-side requirement that demanded the registered release
            # would land here with a different URL (or ``None``) and change
            # which artifact a no-extras install pulls without notice.
            if (base_link := base_links.get(name)) is not None:
                resolved_link = effective_link(ireq)
                resolved_url = (
                    resolved_link.url_without_fragment
                    if resolved_link is not None
                    else None
                )
                base_normalized = normalize_for_compare(base_link)
                resolved_normalized = normalize_for_compare(resolved_url)
                if (
                    resolved_normalized != base_normalized
                    and name not in warned_link_swap
                ):
                    warned_link_swap.add(name)
                    log.warning(
                        f"Combined-extras pass replaced direct-URL pin for "
                        f"{name!r} ({base_link!r}) with {resolved_url!r}; an "
                        f"extras requirement overrode the URL, so installs "
                        f"without the extra will pull a different artifact."
                    )


def _collect_base_constraints(
    raw_constraints: list[InstallRequirement],
    extras: tuple[str, ...],
) -> tuple[dict[str, SpecifierSet], dict[str, str]]:
    """Return ``(base_specifiers, base_links)`` for non-extras constraints.

    ``base_specifiers`` maps name to ``SpecifierSet`` for ``pkg<spec>``
    pins; ``base_links`` maps name to URL for ``pkg @ url`` pins. The
    splice uses both to detect when the combined-extras pass replaced a
    base constraint with a different artifact, where installs without
    the extra would pick up the swap without notice.
    """
    base_specifiers: dict[str, SpecifierSet] = {}
    base_links: dict[str, str] = {}
    known = frozenset(extras)
    for requirement in raw_constraints:
        if requirement.req is None or requirement.req.name is None:
            continue
        # Seeded ``name==<old>`` pins from the previous lockfile arrive as
        # ``constraint=True`` install requirements. Treating them as base specs
        # would fire a spurious "combined-extras pass widened the pin" warning
        # whenever the new resolution picks a newer version, since the seeded
        # ``==`` would no longer contain it. Drop constraint-only entries here
        # so widening detection fires on user-authored pins alone.
        if requirement.constraint:
            continue
        if _extras_in_marker(requirement.markers, tuple(known)):
            # Extras-side constraint; not a base spec.
            continue
        name = canonicalize_name(requirement.req.name)
        if (link := effective_link(requirement)) is not None:
            if url := link.url_without_fragment:
                base_links[name] = url
        if str(spec := requirement.specifier):
            base_specifiers[name] = spec
    return base_specifiers, base_links


def _classify_extras_roots(
    raw_constraints: list[InstallRequirement],
    extras: tuple[str, ...],
) -> tuple[set[str], dict[str, set[str]]]:
    base_roots: set[str] = set()
    per_extra: dict[str, set[str]] = {extra: set() for extra in extras}
    for requirement in raw_constraints:
        if requirement.req is None or requirement.req.name is None:
            continue
        name = canonicalize_name(requirement.req.name)
        # ``extra == 'X'`` markers on the requirement say "this constraint came from
        # ``[project.optional-dependencies].X``". Inspect the marker text rather than
        # calling ``marker.evaluate(...)``: the latter pulls in the running
        # interpreter's ``python_version`` and ``sys_platform`` from
        # ``default_environment``, so a base-only requirement like
        # ``tomli; python_version < '3.11'`` would mis-classify based on which
        # interpreter ran pip-lock.
        owning_extras = _extras_in_marker(requirement.markers, extras)
        if owning_extras:
            for extra in owning_extras:
                per_extra[extra].add(name)
        else:
            base_roots.add(name)
    return base_roots, per_extra


def _extras_in_marker(
    marker: Marker | None, known_extras: tuple[str, ...]
) -> frozenset[str]:
    if marker is None:
        return frozenset()
    # Intersect with ``known_extras`` so an unknown ``extra == 'mystery'``
    # clause does not pull a constraint out of base. The resolver has no
    # handling for an extra it wasn't asked for.
    return frozenset(collect_extras(marker._markers)) & frozenset(known_extras)


def _bfs_forward(forward_deps: dict[str, set[str]], roots: set[str]) -> set[str]:
    seen = set(roots)
    queue = list(roots)
    while queue:
        parent = queue.pop()
        for child in forward_deps.get(parent, ()):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return seen


__all__ = [
    "splice_combined_extras",
]
