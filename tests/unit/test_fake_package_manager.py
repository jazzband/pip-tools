import unittest
from piptools.datastructures import Spec
from piptools.package_manager import FakePackageManager, NoPackageMatch


class TestFakePackageManager(unittest.TestCase):
    content = {
        'foo-0.1': ['bar', 'qux'],
        'bar-0.2': ['qux>0.1'],
        'qux-0.1': [],
        'qux-0.1.1': [],
        'qux-0.1.2': [],
        'qux-0.2': [],
        'qux-0.2.2': [],
    }

    def test_find_all_versions(self):
        """Tests the fake package manager itself."""
        pkgmgr = FakePackageManager(self.content)
        versions = list(pkgmgr.iter_versions('qux'))
        assert ['0.1', '0.1.1', '0.1.2', '0.2', '0.2.2'] == sorted(versions)

    def test_find_best_match(self):
        pkgmgr = FakePackageManager(self.content)
        samples = [
            # (spec, expected_result) tuples
            ('qux', '0.2.2'),
            ('nonexisting', None),
            ('foo', '0.1'),
            ('bar>0.1', '0.2'),
            ('bar>0.1', '0.2'),
            ('bar<=0.1', None),
            ('qux==0.1', '0.1'),
            ('qux>=0.1,<0.2', '0.1.2'),

            # Conflicts
            ('qux<0.1,>0.2', None),
            ('qux==0.1,==0.2', None),
        ]
        for spec, expected_match in samples:
            try:
                best = pkgmgr.find_best_match(Spec.from_line(spec))
            except NoPackageMatch:
                best = None

            assert best == expected_match
