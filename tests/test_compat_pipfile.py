import os

import pytest
from pip._internal.req.req_file import ParsedRequirement

from piptools._compat.pipfile_compat import _handle_requirement


def requirement_to_dict(requirement):
    properties = ("requirement", "is_editable", "options", "constraint")
    return {prop: getattr(requirement, prop) for prop in properties}


@pytest.mark.parametrize(
    ("pipfile_requirement", "requirement_as_text"),
    (
        (("req_name", "*"), "req_name"),
        (("req_name", "==1.0"), "req_name==1.0"),
        (("req_name", ">=1.0"), "req_name>=1.0"),
        (("req_name", ">1.0, <2.0"), "req_name>1.0, <2.0"),
    ),
)
def test_pipfile_requirement(pipfile_requirement, requirement_as_text):
    filename = "Pipfile"
    line = 0
    comes_from = f"-r {filename} (line {line})"
    line_source = f"line {line} of {filename}"

    expected_requirement = ParsedRequirement(
        requirement=requirement_as_text,
        is_editable=False,
        comes_from=comes_from,
        constraint=False,
        options={},
        line_source=line_source,
    )

    parsed_requirement = _handle_requirement(
        pipfile_requirement, filename=filename, lineno=line
    )

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(
        parsed_requirement
    )


@pytest.mark.parametrize(
    ("pipfile_requirement", "requirement_as_text"),
    (
        (
            ("req_name", dict(editable=True, path="/path/to/req")),
            os.path.abspath("/path/to/req"),
        ),
        (
            ("req_name", dict(editable=True, path="/path/to/req", extras=["extra"])),
            os.path.abspath("/path/to/req") + "[extra]",
        ),
    ),
)
def test_pipfile_requirement_editable(pipfile_requirement, requirement_as_text):
    filename = "Pipfile"
    line = 0
    comes_from = f"-r {filename} (line {line})"
    expected_requirement = ParsedRequirement(
        requirement=requirement_as_text,
        is_editable=True,
        comes_from=comes_from,
        constraint=False,
    )

    parsed_requirement = _handle_requirement(
        pipfile_requirement, filename=filename, lineno=line
    )

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(
        parsed_requirement
    )


@pytest.mark.parametrize(
    ("pipfile_requirement", "requirement_as_text"),
    (
        (("req_name", dict(version="*", extras=["test"])), "req_name[test]"),
        (("req_name", dict(version="==1.0", extras=["test"])), "req_name[test]==1.0"),
        (("req_name", dict(version=">=1.0", extras=["test"])), "req_name[test]>=1.0"),
        (
            ("req_name", dict(version=">1.0, <2.0", extras=["test"])),
            "req_name[test]>1.0, <2.0",
        ),
    ),
)
def test_pipfile_requirement_extras(pipfile_requirement, requirement_as_text):
    filename = "Pipfile"
    line = 0
    comes_from = f"-r {filename} (line {line})"
    line_source = f"line {line} of {filename}"

    expected_requirement = ParsedRequirement(
        requirement=requirement_as_text,
        is_editable=False,
        comes_from=comes_from,
        constraint=False,
        options={},
        line_source=line_source,
    )

    parsed_requirement = _handle_requirement(
        pipfile_requirement, filename=filename, lineno=line
    )

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(
        parsed_requirement
    )


@pytest.mark.parametrize(
    ("pipfile_requirement", "requirement_as_text"),
    (
        (
            ("req_name", dict(version="*", markers=["python_version>=3.6"])),
            "req_name;python_version>=3.6",
        ),
    ),
)
def test_pipfile_requirement_environment_markers(
    pipfile_requirement, requirement_as_text
):
    filename = "Pipfile"
    line = 0
    comes_from = f"-r {filename} (line {line})"
    line_source = f"line {line} of {filename}"

    expected_requirement = ParsedRequirement(
        requirement=requirement_as_text,
        is_editable=False,
        comes_from=comes_from,
        constraint=False,
        options={},
        line_source=line_source,
    )

    parsed_requirement = _handle_requirement(
        pipfile_requirement, filename=filename, lineno=line
    )

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(
        parsed_requirement
    )


@pytest.mark.parametrize(
    ("pipfile_requirement", "requirement_as_text"),
    (
        (("req_name", dict(file="/path/to/req.zip")), "/path/to/req.zip"),
        (("req_name", dict(file="/path/to/req.whl")), "/path/to/req.whl"),
        (
            ("req_name", dict(git="https://github.com/nobody/nothing.git", ref="1.0")),
            "git+https://github.com/nobody/nothing.git@1.0#egg=req_name",
        ),
        (
            ("req_name", dict(git="git@github.com/nobody/nothing.git", ref="1.0")),
            "git+git@github.com/nobody/nothing.git@1.0#egg=req_name",
        ),
    ),
)
def test_pipfile_requirement_noindex(pipfile_requirement, requirement_as_text):
    filename = "Pipfile"
    line = 0
    comes_from = f"-r {filename} (line {line})"
    line_source = f"line {line} of {filename}"

    expected_requirement = ParsedRequirement(
        requirement=requirement_as_text,
        is_editable=False,
        comes_from=comes_from,
        constraint=False,
        options={},
        line_source=line_source,
    )

    parsed_requirement = _handle_requirement(
        pipfile_requirement, filename=filename, lineno=line
    )

    assert requirement_to_dict(expected_requirement) == requirement_to_dict(
        parsed_requirement
    )
