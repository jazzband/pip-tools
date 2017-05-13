from pytest import fixture, yield_fixture

from pip.index import FormatControl
from piptools.utils import comment, UNSAFE_PACKAGES
from piptools.writer import OutputWriter


class Writer(object):
    def __call__(self, **kwargs):
        return OutputWriter(src_files=["src_file", "src_file2"], dst_file="dst_file",
                            dry_run=True,
                            emit_header=True, emit_index=True, emit_trusted_host=True,
                            annotate=True,
                            generate_hashes=False,
                            default_index_url=None, index_urls=[],
                            trusted_hosts=[],
                            format_control=FormatControl(set(), set()),
                            **kwargs)


@yield_fixture
def writer():
    yield Writer()


def test_format_requirement_annotation_editable(from_editable, writer):
    # Annotations are printed as comments at a fixed column
    ireq = from_editable('git+git://fake.org/x/y.git#egg=y')
    reverse_dependencies = {'y': ['xyz']}

    assert (writer()._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            '-e git+git://fake.org/x/y.git#egg=y  ' + comment('# via xyz'))


def test_format_requirement_annotation(from_line, writer):
    ireq = from_line('test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer()._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            'test==1.2                 ' + comment('# via xyz'))


def test_format_requirement_annotation_lower_case(from_line, writer):
    ireq = from_line('Test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer()._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            'test==1.2                 ' + comment('# via xyz'))


def test_format_requirement_not_for_primary(from_line, writer):
    "Primary packages should not get annotated."
    ireq = from_line('test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer()._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=['test']) ==
            'test==1.2')


def test_format_requirement_environment_marker(from_line, writer):
    "Environment markers should get passed through to output."
    ireq = from_line('test ; python_version == "2.7" and platform_python_implementation == "CPython"')
    reverse_dependencies = set()

    result = writer()._format_requirement(
        ireq, reverse_dependencies, primary_packages=['test'],
        marker=ireq.markers)
    assert (result ==
            'test ; python_version == "2.7" and platform_python_implementation == "CPython"')


def test_iter_lines__do_not_allow_unsafe_packages(mocker, from_line, writer):
    unsafe_package = UNSAFE_PACKAGES.copy().pop()
    unsafe_dep = '{}==1.2'.format(unsafe_package)
    ireq = from_line(unsafe_dep)
    w = writer(allow_unsafe=False)
    mocker.patch.object(w, 'write_header', return_value=['header'])
    mocker.patch.object(w, 'write_flags', return_value=['flags'])
    mocker.patch.object(w, '_sort_key', return_value=(ireq.editable, str(ireq.req).lower()))
    format_requirement = mocker.patch.object(
        w, '_format_requirement', return_value='{}'.format(unsafe_package)
    )
    comment = mocker.patch(
        'piptools.writer.comment', side_effect=['foobar', '# {}'.format(unsafe_package)])

    expected_results = ['header', 'flags', '', 'foobar', '# {}'.format(unsafe_package)]
    result = w._iter_lines([ireq], False, [], {unsafe_package: 'marker'}, 'hashes')
    for line in result:
        assert line in expected_results

    format_requirement.assert_called_once_with(
        ireq, False, [], include_specifier=False, marker='marker', hashes=None)
    comment.assert_any_call('# The following packages are considered to be unsafe in a requirements file:')
    comment.assert_any_call('# {}'.format(unsafe_package))
    assert comment.call_count == 2


def test_iter_lines__allow_unsafe_packages(mocker, from_line, writer):
    unsafe_package = UNSAFE_PACKAGES.copy().pop()
    unsafe_dep = '{}==1.2'.format(unsafe_package)
    ireq = from_line(unsafe_dep)
    w = writer(allow_unsafe=True)
    mocker.patch.object(w, 'write_header', return_value=['header'])
    mocker.patch.object(w, 'write_flags', return_value=['flags'])
    mocker.patch.object(w, '_sort_key', return_value=(ireq.editable, str(ireq.req).lower()))
    format_requirement = mocker.patch.object(
        w, '_format_requirement', return_value='{}==1.2'.format(unsafe_package)
    )
    comment = mocker.patch('piptools.writer.comment', return_value='foobar')

    result = w._iter_lines([ireq], False, [], {unsafe_package: 'marker'}, 'hashes')
    expected_results = ['header', 'flags', '', 'foobar', unsafe_dep]
    for line in result:
        assert line in expected_results


    format_requirement.assert_called_once_with(
        ireq, False, [], include_specifier=True, marker='marker', hashes='hashes')
    comment.assert_any_call('# The following packages are considered to be unsafe in a requirements file:')
    assert comment.call_count == 1
