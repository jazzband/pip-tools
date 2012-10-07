import unittest
from piptools.datastructures import SpecSet
from piptools.resolver import Resolver
from piptools.package_manager import FakePackageManager


simple = {
    'foo-0.1': ['bar'],
    'bar-1.2': ['qux', 'simplejson'],
    'qux-0.1': ['simplejson<2.6'],

    'simplejson-2.4.0': [],
    'simplejson-2.6.2': [],
}




class TestDependencyResolving(unittest.TestCase):
    def test_find_dependencies_simple(self):
        """A simple scenario for finding dependencies."""
        pkgmgr = FakePackageManager(simple)

        # Given a simple top-level configuration (just "foo")...
        spec_set = SpecSet()
        spec_set.add_spec('foo')

        # ...let's see what this leads to
        resolver = Resolver(spec_set, pkgmgr)
        self.assertItemsEqual(
                ['foo==0.1', 'bar==1.2', 'qux==0.1', 'simplejson==2.4.0'],
                map(str, resolver.resolve()))
