import json
import optparse
import os
import shlex
import shutil
import subprocess
import sys
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from textwrap import dedent
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Tuple

import pytest
from click.testing import CliRunner
from pip._internal.index.package_finder import PackageFinder
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.network.session import PipSession
from pip._internal.req import InstallRequirement
from pip._internal.req.constructors import (
    install_req_from_editable,
    install_req_from_line,
)
from pip._internal.utils.urls import path_to_url
from pip._vendor.packaging.version import Version
from pip._vendor.pkg_resources import Requirement
from typing_extensions import Protocol

from piptools.cache import DependencyCache
from piptools.exceptions import NoCandidateFound
from piptools.repositories import PyPIRepository
from piptools.repositories.base import BaseRepository
from piptools.resolver import Resolver
from piptools.utils import (
    as_tuple,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
    make_install_requirement,
)

from .constants import MINIMAL_WHEELS_PATH
from .utils import looks_like_ci


class FakeRepository(BaseRepository):
    def __init__(self):
        with open("tests/test_data/fake-index.json") as f:
            self.index = json.load(f)

        with open("tests/test_data/fake-editables.json") as f:
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

    def copy_ireq_dependencies(self, source, dest):
        # No state to update.
        pass

    @property
    def options(self) -> optparse.Values:
        """Not used"""

    @property
    def session(self) -> PipSession:
        """Not used"""

    @property
    def finder(self) -> PackageFinder:
        """Not used"""


class FakeMetadataProvider(NamedTuple):
    files_dir: Path

    def _get_metadata_path(self, name: str) -> str:
        """Method relied upon by sync implementation"""
        return str(self.files_dir / name)

    def read_metadata(self, name: str) -> Optional[str]:
        path = self.files_dir / name
        if path.is_file():
            return path.read_text()
        else:
            return None

    def write_metadata(self, name: str, content: str) -> None:
        (self.files_dir / name).write_text(content)


class FakeInstalledDistribution:
    def __init__(
        self, line: str, deps: Optional[Iterable[str]], provider: FakeMetadataProvider
    ):
        if deps is None:
            deps = []
        self.deps = [Requirement.parse(d) for d in deps]

        self.req = Requirement.parse(line)

        self.key = key_from_req(self.req)
        self.specifier = self.req.specifier

        self.version = line.split("==")[1]
        self._provider = provider

    @property
    def provider(self) -> FakeMetadataProvider:
        return self._provider

    def requires(self):
        return self.deps


def pytest_collection_modifyitems(config, items):
    for item in items:
        # Mark network tests as flaky
        if item.get_closest_marker("network") and looks_like_ci():
            item.add_marker(pytest.mark.flaky(reruns=3, reruns_delay=2))


class FakeDistFunc(Protocol):
    def __call__(
        self, line: str, deps: Optional[Iterable[str]] = ...
    ) -> FakeInstalledDistribution:
        ...


@pytest.fixture
def fake_dist():
    with TemporaryDirectory() as metadata_dir:

        def make_fake_dist(
            line: str, deps: Optional[Iterable[str]] = None
        ) -> FakeInstalledDistribution:
            provider = FakeMetadataProvider(Path(metadata_dir))
            return FakeInstalledDistribution(line, deps, provider)

        yield make_fake_dist


@pytest.fixture
def repository():
    return FakeRepository()


@pytest.fixture
def pypi_repository(tmpdir):
    return PyPIRepository(
        ["--index-url", PyPIRepository.DEFAULT_INDEX_URL],
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
    return partial(Resolver, repository=repository, cache=depcache)


@pytest.fixture
def base_resolver(depcache):
    return partial(Resolver, cache=depcache)


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
        make_package("small-fake-d", version="0.4"),
        make_package("small-fake-e", version="0.5"),
        make_package("small-fake-f", version="0.6"),
    ]
    for pkg in pkgs:
        make_wheel(pkg, dists_path)
    return dists_path


class SmallFakeVcsIreqFunc(Protocol):
    def __call__(self, is_vcs: bool) -> Tuple[InstallRequirement, str]:
        ...


@contextmanager
def _permissive_temp_dir() -> Iterator[str]:
    """
    We can't always use TemporaryDirectory because that relies on shutil.rmtree to
    cleanup which sometimes fails on Windows for Pythons before 3.8. In this case,
    we want to ignore that failure so we don't prevent tests from passing in CI.
    """
    temp_dir = mkdtemp()
    try:
        yield temp_dir
    finally:
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            pass


@pytest.fixture(params=["editable", "non-editable"])
def small_fake_vcs_ireq(request, from_editable, from_line):
    """Creates a VCS repo with a package in its root.

    Fixture is a function which takes arguments and returns an ireq and the current
    revision of the VCS repo.

    The returned ireq is controlled by the arguments, and can either be a VCS ireq or
    not (eg with `git+` or just a bare `file:`) and can be editable or not.
    """
    editable = request.param == "editable"
    with _permissive_temp_dir() as repo_dir, _permissive_temp_dir() as source_dir:

        def git(cmd: str, **kwargs: Any) -> subprocess.CompletedProcess:
            """Helper to run git commands in the temp repo."""
            args = shlex.split(cmd)
            return subprocess.run(["git"] + args, cwd=repo_dir, check=True, **kwargs)

        def make_small_fake_vcs_ireq(is_vcs: bool) -> Tuple[InstallRequirement, str]:
            # Setup git repo with simple setup.py file and a single commit.
            (Path(repo_dir) / "setup.py").write_text(
                "from setuptools import setup\n"
                "\n"
                "setup(name='small_fake_vcs', version=0.1)\n"
            )
            git("init .")
            git("config user.email ''")
            git("config user.name 'tests'")
            git("add setup.py")
            git("commit -m 'initial commit'")
            revision = (
                git("rev-parse HEAD", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                .stdout.decode()
                .rstrip()
            )

            # Construct ireq
            file_url = path_to_url(repo_dir)
            if is_vcs:
                ireq_str = f"git+{file_url}#egg=small-fake-vcs"
            else:
                ireq_str = f"{file_url}#egg=small-fake-vcs"
            if editable:
                ireq = from_editable(ireq_str)
            else:
                ireq = from_line(ireq_str)
            ireq.source_dir = os.path.join(source_dir, "repo")

            return ireq, revision

        yield make_small_fake_vcs_ireq
