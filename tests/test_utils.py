import six
from pytest import mark, raises

from piptools.utils import (
    as_tuple,
    dedup,
    flat_map,
    format_requirement,
    format_specifier,
    fs_str,
    get_hashes_from_ireq,
    is_pinned_requirement,
    name_from_req,
)


def test_format_requirement(from_line):
    ireq = from_line("test==1.2")
    assert format_requirement(ireq) == "test==1.2"


def test_format_requirement_editable(from_editable):
    ireq = from_editable("git+git://fake.org/x/y.git#egg=y")
    assert format_requirement(ireq) == "-e git+git://fake.org/x/y.git#egg=y"


def test_format_requirement_ireq_with_hashes(from_line):
    ireq = from_line("pytz==2017.2")
    ireq_hashes = [
        "sha256:d1d6729c85acea5423671382868627129432fba9a89ecbb248d8d1c7a9f01c67",
        "sha256:f5c056e8f62d45ba8215e5cb8f50dfccb198b4b9fbea8500674f3443e4689589",
    ]

    expected = (
        "pytz==2017.2 \\\n"
        "    --hash=sha256:d1d6729c85acea542367138286"
        "8627129432fba9a89ecbb248d8d1c7a9f01c67 \\\n"
        "    --hash=sha256:f5c056e8f62d45ba8215e5cb8f5"
        "0dfccb198b4b9fbea8500674f3443e4689589"
    )
    assert format_requirement(ireq, hashes=ireq_hashes) == expected


def test_format_requirement_ireq_with_hashes_and_markers(from_line):
    ireq = from_line("pytz==2017.2")
    marker = 'python_version<"3.0"'
    ireq_hashes = [
        "sha256:d1d6729c85acea5423671382868627129432fba9a89ecbb248d8d1c7a9f01c67",
        "sha256:f5c056e8f62d45ba8215e5cb8f50dfccb198b4b9fbea8500674f3443e4689589",
    ]

    expected = (
        'pytz==2017.2 ; python_version<"3.0" \\\n'
        "    --hash=sha256:d1d6729c85acea542367138286"
        "8627129432fba9a89ecbb248d8d1c7a9f01c67 \\\n"
        "    --hash=sha256:f5c056e8f62d45ba8215e5cb8f5"
        "0dfccb198b4b9fbea8500674f3443e4689589"
    )
    assert format_requirement(ireq, marker, hashes=ireq_hashes) == expected


def test_format_specifier(from_line):
    ireq = from_line("foo")
    assert format_specifier(ireq) == "<any>"

    ireq = from_line("foo==1.2")
    assert format_specifier(ireq) == "==1.2"

    ireq = from_line("foo>1.2,~=1.1,<1.5")
    assert format_specifier(ireq) == "~=1.1,>1.2,<1.5"
    ireq = from_line("foo~=1.1,<1.5,>1.2")
    assert format_specifier(ireq) == "~=1.1,>1.2,<1.5"


def test_as_tuple(from_line):
    ireq = from_line("foo==1.1")
    name, version, extras = as_tuple(ireq)
    assert name == "foo"
    assert version == "1.1"
    assert extras == ()

    ireq = from_line("foo[extra1,extra2]==1.1")
    name, version, extras = as_tuple(ireq)
    assert name == "foo"
    assert version == "1.1"
    assert extras == ("extra1", "extra2")

    # Non-pinned versions aren't accepted
    should_be_rejected = ["foo==1.*", "foo~=1.1,<1.5,>1.2", "foo"]
    for spec in should_be_rejected:
        ireq = from_line(spec)
        with raises(TypeError):
            as_tuple(ireq)


def test_flat_map():
    assert [1, 2, 4, 1, 3, 9] == list(flat_map(lambda x: [1, x, x * x], [2, 3]))


def test_dedup():
    assert list(dedup([3, 1, 2, 4, 3, 5])) == [3, 1, 2, 4, 5]


def test_get_hashes_from_ireq(from_line):
    ireq = from_line(
        "pytz==2017.2",
        options={
            "hashes": {
                "sha256": [
                    "d1d6729c85acea5423671382868627129432fba9a89ecbb248d8d1c7a9f01c67",
                    "f5c056e8f62d45ba8215e5cb8f50dfccb198b4b9fbea8500674f3443e4689589",
                ]
            }
        },
    )
    expected = [
        "sha256:d1d6729c85acea5423671382868627129432fba9a89ecbb248d8d1c7a9f01c67",
        "sha256:f5c056e8f62d45ba8215e5cb8f50dfccb198b4b9fbea8500674f3443e4689589",
    ]
    assert get_hashes_from_ireq(ireq) == expected


@mark.parametrize(
    ("line", "expected"),
    [
        ("django==1.8", True),
        ("django===1.8", True),
        ("django>1.8", False),
        ("django~=1.8", False),
        ("django==1.*", False),
    ],
)
def test_is_pinned_requirement(from_line, line, expected):
    ireq = from_line(line)
    assert is_pinned_requirement(ireq) is expected


def test_is_pinned_requirement_editable(from_editable):
    ireq = from_editable("git+git://fake.org/x/y.git#egg=y")
    assert not is_pinned_requirement(ireq)


def test_name_from_req(from_line):
    ireq = from_line("django==1.8")
    assert name_from_req(ireq.req) == "django"


def test_name_from_req_with_project_name(from_line):
    ireq = from_line("foo==1.8")
    ireq.req.project_name = "bar"
    assert name_from_req(ireq.req) == "bar"


def test_fs_str():
    assert fs_str(u"some path component/Something") == "some path component/Something"
    assert isinstance(fs_str("whatever"), str)
    assert isinstance(fs_str(u"whatever"), str)


@mark.skipif(six.PY2, reason="Not supported in py2")
def test_fs_str_with_bytes():
    with raises(AssertionError):
        fs_str(b"whatever")
