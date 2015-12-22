from pytest import fixture

from piptools.utils import comment
from piptools.writer import OutputWriter


@fixture
def writer():
    return OutputWriter(src_file="src_file", dry_run=True, header=True,
                        annotate=True, default_index_url=None, index_urls=[])


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


def test_format_requirement_not_for_primary(from_line, writer):
    "Primary packages should not get annotated."
    ireq = from_line('test==1.2')
    reverse_dependencies = {'test': ['xyz']}

    assert (writer._format_requirement(ireq,
                                       reverse_dependencies,
                                       primary_packages=['test']) ==
            'test==1.2')


def test_footer_output(from_line, writer):
    """Test that footer output is not suppressed by default."""
    ireq = from_line('setuptools')
    reverse_dependencies = {'test': ['setuptools']}
    lines = list(writer._iter_lines([ireq],
                                    reverse_dependencies,
                                    primary_packages=[]))
    # In this case, the commented requirement is expected to be in the
    # last line of the output.
    assert '# setuptools' in lines[-1]


def test_footer_output_suppression(from_line, writer):
    """Test that footer output is suppressed when it should be."""
    # Set the writer to omit the footer in this case.
    writer.footer = False
    ireq = from_line('setuptools')
    reverse_dependencies = {'test': ['setuptools']}
    lines = list(writer._iter_lines([ireq],
                                    reverse_dependencies,
                                    primary_packages=[]))
    # The commented requirement would normally be expected to be in the
    # last line of the output. Because the footer is disabled, we assert
    # that this line is not present.
    assert '# setuptools' not in lines[-1]
