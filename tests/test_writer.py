import sys

import pytest
from pip._internal.models.format_control import FormatControl

from piptools.scripts.compile import cli
from piptools.utils import comment
from piptools.writer import (
    MESSAGE_UNHASHED_PACKAGE,
    MESSAGE_UNINSTALLABLE,
    MESSAGE_UNSAFE_PACKAGES,
    MESSAGE_UNSAFE_PACKAGES_UNPINNED,
    OutputWriter,
)


@pytest.fixture
def writer(tmpdir_cwd):
    with open("src_file", "w"), open("src_file2", "w"):
        pass

    cli_args = [
        "--dry-run",
        "--output-file",
        "requirements.txt",
        "src_file",
        "src_file2",
    ]

    with cli.make_context("pip-compile", cli_args) as ctx:
        writer = OutputWriter(
            dst_file=ctx.params["output_file"],
            click_ctx=ctx,
            dry_run=True,
            emit_header=True,
            emit_index_url=True,
            emit_trusted_host=True,
            annotate=True,
            annotation_style="split",
            generate_hashes=False,
            default_index_url=None,
            index_urls=[],
            trusted_hosts=[],
            format_control=FormatControl(set(), set()),
            allow_unsafe=False,
            find_links=[],
            emit_find_links=True,
            strip_extras=False,
            emit_options=True,
        )
        yield writer


def test_format_requirement_annotation_editable(from_editable, writer):
    # Annotations are printed as comments at a fixed column
    ireq = from_editable("git+git://fake.org/x/y.git#egg=y")
    ireq.comes_from = "xyz"

    assert writer._format_requirement(
        ireq
    ) == "-e git+git://fake.org/x/y.git#egg=y\n    " + comment("# via xyz")


def test_format_requirement_annotation(from_line, writer):
    ireq = from_line("test==1.2")
    ireq.comes_from = "xyz"

    assert writer._format_requirement(ireq) == "test==1.2\n    " + comment("# via xyz")


def test_format_requirement_annotation_lower_case(from_line, writer):
    ireq = from_line("Test==1.2")
    ireq.comes_from = "xyz"

    assert writer._format_requirement(ireq) == "test==1.2\n    " + comment("# via xyz")


def test_format_requirement_for_primary(from_line, writer):
    "Primary packages should get annotated."
    ireq = from_line("test==1.2")
    ireq.comes_from = "xyz"

    assert writer._format_requirement(ireq) == "test==1.2\n    " + comment("# via xyz")


def test_format_requirement_for_primary_lower_case(from_line, writer):
    "Primary packages should get annotated."
    ireq = from_line("Test==1.2")
    ireq.comes_from = "xyz"

    assert writer._format_requirement(ireq) == "test==1.2\n    " + comment("# via xyz")


def test_format_requirement_environment_marker(from_line, writer):
    "Environment markers should get passed through to output."
    ireq = from_line(
        'test ; python_version == "2.7" and platform_python_implementation == "CPython"'
    )

    result = writer._format_requirement(ireq, marker=ireq.markers)
    assert (
        result == 'test ; python_version == "2.7" and '
        'platform_python_implementation == "CPython"'
    )


@pytest.mark.parametrize("allow_unsafe", ((True,), (False,)))
def test_iter_lines__unsafe_dependencies(writer, from_line, allow_unsafe):
    writer.allow_unsafe = allow_unsafe
    writer.emit_header = False

    lines = writer._iter_lines(
        [from_line("test==1.2")], [from_line("setuptools==1.10.0")]
    )

    expected_lines = (
        "test==1.2",
        "",
        MESSAGE_UNSAFE_PACKAGES,
        "setuptools==1.10.0" if allow_unsafe else comment("# setuptools"),
    )
    assert tuple(lines) == expected_lines


def test_iter_lines__unsafe_with_hashes(capsys, writer, from_line):
    writer.allow_unsafe = False
    writer.emit_header = False
    ireqs = [from_line("test==1.2")]
    unsafe_ireqs = [from_line("setuptools==1.10.0")]
    hashes = {ireqs[0]: {"FAKEHASH"}, unsafe_ireqs[0]: set()}

    lines = writer._iter_lines(ireqs, unsafe_ireqs, hashes=hashes)

    expected_lines = (
        "test==1.2 \\\n    --hash=FAKEHASH",
        "",
        MESSAGE_UNSAFE_PACKAGES_UNPINNED,
        comment("# setuptools"),
    )
    assert tuple(lines) == expected_lines
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == MESSAGE_UNINSTALLABLE


def test_iter_lines__hash_missing(capsys, writer, from_line):
    writer.allow_unsafe = False
    writer.emit_header = False
    ireqs = [from_line("test==1.2"), from_line("file:///example/#egg=example")]
    hashes = {ireqs[0]: {"FAKEHASH"}, ireqs[1]: set()}

    lines = writer._iter_lines(ireqs, hashes=hashes)

    expected_lines = (
        MESSAGE_UNHASHED_PACKAGE,
        "example @ file:///example/",
        "test==1.2 \\\n    --hash=FAKEHASH",
    )
    assert tuple(lines) == expected_lines
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == MESSAGE_UNINSTALLABLE


def test_iter_lines__no_warn_if_only_unhashable_packages(writer, from_line):
    """
    There shouldn't be MESSAGE_UNHASHED_PACKAGE warning if there are only unhashable
    packages. See GH-1101.
    """
    writer.allow_unsafe = False
    writer.emit_header = False
    ireqs = [
        from_line("file:///unhashable-pkg1/#egg=unhashable-pkg1"),
        from_line("file:///unhashable-pkg2/#egg=unhashable-pkg2"),
    ]
    hashes = {ireq: set() for ireq in ireqs}

    lines = writer._iter_lines(ireqs, hashes=hashes)

    expected_lines = (
        "unhashable-pkg1 @ file:///unhashable-pkg1/",
        "unhashable-pkg2 @ file:///unhashable-pkg2/",
    )
    assert tuple(lines) == expected_lines


def test_write_header(writer):
    expected = map(
        comment,
        [
            "#",
            "# This file is autogenerated by pip-compile with python "
            f"{sys.version_info.major}.{sys.version_info.minor}",
            "# To update, run:",
            "#",
            "#    pip-compile --output-file={} src_file src_file2".format(
                writer.click_ctx.params["output_file"].name
            ),
            "#",
        ],
    )
    assert list(writer.write_header()) == list(expected)


def test_write_header_custom_compile_command(writer, monkeypatch):
    monkeypatch.setenv("CUSTOM_COMPILE_COMMAND", "./pipcompilewrapper")
    expected = map(
        comment,
        [
            "#",
            "# This file is autogenerated by pip-compile with python "
            f"{sys.version_info.major}.{sys.version_info.minor}",
            "# To update, run:",
            "#",
            "#    ./pipcompilewrapper",
            "#",
        ],
    )
    assert list(writer.write_header()) == list(expected)


def test_write_header_no_emit_header(writer):
    """
    There should not be headers if emit_header is False
    """
    writer.emit_header = False

    with pytest.raises(StopIteration):
        next(writer.write_header())


@pytest.mark.parametrize(
    ("emit_options", "expected_flags"),
    (
        pytest.param(
            True,
            (
                "--index-url https://index-server",
                "--find-links links",
                "--trusted-host index-server",
                "--no-binary flask",
                "--only-binary django",
                "",
            ),
            id="on",
        ),
        pytest.param(False, (), id="off"),
    ),
)
def test_write_flags_emit_options(writer, emit_options, expected_flags):
    """
    There should be options if emit_options is True
    """
    writer.emit_options = emit_options
    writer.index_urls = ["https://index-server"]
    writer.find_links = ["links"]
    writer.trusted_hosts = ["index-server"]
    writer.format_control = FormatControl(no_binary=["flask"], only_binary=["django"])

    assert tuple(writer.write_flags()) == expected_flags


def test_write_format_controls(writer):
    """
    Tests --no-binary/--only-binary options.
    """

    # FormatControl actually expects sets, but we give it lists here to
    # ensure that we are sorting them when writing.
    writer.format_control = FormatControl(
        no_binary=["psycopg2", "click"], only_binary=["pytz", "django"]
    )
    lines = list(writer.write_format_controls())

    expected_lines = [
        "--no-binary click",
        "--no-binary psycopg2",
        "--only-binary django",
        "--only-binary pytz",
    ]
    assert lines == expected_lines


@pytest.mark.parametrize(
    ("index_urls", "expected_lines"),
    (
        # No urls - no options
        ([], []),
        # Single URL should be index-url
        (["https://index-url.com"], ["--index-url https://index-url.com"]),
        # First URL should be index-url, the others should be extra-index-url
        (
            [
                "https://index-url1.com",
                "https://index-url2.com",
                "https://index-url3.com",
            ],
            [
                "--index-url https://index-url1.com",
                "--extra-index-url https://index-url2.com",
                "--extra-index-url https://index-url3.com",
            ],
        ),
        # If a first URL equals to the default URL, the the index url must not be set
        # and the others should be extra-index-url
        (
            [
                "https://default-index-url.com",
                "https://index-url1.com",
                "https://index-url2.com",
            ],
            [
                "--extra-index-url https://index-url1.com",
                "--extra-index-url https://index-url2.com",
            ],
        ),
        # Not ignore URLs equal to the default index-url
        # (note: the previous case is exception)
        (
            [
                "https://index-url1.com",
                "https://default-index-url.com",
                "https://index-url2.com",
            ],
            [
                "--index-url https://index-url1.com",
                "--extra-index-url https://default-index-url.com",
                "--extra-index-url https://index-url2.com",
            ],
        ),
        # Ignore URLs equal to the default index-url
        (["https://default-index-url.com", "https://default-index-url.com"], []),
        # All URLs must be deduplicated
        (
            [
                "https://index-url1.com",
                "https://index-url1.com",
                "https://index-url2.com",
            ],
            [
                "--index-url https://index-url1.com",
                "--extra-index-url https://index-url2.com",
            ],
        ),
    ),
)
def test_write_index_options(writer, index_urls, expected_lines):
    """
    Test write_index_options method.
    """
    writer.index_urls = index_urls
    writer.default_index_url = "https://default-index-url.com"
    assert list(writer.write_index_options()) == expected_lines


def test_write_index_options_no_emit_index(writer):
    """
    There should not be --index-url/--extra-index-url options
    if emit_index_url is False.
    """
    writer.emit_index_url = False
    with pytest.raises(StopIteration):
        next(writer.write_index_options())


@pytest.mark.parametrize(
    ("find_links", "expected_lines"),
    (
        ([], []),
        (["./foo"], ["--find-links ./foo"]),
        (["./foo", "./bar"], ["--find-links ./foo", "--find-links ./bar"]),
    ),
)
def test_write_find_links(writer, find_links, expected_lines):
    """
    Test write_find_links method.
    """
    writer.find_links = find_links
    assert list(writer.write_find_links()) == expected_lines


def test_write_order(writer, from_line):
    """
    Order of packages should match that of `pip freeze`, with the exception
    that requirement names should be canonicalized.
    """
    writer.emit_header = False

    packages = [
        from_line("package_a==0.1"),
        from_line("Package-b==2.3.4"),
        from_line("Package==5.6"),
        from_line("package2==7.8.9"),
    ]
    expected_lines = [
        "package==5.6",
        "package-a==0.1",
        "package-b==2.3.4",
        "package2==7.8.9",
    ]
    assert list(writer._iter_lines(packages)) == expected_lines
