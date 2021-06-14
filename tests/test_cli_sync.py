import os
import subprocess
import sys
from unittest import mock

import pytest
from pip._vendor.packaging.version import Version

from piptools.scripts.sync import DEFAULT_REQUIREMENTS_FILE, cli


def test_run_as_module_sync():
    """piptools can be run as ``python -m piptools ...``."""

    result = subprocess.run(
        [sys.executable, "-m", "piptools", "sync", "--help"],
        stdout=subprocess.PIPE,
        check=True,
    )

    # Should have run pip-compile successfully.
    assert result.stdout.startswith(b"Usage:")
    assert b"Synchronize virtual environment with" in result.stdout


@mock.patch("piptools.sync.run")
def test_quiet_option(run, runner):
    """sync command can be run with `--quiet` or `-q` flag."""

    with open("requirements.txt", "w") as req_in:
        req_in.write("six==1.10.0")

    out = runner.invoke(cli, ["-q"])
    assert not out.stderr_bytes
    assert out.exit_code == 0

    # for every call to pip ensure the `-q` flag is set
    assert run.call_count == 2
    for call in run.call_args_list:
        assert "-q" in call[0][0]


@mock.patch("piptools.sync.run")
def test_quiet_option_when_up_to_date(run, runner):
    """
    Sync should output nothing when everything is up to date and quiet option is set.
    """
    with open("requirements.txt", "w"):
        pass

    with mock.patch("piptools.sync.diff", return_value=(set(), set())):
        out = runner.invoke(cli, ["-q"])

    assert not out.stderr_bytes
    assert out.exit_code == 0
    run.assert_not_called()


def test_no_requirements_file(runner):
    """
    It should raise an error if there are no input files
    or a requirements.txt file does not exist.
    """
    out = runner.invoke(cli)

    assert "No requirement files given" in out.stderr
    assert out.exit_code == 2


def test_input_files_with_dot_in_extension(runner):
    """
    It should raise an error if some of the input files have .in extension.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six==1.10.0")

    out = runner.invoke(cli, ["requirements.in"])

    assert "ERROR: Some input files have the .in extension" in out.stderr
    assert out.exit_code == 2


def test_force_files_with_dot_in_extension(runner):
    """
    It should print a warning and sync anyway if some of the input files
    have .in extension.
    """

    with open("requirements.in", "w") as req_in:
        req_in.write("six==1.10.0")

    with mock.patch("piptools.sync.run"):
        out = runner.invoke(cli, ["requirements.in", "--force"])

    assert "WARNING: Some input files have the .in extension" in out.stderr
    assert out.exit_code == 0


@pytest.mark.parametrize(
    ("req_lines", "should_raise"),
    (
        (["six>1.10.0", "six<1.10.0"], True),
        (
            ["six>1.10.0 ; python_version>='3.0'", "six<1.10.0 ; python_version<'3.0'"],
            False,
        ),
    ),
)
def test_merge_error(req_lines, should_raise, runner):
    """
    Sync command should raise an error if there are merge errors.
    It should not raise an error if otherwise incompatible requirements
    are isolated by exclusive environment markers.
    """
    with open("requirements.txt", "w") as req_in:
        for line in req_lines:
            req_in.write(line + "\n")

    with mock.patch("piptools.sync.run"):
        out = runner.invoke(cli, ["-n"])

    if should_raise:
        assert out.exit_code == 2
        assert "Incompatible requirements found" in out.stderr
    else:
        assert out.exit_code == 1


@pytest.mark.parametrize(
    ("cli_flags", "expected_install_flags"),
    (
        (
            ["--find-links", "./libs1", "--find-links", "./libs2"],
            ["--find-links", "./libs1", "--find-links", "./libs2"],
        ),
        (["--no-index"], ["--no-index"]),
        (
            ["--index-url", "https://example.com"],
            ["--index-url", "https://example.com"],
        ),
        (
            ["--extra-index-url", "https://foo", "--extra-index-url", "https://bar"],
            ["--extra-index-url", "https://foo", "--extra-index-url", "https://bar"],
        ),
        (
            ["--trusted-host", "foo", "--trusted-host", "bar"],
            ["--trusted-host", "foo", "--trusted-host", "bar"],
        ),
        (["--user"], ["--user"]),
        (["--cert", "foo.crt"], ["--cert", "foo.crt"]),
        (["--client-cert", "foo.pem"], ["--client-cert", "foo.pem"]),
        (
            ["--pip-args", "--no-cache-dir --no-deps --no-warn-script-location"],
            ["--no-cache-dir", "--no-deps", "--no-warn-script-location"],
        ),
        (["--pip-args='--cache-dir=/tmp'"], ["--cache-dir=/tmp"]),
        (
            ["--pip-args=\"--cache-dir='/tmp/cache dir with spaces/'\""],
            ["--cache-dir='/tmp/cache dir with spaces/'"],
        ),
    ),
)
@mock.patch("piptools.sync.run")
def test_pip_install_flags(run, cli_flags, expected_install_flags, runner):
    """
    Test the cli flags have to be passed to the pip install command.
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("six==1.10.0")

    runner.invoke(cli, cli_flags)

    call_args = [call[0][0] for call in run.call_args_list]
    called_install_options = [args[6:] for args in call_args if args[3] == "install"]
    assert called_install_options == [expected_install_flags], "Called args: {}".format(
        call_args
    )


@pytest.mark.parametrize(
    "install_flags",
    (
        ["--no-index"],
        ["--index-url", "https://example.com"],
        ["--extra-index-url", "https://example.com"],
        ["--find-links", "./libs1"],
        ["--trusted-host", "example.com"],
        ["--no-binary", ":all:"],
        ["--only-binary", ":all:"],
    ),
)
@mock.patch("piptools.sync.run")
def test_pip_install_flags_in_requirements_file(run, runner, install_flags):
    """
    Test the options from requirements.txt file pass to the pip install command.
    """
    with open(DEFAULT_REQUIREMENTS_FILE, "w") as reqs:
        reqs.write(" ".join(install_flags) + "\n")
        reqs.write("six==1.10.0")

    out = runner.invoke(cli)
    assert out.exit_code == 0, out

    # Make sure pip install command has expected options
    call_args = [call[0][0] for call in run.call_args_list]
    called_install_options = [args[6:] for args in call_args if args[3] == "install"]
    assert called_install_options == [install_flags], f"Called args: {call_args}"


@mock.patch("piptools.sync.run")
def test_sync_ask_declined(run, runner):
    """
    Make sure nothing is installed if the confirmation is declined
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    runner.invoke(cli, ["--ask"], input="n\n")

    run.assert_not_called()


@mock.patch("piptools.sync.run")
def test_sync_ask_accepted(run, runner):
    """
    Make sure pip is called when the confirmation is accepted (even if
    --dry-run is given)
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    runner.invoke(cli, ["--ask", "--dry-run"], input="y\n")

    assert run.call_count == 2


def test_sync_dry_run_returns_non_zero_exit_code(runner):
    """
    Make sure non-zero exit code is returned when --dry-run is given.
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    out = runner.invoke(cli, ["--dry-run"])

    assert out.exit_code == 1


@mock.patch("piptools.sync.run")
def test_python_executable_option(
    run,
    runner,
    fake_dist,
):
    """
    Make sure sync command can run with `--python-executable` option.
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    custom_executable = os.path.abspath(sys.executable)

    runner.invoke(cli, ["--python-executable", custom_executable])

    assert run.call_count == 2

    call_args = [call[0][0] for call in run.call_args_list]
    called_uninstall_options = [
        args[:5] for args in call_args if args[3] == "uninstall"
    ]
    called_install_options = [args[:-1] for args in call_args if args[3] == "install"]

    assert called_uninstall_options == [
        [custom_executable, "-m", "pip", "uninstall", "-y"]
    ]
    assert called_install_options == [[custom_executable, "-m", "pip", "install", "-r"]]


@pytest.mark.parametrize(
    "python_executable",
    (
        "/tmp/invalid_executable",
        "invalid_python",
    ),
)
def test_invalid_python_executable(runner, python_executable):
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    out = runner.invoke(cli, ["--python-executable", python_executable])
    assert out.exit_code == 2, out
    message = "Could not resolve '{}' as valid executable path or alias.\n"
    assert out.stderr == message.format(python_executable)


@mock.patch("piptools.scripts.sync.get_pip_version_for_python_executable")
def test_invalid_pip_version_in_python_executable(
    get_pip_version_for_python_executable, runner
):
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    custom_executable = os.path.abspath("custom_executable")
    with open(custom_executable, "w") as exec_file:
        exec_file.write("")

    os.chmod(custom_executable, 0o700)

    get_pip_version_for_python_executable.return_value = Version("19.1")

    out = runner.invoke(cli, ["--python-executable", custom_executable])
    assert out.exit_code == 2, out
    message = (
        "Target python executable '{}' has pip version 19.1 installed. "
        "Version"  # ">=20.3 is expected.\n" part is omitted
    )
    assert out.stderr.startswith(message.format(custom_executable))


@mock.patch("piptools.sync.run")
def test_default_python_executable_option(run, runner):
    """
    Make sure sys.executable is used when --python-executable is not provided.
    """
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==1.10.0")

    runner.invoke(cli)

    assert run.call_count == 2

    call_args = [call[0][0] for call in run.call_args_list]
    called_install_options = [args[:-1] for args in call_args if args[3] == "install"]
    assert called_install_options == [
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
        ]
    ]
