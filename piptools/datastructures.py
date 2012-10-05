from collections import defaultdict
from itertools import chain


def flatten(list_of_lists):
    """Flatten an iterable of iterables."""
    return chain.from_iterable(list_of_lists)


class Spec(object):
    @classmethod
    def from_line(cls, line):
        """Parses a spec line from a requirements file and returns a Spec."""
        from pkg_resources import Requirement
        req = Requirement.parse(line)
        return cls(req.project_name, req.specs)

    def __init__(self, name, specs, source=None):
        """The Spec class represents a package version specification,
        typically given by a single line in a requirements.txt file.

        Each Spec belongs to a single package name, and can have multiple
        'specs' (lowercase), which are the famous (qualifier, version) tuples.

        The source is an instance of SpecSource, and defines where this spec
        comes from.
        """
        self.name = name
        self.specs = specs if specs else []
        self.source = source

    def description(self, with_source=True):
        qualifiers = ','.join(map(''.join, self.specs))
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


class SpecSource(object):
    def __str__(self):
        return str(unicode(self))


class FileSource(SpecSource):
    def __init__(self, filename, lineno):
        """Records a given filename and line number as a spec source."""
        self.filename = filename
        self.lineno = lineno

    def __unicode__(self):
        return '%s:%s' % (self.filename, self.lineno)


class InferredSource(SpecSource):
    def __init__(self):
        """Records that this spec source was inferred."""
        pass

    def __unicode__(self):
        return 'inferred'


class RequiredBySource(SpecSource):
    def __init__(self, package):
        """Records a dependency of another package."""
        self.required_by = package

    def __unicode__(self):
        return unicode(self.required_by)


class SpecSet(object):
    def __init__(self):
        """A collection of Spec instances that can be normalized and used for
        conflict detection.
        """
        self._byname = defaultdict(list)
        self._items = []

    def __iter__(self):
        """Iterate over all specs in the set."""
        for specs in self._byname.itervalues():
            for spec in specs:
                yield spec

    def add_specs(self, iterable):
        for spec in iterable:
            self.add_spec(spec)

    def add_spec(self, spec):
        self._items.append(spec)
        self._byname[spec.name].append(spec)

    def normalize_specs_for_name(self, name):
        # TODO: This method should not lose source information, as it does
        # right now.  When normalizing, we might drop a few specs, but for the
        # ones we are keeping, the source should remain clear.

        """Normalizes specs for the given package name.

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
        specs = list(flatten(map(lambda s: s.specs, self._byname[name])))

        # First, group the flattened spec list by qualifier
        by_qualifiers = defaultdict(list)
        for spec in specs:
            qualifier, version = spec
            by_qualifiers[qualifier].append(version)

        # For each qualifier type, apply selection logic.  For the unequality
        # qualifiers, select the value that yields the narrowest range
        # possible.

        # Pick the smallest less-than spec
        if '<' in by_qualifiers:
            by_qualifiers['<'] = sorted(by_qualifiers['<'])[0]
        if '<=' in by_qualifiers:
            by_qualifiers['<='] = sorted(by_qualifiers['<='])[0]

        if '<' in by_qualifiers and '<=' in by_qualifiers:
            if by_qualifiers['<'] <= by_qualifiers['<=']:
                # < xyz wins over <= xyz
                del by_qualifiers['<=']
            else:
                del by_qualifiers['<']

        # Pick the highest greater-than spec
        if '>' in by_qualifiers:
            by_qualifiers['>'] = sorted(by_qualifiers['>'])[-1]
        if '>=' in by_qualifiers:
            by_qualifiers['>='] = sorted(by_qualifiers['>='])[-1]

        if '>' in by_qualifiers and '>=' in by_qualifiers:
            if by_qualifiers['>'] >= by_qualifiers['>=']:
                # > xyz wins over >= xyz
                del by_qualifiers['>=']
            else:
                del by_qualifiers['>']

        # Normalize less-than/greater-than in the specific case where they
        # overlap on a specific version
        if '>=' in by_qualifiers and '<=' in by_qualifiers:
            if by_qualifiers['>='] == by_qualifiers['<=']:
                by_qualifiers['=='].append(by_qualifiers['<='])
                del by_qualifiers['>=']
                del by_qualifiers['<=']

        # Detect any conflicts
        if '==' in by_qualifiers:
            # Multiple '==' keys are conflicts
            assert len(set(by_qualifiers['=='])) <= 1, 'Conflict! %s' % (' with '.join(map(lambda v: '%s==%s' % (name, v), by_qualifiers['=='],)))  # noqa

            # Pick the only == qualifier
            by_qualifiers['=='] = by_qualifiers['=='][0]

            # Any non-'==' key is a conflict if the pinned version does not
            # fall in that range.  Otherwise, the unequality variant can be
            # removed from the spec set.
            pinned_version = by_qualifiers['==']
            for qual, value in by_qualifiers.items():
                if qual == '==':
                    continue

                # Perform conflict checks
                if qual == '>':
                    assert pinned_version > value, 'Conflict: %s==%s with %s>%s' % (name, pinned_version, name, value)
                if qual == '>=':
                    assert pinned_version >= value, 'Conflict: %s==%s with %s>=%s' % (name, pinned_version, name, value)
                if qual == '<':
                    assert pinned_version < value, 'Conflict: %s==%s with %s<%s' % (name, pinned_version, name, value)
                if qual == '<=':
                    assert pinned_version <= value, 'Conflict: %s==%s with %s<=%s' % (name, pinned_version, name, value)

                # If no conflicts are found, prefer the pinned version and
                # discard the inequality spec
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

        inferred_spec = Spec(name, by_qualifiers.items(), source=InferredSource())
        return inferred_spec

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
        lines = map(lambda s: s.description(), flatten(self._byname.values()))
        return '\n'.join(lines)
