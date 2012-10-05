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
        'Django-1.3.3': [],
        'django-pipeline-1.2.17': [],
    }

    def test_find_all_versions(self):
        """Tests the fake package manager itself."""
        pkgmgr = FakePackageManager(self.content)
        versions = list(pkgmgr.iter_versions('qux'))
        assert ['0.1', '0.1.1', '0.1.2', '0.2', '0.2.2'] == sorted(versions)

        # Test names with dashes in them
        versions = list(pkgmgr.iter_versions('django-pipeline'))
        assert '1.2.17' in versions

        # Test mixed case names
        versions = list(pkgmgr.iter_versions('django'))
        assert '1.3.3' in versions

    def test_find_best_match(self):
        pkgmgr = FakePackageManager(self.content)
        samples = [
            # (spec, expected_result) or
            # (spec, expected_version, expected_name) tuples
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

            # Other casings
            ('Django', '1.3.3', 'Django'),
            ('django', '1.3.3', 'Django'),
            ('django-pipeline', '1.2.17', 'django-pipeline'),
            ('django_pipeline', '1.2.17', 'django-pipeline'),
            ('dJaNgO_PIPEline', '1.2.17', 'django-pipeline'),
        ]

        for sample in samples:
            if len(sample) > 2:
                spec_line, expected_version, expected_name = sample
            else:
                spec_line, expected_version = sample
                expected_name = None

            spec = Spec.from_line(spec_line)
            try:
                name, best = pkgmgr.find_best_match(spec)
            except NoPackageMatch:
                name, best = None, None

            if expected_name:
                assert name == expected_name
            assert best == expected_version
