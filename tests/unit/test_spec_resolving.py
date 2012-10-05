import unittest
from piptools.datastructures import SpecSet
from piptools.package_manager import FakePackageManager


content = {
    'foo-0.1': ['bar'],
    'bar-1.2': ['qux', 'simplejson'],
    'qux-0.1': ['simplejson<2.6'],

    'simplejson-2.4.0': [],
    'simplejson-2.6.2': [],
}


class TestDependencyResolving(unittest.TestCase):
    def test_find_dependencies_simple(self):
        """A simple scenario for finding dependencies."""
        pkgmgr = FakePackageManager(content)

        spec_set = SpecSet()
        spec_set.add_spec('foo')

        while True:
            new_deps = []
            for spec in spec_set.normalize():
                name, version = pkgmgr.find_best_match(spec)
                new_deps += pkgmgr.get_dependencies(name, version)

            if not new_deps:
                break

            # TODO: We should detect whether adding the new_deps really
            # "changes anything" to the spec set.  In order words: if no
            # significant new constraints are added, we're done

            # XXX: FIXME: Current, we "just stop" if all new_deps keys exist
            # (to prevent endless loops), but obviously this is not the
            # correct impl!
            do_add_em = False
            existing_specs = set([s.name for s in spec_set])
            for spec in new_deps:
                if spec.name not in existing_specs:
                    # Significant change, add all of them!
                    do_add_em = True
                    break

            if do_add_em:
                #print('Adding %s to spec set.' % (new_deps,))
                spec_set.add_specs(new_deps)
            else:
                # We're done---nothing significant added
                break

        spec_set = spec_set.normalize()
        self.assertItemsEqual(['foo', 'qux', 'bar', 'simplejson<2.6'], map(str, spec_set))
