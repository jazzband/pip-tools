import os
import shutil
import subprocess
import sys
from textwrap import dedent
from unittest import mock

import pytest
from pip._internal.utils.urls import path_to_url

from piptools.scripts.compile import cli

from .constants import MINIMAL_WHEELS_PATH, PACKAGES_PATH

is_pypy = "__pypy__" in sys.builtin_module_names
is_windows = sys.platform == "win32"


@pytest.fixture(autouse=True)
def _temp_dep_cache(tmpdir, monkeypatch):
    monkeypatch.setenv("PIP_TOOLS_CACHE_DIR", str(tmpdir / "cache"))


def test_default_pip_conf_read(pip_with_index_conf, runner):
    # preconditions
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(cli, ["-v"])

    # check that we have our index-url as specified in pip.conf
    assert "Using indexes:\n  http://example.com" in out.stderr
    assert "--index-url http://example.com" in out.stderr


def test_command_line_overrides_pip_conf(pip_with_index_conf, runner):
    # preconditions
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(cli, ["-v", "-i", "http://override.com"])

    # check that we have our index-url as specified in pip.conf
    assert "Using indexes:\n  http://override.com" in out.stderr


@pytest.mark.network
@pytest.mark.parametrize(
    ("install_requires", "expected_output"),
    (
        pytest.param("small-fake-a==0.1", "small-fake-a==0.1", id="regular"),
        pytest.param(
            "pip-tools @ https://github.com/jazzband/pip-tools/archive/7d86c8d3.zip",
            "pip-tools @ https://github.com/jazzband/pip-tools/archive/7d86c8d3.zip",
            id="zip URL",
        ),
        pytest.param(
            "pip-tools @ git+https://github.com/jazzband/pip-tools@7d86c8d3",
            "pip-tools @ git+https://github.com/jazzband/pip-tools@7d86c8d3",
            id="scm URL",
        ),
        pytest.param(
            "pip-tools @ https://files.pythonhosted.org/packages/06/96/"
            "89872db07ae70770fba97205b0737c17ef013d0d1c790"
            "899c16bb8bac419/pip_tools-3.6.1-py2.py3-none-any.whl",
            "pip-tools @ https://files.pythonhosted.org/packages/06/96/"
            "89872db07ae70770fba97205b0737c17ef013d0d1c790"
            "899c16bb8bac419/pip_tools-3.6.1-py2.py3-none-any.whl",
            id="wheel URL",
        ),
    ),
)
def test_command_line_setuptools_read(
    runner, make_pip_conf, make_package, install_requires, expected_output
):
    package_dir = make_package(
        name="fake-setuptools-a",
        install_requires=(install_requires,),
    )

    out = runner.invoke(
        cli,
        (str(package_dir / "setup.py"), "--find-links", MINIMAL_WHEELS_PATH),
    )

    assert expected_output in out.stderr.splitlines()

    # check that pip-compile generated a configuration file
    assert (package_dir / "requirements.txt").exists()


@pytest.mark.network
@pytest.mark.parametrize(
    ("options", "expected_output_file"),
    (
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
    ),
)
def test_command_line_setuptools_output_file(runner, options, expected_output_file):
    """
    Test the output files for setup.py as a requirement file.
    """

    with open("setup.py", "w") as package:
        package.write(
            dedent(
                """\
                from setuptools import setup
                setup(install_requires=[])
                """
            )
        )

    out = runner.invoke(cli, options)
    assert out.exit_code == 0
    assert os.path.exists(expected_output_file)


@pytest.mark.network
def test_command_line_setuptools_nested_output_file(tmpdir, runner):
    """
    Test the output file for setup.py in nested folder as a requirement file.
    """
    proj_dir = tmpdir.mkdir("proj")

    with open(str(proj_dir / "setup.py"), "w") as package:
        package.write(
            dedent(
                """\
                from setuptools import setup
                setup(install_requires=[])
                """
            )
        )

    out = runner.invoke(cli, [str(proj_dir / "setup.py")])
    assert out.exit_code == 0
    assert (proj_dir / "requirements.txt").exists()


@pytest.mark.network
def test_setuptools_preserves_environment_markers(
    runner, make_package, make_wheel, make_pip_conf, tmpdir
):
    make_pip_conf(
        dedent(
            """\
            [global]
            disable-pip-version-check = True
            """
        )
    )

    dists_dir = tmpdir / "dists"

    foo_dir = make_package(name="foo", version="1.0")
    make_wheel(foo_dir, dists_dir)

    bar_dir = make_package(
        name="bar", version="2.0", install_requires=['foo ; python_version >= "1"']
    )
    out = runner.invoke(
        cli,
        [
            str(bar_dir / "setup.py"),
            "--no-header",
            "--no-annotate",
            "--no-emit-find-links",
            "--find-links",
            str(dists_dir),
        ],
    )

    assert out.exit_code == 0, out.stderr
    assert out.stderr == 'foo==1.0 ; python_version >= "1"\n'


def test_find_links_option(runner):
    with open("requirements.in", "w") as req_in:
        req_in.write("-f ./libs3")

    out = runner.invoke(cli, ["-v", "-f", "./libs1", "-f", "./libs2"])

    # Check that find-links has been passed to pip
    assert "Using links:\n  ./libs1\n  ./libs2\n  ./libs3\n" in out.stderr

    # Check that find-links has been written to a requirements.txt
    with open("requirements.txt") as req_txt:
        assert (
            "--find-links ./libs1\n--find-links ./libs2\n--find-links ./libs3\n"
            in req_txt.read()
        )


def test_find_links_envvar(monkeypatch, runner):
    with open("requirements.in", "w") as req_in:
        req_in.write("-f ./libs3")

    monkeypatch.setenv("PIP_FIND_LINKS", "./libs1 ./libs2")
    out = runner.invoke(cli, ["-v"])

    # Check that find-links has been passed to pip
    assert "Using links:\n  ./libs1\n  ./libs2\n  ./libs3\n" in out.stderr

    # Check that find-links has been written to a requirements.txt
    with open("requirements.txt") as req_txt:
        assert (
            "--find-links ./libs1\n--find-links ./libs2\n--find-links ./libs3\n"
            in req_txt.read()
        )


def test_extra_index_option(pip_with_index_conf, runner):
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


def test_extra_index_envvar(monkeypatch, runner):
    with open("requirements.in", "w"):
        pass

    monkeypatch.setenv("PIP_INDEX_URL", "http://example.com")
    monkeypatch.setenv(
        "PIP_EXTRA_INDEX_URL", "http://extraindex1.com http://extraindex2.com"
    )
    out = runner.invoke(cli, ["-v"])
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


@pytest.mark.parametrize("option", ("--extra-index-url", "--find-links"))
def test_redacted_urls_in_verbose_output(runner, option):
    """
    Test that URLs with sensitive data don't leak to the output.
    """
    with open("requirements.in", "w"):
        pass

    out = runner.invoke(
        cli,
        [
            "--no-header",
            "--no-emit-index-url",
            "--no-emit-find-links",
            "--verbose",
            option,
            "http://username:password@example.com",
        ],
    )

    assert "http://username:****@example.com" in out.stderr
    assert "password" not in out.stderr


def test_trusted_host_option(pip_conf, runner):
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(
        cli, ["-v", "--trusted-host", "example.com", "--trusted-host", "example2.com"]
    )
    assert "--trusted-host example.com\n--trusted-host example2.com\n" in out.stderr


def test_trusted_host_envvar(monkeypatch, pip_conf, runner):
    with open("requirements.in", "w"):
        pass
    monkeypatch.setenv("PIP_TRUSTED_HOST", "example.com example2.com")
    out = runner.invoke(cli, ["-v"])
    assert "--trusted-host example.com\n--trusted-host example2.com\n" in out.stderr


@pytest.mark.parametrize(
    "options",
    (
        pytest.param(
            ["--trusted-host", "example.com", "--no-emit-trusted-host"],
            id="trusted host",
        ),
        pytest.param(
            ["--find-links", "wheels", "--no-emit-find-links"], id="find links"
        ),
        pytest.param(
            ["--index-url", "https://index-url", "--no-emit-index-url"], id="index url"
        ),
    ),
)
def test_all_no_emit_options(runner, options):
    with open("requirements.in", "w"):
        pass
    out = runner.invoke(cli, ["--no-header", *options])
    assert out.stderr.strip().splitlines() == []


@pytest.mark.parametrize(
    ("option", "expected_output"),
    (
        pytest.param(
            "--emit-index-url", ["--index-url https://index-url"], id="index url"
        ),
        pytest.param("--no-emit-index-url", [], id="no index"),
    ),
)
def test_emit_index_url_option(runner, option, expected_output):
    with open("requirements.in", "w"):
        pass

    out = runner.invoke(
        cli, ["--no-header", "--index-url", "https://index-url", option]
    )

    assert out.stderr.strip().splitlines() == expected_output


@pytest.mark.network
@pytest.mark.xfail(
    is_pypy and is_windows, reason="https://github.com/jazzband/pip-tools/issues/1148"
)
def test_realistic_complex_sub_dependencies(runner):
    wheels_dir = "wheels"

    # make a temporary wheel of a fake package
    subprocess.run(
        [
            "pip",
            "wheel",
            "--no-deps",
            "-w",
            wheels_dir,
            os.path.join(PACKAGES_PATH, "fake_with_deps", "."),
        ],
        check=True,
    )

    with open("requirements.in", "w") as req_in:
        req_in.write("fake_with_deps")  # require fake package

    out = runner.invoke(cli, ["-n", "--rebuild", "-f", wheels_dir])

    assert out.exit_code == 0


def test_run_as_module_compile():
    """piptools can be run as ``python -m piptools ...``."""

    result = subprocess.run(
        [sys.executable, "-m", "piptools", "compile", "--help"],
        stdout=subprocess.PIPE,
        check=True,
    )

    # Should have run pip-compile successfully.
    assert result.stdout.startswith(b"Usage:")
    assert b"Compiles requirements.txt from requirements.in" in result.stdout


def test_editable_package(pip_conf, runner):
    """piptools can compile an editable"""
    fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_with_deps")
    fake_package_dir = path_to_url(fake_package_dir)
    with open("requirements.in", "w") as req_in:
        req_in.write("-e " + fake_package_dir)  # require editable fake package

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    assert "small-fake-a==0.1" in out.stderr


def test_editable_package_without_non_editable_duplicate(pip_conf, runner):
    """
    piptools keeps editable requirement,
    without also adding a duplicate "non-editable" requirement variation
    """
    fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_a")
    fake_package_dir = path_to_url(fake_package_dir)
    with open("requirements.in", "w") as req_in:
        # small_fake_with_unpinned_deps also requires small_fake_a
        req_in.write(
            "-e "
            + fake_package_dir
            + "\nsmall_fake_with_unpinned_deps"  # require editable fake package
        )

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    # Shouldn't include a non-editable small-fake-a==<version>.
    assert "small-fake-a==" not in out.stderr


def test_editable_package_constraint_without_non_editable_duplicate(pip_conf, runner):
    """
    piptools keeps editable constraint,
    without also adding a duplicate "non-editable" requirement variation
    """
    fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_a")
    fake_package_dir = path_to_url(fake_package_dir)
    with open("constraints.txt", "w") as constraints:
        constraints.write("-e " + fake_package_dir)  # require editable fake package

    with open("requirements.in", "w") as req_in:
        req_in.write(
            "-c constraints.txt"  # require editable fake package
            "\nsmall_fake_with_unpinned_deps"  # This one also requires small_fake_a
        )

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    # Shouldn't include a non-editable small-fake-a==<version>.
    assert "small-fake-a==" not in out.stderr


@pytest.mark.parametrize("req_editable", ((True,), (False,)))
def test_editable_package_in_constraints(pip_conf, runner, req_editable):
    """
    piptools can compile an editable that appears in both primary requirements
    and constraints
    """
    fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_with_deps")
    fake_package_dir = path_to_url(fake_package_dir)

    with open("constraints.txt", "w") as constraints_in:
        constraints_in.write("-e " + fake_package_dir)

    with open("requirements.in", "w") as req_in:
        prefix = "-e " if req_editable else ""
        req_in.write(prefix + fake_package_dir + "\n-c constraints.txt")

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    assert "small-fake-a==0.1" in out.stderr


@pytest.mark.network
def test_editable_package_vcs(runner):
    vcs_package = (
        "git+https://github.com/jazzband/pip-tools@"
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
    pip_conf, tmpdir, runner
):
    """
    piptools will not create an archive for a locally available editable requirement
    """
    cache_dir = tmpdir.mkdir("cache_dir")

    fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_with_deps")
    fake_package_dir = path_to_url(fake_package_dir)

    with open("requirements.in", "w") as req_in:
        req_in.write("-e " + fake_package_dir)  # require editable fake package

    out = runner.invoke(cli, ["-n", "--rebuild", "--cache-dir", str(cache_dir)])

    assert out.exit_code == 0
    assert fake_package_dir in out.stderr
    assert "small-fake-a==0.1" in out.stderr

    # we should not find any archived file in {cache_dir}/pkgs
    assert not os.listdir(os.path.join(str(cache_dir), "pkgs"))


@pytest.mark.parametrize(
    ("line", "dependency"),
    (
        # use pip-tools version prior to its use of setuptools_scm,
        # which is incompatible with https: install
        pytest.param(
            "https://github.com/jazzband/pip-tools/archive/"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip",
            "\nclick==",
            id="Zip URL",
        ),
        pytest.param(
            "git+https://github.com/jazzband/pip-tools@"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3",
            "\nclick==",
            id="VCS URL",
        ),
        pytest.param(
            "https://files.pythonhosted.org/packages/06/96/"
            "89872db07ae70770fba97205b0737c17ef013d0d1c790"
            "899c16bb8bac419/pip_tools-3.6.1-py2.py3-none-any.whl",
            "\nclick==",
            id="Wheel URL",
        ),
        pytest.param(
            "pytest-django @ git+https://github.com/pytest-dev/pytest-django"
            "@21492afc88a19d4ca01cd0ac392a5325b14f95c7"
            "#egg=pytest-django",
            "pytest-django @ git+https://github.com/pytest-dev/pytest-django"
            "@21492afc88a19d4ca01cd0ac392a5325b14f95c7",
            id="VCS with direct reference and egg",
        ),
    ),
)
@pytest.mark.parametrize("generate_hashes", ((True,), (False,)))
@pytest.mark.network
def test_url_package(runner, line, dependency, generate_hashes):
    with open("requirements.in", "w") as req_in:
        req_in.write(line)
    out = runner.invoke(
        cli, ["-n", "--rebuild"] + (["--generate-hashes"] if generate_hashes else [])
    )
    assert out.exit_code == 0
    assert dependency in out.stderr


@pytest.mark.parametrize(
    ("line", "dependency", "rewritten_line"),
    (
        pytest.param(
            path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
            "\nsmall-fake-a==0.1",
            None,
            id="Wheel URI",
        ),
        pytest.param(
            path_to_url(os.path.join(PACKAGES_PATH, "small_fake_with_deps")),
            "\nsmall-fake-a==0.1",
            None,
            id="Local project URI",
        ),
        pytest.param(
            os.path.join(
                MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
            ),
            "\nsmall-fake-a==0.1",
            path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
            id="Bare path to file URI",
        ),
        pytest.param(
            os.path.join(
                MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
            ),
            "\nsmall-fake-with-deps @ "
            + path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
            "\nsmall-fake-with-deps @ "
            + path_to_url(
                os.path.join(
                    MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
                )
            ),
            id="Local project with absolute URI",
        ),
        pytest.param(
            path_to_url(os.path.join(PACKAGES_PATH, "small_fake_with_subdir"))
            + "#subdirectory=subdir&egg=small-fake-a",
            "small-fake-a @ "
            + path_to_url(os.path.join(PACKAGES_PATH, "small_fake_with_subdir"))
            + "#subdirectory=subdir",
            "small-fake-a @ "
            + path_to_url(os.path.join(PACKAGES_PATH, "small_fake_with_subdir"))
            + "#subdirectory=subdir",
            id="Local project with subdirectory",
        ),
    ),
)
@pytest.mark.parametrize("generate_hashes", ((True,), (False,)))
def test_local_file_uri_package(
    pip_conf, runner, line, dependency, rewritten_line, generate_hashes
):
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


def test_relative_file_uri_package(pip_conf, runner):
    # Copy wheel into temp dir
    shutil.copy(
        os.path.join(
            MINIMAL_WHEELS_PATH, "small_fake_with_deps-0.1-py2.py3-none-any.whl"
        ),
        ".",
    )
    with open("requirements.in", "w") as req_in:
        req_in.write("file:small_fake_with_deps-0.1-py2.py3-none-any.whl")
    out = runner.invoke(cli, ["-n", "--rebuild"])
    assert out.exit_code == 0
    assert "file:small_fake_with_deps-0.1-py2.py3-none-any.whl" in out.stderr


def test_direct_reference_with_extras(runner):
    with open("requirements.in", "w") as req_in:
        req_in.write(
            "piptools[testing,coverage] @ git+https://github.com/jazzband/pip-tools@6.2.0"
        )
    out = runner.invoke(cli, ["-n", "--rebuild"])
    assert out.exit_code == 0
    assert "pip-tools @ git+https://github.com/jazzband/pip-tools@6.2.0" in out.stderr
    assert "pytest==" in out.stderr
    assert "pytest-cov==" in out.stderr


def test_input_file_without_extension(pip_conf, runner):
    """
    piptools can compile a file without an extension,
    and add .txt as the defaut output file extension.
    """
    with open("requirements", "w") as req_in:
        req_in.write("small-fake-a==0.1")

    out = runner.invoke(cli, ["requirements"])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr
    assert os.path.exists("requirements.txt")


def test_upgrade_packages_option(pip_conf, runner):
    """
    piptools respects --upgrade-package/-P inline list.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\nsmall-fake-b==0.1")

    out = runner.invoke(cli, ["--no-annotate", "-P", "small-fake-b"])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr.splitlines()
    assert "small-fake-b==0.3" in out.stderr.splitlines()


def test_upgrade_packages_option_irrelevant(pip_conf, runner):
    """
    piptools ignores --upgrade-package/-P items not already constrained.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1")

    out = runner.invoke(cli, ["--no-annotate", "--upgrade-package", "small-fake-b"])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr.splitlines()
    assert "small-fake-b==0.3" not in out.stderr.splitlines()


def test_upgrade_packages_option_no_existing_file(pip_conf, runner):
    """
    piptools respects --upgrade-package/-P inline list when the output file
    doesn't exist.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(cli, ["--no-annotate", "-P", "small-fake-b"])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr.splitlines()
    assert "small-fake-b==0.3" in out.stderr.splitlines()


@pytest.mark.parametrize(
    ("current_package", "upgraded_package"),
    (
        pytest.param("small-fake-b==0.1", "small-fake-b==0.3", id="upgrade"),
        pytest.param("small-fake-b==0.3", "small-fake-b==0.1", id="downgrade"),
    ),
)
def test_upgrade_packages_version_option(
    pip_conf, runner, current_package, upgraded_package
):
    """
    piptools respects --upgrade-package/-P inline list with specified versions.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\n" + current_package)

    out = runner.invoke(cli, ["--no-annotate", "--upgrade-package", upgraded_package])

    assert out.exit_code == 0
    stderr_lines = out.stderr.splitlines()
    assert "small-fake-a==0.1" in stderr_lines
    assert upgraded_package in stderr_lines


def test_upgrade_packages_version_option_no_existing_file(pip_conf, runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(cli, ["-P", "small-fake-b==0.2"])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.2" in out.stderr


def test_upgrade_packages_version_option_and_upgrade(pip_conf, runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions
    whilst also doing --upgrade.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")
    with open("requirements.txt", "w") as req_in:
        req_in.write("small-fake-a==0.1\nsmall-fake-b==0.1")

    out = runner.invoke(cli, ["--upgrade", "-P", "small-fake-b==0.1"])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.1" in out.stderr


def test_upgrade_packages_version_option_and_upgrade_no_existing_file(pip_conf, runner):
    """
    piptools respects --upgrade-package/-P inline list with specified versions
    whilst also doing --upgrade and the output file doesn't exist.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\nsmall-fake-b")

    out = runner.invoke(cli, ["--upgrade", "-P", "small-fake-b==0.1"])

    assert out.exit_code == 0
    assert "small-fake-a==0.2" in out.stderr
    assert "small-fake-b==0.1" in out.stderr


def test_quiet_option(runner):
    with open("requirements", "w"):
        pass
    out = runner.invoke(cli, ["--quiet", "requirements"])
    # Pinned requirements result has not been written to stdout or stderr:
    assert not out.stdout_bytes
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
    # Neither dry-run message nor pinned requirements written to output:
    assert not out.stdout_bytes
    # Dry-run message has not been written to stderr:
    assert "dry-run" not in out.stderr.lower()
    # Pinned requirements (just the header in this case) *are* written to stderr:
    assert "# " in out.stderr


def test_generate_hashes_with_editable(pip_conf, runner):
    small_fake_package_dir = os.path.join(PACKAGES_PATH, "small_fake_with_deps")
    small_fake_package_url = path_to_url(small_fake_package_dir)
    with open("requirements.in", "w") as fp:
        fp.write(f"-e {small_fake_package_url}\n")
    out = runner.invoke(cli, ["--no-annotate", "--generate-hashes"])
    expected = (
        "-e {}\n"
        "small-fake-a==0.1 \\\n"
        "    --hash=sha256:5e6071ee6e4c59e0d0408d366f"
        "e9b66781d2cf01be9a6e19a2433bb3c5336330\n"
        "small-fake-b==0.1 \\\n"
        "    --hash=sha256:acdba8f8b8a816213c30d5310c"
        "3fe296c0107b16ed452062f7f994a5672e3b3f\n"
    ).format(small_fake_package_url)
    assert out.exit_code == 0
    assert expected in out.stderr


@pytest.mark.network
def test_generate_hashes_with_url(runner):
    with open("requirements.in", "w") as fp:
        fp.write(
            "https://github.com/jazzband/pip-tools/archive/"
            "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip#egg=pip-tools\n"
        )
    out = runner.invoke(cli, ["--no-annotate", "--generate-hashes"])
    expected = (
        "pip-tools @ https://github.com/jazzband/pip-tools/archive/"
        "7d86c8d3ecd1faa6be11c7ddc6b29a30ffd1dae3.zip \\\n"
        "    --hash=sha256:d24de92e18ad5bf291f25cfcdcf"
        "0171be6fa70d01d0bef9eeda356b8549715e7\n"
    )
    assert out.exit_code == 0
    assert expected in out.stderr


def test_generate_hashes_verbose(pip_conf, runner):
    """
    The hashes generation process should show a progress.
    """
    with open("requirements.in", "w") as fp:
        fp.write("small-fake-a==0.1")

    out = runner.invoke(cli, ["--generate-hashes", "-v"])
    expected_verbose_text = "Generating hashes:\n  small-fake-a\n"
    assert expected_verbose_text in out.stderr


@pytest.mark.network
def test_generate_hashes_with_annotations(runner):
    with open("requirements.in", "w") as fp:
        fp.write("six==1.15.0")

    out = runner.invoke(cli, ["--generate-hashes"])
    assert out.stderr == dedent(
        f"""\
        #
        # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
        # To update, run:
        #
        #    pip-compile --generate-hashes
        #
        six==1.15.0 \\
            --hash=sha256:30639c035cdb23534cd4aa2dd52c3bf48f06e5f4a941509c8bafd8ce11080259 \\
            --hash=sha256:8b74bedcbbbaca38ff6d7491d76f2b06b3592611af620f8426e82dddb04a5ced
            # via -r requirements.in
        """
    )


@pytest.mark.network
def test_generate_hashes_with_split_style_annotations(runner):
    with open("requirements.in", "w") as fp:
        fp.write("Django==1.11.29\n")
        fp.write("django-debug-toolbar==1.11\n")
        fp.write("django-storages==1.9.1\n")
        fp.write("django-taggit==0.24.0\n")
        fp.write("pytz==2020.4\n")
        fp.write("sqlparse==0.3.1\n")

    out = runner.invoke(cli, ["--generate-hashes", "--annotation-style", "split"])
    assert out.stderr == dedent(
        f"""\
        #
        # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
        # To update, run:
        #
        #    pip-compile --generate-hashes
        #
        django==1.11.29 \\
            --hash=sha256:014e3392058d94f40569206a24523ce254d55ad2f9f46c6550b0fe2e4f94cf3f \\
            --hash=sha256:4200aefb6678019a0acf0005cd14cfce3a5e6b9b90d06145fcdd2e474ad4329c
            # via
            #   -r requirements.in
            #   django-debug-toolbar
            #   django-storages
            #   django-taggit
        django-debug-toolbar==1.11 \\
            --hash=sha256:89d75b60c65db363fb24688d977e5fbf0e73386c67acf562d278402a10fc3736 \\
            --hash=sha256:c2b0134119a624f4ac9398b44f8e28a01c7686ac350a12a74793f3dd57a9eea0
            # via -r requirements.in
        django-storages==1.9.1 \\
            --hash=sha256:3103991c2ee8cef8a2ff096709973ffe7106183d211a79f22cf855f33533d924 \\
            --hash=sha256:a59e9923cbce7068792f75344ed7727021ee4ac20f227cf17297d0d03d141e91
            # via -r requirements.in
        django-taggit==0.24.0 \\
            --hash=sha256:710b4d15ec1996550cc68a0abbc41903ca7d832540e52b1336e6858737e410d8 \\
            --hash=sha256:bb8f27684814cd1414b2af75b857b5e26a40912631904038a7ecacd2bfafc3ac
            # via -r requirements.in
        pytz==2020.4 \\
            --hash=sha256:3e6b7dd2d1e0a59084bcee14a17af60c5c562cdc16d828e8eba2e683d3a7e268 \\
            --hash=sha256:5c55e189b682d420be27c6995ba6edce0c0a77dd67bfbe2ae6607134d5851ffd
            # via
            #   -r requirements.in
            #   django
        sqlparse==0.3.1 \\
            --hash=sha256:022fb9c87b524d1f7862b3037e541f68597a730a8843245c349fc93e1643dc4e \\
            --hash=sha256:e162203737712307dfe78860cc56c8da8a852ab2ee33750e33aeadf38d12c548
            # via
            #   -r requirements.in
            #   django-debug-toolbar
        """
    )


@pytest.mark.network
def test_generate_hashes_with_line_style_annotations(runner):
    with open("requirements.in", "w") as fp:
        fp.write("Django==1.11.29\n")
        fp.write("django-debug-toolbar==1.11\n")
        fp.write("django-storages==1.9.1\n")
        fp.write("django-taggit==0.24.0\n")
        fp.write("pytz==2020.4\n")
        fp.write("sqlparse==0.3.1\n")

    out = runner.invoke(cli, ["--generate-hashes", "--annotation-style", "line"])
    assert out.stderr == dedent(
        f"""\
        #
        # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
        # To update, run:
        #
        #    pip-compile --annotation-style=line --generate-hashes
        #
        django==1.11.29 \\
            --hash=sha256:014e3392058d94f40569206a24523ce254d55ad2f9f46c6550b0fe2e4f94cf3f \\
            --hash=sha256:4200aefb6678019a0acf0005cd14cfce3a5e6b9b90d06145fcdd2e474ad4329c
            # via -r requirements.in, django-debug-toolbar, django-storages, django-taggit
        django-debug-toolbar==1.11 \\
            --hash=sha256:89d75b60c65db363fb24688d977e5fbf0e73386c67acf562d278402a10fc3736 \\
            --hash=sha256:c2b0134119a624f4ac9398b44f8e28a01c7686ac350a12a74793f3dd57a9eea0
            # via -r requirements.in
        django-storages==1.9.1 \\
            --hash=sha256:3103991c2ee8cef8a2ff096709973ffe7106183d211a79f22cf855f33533d924 \\
            --hash=sha256:a59e9923cbce7068792f75344ed7727021ee4ac20f227cf17297d0d03d141e91
            # via -r requirements.in
        django-taggit==0.24.0 \\
            --hash=sha256:710b4d15ec1996550cc68a0abbc41903ca7d832540e52b1336e6858737e410d8 \\
            --hash=sha256:bb8f27684814cd1414b2af75b857b5e26a40912631904038a7ecacd2bfafc3ac
            # via -r requirements.in
        pytz==2020.4 \\
            --hash=sha256:3e6b7dd2d1e0a59084bcee14a17af60c5c562cdc16d828e8eba2e683d3a7e268 \\
            --hash=sha256:5c55e189b682d420be27c6995ba6edce0c0a77dd67bfbe2ae6607134d5851ffd
            # via -r requirements.in, django
        sqlparse==0.3.1 \\
            --hash=sha256:022fb9c87b524d1f7862b3037e541f68597a730a8843245c349fc93e1643dc4e \\
            --hash=sha256:e162203737712307dfe78860cc56c8da8a852ab2ee33750e33aeadf38d12c548
            # via -r requirements.in, django-debug-toolbar
        """
    )


def test_filter_pip_markers(pip_conf, runner):
    """
    Check that pip-compile works with pip environment markers (PEP496)
    """
    with open("requirements", "w") as req_in:
        req_in.write("small-fake-a==0.1\nunknown_package==0.1; python_version == '1'")

    out = runner.invoke(cli, ["-n", "requirements"])

    assert out.exit_code == 0
    assert "small-fake-a==0.1" in out.stderr
    assert "unknown_package" not in out.stderr


def test_no_candidates(pip_conf, runner):
    with open("requirements", "w") as req_in:
        req_in.write("small-fake-a>0.3b1,<0.3b2")

    out = runner.invoke(cli, ["-n", "requirements"])

    assert out.exit_code == 2
    assert "Skipped pre-versions:" in out.stderr


def test_no_candidates_pre(pip_conf, runner):
    with open("requirements", "w") as req_in:
        req_in.write("small-fake-a>0.3b1,<0.3b1")

    out = runner.invoke(cli, ["-n", "requirements", "--pre"])

    assert out.exit_code == 2
    assert "Tried pre-versions:" in out.stderr


@pytest.mark.parametrize(
    ("url", "expected_url"),
    (
        pytest.param("https://example.com", b"https://example.com", id="regular url"),
        pytest.param(
            "https://username:password@example.com",
            b"https://username:****@example.com",
            id="url with credentials",
        ),
    ),
)
def test_default_index_url(make_pip_conf, url, expected_url):
    """
    Test help's output with default index URL.
    """
    make_pip_conf(
        dedent(
            f"""\
            [global]
            index-url = {url}
            """
        )
    )

    result = subprocess.run(
        [sys.executable, "-m", "piptools", "compile", "--help"],
        stdout=subprocess.PIPE,
        check=True,
    )

    assert expected_url in result.stdout


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


def test_stdin(pip_conf, runner):
    """
    Test compile requirements from STDIN.
    """
    out = runner.invoke(
        cli,
        ["-", "--output-file", "requirements.txt", "-n", "--no-emit-find-links"],
        input="small-fake-a==0.1",
    )

    assert out.stderr == dedent(
        f"""\
        #
        # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
        # To update, run:
        #
        #    pip-compile --no-emit-find-links --output-file=requirements.txt -
        #
        small-fake-a==0.1
            # via -r -
        Dry-run, so nothing updated.
        """
    )


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
    ("options", "expected"),
    (
        pytest.param(
            ("--annotate",),
            f"""\
            #
            # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
            # To update, run:
            #
            #    pip-compile --no-emit-find-links
            #
            small-fake-a==0.1
                # via
                #   -c constraints.txt
                #   small-fake-with-deps
            small-fake-with-deps==0.1
                # via -r requirements.in
            Dry-run, so nothing updated.
            """,
            id="annotate",
        ),
        pytest.param(
            ("--annotate", "--annotation-style", "line"),
            f"""\
            #
            # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
            # To update, run:
            #
            #    pip-compile --annotation-style=line --no-emit-find-links
            #
            small-fake-a==0.1         # via -c constraints.txt, small-fake-with-deps
            small-fake-with-deps==0.1  # via -r requirements.in
            Dry-run, so nothing updated.
            """,
            id="annotate line style",
        ),
        pytest.param(
            ("--no-annotate",),
            f"""\
            #
            # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
            # To update, run:
            #
            #    pip-compile --no-annotate --no-emit-find-links
            #
            small-fake-a==0.1
            small-fake-with-deps==0.1
            Dry-run, so nothing updated.
            """,
            id="no annotate",
        ),
    ),
)
def test_annotate_option(pip_conf, runner, options, expected):
    """
    The output lines have annotations if the option is turned on.
    """
    with open("constraints.txt", "w") as constraints_in:
        constraints_in.write("small-fake-a==0.1")
    with open("requirements.in", "w") as req_in:
        req_in.write("-c constraints.txt\n")
        req_in.write("small_fake_with_deps")

    out = runner.invoke(cli, [*options, "-n", "--no-emit-find-links"])

    assert out.stderr == dedent(expected)
    assert out.exit_code == 0


@pytest.mark.parametrize(
    ("option", "expected"),
    (
        ("--allow-unsafe", "small-fake-a==0.1"),
        ("--no-allow-unsafe", "# small-fake-a"),
        (None, "# small-fake-a"),
    ),
)
def test_allow_unsafe_option(pip_conf, monkeypatch, runner, option, expected):
    """
    Unsafe packages are printed as expected with and without --allow-unsafe.
    """
    monkeypatch.setattr("piptools.resolver.UNSAFE_PACKAGES", {"small-fake-a"})
    with open("requirements.in", "w") as req_in:
        req_in.write(path_to_url(os.path.join(PACKAGES_PATH, "small_fake_with_deps")))

    out = runner.invoke(cli, ["--no-annotate", option] if option else [])

    assert expected in out.stderr.splitlines()
    assert out.exit_code == 0


@pytest.mark.parametrize(
    ("option", "attr", "expected"),
    (("--cert", "cert", "foo.crt"), ("--client-cert", "client_cert", "bar.pem")),
)
@mock.patch("piptools.scripts.compile.parse_requirements")
def test_cert_option(parse_requirements, runner, option, attr, expected):
    """
    The options --cert and --client-cert have to be passed to the PyPIRepository.
    """
    with open("requirements.in", "w"):
        pass

    runner.invoke(cli, [option, expected])

    # Ensure the options in parse_requirements has the expected option
    args, kwargs = parse_requirements.call_args
    assert getattr(kwargs["options"], attr) == expected


@pytest.mark.parametrize(
    ("option", "expected"),
    (("--build-isolation", True), ("--no-build-isolation", False)),
)
@mock.patch("piptools.scripts.compile.parse_requirements")
def test_build_isolation_option(parse_requirements, runner, option, expected):
    """
    A value of the --build-isolation/--no-build-isolation flag
    must be passed to parse_requirements().
    """
    with open("requirements.in", "w"):
        pass

    runner.invoke(cli, [option])

    # Ensure the options in parse_requirements has the expected build_isolation option
    args, kwargs = parse_requirements.call_args
    assert kwargs["options"].build_isolation is expected


@mock.patch("piptools.scripts.compile.PyPIRepository")
def test_forwarded_args(PyPIRepository, runner):
    """
    Test the forwarded cli args (--pip-args 'arg...') are passed to the pip command.
    """
    with open("requirements.in", "w"):
        pass

    cli_args = ("--no-annotate", "--generate-hashes")
    pip_args = ("--no-color", "--isolated", "--disable-pip-version-check")
    runner.invoke(cli, [*cli_args, "--pip-args", " ".join(pip_args)])
    args, kwargs = PyPIRepository.call_args
    assert set(pip_args).issubset(set(args[0]))


@pytest.mark.parametrize(
    ("cli_option", "infile_option", "expected_package"),
    (
        # no --pre pip-compile should resolve to the last stable version
        (False, False, "small-fake-a==0.2"),
        # pip-compile --pre should resolve to the last pre-released version
        (True, False, "small-fake-a==0.3b1"),
        (False, True, "small-fake-a==0.3b1"),
        (True, True, "small-fake-a==0.3b1"),
    ),
)
def test_pre_option(pip_conf, runner, cli_option, infile_option, expected_package):
    """
    Tests pip-compile respects --pre option.
    """
    with open("requirements.in", "w") as req_in:
        if infile_option:
            req_in.write("--pre\n")
        req_in.write("small-fake-a\n")

    out = runner.invoke(cli, ["--no-annotate", "-n"] + (["-p"] if cli_option else []))

    assert out.exit_code == 0, out.stderr
    assert expected_package in out.stderr.splitlines(), out.stderr


@pytest.mark.parametrize(
    "add_options",
    (
        [],
        ["--output-file", "requirements.txt"],
        ["--upgrade"],
        ["--upgrade", "--output-file", "requirements.txt"],
        ["--upgrade-package", "small-fake-a"],
        ["--upgrade-package", "small-fake-a", "--output-file", "requirements.txt"],
    ),
)
def test_dry_run_option(pip_conf, runner, add_options):
    """
    Tests pip-compile doesn't create requirements.txt file on dry-run.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\n")

    out = runner.invoke(cli, ["--no-annotate", "--dry-run", *add_options])

    assert out.exit_code == 0, out.stderr
    assert "small-fake-a==0.2" in out.stderr.splitlines()
    assert not os.path.exists("requirements.txt")


@pytest.mark.parametrize(
    ("add_options", "expected_cli_output_package"),
    (
        ([], "small-fake-a==0.1"),
        (["--output-file", "requirements.txt"], "small-fake-a==0.1"),
        (["--upgrade"], "small-fake-a==0.2"),
        (["--upgrade", "--output-file", "requirements.txt"], "small-fake-a==0.2"),
        (["--upgrade-package", "small-fake-a"], "small-fake-a==0.2"),
        (
            ["--upgrade-package", "small-fake-a", "--output-file", "requirements.txt"],
            "small-fake-a==0.2",
        ),
    ),
)
def test_dry_run_doesnt_touch_output_file(
    pip_conf, runner, add_options, expected_cli_output_package
):
    """
    Tests pip-compile doesn't touch requirements.txt file on dry-run.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a\n")

    with open("requirements.txt", "w") as req_txt:
        req_txt.write("small-fake-a==0.1\n")

    before_compile_mtime = os.stat("requirements.txt").st_mtime

    out = runner.invoke(cli, ["--no-annotate", "--dry-run", *add_options])

    assert out.exit_code == 0, out.stderr
    assert expected_cli_output_package in out.stderr.splitlines()

    # The package version must NOT be updated in the output file
    with open("requirements.txt") as req_txt:
        assert "small-fake-a==0.1" in req_txt.read().splitlines()

    # The output file must not be touched
    after_compile_mtime = os.stat("requirements.txt").st_mtime
    assert after_compile_mtime == before_compile_mtime


@pytest.mark.parametrize(
    ("empty_input_pkg", "prior_output_pkg"),
    (
        ("", ""),
        ("", "small-fake-a==0.1\n"),
        ("# Nothing to see here", ""),
        ("# Nothing to see here", "small-fake-a==0.1\n"),
    ),
)
def test_empty_input_file_no_header(runner, empty_input_pkg, prior_output_pkg):
    """
    Tests pip-compile creates an empty requirements.txt file,
    given --no-header and empty requirements.in
    """
    with open("requirements.in", "w") as req_in:
        req_in.write(empty_input_pkg)  # empty input file

    with open("requirements.txt", "w") as req_txt:
        req_txt.write(prior_output_pkg)

    runner.invoke(cli, ["--no-header", "requirements.in"])

    with open("requirements.txt") as req_txt:
        assert req_txt.read().strip() == ""


def test_upgrade_package_doesnt_remove_annotation(pip_conf, runner):
    """
    Tests pip-compile --upgrade-package shouldn't remove "via" annotation.
    See: GH-929
    """
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-with-deps\n")

    runner.invoke(cli)

    # Downgrade small-fake-a to 0.1
    with open("requirements.txt", "w") as req_txt:
        req_txt.write(
            "small-fake-with-deps==0.1\n"
            "small-fake-a==0.1         # via small-fake-with-deps\n"
        )

    runner.invoke(cli, ["-P", "small-fake-a", "--no-emit-find-links"])
    with open("requirements.txt") as req_txt:
        assert req_txt.read() == dedent(
            f"""\
            #
            # This file is autogenerated by pip-compile with python \
{sys.version_info.major}.{sys.version_info.minor}
            # To update, run:
            #
            #    pip-compile --no-emit-find-links
            #
            small-fake-a==0.1
                # via small-fake-with-deps
            small-fake-with-deps==0.1
                # via -r requirements.in
            """
        )


@pytest.mark.parametrize(
    "options",
    (
        "--index-url https://example.com",
        "--extra-index-url https://example.com",
        "--find-links ./libs1",
        "--trusted-host example.com",
        "--no-binary :all:",
        "--only-binary :all:",
    ),
)
def test_options_in_requirements_file(runner, options):
    """
    Test the options from requirements.in is copied to requirements.txt.
    """
    with open("requirements.in", "w") as reqs_in:
        reqs_in.write(options)

    out = runner.invoke(cli)
    assert out.exit_code == 0, out

    with open("requirements.txt") as reqs_txt:
        assert options in reqs_txt.read().splitlines()


@pytest.mark.parametrize(
    ("cli_options", "expected_message"),
    (
        pytest.param(
            ["--index-url", "scheme://foo"],
            "Was scheme://foo reachable?",
            id="single index url",
        ),
        pytest.param(
            ["--index-url", "scheme://foo", "--extra-index-url", "scheme://bar"],
            "Were scheme://foo or scheme://bar reachable?",
            id="multiple index urls",
        ),
        pytest.param(
            ["--index-url", "scheme://username:password@host"],
            "Was scheme://username:****@host reachable?",
            id="index url with credentials",
        ),
    ),
)
def test_unreachable_index_urls(runner, cli_options, expected_message):
    """
    Test pip-compile raises an error if index URLs are not reachable.
    """
    with open("requirements.in", "w") as reqs_in:
        reqs_in.write("some-package")

    out = runner.invoke(cli, cli_options)

    assert out.exit_code == 2, out

    stderr_lines = out.stderr.splitlines()
    assert "No versions found" in stderr_lines
    assert expected_message in stderr_lines


@pytest.mark.parametrize(
    ("current_package", "upgraded_package"),
    (
        pytest.param("small-fake-b==0.1", "small-fake-b==0.2", id="upgrade"),
        pytest.param("small-fake-b==0.2", "small-fake-b==0.1", id="downgrade"),
    ),
)
def test_upgrade_packages_option_subdependency(
    pip_conf, runner, current_package, upgraded_package
):
    """
    Test that pip-compile --upgrade-package/-P upgrades/dpwngrades subdependencies.
    """

    with open("requirements.in", "w") as reqs:
        reqs.write("small-fake-with-unpinned-deps\n")

    with open("requirements.txt", "w") as reqs:
        reqs.write("small-fake-a==0.1\n")
        reqs.write(current_package + "\n")
        reqs.write("small-fake-with-unpinned-deps==0.1\n")

    out = runner.invoke(
        cli, ["--no-annotate", "--dry-run", "--upgrade-package", upgraded_package]
    )

    stderr_lines = out.stderr.splitlines()
    assert "small-fake-a==0.1" in stderr_lines, "small-fake-a must keep its version"
    assert (
        upgraded_package in stderr_lines
    ), f"{current_package} must be upgraded/downgraded to {upgraded_package}"


@pytest.mark.parametrize(
    ("input_opts", "output_opts"),
    (
        # Test that input options overwrite output options
        pytest.param(
            "--index-url https://index-url",
            "--index-url https://another-index-url",
            id="index url",
        ),
        pytest.param(
            "--extra-index-url https://extra-index-url",
            "--extra-index-url https://another-extra-index-url",
            id="extra index url",
        ),
        pytest.param("--find-links dir", "--find-links another-dir", id="find links"),
        pytest.param(
            "--trusted-host hostname",
            "--trusted-host another-hostname",
            id="trusted host",
        ),
        pytest.param(
            "--no-binary :package:", "--no-binary :another-package:", id="no binary"
        ),
        pytest.param(
            "--only-binary :package:",
            "--only-binary :another-package:",
            id="only binary",
        ),
        # Test misc corner cases
        pytest.param("", "--index-url https://index-url", id="empty input options"),
        pytest.param(
            "--index-url https://index-url",
            (
                "--index-url https://index-url\n"
                "--extra-index-url https://another-extra-index-url"
            ),
            id="partially matched options",
        ),
    ),
)
def test_remove_outdated_options(runner, input_opts, output_opts):
    """
    Test that the options from the current requirements.txt wouldn't stay
    after compile if they were removed from requirements.in file.
    """
    with open("requirements.in", "w") as req_in:
        req_in.write(input_opts)
    with open("requirements.txt", "w") as req_txt:
        req_txt.write(output_opts)

    out = runner.invoke(cli, ["--no-header"])

    assert out.exit_code == 0, out
    assert out.stderr.strip() == input_opts


def test_sub_dependencies_with_constraints(pip_conf, runner):
    # Write constraints file
    with open("constraints.txt", "w") as constraints_in:
        constraints_in.write("small-fake-a==0.1\n")
        constraints_in.write("small-fake-b==0.2\n")
        constraints_in.write("small-fake-with-unpinned-deps==0.1")

    with open("requirements.in", "w") as req_in:
        req_in.write("-c constraints.txt\n")
        req_in.write("small_fake_with_deps_and_sub_deps")  # require fake package

    out = runner.invoke(cli, ["--no-annotate"])

    assert out.exit_code == 0

    req_out_lines = set(out.stderr.splitlines())
    assert {
        "small-fake-a==0.1",
        "small-fake-b==0.2",
        "small-fake-with-deps-and-sub-deps==0.1",
        "small-fake-with-unpinned-deps==0.1",
    }.issubset(req_out_lines)


def test_preserve_compiled_prerelease_version(pip_conf, runner):
    with open("requirements.in", "w") as req_in:
        req_in.write("small-fake-a")

    with open("requirements.txt", "w") as req_txt:
        req_txt.write("small-fake-a==0.3b1")

    out = runner.invoke(cli, ["--no-annotate", "--no-header"])

    assert out.exit_code == 0, out
    assert "small-fake-a==0.3b1" in out.stderr.splitlines()


def test_prefer_binary_dist(
    pip_conf, make_package, make_sdist, make_wheel, tmpdir, runner
):
    """
    Test pip-compile chooses a correct version of a package with
    a binary distribution when PIP_PREFER_BINARY environment variable is on.
    """
    dists_dir = tmpdir / "dists"

    # Make first-package==1.0 and wheels
    first_package_v1 = make_package(name="first-package", version="1.0")
    make_wheel(first_package_v1, dists_dir)

    # Make first-package==2.0 and sdists
    first_package_v2 = make_package(name="first-package", version="2.0")
    make_sdist(first_package_v2, dists_dir)

    # Make second-package==1.0 which depends on first-package, and wheels
    second_package_v1 = make_package(
        name="second-package", version="1.0", install_requires=["first-package"]
    )
    make_wheel(second_package_v1, dists_dir)

    with open("requirements.in", "w") as req_in:
        req_in.write("second-package")

    out = runner.invoke(
        cli,
        ["--no-annotate", "--find-links", str(dists_dir)],
        env={"PIP_PREFER_BINARY": "1"},
    )

    assert out.exit_code == 0, out
    assert "first-package==1.0" in out.stderr.splitlines(), out.stderr
    assert "second-package==1.0" in out.stderr.splitlines(), out.stderr


@pytest.mark.parametrize("prefer_binary", (True, False))
def test_prefer_binary_dist_even_there_is_source_dists(
    pip_conf, make_package, make_sdist, make_wheel, tmpdir, runner, prefer_binary
):
    """
    Test pip-compile chooses a correct version of a package with a binary distribution
    (despite a source dist existing) when PIP_PREFER_BINARY environment variable is on
    or off.

    Regression test for issue GH-1118.
    """
    dists_dir = tmpdir / "dists"

    # Make first version of package with only wheels
    package_v1 = make_package(name="test-package", version="1.0")
    make_wheel(package_v1, dists_dir)

    # Make seconds version with wheels and sdists
    package_v2 = make_package(name="test-package", version="2.0")
    make_wheel(package_v2, dists_dir)
    make_sdist(package_v2, dists_dir)

    with open("requirements.in", "w") as req_in:
        req_in.write("test-package")

    out = runner.invoke(
        cli,
        ["--no-annotate", "--find-links", str(dists_dir)],
        env={"PIP_PREFER_BINARY": str(int(prefer_binary))},
    )

    assert out.exit_code == 0, out
    assert "test-package==2.0" in out.stderr.splitlines(), out.stderr


@pytest.mark.parametrize("output_content", ("test-package-1==0.1", ""))
def test_duplicate_reqs_combined(
    pip_conf, make_package, make_sdist, tmpdir, runner, output_content
):
    """
    Test pip-compile tracks dependencies properly when install requirements are
    combined, especially when an output file already exists.

    Regression test for issue GH-1154.
    """
    test_package_1 = make_package("test_package_1", version="0.1")
    test_package_2 = make_package(
        "test_package_2", version="0.1", install_requires=["test-package-1"]
    )

    dists_dir = tmpdir / "dists"

    for pkg in (test_package_1, test_package_2):
        make_sdist(pkg, dists_dir)

    with open("requirements.in", "w") as reqs_in:
        reqs_in.write(f"file:{test_package_2}\n")
        reqs_in.write(f"file:{test_package_2}#egg=test-package-2\n")

    if output_content:
        with open("requirements.txt", "w") as reqs_out:
            reqs_out.write(output_content)

    out = runner.invoke(cli, ["--find-links", str(dists_dir)])

    assert out.exit_code == 0, out
    assert str(test_package_2) in out.stderr
    assert "test-package-1==0.1" in out.stderr


def test_combine_extras(pip_conf, runner, make_package):
    """
    Ensure that multiple declarations of a dependency that specify different
    extras produces a requirement for that package with the union of the extras
    """
    package_with_extras = make_package(
        "package_with_extras",
        extras_require={
            "extra1": ["small-fake-a==0.1"],
            "extra2": ["small-fake-b==0.1"],
        },
    )

    with open("requirements.in", "w") as req_in:
        req_in.writelines(
            [
                "-r ./requirements-second.in\n",
                f"{package_with_extras}[extra1]",
            ]
        )

    with open("requirements-second.in", "w") as req_sec_in:
        req_sec_in.write(f"{package_with_extras}[extra2]")

    out = runner.invoke(cli, ["-n"])

    assert out.exit_code == 0
    assert "package-with-extras" in out.stderr
    assert "small-fake-a==" in out.stderr
    assert "small-fake-b==" in out.stderr


@pytest.mark.parametrize(
    ("pkg2_install_requires", "req_in_content", "out_expected_content"),
    (
        pytest.param(
            "",
            ["test-package-1===0.1.0\n"],
            ["test-package-1===0.1.0"],
            id="pin package with ===",
        ),
        pytest.param(
            "",
            ["test-package-1==0.1.0\n"],
            ["test-package-1==0.1.0"],
            id="pin package with ==",
        ),
        pytest.param(
            "test-package-1==0.1.0",
            ["test-package-1===0.1.0\n", "test-package-2==0.1.0\n"],
            ["test-package-1===0.1.0", "test-package-2==0.1.0"],
            id="dep === pin preferred over == pin, main package == pin",
        ),
        pytest.param(
            "test-package-1==0.1.0",
            ["test-package-1===0.1.0\n", "test-package-2===0.1.0\n"],
            ["test-package-1===0.1.0", "test-package-2===0.1.0"],
            id="dep === pin preferred over == pin, main package === pin",
        ),
        pytest.param(
            "test-package-1==0.1.0",
            ["test-package-2===0.1.0\n"],
            ["test-package-1==0.1.0", "test-package-2===0.1.0"],
            id="dep == pin conserved, main package === pin",
        ),
    ),
)
def test_triple_equal_pinned_dependency_is_used(
    runner,
    make_package,
    make_wheel,
    tmpdir,
    pkg2_install_requires,
    req_in_content,
    out_expected_content,
):
    """
    Test that pip-compile properly emits the pinned requirement with ===
    torchvision 0.8.2 requires torch==1.7.1 which can resolve to versions with
    patches (e.g. torch 1.7.1+cu110), we want torch===1.7.1 without patches
    """

    dists_dir = tmpdir / "dists"

    test_package_1 = make_package("test_package_1", version="0.1.0")
    make_wheel(test_package_1, dists_dir)

    test_package_2 = make_package(
        "test_package_2", version="0.1.0", install_requires=[pkg2_install_requires]
    )
    make_wheel(test_package_2, dists_dir)

    with open("requirements.in", "w") as reqs_in:
        for line in req_in_content:
            reqs_in.write(line)

    out = runner.invoke(cli, ["--find-links", str(dists_dir)])

    assert out.exit_code == 0, out
    for line in out_expected_content:
        assert line in out.stderr


METADATA_TEST_CASES = (
    pytest.param(
        "setup.cfg",
        """
            [metadata]
            name = sample_lib
            author = Vincent Driessen
            author_email = me@nvie.com

            [options]
            packages = find:
            install_requires =
                small-fake-a==0.1
                small-fake-b==0.2

            [options.extras_require]
            dev =
                small-fake-c==0.3
                small-fake-d==0.4
            test =
                small-fake-e==0.5
                small-fake-f==0.6
        """,
        id="setup.cfg",
    ),
    pytest.param(
        "setup.py",
        """
            from setuptools import setup, find_packages

            setup(
                name="sample_lib",
                version=0.1,
                install_requires=["small-fake-a==0.1", "small-fake-b==0.2"],
                packages=find_packages(),
                extras_require={
                    "dev": ["small-fake-c==0.3", "small-fake-d==0.4"],
                    "test": ["small-fake-e==0.5", "small-fake-f==0.6"],
                },
            )
        """,
        id="setup.py",
    ),
    pytest.param(
        "pyproject.toml",
        """
            [build-system]
            requires = ["flit_core >=2,<4"]
            build-backend = "flit_core.buildapi"

            [tool.flit.metadata]
            module = "sample_lib"
            author = "Vincent Driessen"
            author-email = "me@nvie.com"

            requires = ["small-fake-a==0.1", "small-fake-b==0.2"]

            [tool.flit.metadata.requires-extra]
            dev  = ["small-fake-c==0.3", "small-fake-d==0.4"]
            test = ["small-fake-e==0.5", "small-fake-f==0.6"]
        """,
        id="flit",
    ),
    pytest.param(
        "pyproject.toml",
        """
            [build-system]
            requires = ["poetry_core>=1.0.0"]
            build-backend = "poetry.core.masonry.api"

            [tool.poetry]
            name = "sample_lib"
            version = "0.1.0"
            description = ""
            authors = ["Vincent Driessen <me@nvie.com>"]

            [tool.poetry.dependencies]
            python = "*"
            small-fake-a = "0.1"
            small-fake-b = "0.2"

            small-fake-c = "0.3"
            small-fake-d = "0.4"
            small-fake-e = "0.5"
            small-fake-f = "0.6"

            [tool.poetry.extras]
            dev  = ["small-fake-c", "small-fake-d"]
            test = ["small-fake-e", "small-fake-f"]
        """,
        id="poetry",
    ),
)


@pytest.mark.network
@pytest.mark.parametrize(("fname", "content"), METADATA_TEST_CASES)
@pytest.mark.xfail(is_pypy, reason="https://github.com/jazzband/pip-tools/issues/1375")
def test_input_formats(fake_dists, runner, make_module, fname, content):
    """
    Test different dependency formats as input file.
    """
    meta_path = make_module(fname=fname, content=content)
    out = runner.invoke(cli, ["-n", "--find-links", fake_dists, meta_path])
    assert out.exit_code == 0, out.stderr
    assert "small-fake-a==0.1" in out.stderr
    assert "small-fake-b==0.2" in out.stderr
    assert "small-fake-c" not in out.stderr
    assert "small-fake-d" not in out.stderr
    assert "small-fake-e" not in out.stderr
    assert "small-fake-f" not in out.stderr
    assert "extra ==" not in out.stderr


@pytest.mark.network
@pytest.mark.parametrize(("fname", "content"), METADATA_TEST_CASES)
@pytest.mark.xfail(is_pypy, reason="https://github.com/jazzband/pip-tools/issues/1375")
def test_one_extra(fake_dists, runner, make_module, fname, content):
    """
    Test one `--extra` (dev) passed, other extras (test) must be ignored.
    """
    meta_path = make_module(fname=fname, content=content)
    out = runner.invoke(
        cli, ["-n", "--extra", "dev", "--find-links", fake_dists, meta_path]
    )
    assert out.exit_code == 0, out.stderr
    assert "small-fake-a==0.1" in out.stderr
    assert "small-fake-b==0.2" in out.stderr
    assert "small-fake-c==0.3" in out.stderr
    assert "small-fake-d==0.4" in out.stderr
    assert "small-fake-e" not in out.stderr
    assert "small-fake-f" not in out.stderr
    assert "extra ==" not in out.stderr


@pytest.mark.network
@pytest.mark.parametrize(
    "extra_opts",
    (
        pytest.param(("--extra", "dev", "--extra", "test"), id="singular"),
        pytest.param(("--extra", "dev,test"), id="comma-separated"),
    ),
)
@pytest.mark.parametrize(("fname", "content"), METADATA_TEST_CASES)
@pytest.mark.xfail(is_pypy, reason="https://github.com/jazzband/pip-tools/issues/1375")
def test_multiple_extras(fake_dists, runner, make_module, fname, content, extra_opts):
    """
    Test passing multiple `--extra` params.
    """
    meta_path = make_module(fname=fname, content=content)
    out = runner.invoke(
        cli,
        [
            "-n",
            *extra_opts,
            "--find-links",
            fake_dists,
            meta_path,
        ],
    )
    assert out.exit_code == 0, out.stderr
    assert "small-fake-a==0.1" in out.stderr
    assert "small-fake-b==0.2" in out.stderr
    assert "small-fake-c==0.3" in out.stderr
    assert "small-fake-d==0.4" in out.stderr
    assert "small-fake-e==0.5" in out.stderr
    assert "small-fake-f==0.6" in out.stderr
    assert "extra ==" not in out.stderr


def test_extras_fail_with_requirements_in(runner, tmpdir):
    """
    Test that passing `--extra` with `requirements.in` input file fails.
    """
    path = os.path.join(tmpdir, "requirements.in")
    with open(path, "w") as stream:
        stream.write("\n")
    out = runner.invoke(cli, ["-n", "--extra", "something", path])
    assert out.exit_code == 2
    exp = "--extra has effect only with setup.py and PEP-517 input formats"
    assert exp in out.stderr


def test_cli_compile_strip_extras(runner, make_package, make_sdist, tmpdir):
    """
    Assures that --strip-extras removes mention of extras from output.
    """
    test_package_1 = make_package(
        "test_package_1", version="0.1", extras_require={"more": "test_package_2"}
    )
    test_package_2 = make_package(
        "test_package_2",
        version="0.1",
    )
    dists_dir = tmpdir / "dists"

    for pkg in (test_package_1, test_package_2):
        make_sdist(pkg, dists_dir)

    with open("requirements.in", "w") as reqs_out:
        reqs_out.write("test_package_1[more]")

    out = runner.invoke(cli, ["--strip-extras", "--find-links", str(dists_dir)])

    assert out.exit_code == 0, out
    assert "test-package-2==0.1" in out.stderr
    assert "[more]" not in out.stderr
