from pip.req import InstallRequirement
from pytest import fixture


@fixture
def from_line():
    return InstallRequirement.from_line


@fixture
def from_editable():
    return InstallRequirement.from_editable
