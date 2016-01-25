import json
from functools import partial

from pip._vendor.packaging.version import Version
from pip._vendor.pkg_resources import Requirement
from pip.req import InstallRequirement
from pytest import fixture

from piptools.cache import DependencyCache
from piptools.repositories.base import BaseRepository
from piptools.resolver import Resolver
from piptools.utils import as_tuple, make_install_requirement


class FakeRepository(BaseRepository):
    def __init__(self):
        with open('tests/fixtures/fake-index.json', 'r') as f:
            self.index = json.load(f)

        with open('tests/fixtures/fake-editables.json', 'r') as f:
            self.editables = json.load(f)

    def find_best_match(self, ireq, prereleases=False):
        if ireq.editable:
            return ireq

        versions = ireq.specifier.filter(self.index[ireq.req.key], prereleases=prereleases)
        best_version = max(versions, key=Version)
        return make_install_requirement(ireq.req.key, best_version, ireq.extras)

    def get_dependencies(self, ireq):
        if ireq.editable:
            return self.editables[str(ireq.link)]

        name, version, extras = as_tuple(ireq)
        # Store non-extra dependencies under the empty string
        extras = ireq.extras + ("",)
        dependencies = [dep for extra in extras for dep in self.index[name][version][extra]]
        return [InstallRequirement.from_line(dep) for dep in dependencies]


class FakeInstalledDistribution(object):
    def __init__(self, line, deps=None):
        if deps is None:
            deps = []
        self.deps = [Requirement.parse(d) for d in deps]

        self.req = Requirement.parse(line)

        self.key = self.req.key
        self.specifier = self.req.specifier

        self.version = line.split("==")[1]

    def requires(self):
        return self.deps

    def as_requirement(self):
        return self.req


@fixture
def fake_dist():
    return FakeInstalledDistribution


@fixture
def repository():
    return FakeRepository()


@fixture
def depcache(tmpdir):
    return DependencyCache(str(tmpdir))


@fixture
def resolver(depcache, repository):
    # TODO: It'd be nicer if Resolver instance could be set up and then
    #       use .resolve(...) on the specset, instead of passing it to
    #       the constructor like this (it's not reusable)
    return partial(Resolver, repository=repository, cache=depcache)


@fixture
def base_resolver(depcache):
    return partial(Resolver, cache=depcache)


@fixture
def from_line():
    return InstallRequirement.from_line


@fixture
def from_editable():
    return InstallRequirement.from_editable
