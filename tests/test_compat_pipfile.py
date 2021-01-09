from optparse import Values

import pytest
from pip._internal.req.req_file import ParsedLine
from pip._internal.req.req_file import handle_requirement_line

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

