from pytest import fixture

from pip.index import FormatControl
from piptools.utils import comment
from piptools.writer import OutputWriter


@fixture
def writer():
    return OutputWriter(src_files=["src_file", "src_file2"], dst_file="dst_file", dry_run=True,
                        emit_header=True, emit_index=True, annotate=True,
                        default_index_url=None, index_urls=[], format_control=FormatControl(set(), set()))


def test_format_requirement_annotation_editable(from_editable, writer):
    # Annotations are printed as comments at a fixed column
    ireq = from_editable('git+git://fake.org/x/y.git#egg=y')
    reverse_dependencies = {'y': ['xyz']}

    assert (writer._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            '-e git+git://fake.org/x/y.git#egg=y' + comment('  # via xyz'))


def test_format_requirement_annotation(from_line, writer):
    ireq = from_line('test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            'test==1.2               ' + comment('  # via xyz'))


def test_format_requirement_annotation_case_sensitive(from_line, writer):
    ireq = from_line('Test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=[]) ==
            'Test==1.2               ' + comment('  # via xyz'))


def test_format_requirement_not_for_primary(from_line, writer):
    "Primary packages should not get annotated."
    ireq = from_line('test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=['test']) ==
            'test==1.2')
