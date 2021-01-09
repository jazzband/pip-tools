from optparse import Values

import pytest
from pip._internal.req.req_file import ParsedLine
from pip._internal.req.req_file import get_line_parser
from pip._internal.req.req_file import handle_requirement_line

from piptools._compat.pipfile_compat import ValuesFactory
from piptools._compat.pipfile_compat import _handle_requirement


def requirement_to_dict(requirement):
    properties = ('requirement', 'is_editable', 'options', 'constraint')
    return {prop: getattr(requirement, prop) for prop in properties}


@pytest.mark.parametrize(
    "pipfile_requirement,requirement_as_text",
    [
        (('req_name', "*"), "req_name"),
        (('req_name', "==1.0"), "req_name==1.0"),
        (('req_name', ">=1.0"), "req_name>=1.0"),
        (('req_name', ">1.0, <2.0"), "req_name>1.0, <2.0"),
    ]
)
def test_pipfile_requirement(pipfile_requirement, requirement_as_text):
    filename = "no file"
    line = 0
    expected_requirement = ParsedLine(filename, line, requirement_as_text, Values(), False)

    expected_requirement = handle_requirement_line(expected_requirement)
    parsed_requirement = _handle_requirement(pipfile_requirement, filename=filename, lineno=line)

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(parsed_requirement)

@pytest.mark.parametrize(
    "pipfile_requirement,requirement_as_text",
    [
        (('req_name', dict(editable=True, path="/path/to/req")), "-e /path/to/req"),
    ]
)
def test_pipfile_requirement_editable(pipfile_requirement, requirement_as_text):
    line_parser = get_line_parser(None)

    filename = "no file"
    line = 0
    args, opts = line_parser(requirement_as_text)

    expected_requirement = handle_requirement_line(ParsedLine(filename, line, args, opts, False))
    parsed_requirement = _handle_requirement(pipfile_requirement, filename=filename, lineno=line)

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(parsed_requirement)


@pytest.mark.parametrize(
    "pipfile_requirement,requirement_as_text",
    [
        (('req_name', dict(version="*", extras=['test'])), "req_name[test]"),
        (('req_name', dict(version="==1.0", extras=['test'])), "req_name[test]==1.0"),
        (('req_name', dict(version=">=1.0", extras=['test'])), "req_name[test]>=1.0"),
        (('req_name', dict(version=">1.0, <2.0", extras=['test'])), "req_name[test]>1.0, <2.0"),
    ]
)
def test_pipfile_requirement_extras(pipfile_requirement, requirement_as_text):
    line_parser = get_line_parser(None)

    filename = "no file"
    line = 0
    args, opts = line_parser(requirement_as_text)

    expected_requirement = handle_requirement_line(ParsedLine(filename, line, args, opts, False))
    parsed_requirement = _handle_requirement(pipfile_requirement, filename=filename, lineno=line)

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(parsed_requirement)


@pytest.mark.parametrize(
    "pipfile_requirement,requirement_as_text",
    [
        (('req_name', dict(version="*", markers=['python_version>=3.6'])),
         "req_name;python_version>=3.6"),
    ]
)
def test_pipfile_requirement_environment_markers(pipfile_requirement, requirement_as_text):
    line_parser = get_line_parser(None)

    filename = "no file"
    line = 0
    args, opts = line_parser(requirement_as_text)

    expected_requirement = handle_requirement_line(ParsedLine(filename, line, args, opts, False))
    parsed_requirement = _handle_requirement(pipfile_requirement, filename=filename, lineno=line)

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(parsed_requirement)
