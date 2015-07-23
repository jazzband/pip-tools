import pytest

from piptools.sync import (dependency_tree, merge)
from piptools.exceptions import IncompatibleRequirements
from collections import Counter


@pytest.mark.parametrize(
    ('installed', 'root', 'expected'),

    [
        ([],
            'pip-tools', []),

        ([('pip-tools==1', [])],
            'pip-tools', ['pip-tools']),

        ([('pip-tools==1', []),
          ('django==1.7', [])],
            'pip-tools', ['pip-tools']),

        ([('pip-tools==1', ['click>=2']),
          ('django==1.7', []),
          ('click==3', [])],
            'pip-tools', ['pip-tools', 'click']),

        ([('pip-tools==1', ['click>=2']),
          ('django==1.7', []),
          ('click==1', [])],
            'pip-tools', ['pip-tools']),

        ([('root==1', ['child==2']),
          ('child==2', ['grandchild==3']),
          ('grandchild==3', [])],
            'root', ['root', 'child', 'grandchild']),

        ([('root==1', ['child==2']),
          ('child==2', ['root==1'])],
            'root', ['root', 'child']),
    ]
)
def test_dependency_tree(installed_distribution, installed, root, expected):
    installed = {
            distribution.key: distribution
            for distribution in (
                installed_distribution(name, deps)
                for name, deps in installed ) }

    actual = dependency_tree(installed, root)
    assert actual == set(expected)


def test_merge_detect_conflicts(from_line):
    requirements = [from_line('flask==1'), from_line('flask==2')]

    with pytest.raises(IncompatibleRequirements):
        merge(requirements, ignore_conflicts=False)


def test_merge_ignore_conflicts(from_line):
    requirements = [from_line('flask==1'), from_line('flask==2')]

    assert Counter(requirements[1:2]) == Counter(merge(requirements, ignore_conflicts=True))


def test_merge(from_line):
    requirements = [
            from_line('flask==1'),
            from_line('flask==1'),
            from_line('django==2')]

    assert Counter(requirements[1:3]) == Counter(merge(requirements, ignore_conflicts=True))
