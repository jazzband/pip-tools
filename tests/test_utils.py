import logging
import operator
import os
import shlex
import sys

import pip
import pytest
from pip._vendor.packaging.version import Version

from piptools.scripts.compile import cli as compile_cli
from piptools.utils import (
    as_tuple,
    dedup,
    drop_extras,
    flat_map,
    format_requirement,
    format_specifier,
    get_compile_command,
    get_hashes_from_ireq,
    get_pip_version_for_python_executable,
    get_sys_path_for_python_executable,
    is_pinned_requirement,
    is_url_requirement,
    key_from_ireq,
    lookup_table,
    lookup_table_from_tuples,
)


def test_format_requirement(from_line):
    ireq = from_line("test==1.2")
    assert format_requirement(ireq) == "test==1.2"


@pytest.mark.parametrize(
    ("line", "expected"),
    (
        pytest.param(
            "https://example.com/example.zip",
            "https://example.com/example.zip",
            id="simple url",
        ),
        pytest.param(
            "example @ https://example.com/example.zip",
            "example @ https://example.com/example.zip",
            id="direct reference",
        ),
        pytest.param(
            "Example @ https://example.com/example.zip",
            "example @ https://example.com/example.zip",
            id="direct reference lowered case",
        ),
        pytest.param(
            "example @ https://example.com/example.zip#egg=example",
            "example @ https://example.com/example.zip",
            id="direct reference with egg in fragment",
        ),
        pytest.param(
            "example @ https://example.com/example.zip#subdirectory=test&egg=example",
            "example @ https://example.com/example.zip#subdirectory=test",
            id="direct reference with subdirectory and egg in fragment",
        ),
        pytest.param(
            "example @ https://example.com/example.zip#subdirectory=test"
            "&egg=example&sha1=594b7dd32bec37d8bf70a6ffa8866d30e93f3c42",
            "example @ https://example.com/example.zip#subdirectory=test"
            "&sha1=594b7dd32bec37d8bf70a6ffa8866d30e93f3c42",
            id="direct reference with subdirectory, hash and egg in fragment",
        ),
        pytest.param(
            "example @ https://example.com/example.zip?egg=test",
            "example @ https://example.com/example.zip?egg=test",
            id="direct reference with egg in query",
        ),
        pytest.param(
            "file:./vendor/package.zip",
            "file:./vendor/package.zip",
            id="file scheme relative path",
        ),
        pytest.param(
            "file:vendor/package.zip",
            "file:vendor/package.zip",
            id="file scheme relative path",
        ),
        pytest.param(
            "file:vendor/package.zip#egg=example",
            "file:vendor/package.zip#egg=example",
            id="file scheme relative path with egg",
        ),
        pytest.param(
            "file:./vendor/package.zip#egg=example",
            "file:./vendor/package.zip#egg=example",
            id="file scheme relative path with egg",
        ),
        pytest.param(
            "file:///vendor/package.zip",
            "file:///vendor/package.zip",
            id="file scheme absolute path without direct reference",
        ),
        pytest.param(
            "file:///vendor/package.zip#egg=test",
            "test @ file:///vendor/package.zip",
            id="file scheme absolute path with egg",
        ),
        pytest.param(
            "package @ file:///vendor/package.zip",
            "package @ file:///vendor/package.zip",
            id="file scheme absolute path with direct reference",
        ),
        pytest.param(
            "package @ file:///vendor/package.zip#egg=example",
            "package @ file:///vendor/package.zip",
            id="file scheme absolute path with direct reference and egg",
        ),
        pytest.param(
            "package @ file:///vendor/package.zip#egg=example&subdirectory=test"
            "&sha1=594b7dd32bec37d8bf70a6ffa8866d30e93f3c42",
            "package @ file:///vendor/package.zip#subdirectory=test"
            "&sha1=594b7dd32bec37d8bf70a6ffa8866d30e93f3c42",
            id="full path with direct reference, egg, subdirectory and hash",
        ),
    ),
)
def test_format_requirement_url(from_line, line, expected):
    ireq = from_line(line)
    assert format_requirement(ireq) == expected


def test_format_requirement_editable_vcs(from_editable):
    ireq = from_editable("git+git://fake.org/x/y.git#egg=y")
    assert format_requirement(ireq) == "-e git+git://fake.org/x/y.git#egg=y"


def test_format_requirement_editable_vcs_with_password(from_editable):
    ireq = from_editable("git+git://user:password@fake.org/x/y.git#egg=y")
    assert (
        format_requirement(ireq) == "-e git+git://user:password@fake.org/x/y.git#egg=y"
    )


def test_format_requirement_editable_local_path(from_editable):
    ireq = from_editable("file:///home/user/package")
    assert format_requirement(ireq) == "-e file:///home/user/package"


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


def test_format_specifier(from_line, from_editable):
    ireq = from_line("foo")
    assert format_specifier(ireq) == "<any>"

    ireq = from_line("foo==1.2")
    assert format_specifier(ireq) == "==1.2"

    ireq = from_line("foo>1.2,~=1.1,<1.5")
    assert format_specifier(ireq) == "~=1.1,>1.2,<1.5"
    ireq = from_line("foo~=1.1,<1.5,>1.2")
    assert format_specifier(ireq) == "~=1.1,>1.2,<1.5"

    ireq = from_editable("git+https://github.com/django/django.git#egg=django")
    assert format_specifier(ireq) == "<any>"
    ireq = from_editable("file:///home/user/package")
    assert format_specifier(ireq) == "<any>"


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
        with pytest.raises(TypeError):
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
    expected = {
        "sha256:d1d6729c85acea5423671382868627129432fba9a89ecbb248d8d1c7a9f01c67",
        "sha256:f5c056e8f62d45ba8215e5cb8f50dfccb198b4b9fbea8500674f3443e4689589",
    }
    assert get_hashes_from_ireq(ireq) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    (
        ("django==1.8", True),
        ("django===1.8", True),
        ("django>1.8", False),
        ("django~=1.8", False),
        ("django==1.*", False),
        ("file:///example.zip", False),
        ("https://example.com/example.zip", False),
    ),
)
def test_is_pinned_requirement(from_line, line, expected):
    ireq = from_line(line)
    assert is_pinned_requirement(ireq) is expected


def test_is_pinned_requirement_editable(from_editable):
    ireq = from_editable("git+git://fake.org/x/y.git#egg=y")
    assert not is_pinned_requirement(ireq)


def test_key_from_ireq_normalization(from_line):
    keys = set()
    for line in ("zope.event", "zope-event", "zope_event", "ZOPE.event"):
        keys.add(key_from_ireq(from_line(line)))
    assert len(keys) == 1


@pytest.mark.parametrize(
    ("line", "expected"),
    (
        ("django==1.8", False),
        ("django", False),
        ("file:///example.zip", True),
        ("https://example.com/example.zip", True),
        ("https://example.com/example.zip#egg=example", True),
        ("git+https://github.com/jazzband/pip-tools@master", True),
    ),
)
def test_is_url_requirement(caplog, from_line, line, expected):
    ireq = from_line(line)
    assert is_url_requirement(ireq) is expected


@pytest.mark.parametrize("line", ("../example.zip", "/example.zip"))
def test_is_url_requirement_filename(caplog, from_line, line):
    # Ignore warning:
    #
    #     Requirement '../example.zip' looks like a filename, but the file does
    #     not exist
    caplog.set_level(logging.ERROR, logger="pip")
    ireq = from_line(line)
    assert is_url_requirement(ireq) is True


@pytest.mark.parametrize(
    ("cli_args", "expected_command"),
    (
        # Check empty args
        ([], "pip-compile"),
        # Check all options which will be excluded from command
        (["-v"], "pip-compile"),
        (["--verbose"], "pip-compile"),
        (["-n"], "pip-compile"),
        (["--dry-run"], "pip-compile"),
        (["-q"], "pip-compile"),
        (["--quiet"], "pip-compile"),
        (["-r"], "pip-compile"),
        (["--rebuild"], "pip-compile"),
        (["-U"], "pip-compile"),
        (["--upgrade"], "pip-compile"),
        (["-P", "django"], "pip-compile"),
        (["--upgrade-package", "django"], "pip-compile"),
        # Check options
        (["--max-rounds", "42"], "pip-compile --max-rounds=42"),
        (["--index-url", "https://foo"], "pip-compile --index-url=https://foo"),
        # Check that short options will be expanded to long options
        (["-p"], "pip-compile --pre"),
        (["-f", "links"], "pip-compile --find-links=links"),
        (["-i", "https://foo"], "pip-compile --index-url=https://foo"),
        # Check positive flags
        (["--generate-hashes"], "pip-compile --generate-hashes"),
        (["--pre"], "pip-compile --pre"),
        (["--allow-unsafe"], "pip-compile --allow-unsafe"),
        # Check negative flags
        (["--no-emit-index-url"], "pip-compile --no-emit-index-url"),
        (["--no-emit-trusted-host"], "pip-compile --no-emit-trusted-host"),
        (["--no-annotate"], "pip-compile --no-annotate"),
        (["--no-allow-unsafe"], "pip-compile"),
        (["--no-emit-options"], "pip-compile --no-emit-options"),
        # Check that default values will be removed from the command
        (["--emit-trusted-host"], "pip-compile"),
        (["--emit-options"], "pip-compile"),
        (["--annotate"], "pip-compile"),
        (["--emit-index-url"], "pip-compile"),
        (["--max-rounds=10"], "pip-compile"),
        (["--build-isolation"], "pip-compile"),
        # Check options with multiple values
        (
            ["--find-links", "links1", "--find-links", "links2"],
            "pip-compile --find-links=links1 --find-links=links2",
        ),
        # Check that option values will be quoted
        (["-f", "foo;bar"], "pip-compile --find-links='foo;bar'"),
        (["-f", "συνδέσεις"], "pip-compile --find-links='συνδέσεις'"),
        (["-o", "my file.txt"], "pip-compile --output-file='my file.txt'"),
        (["-o", "απαιτήσεις.txt"], "pip-compile --output-file='απαιτήσεις.txt'"),
        # Check '--pip-args' (forwarded) arguments
        (
            ["--pip-args", "--disable-pip-version-check"],
            "pip-compile --pip-args='--disable-pip-version-check'",
        ),
        (
            ["--pip-args", "--disable-pip-version-check --isolated"],
            "pip-compile --pip-args='--disable-pip-version-check --isolated'",
        ),
        pytest.param(
            ["--extra-index-url", "https://username:password@example.com/"],
            "pip-compile --extra-index-url='https://username:****@example.com/'",
            id="redact password in index",
        ),
        pytest.param(
            ["--find-links", "https://username:password@example.com/"],
            "pip-compile --find-links='https://username:****@example.com/'",
            id="redact password in link",
        ),
    ),
)
def test_get_compile_command(tmpdir_cwd, cli_args, expected_command):
    """
    Test general scenarios for the get_compile_command function.
    """
    with compile_cli.make_context("pip-compile", cli_args) as ctx:
        assert get_compile_command(ctx) == expected_command


def test_get_compile_command_escaped_filenames(tmpdir_cwd):
    """
    Test that get_compile_command output (re-)escapes ' -- '-escaped filenames.
    """
    with open("--requirements.in", "w"):
        pass
    with compile_cli.make_context("pip-compile", ["--", "--requirements.in"]) as ctx:
        assert get_compile_command(ctx) == "pip-compile -- --requirements.in"


@pytest.mark.parametrize(
    "filename", ("requirements.in", "my requirements.in", "απαιτήσεις.txt")
)
def test_get_compile_command_with_files(tmpdir_cwd, filename):
    """
    Test that get_compile_command returns a command with correct
    and sanitized file names.
    """
    os.mkdir("sub")

    path = os.path.join("sub", filename)
    with open(path, "w"):
        pass

    args = [path, "--output-file", "requirements.txt"]
    with compile_cli.make_context("pip-compile", args) as ctx:
        assert (
            get_compile_command(ctx)
            == f"pip-compile --output-file=requirements.txt {shlex.quote(path)}"
        )


def test_get_compile_command_sort_args(tmpdir_cwd):
    """
    Test that get_compile_command correctly sorts arguments.

    The order is "pip-compile {sorted options} {sorted src files}".
    """
    with open("setup.py", "w"), open("requirements.in", "w"):
        pass

    args = [
        "--no-emit-index-url",
        "--no-emit-trusted-host",
        "--no-annotate",
        "setup.py",
        "--find-links",
        "foo",
        "--find-links",
        "bar",
        "requirements.in",
    ]
    with compile_cli.make_context("pip-compile", args) as ctx:
        assert get_compile_command(ctx) == (
            "pip-compile --find-links=bar --find-links=foo "
            "--no-annotate --no-emit-index-url --no-emit-trusted-host "
            "requirements.in setup.py"
        )


@pytest.mark.parametrize(
    "tuples",
    (
        (("f", "foo"), ("b", "bar"), ("b", "baz"), ("q", "qux"), ("q", "quux")),
        iter((("f", "foo"), ("b", "bar"), ("b", "baz"), ("q", "qux"), ("q", "quux"))),
    ),
)
def test_lookup_table_from_tuples(tuples):
    expected = {"b": {"bar", "baz"}, "f": {"foo"}, "q": {"quux", "qux"}}
    assert lookup_table_from_tuples(tuples) == expected


@pytest.mark.parametrize(
    ("values", "key"),
    (
        (("foo", "bar", "baz", "qux", "quux"), operator.itemgetter(0)),
        (iter(("foo", "bar", "baz", "qux", "quux")), operator.itemgetter(0)),
    ),
)
def test_lookup_table(values, key):
    expected = {"b": {"bar", "baz"}, "f": {"foo"}, "q": {"quux", "qux"}}
    assert lookup_table(values, key) == expected


def test_lookup_table_from_tuples_with_empty_values():
    assert lookup_table_from_tuples(()) == {}


def test_lookup_table_with_empty_values():
    assert lookup_table((), operator.itemgetter(0)) == {}


@pytest.mark.parametrize(
    ("given", "expected"),
    (
        ("", None),
        ("extra == 'dev'", None),
        ("extra == 'dev' or extra == 'test'", None),
        ("os_name == 'nt' and extra == 'dev'", "os_name == 'nt'"),
        ("extra == 'dev' and os_name == 'nt'", "os_name == 'nt'"),
        ("os_name == 'nt' or extra == 'dev'", "os_name == 'nt'"),
        ("extra == 'dev' or os_name == 'nt'", "os_name == 'nt'"),
        ("(extra == 'dev') or os_name == 'nt'", "os_name == 'nt'"),
        ("os_name == 'nt' and (extra == 'dev' or extra == 'test')", "os_name == 'nt'"),
        ("os_name == 'nt' or (extra == 'dev' or extra == 'test')", "os_name == 'nt'"),
        ("(extra == 'dev' or extra == 'test') or os_name == 'nt'", "os_name == 'nt'"),
        ("(extra == 'dev' or extra == 'test') and os_name == 'nt'", "os_name == 'nt'"),
        (
            "os_name == 'nt' or (os_name == 'unix' and extra == 'test')",
            "os_name == 'nt' or os_name == 'unix'",
        ),
        (
            "(os_name == 'unix' and extra == 'test') or os_name == 'nt'",
            "os_name == 'unix' or os_name == 'nt'",
        ),
        (
            "(os_name == 'unix' or extra == 'test') and os_name == 'nt'",
            "os_name == 'unix' and os_name == 'nt'",
        ),
        (
            "(os_name == 'unix' or os_name == 'nt') and extra == 'dev'",
            "os_name == 'unix' or os_name == 'nt'",
        ),
        (
            "(os_name == 'unix' and extra == 'test' or python_version < '3.5')"
            " or os_name == 'nt'",
            "(os_name == 'unix' or python_version < '3.5') or os_name == 'nt'",
        ),
        (
            "os_name == 'unix' and extra == 'test' or os_name == 'nt'",
            "os_name == 'unix' or os_name == 'nt'",
        ),
        (
            "os_name == 'unix' or extra == 'test' and os_name == 'nt'",
            "os_name == 'unix' or os_name == 'nt'",
        ),
    ),
)
def test_drop_extras(from_line, given, expected):
    ireq = from_line(f"test;{given}")
    drop_extras(ireq)
    if expected is None:
        assert ireq.markers is None
    else:
        assert str(ireq.markers).replace("'", '"') == expected.replace("'", '"')


def test_get_pip_version_for_python_executable():
    result = get_pip_version_for_python_executable(sys.executable)
    assert Version(pip.__version__) == result


def test_get_sys_path_for_python_executable():
    result = get_sys_path_for_python_executable(sys.executable)
    assert result, "get_sys_path_for_python_executable should not return empty result"
    # not testing for equality, because pytest adds extra paths into current sys.path
    for path in result:
        assert path in sys.path
