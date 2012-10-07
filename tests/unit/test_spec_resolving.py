import unittest
from piptools.datastructures import SpecSet
from piptools.package_manager import FakePackageManager


def print_specset(specset, round):
    print('After round #%s:' % (round,))
    for spec in specset:
        print('  - %s' % (spec.description(),))


simple = {
    'foo-0.1': ['bar'],
    'bar-1.2': ['qux', 'simplejson'],
    'qux-0.1': ['simplejson<2.6'],

    'simplejson-2.4.0': [],
    'simplejson-2.6.2': [],
}


# The following example _does_ have a solution, but the algorithm doesn't find
# it.  If we're able to smartly backtrack and be able to select qux-0.1, we
# solve it.  My basic idea for the backtracking:
#
# When we encounter a conflict in a round with a newly added package, like
# when we add 'simplejson<2.6 (from qux==0.2)', which conflicts with the
# existing 'simplejson>=2.6 (from foo==0.1)', then we remove the source
# package for that from the spec set.  In our case, this would be qux==0.2.
# And instead, we add a fake spec 'qux<0.2 (from conflict resolution
# attempt)' and continue from there.
#
# I like the idea above, but I'm worried about some details:
# - How complex will this make real-life situations with many dependencies?
#   In the case above, only qux conflicts, but in reality multiple packages
#   may cause conflicts.  Theoretically, any combination of packages should be
#   tried, potentially causing an explosion of conflict resolution attempts.
# - Also, this can potentially try out each version of a package (until there
#   is a conflict or we run out of versions).  This, of course, is exactly the
#   point, but in practice, it's not likely that you'll find anything useful
#   with this technique.
#
# Alternatively, we can stop trying to solve this programatically, and instead
# output some useful information so the user at the wheel can guide the
# process and explicitly add the conflict resolution spec in his/her
# requirements.in manually.
#
# Thoughts?
#
complex = {
    'foo-0.1': ['bar'],
    'bar-1.2': ['qux', 'simplejson>=2.6'],
    'qux-0.1': ['simplejson'],
    'qux-0.2': ['simplejson<2.6'],

    'simplejson-2.4.0': [],
    'simplejson-2.6.2': [],
}


class TestDependencyResolving(unittest.TestCase):
    def test_find_dependencies_simple(self):
        """A simple scenario for finding dependencies."""
        pkgmgr = FakePackageManager(simple)

        spec_set = SpecSet()
        spec_set.add_spec('foo')

        round = 1
        print_specset(spec_set, round)
        while True:
            round += 1
            new_deps = []
            for spec in spec_set.normalize():
                name, version = pkgmgr.find_best_match(spec)
                pkg_deps = pkgmgr.get_dependencies(name, version)

                # Append source information to the new specs
                if spec.source:
                    source = '%s ~> %s==%s' % (spec.source, name, version)
                else:
                    source = '%s==%s' % (name, version)
                pkg_deps = [s.add_source(source) for s in pkg_deps]
                new_deps += pkg_deps

            if not new_deps:
                break

            # TODO: We should detect whether adding the new_deps really
            # "changes anything" to the spec set.  In order words: if no
            # significant new constraints are added, we're done

            # XXX: FIXME: Current, we "just stop" after X rounds (to prevent
            # endless loops), but obviously this is not the correct impl!
            if round > 4:
                break

            spec_set.add_specs(new_deps)
            print_specset(spec_set, round)

        # Print the final result:
        print_specset(spec_set.normalize(), 'final')

        spec_set = spec_set.normalize()
        self.assertItemsEqual(['foo', 'qux', 'bar', 'simplejson<2.6'], map(str, spec_set))
