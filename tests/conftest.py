from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from textwrap import dedent

import pytest
from click.testing import CliRunner
from pip._internal.commands.install import InstallCommand
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.network.session import PipSession
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._vendor.packaging.version import Version
from pip._vendor.pkg_resources import Requirement

from piptools._compat.pip_compat import uses_pkg_resources
from piptools.cache import DependencyCache
from piptools.exceptions import NoCandidateFound
from piptools.logging import log
from piptools.repositories import PyPIRepository
from piptools.repositories.base import BaseRepository
from piptools.resolver import BacktrackingResolver, LegacyResolver
from piptools.utils import (
    as_tuple,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
    make_install_requirement,
)

from .constants import MINIMAL_WHEELS_PATH, TEST_DATA_PATH
from .utils import looks_like_ci


@dataclass
class FakeOptions:
    features_enabled: list[str] = field(default_factory=list)
    deprecated_features_enabled: list[str] = field(default_factory=list)
    target_dir: str | None = None


class FakeRepository(BaseRepository):
    def __init__(self, options: FakeOptions):
        self._options = options

        with open(os.path.join(TEST_DATA_PATH, "fake-index.json")) as f:
            self.index = json.load(f)

        with open(os.path.join(TEST_DATA_PATH, "fake-editables.json")) as f:
            self.editables = json.load(f)

    def get_hashes(self, ireq):
        # Some fake hashes
        return {
            "test:123",
            "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        }

    def find_best_match(self, ireq, prereleases=False):
        if ireq.editable:
            return ireq

        versions = list(
            ireq.specifier.filter(
                self.index[key_from_ireq(ireq)], prereleases=prereleases
            )
        )
        if not versions:
            tried_versions = [
                InstallationCandidate(ireq.name, version, "https://fake.url.foo")
                for version in self.index[key_from_ireq(ireq)]
            ]
            raise NoCandidateFound(ireq, tried_versions, ["https://fake.url.foo"])
        best_version = max(versions, key=Version)
        return make_install_requirement(key_from_ireq(ireq), best_version, ireq)

    def get_dependencies(self, ireq):
        if ireq.editable or is_url_requirement(ireq):
            return self.editables[str(ireq.link)]

        name, version, extras = as_tuple(ireq)
        # Store non-extra dependencies under the empty string
        extras += ("",)
        dependencies = [
            dep for extra in extras for dep in self.index[name][version][extra]
        ]
        return [
            install_req_from_line(dep, constraint=ireq.constraint)
            for dep in dependencies
        ]

    @contextmanager
    def allow_all_wheels(self):
        # No need to do an actual pip.Wheel mock here.
        yield

    @property
    def options(self):
        return self._options

    @property
    def session(self) -> PipSession:
        """Not used"""

    @property
    def finder(self) -> PackageFinder:
        """Not used"""

    @property
    def command(self) -> InstallCommand:
        """Not used"""


class FakeInstalledDistribution:
    def __init__(self, line, deps=None):
        if deps is None:
            deps = []
        self.dep_strs = deps
        self.deps = [Requirement.parse(d) for d in deps]

        self.req = Requirement.parse(line)

        self.key = key_from_req(self.req)
        self.specifier = self.req.specifier

        self.version = line.split("==")[1]

    # The Distribution interface has changed between pkg_resources and
    # importlib.metadata.
    if uses_pkg_resources:

        def requires(self):
            return self.deps

    else:

        @property
        def requires(self):
            return self.dep_strs


def pytest_collection_modifyitems(config, items):
    for item in items:
        # Mark network tests as flaky
        if item.get_closest_marker("network") and looks_like_ci():
            item.add_marker(pytest.mark.flaky(reruns=3, reruns_delay=2))


@pytest.fixture
def fake_dist():
    return FakeInstalledDistribution


@pytest.fixture
def repository():
    return FakeRepository(
        options=FakeOptions(deprecated_features_enabled=["legacy-resolver"])
    )


@pytest.fixture
def pypi_repository(tmpdir):
    return PyPIRepository(
        [
            "--index-url",
            PyPIRepository.DEFAULT_INDEX_URL,
            "--use-deprecated",
            "legacy-resolver",
        ],
        cache_dir=(tmpdir / "pypi-repo"),
    )


@pytest.fixture
def depcache(tmpdir):
    return DependencyCache(tmpdir / "dep-cache")


@pytest.fixture
def resolver(depcache, repository):
    # TODO: It'd be nicer if Resolver instance could be set up and then
    #       use .resolve(...) on the specset, instead of passing it to
    #       the constructor like this (it's not reusable)
    return partial(
        LegacyResolver, repository=repository, cache=depcache, existing_constraints={}
    )


@pytest.fixture
def backtracking_resolver(depcache):
    # TODO: It'd be nicer if Resolver instance could be set up and then
    #       use .resolve(...) on the specset, instead of passing it to
    #       the constructor like this (it's not reusable)
    return partial(
        BacktrackingResolver,
        repository=FakeRepository(options=FakeOptions()),
        cache=depcache,
        existing_constraints={},
    )


@pytest.fixture
def base_resolver(depcache):
    return partial(LegacyResolver, cache=depcache, existing_constraints={})


@pytest.fixture
def from_line():
    return install_req_from_line


@pytest.fixture
def from_editable():
    return install_req_from_editable


@pytest.fixture
def runner():
    cli_runner = CliRunner(mix_stderr=False)
    with cli_runner.isolated_filesystem():
        yield cli_runner


@pytest.fixture
def tmpdir_cwd(tmpdir):
    with tmpdir.as_cwd():
        yield tmpdir


@pytest.fixture
def make_pip_conf(tmpdir, monkeypatch):
    created_paths = []

    def _make_pip_conf(content):
        pip_conf_file = "pip.conf" if os.name != "nt" else "pip.ini"
        path = (tmpdir / pip_conf_file).strpath

        with open(path, "w") as f:
            f.write(content)

        monkeypatch.setenv("PIP_CONFIG_FILE", path)

        created_paths.append(path)
        return path

    try:
        yield _make_pip_conf
    finally:
        for path in created_paths:
            os.remove(path)


@pytest.fixture
def pip_conf(make_pip_conf):
    return make_pip_conf(
        dedent(
            f"""\
            [global]
            no-index = true
            find-links = {MINIMAL_WHEELS_PATH}
            """
        )
    )


@pytest.fixture
def pip_with_index_conf(make_pip_conf):
    return make_pip_conf(
        dedent(
            f"""\
            [global]
            index-url = http://example.com
            find-links = {MINIMAL_WHEELS_PATH}
            """
        )
    )


@pytest.fixture
def make_package(tmp_path):
    """
    Make a package from a given name, version and list of required packages.
    """

    def _make_package(name, version="0.1", install_requires=None, extras_require=None):

        if install_requires is None:
            install_requires = []

        if extras_require is None:
            extras_require = dict()

        install_requires_str = "[{}]".format(
            ",".join(f"{package!r}" for package in install_requires)
        )

        package_dir = tmp_path / "packages" / name / version
        package_dir.mkdir(parents=True)

        with (package_dir / "setup.py").open("w") as fp:
            fp.write(
                dedent(
                    f"""\
                    from setuptools import setup
                    setup(
                        name={name!r},
                        version={version!r},
                        author="pip-tools",
                        author_email="pip-tools@localhost",
                        url="https://github.com/jazzband/pip-tools",
                        install_requires={install_requires_str},
                        extras_require={extras_require},
                    )
                    """
                )
            )

        # Create a README to avoid setuptools warnings.
        (package_dir / "README").touch()

        return package_dir

    return _make_package


@pytest.fixture
def run_setup_file():
    """
    Run a setup.py file from a given package dir.
    """

    def _run_setup_file(package_dir_path, *args):
        setup_file = package_dir_path / "setup.py"
        return subprocess.run(
            [sys.executable, str(setup_file), *args],
            cwd=str(package_dir_path),
            stdout=subprocess.DEVNULL,
            check=True,
        )  # nosec

    return _run_setup_file


@pytest.fixture
def make_wheel(run_setup_file):
    """
    Make a wheel distribution from a given package dir.
    """

    def _make_wheel(package_dir, dist_dir, *args):
        return run_setup_file(
            package_dir, "bdist_wheel", "--dist-dir", str(dist_dir), *args
        )

    return _make_wheel


@pytest.fixture
def make_sdist(run_setup_file):
    """
    Make a source distribution from a given package dir.
    """

    def _make_sdist(package_dir, dist_dir, *args):
        return run_setup_file(package_dir, "sdist", "--dist-dir", str(dist_dir), *args)

    return _make_sdist


@pytest.fixture
def make_module(tmpdir):
    """
    Make a metadata file with the given name and content and a fake module.
    """

    def _make_module(fname, content):
        path = os.path.join(tmpdir, "sample_lib")
        os.mkdir(path)
        path = os.path.join(tmpdir, "sample_lib", "__init__.py")
        with open(path, "w") as stream:
            stream.write("'example module'\n__version__ = '1.2.3'")
        if fname == "setup.cfg":
            path = os.path.join(tmpdir, "pyproject.toml")
            with open(path, "w") as stream:
                stream.write(
                    "\n".join(
                        (
                            "[build-system]",
                            'requires = ["setuptools"]',
                            'build-backend = "setuptools.build_meta"',
                        )
                    )
                )
        path = os.path.join(tmpdir, fname)
        with open(path, "w") as stream:
            stream.write(dedent(content))
        return path

    return _make_module


@pytest.fixture
def fake_dists(tmpdir, make_package, make_wheel):
    """
    Generate distribution packages `small-fake-{a..f}`
    """
    dists_path = os.path.join(tmpdir, "dists")
    pkgs = [
        make_package("small-fake-a", version="0.1"),
        make_package("small-fake-b", version="0.2"),
        make_package("small-fake-c", version="0.3"),
    ]
    for pkg in pkgs:
        make_wheel(pkg, dists_path)
    return dists_path


@pytest.fixture
def venv(tmp_path):
    """Create a temporary venv and get the path of its directory of executables."""
    subprocess.run(
        [sys.executable, "-m", "venv", os.fspath(tmp_path)],
        check=True,
    )
    return tmp_path / ("Scripts" if platform.system() == "Windows" else "bin")


@pytest.fixture(autouse=True)
def _reset_log():
    """
    Since piptools.logging.log is a global variable we have to restore its initial
    state. Some tests can change logger verbosity which might cause a conflict
    with other tests that depend on it.
    """
    log.reset()
