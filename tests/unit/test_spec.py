import unittest
from piptools.datastructures import Spec, _parse_vcs_url


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

    def test_vcs_url_parsing(self):
        assert _parse_vcs_url('git+git://github.com/svetlyak40wt/tdaemon.git') == dict(
            url='git+git://github.com/svetlyak40wt/tdaemon.git',
            name='tdaemon')

        assert _parse_vcs_url('-e git+git://github.com/svetlyak40wt/tdaemon.git') == dict(
            url='git+git://github.com/svetlyak40wt/tdaemon.git',
            name='tdaemon',
            editable=True)
        
        assert _parse_vcs_url('git+git://github.com/svetlyak40wt/tdaemon.git@develop') == dict(
            url='git+git://github.com/svetlyak40wt/tdaemon.git',
            name='tdaemon',
            branch='develop')

        assert _parse_vcs_url('git+git://github.com/svetlyak40wt/tdaemon.git#egg=TDaemon') == dict(
            url='git+git://github.com/svetlyak40wt/tdaemon.git',
            name='TDaemon')

        assert _parse_vcs_url('git+git://github.com/svetlyak40wt/tdaemon.git@develop#egg=TDaemon') == dict(
            url='git+git://github.com/svetlyak40wt/tdaemon.git',
            branch='develop',
            name='TDaemon')

    def test_with_vcs(self):
        spec = Spec.from_line('git+git://github.com/svetlyak40wt/tdaemon.git')
        assert spec.is_pinned, 'VCS spec is always pinned to some branch or tag'
        assert spec.name == 'tdaemon'
        assert spec.url == 'git+git://github.com/svetlyak40wt/tdaemon.git'
        assert spec.preds == frozenset([('==', 'master')])

    def test_with_pinned_vcs(self):
        spec = Spec.from_line('git+git://github.com/svetlyak40wt/tdaemon.git@develop')
        assert spec.is_pinned
        assert spec.name == 'tdaemon'
        assert spec.url == 'git+git://github.com/svetlyak40wt/tdaemon.git'
        assert spec.preds == frozenset([('==', 'develop')])
        
