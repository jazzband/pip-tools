import os
import shutil

from pytest import raises

from piptools.utils import (
    as_tuple, format_requirement, format_specifier, flat_map, dedup, is_subdirectory)


def test_is_subdirectory():
    cwd = os.getcwd()
    test_dir = os.path.join(cwd, 'test')
    assert is_subdirectory(cwd, test_dir)
    assert is_subdirectory(os.path.join(test_dir, '..'), test_dir)
    assert is_subdirectory(cwd, cwd)

    assert not is_subdirectory(test_dir, cwd)


def test_format_requirement(from_line):
    ireq = from_line('test==1.2')
    assert format_requirement(ireq) == 'test==1.2'


def test_format_requirement_editable(from_editable):
    ireq = from_editable('git+git://fake.org/x/y.git#egg=y')
    assert format_requirement(ireq) == '-e git+git://fake.org/x/y.git#egg=y'


def test_format_requirement_non_relative_editable(from_editable, small_fake_package_dir, tmpdir):
    tmp_package_dir = os.path.join(str(tmpdir), 'small_fake_package')
    shutil.copytree(small_fake_package_dir, tmp_package_dir)
    ireq = from_editable(tmp_package_dir)
    assert format_requirement(ireq) == '-e file://' + tmp_package_dir


def test_format_requirement_relative_editable(from_editable, small_fake_package_dir):
    ireq = from_editable(small_fake_package_dir)
    assert format_requirement(ireq) == '-e file:./tests/fixtures/small_fake_package'


def test_format_specifier(from_line):
    ireq = from_line('foo')
    assert format_specifier(ireq) == '<any>'

    ireq = from_line('foo==1.2')
    assert format_specifier(ireq) == '==1.2'

    ireq = from_line('foo>1.2,~=1.1,<1.5')
    assert format_specifier(ireq) == '~=1.1,>1.2,<1.5'
    ireq = from_line('foo~=1.1,<1.5,>1.2')
    assert format_specifier(ireq) == '~=1.1,>1.2,<1.5'


def test_as_tuple(from_line):
    ireq = from_line('foo==1.1')
    name, version, extras = as_tuple(ireq)
    assert name == 'foo'
    assert version == '1.1'
    assert extras == ()

    ireq = from_line('foo[extra1,extra2]==1.1')
    name, version, extras = as_tuple(ireq)
    assert name == 'foo'
    assert version == '1.1'
    assert extras == ("extra1", "extra2")

    # Non-pinned versions aren't accepted
    should_be_rejected = [
        'foo==1.*',
        'foo~=1.1,<1.5,>1.2',
        'foo',
    ]
    for spec in should_be_rejected:
        ireq = from_line(spec)
        with raises(TypeError):
            as_tuple(ireq)


def test_flat_map():
    assert [1, 2, 4, 1, 3, 9] == list(flat_map(lambda x: [1, x, x * x], [2, 3]))


def test_dedup():
    assert list(dedup([3, 1, 2, 4, 3, 5])) == [3, 1, 2, 4, 5]
