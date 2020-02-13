import sys

import pytest

from .utils import invoke

from piptools.scripts.check import cli


def test_run_as_module_check():
    """piptools can be run as ``python -m piptools ...``."""

    status, output = invoke([sys.executable, "-m", "piptools", "check", "--help"])

    # Should have run pip-check successfully.
    output = output.decode("utf-8")
    assert output.startswith("Usage:")
    assert "Checks whether requirements" in output
    assert status == 0


def test_exits_successfully_if_lock_up_to_date(tmpdir_cwd, runner):
    """
    If lock in requirements.txt is up-to-date pip-check exits with 0
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six")
    with open("requirements.txt", "w") as req_txt:
        req_txt.write(
            "# sha256:44778d82365e4af681c40d5f0eef5cf6f5899d3f0ac335050a7ed6779cf3f674"
            "  requirements.in\n"
        )
        req_txt.write("six==1.10.0")

    out = runner.invoke(cli, ["requirements.txt"])
    assert out.exit_code == 0


def test_exits_unsuccessfully_if_lock_not_up_to_date(tmpdir_cwd, runner):
    """
    If lock in requirements.txt is not up-to-date pip-check exits with 1
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six<1.10.0")
    with open("requirements.txt", "w") as req_txt:
        req_txt.write(
            "# sha256:fe2547fe2604b445e70fc9d819062960552f9145bdb043b51986e478a4806a2b"
            "  requirements.in\n"
        )
        req_txt.write("six==1.10.0")

    out = runner.invoke(cli, ["requirements.txt"])

    assert out.exit_code == 1
    assert "requirements.txt: lock(s) are out-of-date" in out.stderr


def test_exits_unsuccessfully_if_lock_not_present(tmpdir_cwd, runner):
    """
    If lock not in requirements.txt pip-check exits with 1
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six")
    with open("requirements.txt", "w") as req_txt:
        req_txt.write("six==1.10.0")

    out = runner.invoke(cli, ["requirements.txt"])
    assert out.exit_code == 1
    assert "no locks found" in out.stderr


@pytest.mark.parametrize(
    "checksum, expected_exit_code",
    (
        ["44778d82365e4af681c40d5f0eef5cf6f5899d3f0ac335050a7ed6779cf3f674", 0],
        ["4568992cc2c4736b0bee1179b5a3afe324a99aac2d24b0735ede273326b14220", 1],
        ["", 1],
    ),
)
def test_quiet_option(tmpdir_cwd, runner, checksum, expected_exit_code):
    """check command can be run with `--quiet` or `-q` flag."""
    with open("requirements.in", "w") as req_in:
        req_in.write("six")
    with open("requirements.txt", "w") as req_txt:
        if checksum:
            req_txt.write("# sha256:{}  requirements.in\n".format(checksum))
        req_txt.write("six==1.10.0")

    out = runner.invoke(cli, ["-q"])
    assert not out.stderr_bytes
    assert out.exit_code == expected_exit_code


def test_no_requirements_file(tmpdir_cwd, runner):
    """
    It should raise an error if there are no input files
    or a requirements.txt file does not exist.
    """
    out = runner.invoke(cli)

    assert "If you do not specify an input file" in out.stderr
    assert out.exit_code == 2


def test_requirements_file_with_dot_in_extension(tmpdir_cwd, runner):
    """
    It should raise an error if some of the input files have .in extension.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six")

    out = runner.invoke(cli, ["requirements.in"])

    assert "req_file has the .in extension" in out.stderr
    assert out.exit_code == 2


@pytest.mark.parametrize(
    "checksum, expected_exit_code",
    (
        ["44778d82365e4af681c40d5f0eef5cf6f5899d3f0ac335050a7ed6779cf3f674", 0],
        ["4568992cc2c4736b0bee1179b5a3afe324a99aac2d24b0735ede273326b14220", 1],
        ["", 1],
    ),
)
def test_stdin(tmpdir_cwd, runner, checksum, expected_exit_code):
    """
    It can check requirements from stdin
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("six")

    req_txt = (
        "# sha256:{}  requirements.in\n".format(checksum)
        if checksum
        else "" "six==1.10.0"
    )

    out = runner.invoke(cli, ["-"], input=req_txt)

    assert out.exit_code == expected_exit_code


@pytest.mark.parametrize(
    "checksum, expected_exit_code",
    (
        ["c0862201e27e10f591cc0e3fb8d1dd4f6a4af2559d04a71fb0cb142d59b2f6b7", 0],
        ["4568992cc2c4736b0bee1179b5a3afe324a99aac2d24b0735ede273326b14220", 1],
        ["", 1],
    ),
)
def test_multiple_requirement_files(tmpdir_cwd, runner, checksum, expected_exit_code):
    """
    Can check multiple requirements files
    """
    with open("req_file1.in", "w") as req_in:
        req_in.write("Flask")
    with open("req_file2.in", "w") as req_in:
        req_in.write("Django")

    with open("req_file1.txt", "w") as req_txt:
        if checksum:
            req_txt.write("# sha256:{}  req_file1.in\n".format(checksum))
        req_txt.write("Flask==1.1.1")
    with open("req_file2.txt", "w") as req_txt:
        req_txt.write(
            "# sha256:4445d918dfcf1af804b749eeee4835dccfd27c06b6828533be827473ff63439f"
            "  req_file2.in\n"
        )
        req_txt.write("Django==2.2.1")

    out = runner.invoke(cli, ["req_file1.txt", "req_file2.txt"])

    assert out.exit_code == expected_exit_code
