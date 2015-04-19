from pytest import raises

from piptools.utils import (as_name_version_tuple, format_requirement,
                            format_specifier)


def test_format_requirement(from_line):
    ireq = from_line('test==1.2')
    assert format_requirement(ireq) == 'test==1.2'

    # Annotations are printed as comments at a fixed column
    assert (format_requirement(ireq, annotation='xyz') ==
            'test==1.2                 # xyz')


def test_format_requirement_editable(from_editable):
    ireq = from_editable('git+git://fake.org/x/y.git#egg=y')
    assert format_requirement(ireq) == '-e git+git://fake.org/x/y.git#egg=y'

    # Annotations are printed as comments at a fixed column
    assert (format_requirement(ireq, annotation='xyz') ==
            '-e git+git://fake.org/x/y.git#egg=y  # xyz')


def test_format_specifier(from_line):
    ireq = from_line('foo')
    assert format_specifier(ireq) == '<any>'

    ireq = from_line('foo==1.2')
    assert format_specifier(ireq) == '==1.2'

    ireq = from_line('foo>1.2,~=1.1,<1.5')
    assert format_specifier(ireq) == '~=1.1,>1.2,<1.5'
    ireq = from_line('foo~=1.1,<1.5,>1.2')
    assert format_specifier(ireq) == '~=1.1,>1.2,<1.5'


def test_as_name_version_tuple(from_line):
    ireq = from_line('foo==1.1')
    name, version = as_name_version_tuple(ireq)
    assert name == 'foo'
    assert version == '1.1'

    # Non-pinned versions aren't accepted
    should_be_rejected = [
        'foo==1.*',
        'foo~=1.1,<1.5,>1.2',
        'foo',
    ]
    for spec in should_be_rejected:
        ireq = from_line(spec)
        with raises(TypeError):
            as_name_version_tuple(ireq)
