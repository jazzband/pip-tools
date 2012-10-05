import unittest
from piptools.datastructures import SpecSet


class TestSpecSet(unittest.TestCase):
    def test_adding_specs(self):
        """Adding specs to a set."""
        specset = SpecSet()

        specset.add_spec('Django>=1.3')
        assert 'Django>=1.3' in map(str, specset)

        specset.add_spec('django-pipeline')
        self.assertItemsEqual(['Django>=1.3', 'django-pipeline'], map(str, specset))

        specset.add_spec('Django<1.4')
        self.assertItemsEqual(['Django>=1.3', 'django-pipeline', 'Django<1.4'], map(str, specset))

    def test_normalizing(self):
        """Normalizing combines predicates to a single Spec."""
        specset = SpecSet()

        specset.add_spec('Django>=1.3')
        specset.add_spec('Django<1.4')
        specset.add_spec('Django>=1.3.2')
        specset.add_spec('Django<1.3.99')

        normalized = specset.normalize()
        assert 'Django>=1.3.2,<1.3.99' in map(str, normalized)

        specset.add_spec('Django<=1.3.2')
        normalized = specset.normalize()

        assert 'Django==1.3.2' in map(str, normalized)

    def test_normalizing_2(self):
        """Normalizing combines predicates to a single Spec."""
        specset = SpecSet()

        specset.add_spec('Django')
        specset.add_spec('Django<1.4')

        normalized = specset.normalize()
        assert 'Django<1.4' in map(str, normalized)
