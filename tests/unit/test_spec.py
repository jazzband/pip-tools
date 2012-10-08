import unittest
from piptools.datastructures import Spec


class TestSpec(unittest.TestCase):
    def test_simple(self):
        """Adding specs from a spec line."""
        spec1 = Spec.from_line('foo>1.2')
        spec2 = Spec('foo', [('>', '1.2')])
        spec3 = Spec('foo', [('>', '1.2'), ('>', '1.2')])

        assert spec1 == spec2 == spec3

    def test_is_pinned(self):
        assert not Spec.from_line('foo>1.2').is_pinned
        assert not Spec.from_line('foo').is_pinned
        assert Spec.from_line('foo==1.2').is_pinned

        assert Spec.from_line('foo>1.2,==1.2.1').is_pinned
        assert Spec.from_line('foo==1.2.1,==1.2.2').is_pinned  # useless, but pinned ;)
