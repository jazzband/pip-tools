from collections import Counter

import pytest
from piptools.exceptions import IncompatibleRequirements
from piptools.sync import dependency_tree, diff, merge


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
def test_dependency_tree(fake_dist, installed, root, expected):
    installed = {distribution.key: distribution
                 for distribution in
                 (fake_dist(name, deps) for name, deps in installed)}

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
    requirements = [from_line('flask==1'),
                    from_line('flask==1'),
                    from_line('django==2')]

    assert Counter(requirements[1:3]) == Counter(merge(requirements, ignore_conflicts=True))


def test_diff_should_do_nothing():
    installed = []  # empty env
    reqs = []  # no requirements

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == set()
    assert to_uninstall == set()


def test_diff_should_install(from_line):
    installed = []  # empty env
    reqs = [from_line('django==1.8')]

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == {'django==1.8'}
    assert to_uninstall == set()


def test_diff_should_uninstall(fake_dist):
    installed = [fake_dist('django==1.8')]
    reqs = []

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == set()
    assert to_uninstall == {'django'}  # no version spec when uninstalling


def test_diff_should_update(fake_dist, from_line):
    installed = [fake_dist('django==1.7')]
    reqs = [from_line('django==1.8')]

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == {'django==1.8'}
    assert to_uninstall == set()


def test_diff_leave_packaging_packages_alone(fake_dist, from_line):
    # Suppose an env contains Django, and pip itself
    installed = [
        fake_dist('django==1.7'),
        fake_dist('first==2.0.1'),
        fake_dist('pip==7.1.0'),
    ]

    # Then this Django-only requirement should keep pip around (i.e. NOT
    # uninstall it), but uninstall first
    reqs = [
        from_line('django==1.7'),
    ]

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == set()
    assert to_uninstall == {'first'}


def test_diff_leave_piptools_alone(fake_dist, from_line):
    # Suppose an env contains Django, and pip-tools itself (including all of
    # its dependencies)
    installed = [
        fake_dist('django==1.7'),
        fake_dist('first==2.0.1'),
        fake_dist('pip-tools==1.1.1', [
            'click>=4',
            'first',
            'six',
        ]),
        fake_dist('six==1.9.0'),
        fake_dist('click==4.1'),
        fake_dist('foobar==0.3.6'),
    ]

    # Then this Django-only requirement should keep pip around (i.e. NOT
    # uninstall it), but uninstall first
    reqs = [
        from_line('django==1.7'),
    ]

    to_install, to_uninstall = diff(reqs, installed)
    assert to_install == set()
    assert to_uninstall == {'foobar'}
