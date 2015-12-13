# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
from functools import partial
from itertools import chain, count

from first import first
from pip.req import InstallRequirement

from . import click
from .cache import DependencyCache
from .exceptions import UnsupportedConstraint
from .logging import log
from .utils import (format_requirement, format_specifier, full_groupby,
                    is_pinned_requirement)

green = partial(click.style, fg='green')
magenta = partial(click.style, fg='magenta')


def _dep_key(ireq):
    if ireq.req is None and ireq.link is not None:
        return str(ireq.link)
    else:
        return ireq.req.key


class Resolver(object):
    def __init__(self, constraints, repository, cache=None, prereleases=False, clear_caches=False):
        """
        This class resolves a given set of constraints (a collection of
        InstallRequirement objects) by consulting the given Repository and the
        DependencyCache.
        """
        self.our_constraints = set(constraints)
        self.their_constraints = set()
        self.repository = repository
        if cache is None:
            cache = DependencyCache()  # pragma: no cover
        self.dependency_cache = cache
        self.prereleases = prereleases
        self.clear_caches = clear_caches

    @property
    def constraints(self):
        return set(self._group_constraints(chain(self.our_constraints,
                                                 self.their_constraints)))

    def resolve(self, max_rounds=10):
        """
        Finds concrete package versions for all the given InstallRequirements
        and their recursive dependencies.  The end result is a flat list of
        (name, version) tuples.  (Or an editable package.)

        Resolves constraints one round at a time, until they don't change
        anymore.  Protects against infinite loops by breaking out after a max
        number rounds.
        """
        if self.clear_caches:
            self.dependency_cache.clear()
            self.repository.clear_caches()

        self._check_constraints()

        # Ignore existing packages
        os.environ[str('PIP_EXISTS_ACTION')] = str('i')  # NOTE: str() wrapping necessary for Python 2/3 compat
        for current_round in count(start=1):
            if current_round > max_rounds:
                raise RuntimeError('No stable configuration of concrete packages '
                                   'could be found for the given constraints after '
                                   '%d rounds of resolving.\n'
                                   'This is likely a bug.' % max_rounds)

            log.debug('')
            log.debug(magenta('{:^60}'.format('ROUND {}'.format(current_round))))
            has_changed, best_matches = self._resolve_one_round()
            log.debug('-' * 60)
            log.debug('Result of round {}: {}'.format(current_round,
                                                      'not stable' if has_changed else 'stable, done'))
            if not has_changed:
                break

            # If a package version (foo==2.0) was built in a previous round,
            # and in this round a different version of foo needs to be built
            # (i.e. foo==1.0), the directory will exist already, which will
            # cause a pip build failure.  The trick is to start with a new
            # build cache dir for every round, so this can never happen.
            self.repository.freshen_build_caches()

        del os.environ['PIP_EXISTS_ACTION']
        return best_matches

    def _check_constraints(self):
        for constraint in chain(self.our_constraints, self.their_constraints):
            if constraint.link is not None and not constraint.editable:
                msg = ('pip-compile does not support URLs as packages, unless they are editable. '
                       'Perhaps add -e option?')
                raise UnsupportedConstraint(msg, constraint)

    def _group_constraints(self, constraints):
        """
        Groups constraints (remember, InstallRequirements!) by their key name,
        and combining their SpecifierSets into a single InstallRequirement per
        package.  For example, given the following constraints:

            Django<1.9,>=1.4.2
            django~=1.5
            Flask~=0.7

        This will be combined into a single entry per package:

            django~=1.5,<1.9,>=1.4.2
            flask~=0.7

        """
        for _, ireqs in full_groupby(constraints, key=_dep_key):
            ireqs = list(ireqs)
            editable_ireq = first(ireqs, key=lambda ireq: ireq.editable)
            if editable_ireq:
                yield editable_ireq  # ignore all the other specs: the editable one is the one that counts
                continue

            ireqs = iter(ireqs)
            combined_ireq = next(ireqs)
            combined_ireq.comes_from = None
            for ireq in ireqs:
                # NOTE we may be losing some info on dropped reqs here
                combined_ireq.req.specifier &= ireq.req.specifier
                # Return a sorted, de-duped tuple of extras
                combined_ireq.extras = tuple(sorted(set(combined_ireq.extras + ireq.extras)))
            yield combined_ireq

    def _resolve_one_round(self):
        """
        Resolves one level of the current constraints, by finding the best
        match for each package in the repository and adding all requirements
        for those best package versions.  Some of these constraints may be new
        or updated.

        Returns whether new constraints appeared in this round.  If no
        constraints were added or changed, this indicates a stable
        configuration.
        """
        # Sort this list for readability of terminal output
        constraints = sorted(self.constraints, key=_dep_key)
        log.debug('Current constraints:')
        for constraint in constraints:
            log.debug('  {}'.format(constraint))

        log.debug('')
        log.debug('Finding the best candidates:')
        best_matches = set(self.get_best_match(ireq) for ireq in constraints)

        # Find the new set of secondary dependencies
        log.debug('')
        log.debug('Finding secondary dependencies:')
        theirs = set(dep
                     for best_match in best_matches
                     for dep in self._iter_dependencies(best_match))

        # NOTE: We need to compare the underlying Requirement objects, since
        # InstallRequirement does not define equality
        diff = {t.req for t in theirs} - {t.req for t in self.their_constraints}
        has_changed = len(diff) > 0
        if has_changed:
            log.debug('')
            log.debug('New dependencies found in this round:')
            for new_dependency in sorted(diff, key=lambda req: req.key):
                log.debug('  adding {}'.format(new_dependency))

        # Store the last round's results in the their_constraints
        self.their_constraints |= theirs
        return has_changed, best_matches

    def get_best_match(self, ireq):
        """
        Returns a (pinned or editable) InstallRequirement, indicating the best
        match to use for the given InstallRequirement (in the form of an
        InstallRequirement).

        Example:
        Given the constraint Flask>=0.10, may return Flask==0.10.1 at
        a certain moment in time.

        Pinned requirements will always return themselves, i.e.

            Flask==0.10.1 => Flask==0.10.1

        """
        if ireq.editable:
            # NOTE: it's much quicker to immediately return instead of
            # hitting the index server
            best_match = ireq
        elif is_pinned_requirement(ireq):
            # NOTE: it's much quicker to immediately return instead of
            # hitting the index server
            best_match = ireq
        else:
            best_match = self.repository.find_best_match(ireq, prereleases=self.prereleases)

        # Format the best match
        log.debug('  found candidate {} (constraint was {})'.format(format_requirement(best_match),
                                                                    format_specifier(ireq)))
        return best_match

    def _iter_dependencies(self, ireq):
        """
        Given a pinned or editable InstallRequirement, collects all the
        secondary dependencies for them, either by looking them up in a local
        cache, or by reaching out to the repository.

        Editable requirements will never be looked up, as they may have
        changed at any time.
        """
        if ireq.editable:
            for dependency in self.repository.get_dependencies(ireq):
                yield dependency
            return
        elif not is_pinned_requirement(ireq):
            raise TypeError('Expected pinned or editable requirement, got {}'.format(ireq))

        # Now, either get the dependencies from the dependency cache (for
        # speed), or reach out to the external repository to
        # download and inspect the package version and get dependencies
        # from there
        if ireq not in self.dependency_cache:
            log.debug('  {} not in cache, need to check index'.format(format_requirement(ireq)), fg='yellow')
            dependencies = self.repository.get_dependencies(ireq)
            self.dependency_cache[ireq] = sorted(str(ireq.req) for ireq in dependencies)

        # Example: ['Werkzeug>=0.9', 'Jinja2>=2.4']
        dependency_strings = self.dependency_cache[ireq]
        log.debug('  {:25} requires {}'.format(format_requirement(ireq),
                                               ', '.join(sorted(dependency_strings, key=lambda s: s.lower())) or '-'))
        for dependency_string in dependency_strings:
            yield InstallRequirement.from_line(dependency_string)

    def reverse_dependencies(self, ireqs):
        non_editable = [ireq for ireq in ireqs if not ireq.editable]
        return self.dependency_cache.reverse_dependencies(non_editable)
