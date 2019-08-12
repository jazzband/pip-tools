import os
import subprocess
import sys
from textwrap import dedent

import mock
import pytest
from click.testing import CliRunner
from pytest import mark

from .utils import invoke

from piptools._compat.pip_compat import path_to_url
from piptools.repositories import PyPIRepository
from piptools.scripts.compile import cli
from piptools.utils import PIP_VERSION

TEST_DATA_PATH = os.path.join(os.path.split(__file__)[0], "test_data")
MINIMAL_WHEELS_PATH = os.path.join(TEST_DATA_PATH, "minimal_wheels")

fail_below_pip9 = pytest.mark.xfail(PIP_VERSION < (9,), reason="needs pip 9 or greater")


@pytest.fixture
def pip_conf(tmpdir, monkeypatch):
    test_conf = dedent(
        """\
        [global]
        index-url = http://example.com
        trusted-host = example.com
    """
    )

    pip_conf_file = "pip.conf" if os.name != "nt" else "pip.ini"
    path = (tmpdir / pip_conf_file).strpath

    with open(path, "w") as f:
        f.write(test_conf)

    monkeypatch.setenv("PIP_CONFIG_FILE", path)

    try:
        yield path
    finally:
        os.remove(path)


def test_default_pip_conf_read(pip_conf, runner):
    # preconditions
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(cli, ["-v"])

    # check that we have our index-url as specified in pip.conf
    assert "Using indexes:\n  http://example.com" in out.stderr
    assert "--index-url http://example.com" in out.stderr


def test_command_line_overrides_pip_conf(pip_conf, runner):
    # preconditions
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(cli, ["-v", "-i", "http://override.com"])

    # check that we have our index-url as specified in pip.conf
    assert "Using indexes:\n  http://override.com" in out.stderr


def test_command_line_setuptools_read(pip_conf, runner):
    package = open("setup.py", "w")
    package.write(
        dedent(
            """\
        from setuptools import setup
        setup(install_requires=[])
    """
        )
    )
    package.close()
    out = runner.invoke(cli)

    # check that pip-compile generated a configuration
    assert "This file is autogenerated by pip-compile" in out.stderr
    assert os.path.exists("requirements.txt")


@pytest.mark.parametrize(
    "options, expected_output_file",
    [
        # For the `pip-compile` output file should be "requirements.txt"
        ([], "requirements.txt"),
        # For the `pip-compile --output-file=output.txt`
        # output file should be "output.txt"
        (["--output-file", "output.txt"], "output.txt"),
        # For the `pip-compile setup.py` output file should be "requirements.txt"
        (["setup.py"], "requirements.txt"),
        # For the `pip-compile setup.py --output-file=output.txt`
        # output file should be "output.txt"
        (["setup.py", "--output-file", "output.txt"], "output.txt"),
    ],
)
def test_command_line_setuptools_output_file(pip_conf, options, expected_output_file):
    """
    Test the output files for setup.py as a requirement file.
    """
    runner = CliRunner(mix_stderr=False)
    with runner.isolated_filesystem():
        package = open("setup.py", "w")
        package.write(
            dedent(
                """\
            from setuptools import setup
            setup(install_requires=[])
        """
            )
        )
        package.close()

        out = runner.invoke(cli, options)
        assert out.exit_code == 0
        assert os.path.exists(expected_output_file)


def test_find_links_option(pip_conf, runner):
    with open("requirements.in", "w") as req_in:
        req_in.write("-f ./libs3")

    out = runner.invoke(cli, ["-v", "-f", "./libs1", "-f", "./libs2"])

    # Check that find-links has been passed to pip
    assert "Configuration:\n  -f ./libs1\n  -f ./libs2\n  -f ./libs3\n" in out.stderr

    # Check that find-links has been written to a requirements.txt
    with open("requirements.txt", "r") as req_txt:
        assert (
            "--find-links ./libs1\n--find-links ./libs2\n--find-links ./libs3\n"
            in req_txt.read()
        )


def test_extra_index_option(pip_conf, runner):
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(
        cli,
        [
            "-v",
            "--extra-index-url",
            "http://extraindex1.com",
            "--extra-index-url",
            "http://extraindex2.com",
        ],
    )
    assert (
        "Using indexes:\n"
        "  http://example.com\n"
        "  http://extraindex1.com\n"
        "  http://extraindex2.com" in out.stderr
    )
    assert (
        "--index-url http://example.com\n"
        "--extra-index-url http://extraindex1.com\n"
        "--extra-index-url http://extraindex2.com" in out.stderr
    )


def test_trusted_host(pip_conf, runner):
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(
        cli, ["-v", "--trusted-host", "example.com", "--trusted-host", "example2.com"]
    )
    assert "--trusted-host example.com\n" "--trusted-host example2.com\n" in out.stderr


def test_trusted_host_no_emit(pip_conf, runner):
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(
        cli, ["-v", "--trusted-host", "example.com", "--no-emit-trusted-host"]
    )
    assert "--trusted-host example.com" not in out.stderr


def test_realistic_complex_sub_dependencies(runner):
    wheels_dir = "wheels"

    # make a temporary wheel of a fake package
    subprocess.check_output(
        [
            "pip",
            "wheel",
            "--no-deps",
            "-w",
            wheels_dir,
            os.path.join(TEST_DATA_PATH, "fake_package", "."),
        ]
    )

    with open("requirements.in", "w") as req_in:
        req_in.write("fake_with_deps")  # require fake package

    out = runner.invoke(cli, ["-v", "-n", "--rebuild", "-f", wheels_dir])

    assert out.exit_code == 0


def test_run_as_module_compile():
    """piptools can be run as ``python -m piptools ...``."""

    status, output = invoke([sys.executable, "-m", "piptools", "compile", "--help"])

    # Should have run pip-compile successfully.
    output = output.decode("utf-8")
    assert output.startswith("Usage:")
    assert "Compiles requirements.txt from requirements.in" in output
    assert status == 0


def test_editable_package(runner):
    """ piptools can compile an editable """
    fake_package_dir = os.path.join(TEST_DATA_PATH, "small_fake_package")
    fake_package_dir = path_to_url(fake_package_dir)
    with open("requirements.in", "w") as req_in:
        req_in.write("-e " + fake_package_dir)  # require editable fake package

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    assert "six==1.10.0" in out.stderr


def test_editable_package_vcs(runner):
    vcs_package = (
        "git+git://github.com/jazzband/pip-tools@"
        "f97e62ecb0d9b70965c8eff952c001d8e2722e94"
        "#egg=pip-tools"
    )
    with open("requirements.in", "w") as req_in:
        req_in.write("-e " + vcs_package)
    out = runner.invoke(cli, ["-n", "--rebuild"])
    assert out.exit_code == 0
    assert vcs_package in out.stderr
    assert "click" in out.stderr  # dependency of pip-tools


def test_locally_available_editable_package_is_not_archived_in_cache_dir(
    tmpdir, runner
):
    """
    piptools will not create an archive for a locally available editable requirement
    """
    cache_dir = tmpdir.mkdir("cache_dir")

    fake_package_dir = os.path.join(TEST_DATA_PATH, "small_fake_package")
    fake_package_dir = path_to_url(fake_package_dir)

    with mock.patch("piptools.repositories.pypi.CACHE_DIR", new=str(cache_dir)):
        with open("requirements.in", "w") as req_in:
            req_in.write("-e " + fake_package_dir)  # require editable fake package

        out = runner.invoke(cli, ["-n"])

        assert out.exit_code == 0
        assert fake_package_dir in out.stderr
        assert "six==1.10.0" in out.stderr

    # we should not find any archived file in {cache_dir}/pkgs
    assert not os.listdir(os.path.join(str(cache_dir), "pkgs"))


@mark.parametrize(
    ("line", "dependency", "rewritten_line"),
    [
        # zip URL
        # use pip-tools version prior to its use of setuptools_scm,
        # which is incompatible with https: install
        (
            "https://github.com/jazzband/pip-tools/archive/"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip",
            "\nclick==",
            None,
        ),
        # scm URL
        (
            "git+git://github.com/jazzband/pip-tools@"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3",
            "\nclick==",
            None,
        ),
        # wheel URL
        (
            "https://files.pythonhosted.org/packages/06/96/"
            "89872db07ae70770fba97205b0737c17ef013d0d1c790"
            "899c16bb8bac419/pip_tools-3.6.1-py2.py3-none-any.whl",
            "\nclick==",
            None,
        ),
        # file:// wheel URL
        (
            path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
            "\nsix==",
            None,
        ),
        # file:// directory
        (
            path_to_url(os.path.join(TEST_DATA_PATH, "small_fake_package")),
            "\nsix==",
            None,
        ),
        # bare path
        # will be rewritten to file:// URL
        (
            os.path.join(
                MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
            ),
            "\nsix==",
            path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
        ),
    ],
)
@mark.parametrize(("generate_hashes",), [(True,), (False,)])
def test_url_package(runner, line, dependency, rewritten_line, generate_hashes):
    if rewritten_line is None:
        rewritten_line = line
    with open("requirements.in", "w") as req_in:
        req_in.write(line)
    out = runner.invoke(
        cli, ["-n", "--rebuild"] + (["--generate-hashes"] if generate_hashes else [])
    )
    assert out.exit_code == 0
    assert rewritten_line in out.stderr
    assert dependency in out.stderr


def test_input_file_without_extension(runner):
    """
    piptools can compile a file without an extension,
    and add .txt as the defaut output file extension.
    """
    with open("requirements", "w") as req_in:
        req_in.write("six==1.10.0")

    out = runner.invoke(cli, ["requirements"])

    assert out.exit_code == 0
    assert "six==1.10.0" in out.stderr
    assert os.path.exists("requirements.txt")


def test_upgrade_packages_option(runner):
    """
    piptools respects --upgrade-package/-P inline list.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\nsmall-fake-b==0.1")

    out = runner.invoke(cli, ["-P", "small-fake-b", "-f", MINIMAL_WHEELS_PATH])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr
    assert "small-fake-b==0.3" in out.stderr


def test_upgrade_packages_option_no_existing_file(runner):
    """
    piptools respects --upgrade-package/-P inline list when the output file
    doesn't exist.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(cli, ["-P", "small-fake-b", "-f", MINIMAL_WHEELS_PATH])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.3" in out.stderr


def test_upgrade_packages_version_option(runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\nsmall-fake-b==0.1")

    out = runner.invoke(cli, ["-P", "small-fake-b==0.2", "-f", MINIMAL_WHEELS_PATH])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr
    assert "small-fake-b==0.2" in out.stderr


def test_upgrade_packages_version_option_no_existing_file(runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(cli, ["-P", "small-fake-b==0.2", "-f", MINIMAL_WHEELS_PATH])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.2" in out.stderr


def test_upgrade_packages_version_option_and_upgrade(runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions
    whilst also doing --upgrade.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\nsmall-fake-b==0.1")

    out = runner.invoke(
        cli, ["--upgrade", "-P", "small-fake-b==0.1", "-f", MINIMAL_WHEELS_PATH]
    )

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.1" in out.stderr


def test_upgrade_packages_version_option_and_upgrade_no_existing_file(runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions
    whilst also doing --upgrade and the output file doesn't exist.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(
        cli, ["--upgrade", "-P", "small-fake-b==0.1", "-f", MINIMAL_WHEELS_PATH]
    )

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.1" in out.stderr


def test_quiet_option(runner):
    with open("requirements", "w"):
        pass
    out = runner.invoke(cli, ["--quiet", "-n", "requirements"])
    # Pinned requirements result has not been written to output.
    assert not out.stderr_bytes


def test_dry_run_noisy_option(runner):
    with open("requirements", "w"):
        pass
    out = runner.invoke(cli, ["--dry-run", "requirements"])
    # Dry-run message has been written to output
    assert "Dry-run, so nothing updated." in out.stderr.splitlines()


def test_dry_run_quiet_option(runner):
    with open("requirements", "w"):
        pass
    out = runner.invoke(cli, ["--dry-run", "--quiet", "requirements"])
    # Dry-run message has not been written to output.
    assert not out.stderr_bytes


def test_generate_hashes_with_editable(runner):
    small_fake_package_dir = os.path.join(TEST_DATA_PATH, "small_fake_package")
    small_fake_package_url = path_to_url(small_fake_package_dir)
    with open("requirements.in", "w") as fp:
        fp.write("-e {}\n".format(small_fake_package_url))
        fp.write("pytz==2017.2\n")
    out = runner.invoke(
        cli, ["--generate-hashes", "--index-url", PyPIRepository.DEFAULT_INDEX_URL]
    )
    expected = (
        "-e {}\n"
        "pytz==2017.2 \\\n"
        "    --hash=sha256:d1d6729c85acea542367138286"
        "8627129432fba9a89ecbb248d8d1c7a9f01c67 \\\n"
        "    --hash=sha256:f5c056e8f62d45ba8215e5cb8f"
        "50dfccb198b4b9fbea8500674f3443e4689589\n"
    ).format(small_fake_package_url)
    assert out.exit_code == 0
    assert expected in out.stderr


def test_generate_hashes_with_url(runner):
    with open("requirements.in", "w") as fp:
        fp.write(
            "https://github.com/jazzband/pip-tools/archive/"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip#egg=pip-tools\n"
        )
    out = runner.invoke(cli, ["--generate-hashes"])
    expected = (
        "https://github.com/jazzband/pip-tools/archive/"
        "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip#egg=pip-tools \\\n"
        "    --hash=sha256:d24de92e18ad5bf291f25cfcdcf"
        "0171be6fa70d01d0bef9eeda356b8549715e7\n"
    )
    assert out.exit_code == 0
    assert expected in out.stderr


def test_generate_hashes_verbose(runner):
    """
    The hashes generation process should show a progress.
    """
    with open("requirements.in", "w") as fp:
        fp.write("pytz==2017.2")

    out = runner.invoke(cli, ["--generate-hashes", "-v"])

    expected_verbose_text = "Generating hashes:\n  pytz\n"
    assert expected_verbose_text in out.stderr


@fail_below_pip9
def test_filter_pip_markers(runner):
    """
    Check that pip-compile works with pip environment markers (PEP496)
    """
    with open("requirements", "w") as req_in:
        req_in.write("six==1.10.0\n" "unknown_package==0.1; python_version == '1'")

    out = runner.invoke(cli, ["-n", "requirements"])

    assert out.exit_code == 0
    assert "six==1.10.0" in out.stderr
    assert "unknown_package" not in out.stderr


def test_no_candidates(runner):
    with open("requirements", "w") as req_in:
        req_in.write("six>1.0b0,<1.0b0")

    out = runner.invoke(cli, ["-n", "requirements"])

    assert out.exit_code == 2
    assert "Skipped pre-versions:" in out.stderr


def test_no_candidates_pre(runner):
    with open("requirements", "w") as req_in:
        req_in.write("six>1.0b0,<1.0b0")

    out = runner.invoke(cli, ["-n", "requirements", "--pre"])

    assert out.exit_code == 2
    assert "Tried pre-versions:" in out.stderr


def test_default_index_url(pip_conf):
    status, output = invoke([sys.executable, "-m", "piptools", "compile", "--help"])
    output = output.decode("utf-8")

    # Click's subprocess output has \r\r\n line endings on win py27. Fix it.
    output = output.replace("\r\r", "\r")

    assert status == 0
    expected = (
        "  -i, --index-url TEXT            Change index URL (defaults to"
        + os.linesep
        + "                                  http://example.com)"
        + os.linesep
    )
    assert expected in output


def test_stdin_without_output_file(runner):
    """
    The --output-file option is required for STDIN.
    """
    out = runner.invoke(cli, ["-n", "-"])

    assert out.exit_code == 2
    assert "--output-file is required if input is from stdin" in out.stderr


def test_not_specified_input_file(runner):
    """
    It should raise an error if there are no input files or default input files
    such as "setup.py" or "requirements.in".
    """
    out = runner.invoke(cli)
    assert "If you do not specify an input file" in out.stderr
    assert out.exit_code == 2


def test_stdin(runner):
    """
    Test compile requirements from STDIN.
    """
    out = runner.invoke(
        cli, ["-", "--output-file", "requirements.txt", "-n"], input="six==1.10.0"
    )

    assert "six==1.10.0" in out.stderr


def test_multiple_input_files_without_output_file(runner):
    """
    The --output-file option is required for multiple requirement input files.
    """
    with open("src_file1.in", "w") as req_in:
        req_in.write("six==1.10.0")

    with open("src_file2.in", "w") as req_in:
        req_in.write("django==2.1")

    out = runner.invoke(cli, ["src_file1.in", "src_file2.in"])

    assert (
        "--output-file is required if two or more input files are given" in out.stderr
    )
    assert out.exit_code == 2


@pytest.mark.parametrize(
    "option, expected",
    [
        ("--annotate", "six==1.10.0               # via small-fake-with-deps\n"),
        ("--no-annotate", "six==1.10.0\n"),
    ],
)
def test_annotate_option(pip_conf, runner, option, expected):
    """
    The output lines has have annotations if option is turned on.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small_fake_with_deps")

    out = runner.invoke(cli, [option, "-n", "-f", MINIMAL_WHEELS_PATH])

    assert expected in out.stderr
    assert out.exit_code == 0


@pytest.mark.parametrize(
    "option, expected",
    [("--allow-unsafe", "\nsetuptools=="), (None, "\n# setuptools==")],
)
def test_allow_unsafe_option(runner, option, expected):
    """
    Unsafe packages are printed as expected with and without --allow-unsafe.
    """

    with open("requirements.in", "w") as req_in:
        req_in.write(path_to_url(os.path.join(TEST_DATA_PATH, "small_fake_package")))

    out = runner.invoke(cli, [option] if option else [])

    assert expected in out.stderr
    assert out.exit_code == 0


@pytest.mark.parametrize(
    "option, attr, expected",
    [("--cert", "cert", "foo.crt"), ("--client-cert", "client_cert", "bar.pem")],
)
@mock.patch("piptools.scripts.compile.parse_requirements")
def test_cert_option(parse_requirements, runner, option, attr, expected):
    """
    The options --cert and --client-crt have to be passed to the PyPIRepository.
    """
    with open("requirements.in", "w"):
        pass

    runner.invoke(cli, [option, expected])

    # Ensure the options in parse_requirements has the expected option
    assert getattr(parse_requirements.call_args.kwargs["options"], attr) == expected


@pytest.mark.parametrize(
    "option, expected", [("--build-isolation", True), ("--no-build-isolation", False)]
)
@mock.patch("piptools.scripts.compile.PyPIRepository")
@mock.patch("piptools.scripts.compile.parse_requirements")  # prevent to parse
def test_build_isolation_option(
    parse_requirements, PyPIRepository, runner, option, expected
):
    """
    A value of the --build-isolation/--no-build-isolation flag
    must be passed to the PyPIRepository.
    """
    with open("requirements.in", "w"):
        pass

    runner.invoke(cli, [option])

    # Ensure the build_isolation option in PyPIRepository has the expected value.
    assert PyPIRepository.call_args.kwargs["build_isolation"] is expected


@pytest.mark.parametrize(
    "cli_option, infile_option, expected_package",
    [
        # no --pre pip-compile should resolve to the last stable version
        (False, False, "small-fake-a==0.2"),
        # pip-compile --pre should resolve to the last pre-released version
        (True, False, "small-fake-a==0.3b1"),
        (False, True, "small-fake-a==0.3b1"),
        (True, True, "small-fake-a==0.3b1"),
    ],
)
def test_pre_option(runner, cli_option, infile_option, expected_package):
    """
    Tests pip-compile respects --pre option.
    """
    with open("requirements.in", "w") as req_in:
        if infile_option:
            req_in.write("--pre\n")
        req_in.write("small-fake-a\n")

    out = runner.invoke(
        cli, ["-n", "-f", MINIMAL_WHEELS_PATH] + (["-p"] if cli_option else [])
    )

    assert out.exit_code == 0, out.stderr
    assert expected_package in out.stderr.splitlines(), out.stderr


@pytest.mark.parametrize(
    "add_options",
    [
        [],
        ["--output-file", "requirements.txt"],
        ["--upgrade"],
        ["--upgrade", "--output-file", "requirements.txt"],
        ["--upgrade-package", "small-fake-a"],
        ["--upgrade-package", "small-fake-a", "--output-file", "requirements.txt"],
    ],
)
def test_dry_run_option(runner, add_options):
    """
    Tests pip-compile doesn't create requirements.txt file on dry-run.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\n")

    out = runner.invoke(
        cli, ["--dry-run", "--find-links", MINIMAL_WHEELS_PATH] + add_options
    )

    assert out.exit_code == 0, out.stderr
    assert "small-fake-a==0.2" in out.stderr.splitlines()
    assert not os.path.exists("requirements.txt")


@pytest.mark.parametrize(
    "add_options, expected_cli_output_package",
    [
        ([], "small-fake-a==0.1"),
        (["--output-file", "requirements.txt"], "small-fake-a==0.1"),
        (["--upgrade"], "small-fake-a==0.2"),
        (["--upgrade", "--output-file", "requirements.txt"], "small-fake-a==0.2"),
        (["--upgrade-package", "small-fake-a"], "small-fake-a==0.2"),
        (
            ["--upgrade-package", "small-fake-a", "--output-file", "requirements.txt"],
            "small-fake-a==0.2",
        ),
    ],
)
def test_dry_run_doesnt_touch_output_file(
    runner, add_options, expected_cli_output_package
):
    """
    Tests pip-compile doesn't touch requirements.txt file on dry-run.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\n")

    with open("requirements.txt", "w") as req_txt:
        req_txt.write("small-fake-a==0.1\n")

    before_compile_mtime = os.stat("requirements.txt").st_mtime

    out = runner.invoke(
        cli, ["--dry-run", "--find-links", MINIMAL_WHEELS_PATH] + add_options
    )

    assert out.exit_code == 0, out.stderr
    assert expected_cli_output_package in out.stderr.splitlines()

    # The package version must NOT be updated in the output file
    with open("requirements.txt", "r") as req_txt:
        assert "small-fake-a==0.1" in req_txt.read().splitlines()

    # The output file must not be touched
    after_compile_mtime = os.stat("requirements.txt").st_mtime
    assert after_compile_mtime == before_compile_mtime
