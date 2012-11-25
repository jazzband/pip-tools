import operator
from functools import partial, wraps
from collections import defaultdict
from itertools import chain
from .version import NormalizedVersion


class ConflictError(Exception):
    pass


def normalized_op(op):
    @wraps(op)
    def _normalized(v1, v2):
        nv1 = NormalizedVersion(v1)
        nv2 = NormalizedVersion(v2)
        return op(nv1, nv2)
    return _normalized


ops = {
    '==': normalized_op(operator.eq),
    '!=': normalized_op(operator.ne),
    '<': normalized_op(operator.lt),
    '>': normalized_op(operator.gt),
    '<=': normalized_op(operator.le),
    '>=': normalized_op(operator.ge),
}


def first(iterable, default=None):
    for item in iterable:
        return item
    return default


def flatten(list_of_lists):
    """Flatten an iterable of iterables."""
    return chain.from_iterable(list_of_lists)


def spec_cmp(spec1, spec2):
    """Compares two (qual, value) tuples."""
    qual1, val1 = spec1
    qual2, val2 = spec2
    result = -cmp(qual1, qual2)  # sort qualifiers reversed alphabetically
    if result != 0:
        return result

    val1 = NormalizedVersion(val1)
    val2 = NormalizedVersion(val2)
    return cmp(val1, val2)


class Spec(object):
    @classmethod
    def from_pinned(cls, name, version, source=None):
        """Creates a spec line for a pinned representation directly, no
        parsing involved.  Takes an optional source.
        """
        return cls(name, [('==', version)], source)

    @classmethod
    def from_line(cls, line, source=None):
        """Parses a spec line from a requirements file and returns a Spec."""
        from pkg_resources import Requirement
        req = Requirement.parse(line)
        return cls(req.project_name, req.specs, source)

    def __init__(self, name, preds, source=None):
        """The Spec class represents a package version specification,
        typically given by a single line in a requirements.txt file.

        Each Spec belongs to a single package name, and can have multiple
        'preds', short for predicates, which are the famous (qualifier,
        version) tuples.
        """
        self._name = name
        self._preds = frozenset(preds if preds else [])
        self._source = source

    def add_source(self, source):
        """Creates a new, immutable, Spec which is a copy of the current Spec,
        but with the given source attached to it.
        """
        return Spec(self.name, self.preds, source)


    @property  # noqa
    def name(self):
        return self._name

    @property
    def preds(self):
        return self._preds

    @property
    def source(self):
        return self._source

    @property
    def is_pinned(self):
        return any([qual == '==' for qual, _ in self._preds])

    def description(self, with_source=True):  # noqa
        qualifiers = ','.join(map(''.join, sorted(self.preds, cmp=spec_cmp)))
        source = ''
        if with_source and self.source:
            source = ' (from %s)' % (self.source,)
        return '%s%s%s' % (self.name, qualifiers, source)

    def __str__(self):
        return self.description(with_source=False)

    def __unicode__(self):
        return unicode(str(self))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return (self.name == other.name and
                self.preds == other.preds and
                self.source == other.source)

    def __hash__(self):
        return (hash(self.name) ^
                hash(self.preds) ^
                hash(self.source))


class SpecSet(object):
    def __init__(self):
        """A collection of Spec instances that can be normalized and used for
        conflict detection.
        """
        self._byname = defaultdict(set)

    def __iter__(self):
        """Iterate over all specs in the set."""
        for key in sorted(self._byname.keys(), key=str.lower):
            specs = self._byname[key]
            for spec in sorted(specs):
                yield spec

    def add_specs(self, iterable):
        for spec in iterable:
            self.add_spec(spec)

    def add_spec(self, spec):
        if isinstance(spec, basestring):
            spec = Spec.from_line(spec)

        self._byname[spec.name].add(spec)

    def explode(self, name):
        """Explodes the list of all Specs for the given package name into
        a list of Specs with maximally one predicate.
        """
        specs = self._byname[name]
        return [Spec(spec.name, [pred], spec.source)
                for spec in specs
                for pred in spec.preds]

    def normalize_specs_for_name(self, name):
        """Normalizes specs for the given package name.  Normalizing here
        means dropping as much specs as possible while still addressing the
        same package space.

        Example before normalizing:
            [
             Spec('Django', [('>=', '1.3.1'), ('<=', '1.5.0')]),
             Spec('Django', [('>', '1.3.0'), ('<=', '1.3.2')])
            ]

        After normalizing:
            [Spec('Django', [('>=', '1.3.1'), ('<=', '1.3.2')])]

        Example before normalizing:
            [
             Spec('Django', [('>=', '1.3.2'), ('<=', '1.5.0')]),
             Spec('Django', [('>', '1.3.0'), ('<=', '1.3.2')])
            ]

        After normalizing:
            [Spec('Django', [('==', '1.3.2')])]
        """
        exploded_spec_list = self.explode(name)

        # Keep a pred->source mapping around, which we need to reattach the
        # original source to the preds once we've normalized the set
        sources = defaultdict(set)
        all_preds = set()
        for spec in exploded_spec_list:
            pred = first(spec.preds)  # it's the _only_ pred in the set, since it's exploded
            sources[pred].add(spec.source)
            all_preds.add(pred)

        # First, group the flattened pred list by qualifier
        by_qualifiers = defaultdict(set)
        for pred in all_preds:
            qualifier, version = pred
            by_qualifiers[qualifier].add(version)

        # The following nested helper methods each perform in-place
        # modifications on the by_qualifiers dict.

        def select_strongest(qual, selector):
            """Selects the version that defines the narrowest range for the
            given qualifier.  Assumes the values of by_qualifiers to be an
            iterable and will convert that into a single version.
            """
            if qual in by_qualifiers:
                by_qualifiers[qual] = selector(by_qualifiers[qual])

        def drop_either_inequality(qual, qual_or_equal):
            """Keeps one of the given inequality specs and drops the other.

            For example: foo>1.2 and foo>=1.3 will drop foo>1.2; and
                         foo>1.3 and foo>=1.2 will drop foo>=1.2; but
                         foo>1.3 and foo>=1.3 will drop foo>=1.3.
            """
            op = ops[qual_or_equal]
            if qual in by_qualifiers and qual_or_equal in by_qualifiers:
                v1 = by_qualifiers[qual]
                v2 = by_qualifiers[qual_or_equal]
                if op(v1, v2):
                    del by_qualifiers[qual_or_equal]
                else:
                    del by_qualifiers[qual]

        def rewrite_inequalities(qual):
            """Tries to get rid of any non-equal spec, if possible.

            For example: foo<=1.2 and foo!=1.2 can be rewritten to foo<1.2.
            """
            if '!=' not in by_qualifiers:
                return

            qual_or_equal = qual + '='
            if qual_or_equal in by_qualifiers:
                try:
                    by_qualifiers['!='].remove(by_qualifiers[qual_or_equal])
                except KeyError:
                    pass
                else:
                    by_qualifiers[qual] = by_qualifiers[qual_or_equal]
                    del by_qualifiers[qual_or_equal]

        # For each qualifier type, apply selection logic.  For the unequality
        # qualifiers, select the value that yields the strongest range
        # possible.

        # Pick the smallest less-than pred
        select_strongest('<', min)
        select_strongest('<=', min)
        select_strongest('>', max)
        select_strongest('>=', max)

        # Pick either the less-than of less-than-or-equal expression if both
        # are present
        drop_either_inequality('<', '<=')
        drop_either_inequality('>', '>=')

        # Tries to rewrite inequalities to shorter form
        rewrite_inequalities('<')
        rewrite_inequalities('>')

        # Normalize less-than/greater-than in the specific case where they
        # overlap on a specific version
        if '>=' in by_qualifiers and '<=' in by_qualifiers:
            if by_qualifiers['>='] == by_qualifiers['<=']:
                by_qualifiers['=='].add(by_qualifiers['<='])
                del by_qualifiers['>=']
                del by_qualifiers['<=']

        # Detect any conflicts
        if '==' in by_qualifiers:
            # Multiple '==' keys are conflicts
            assert len(set(by_qualifiers['=='])) <= 1, 'Conflict! %s' % (' with '.join(map(lambda v: '%s==%s' % (name, v), by_qualifiers['=='],)))  # noqa

            # Pick the only == qualifier
            by_qualifiers['=='] = first(by_qualifiers['=='])

            # Any non-'==' key is a conflict if the pinned version does not
            # fall in that range.  Otherwise, the unequality variant can be
            # removed from the pred set.
            pinned_version = by_qualifiers['==']
            for qual, value in by_qualifiers.items():
                if qual == '==':
                    continue

                # Perform conflict checks
                if qual == '>' and not pinned_version > value:
                    raise ConflictError('Conflict: %s==%s with %s>%s' % (name, pinned_version, name, value))
                if qual == '>=' and not pinned_version >= value:
                    raise ConflictError('Conflict: %s==%s with %s>=%s' % (name, pinned_version, name, value))
                if qual == '<' and not pinned_version < value:
                    raise ConflictError('Conflict: %s==%s with %s<%s' % (name, pinned_version, name, value))
                if qual == '<=' and not pinned_version <= value:
                    raise ConflictError('Conflict: %s==%s with %s<=%s' % (name, pinned_version, name, value))
                if qual == '!=':
                    # != is the only qualifier than can have multiple values
                    for val in value:
                        if pinned_version == val:
                            raise ConflictError('Conflict: %s==%s with %s!=%s' % (name, pinned_version, name, val))

                # If no conflicts are found, prefer the pinned version and
                # discard the inequality pred
                del by_qualifiers[qual]
        else:
            # Checks for conflicts due to non-overlapping ranges
            less_than = None
            if '<' in by_qualifiers:
                less_than = by_qualifiers['<']
                less_than_op = '<'
            elif '<=' in by_qualifiers:
                less_than = by_qualifiers['<=']
                less_than_op = '<='

            greater_than = None
            if '>' in by_qualifiers:
                greater_than = by_qualifiers['>']
                greater_than_op = '>'
            elif '>=' in by_qualifiers:
                greater_than = by_qualifiers['>=']
                greater_than_op = '>='

            if less_than and greater_than:
                assert less_than > greater_than, 'Conflict: %s%s and %s%s' % (less_than_op, less_than, greater_than_op, greater_than)  # noqa

            # Remove obsolete not-equal versions
            if '!=' in by_qualifiers:
                disallowed_versions = by_qualifiers['!=']
                for qual, version in by_qualifiers.items():
                    if qual == '!=':
                        continue

                    op = ops[qual]

                    def inverse_op(v1, v2):
                        return not op(v1, v2)

                    disallowed_versions = set(filter(partial(inverse_op, version), disallowed_versions))
                by_qualifiers['!='] = set(disallowed_versions)

        # Now, take special care regarding the rare, but valid, != operator,
        # of which multiple values can occur and still make perfect sense.
        preds = []
        for qual, value in by_qualifiers.items():
            if qual == '!=':
                values = value  # it's plural
                for val in values:
                    preds.append((qual, val))
            else:
                preds.append((qual, value))

        # Lookup which sources were used to construct this normalized spec set
        if preds:
            used_sources = {source for pred in preds for source in sources[pred]} - {None}
        else:
            # No predicates, un-pinned requirement. Needs special-casing to
            # keep the original source.
            used_sources = [spec.source for spec in self._byname[name]
                            if spec.source is not None]
        source = ' and '.join(sorted(used_sources, key=str.lower))
        return Spec(name, preds, source)

    def normalize(self):
        """Generates a new spec set that is more compact, but equivalent to
        this spec set.
        """
        new_spec_set = SpecSet()
        for name in self._byname:
            new_spec_set.add_spec(self.normalize_specs_for_name(name))
        return new_spec_set

    def __str__(self):
        """Print the spec set: one line per spec in the set."""
        lines = [s.description() for s in self]
        return '\n'.join(lines)
