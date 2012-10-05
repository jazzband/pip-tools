import unittest
from piptools.datastructures import SpecSet, Spec


class TestSpecSet(unittest.TestCase):
    def test_adding_specs(self):
        """Adding specs to a set."""
        specset = SpecSet()

        specset.add_spec(Spec.from_line('Django>=1.3'))
        assert 'Django>=1.3' in map(str, specset)

        specset.add_spec(Spec.from_line('django-pipeline'))
        self.assertItemsEqual(['Django>=1.3', 'django-pipeline'], map(str, specset))

        specset.add_spec(Spec.from_line('Django<1.4'))
        self.assertItemsEqual(['Django>=1.3', 'django-pipeline', 'Django<1.4'], map(str, specset))

    def test_normalizing(self):
        """Normalizing combines predicates to a single Spec."""
        specset = SpecSet()

        specset.add_spec(Spec.from_line('Django>=1.3'))
        specset.add_spec(Spec.from_line('Django<1.4'))
        specset.add_spec(Spec.from_line('Django>=1.3.2'))
        specset.add_spec(Spec.from_line('Django<1.3.99'))

        normalized = specset.normalize()
        assert 'Django>=1.3.2,<1.3.99' in map(str, normalized)

        specset.add_spec(Spec.from_line('Django<=1.3.2'))
        normalized = specset.normalize()

        assert 'Django==1.3.2' in map(str, normalized)
