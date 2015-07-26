import pip
import collections
from .utils import flat_map
from .exceptions import IncompatibleRequirements

PACKAGES_TO_IGNORE = [
    'pip',
    'pip-tools',
    'setuptools',
    'wheel',
]


def dependency_tree(installed_keys, root_key):
    """
    Calculate the dependency tree for the package `root_key` and return
    a collection of all its dependencies.  Uses a DFS traversal algorithm.

    `installed_keys` should be a {key: requirement} mapping, e.g.
        {'django': from_line('django==1.8')}
    `root_key` should be the key to return the dependency tree for.
    """
    dependencies = set()
    queue = collections.deque()

    if root_key in installed_keys:
        dep = installed_keys[root_key]
        queue.append(dep)

    while queue:
        v = queue.popleft()
        if v.key in dependencies:
            continue

        dependencies.add(v.key)

        for dep_specifier in v.requires():
            dep_name = dep_specifier.key
            if dep_name in installed_keys:
                dep = installed_keys[dep_name]

                if dep_specifier.specifier.contains(dep.version):
                    queue.append(dep)

    return dependencies


def get_dists_to_ignore(installed):
    """
    Returns a collection of package names to ignore when performing pip-sync,
    based on the currently installed environment.  For example, when pip-tools
    is installed in the local environment, it should be ignored, including all
    of its dependencies (e.g. click).  When pip-tools is not installed
    locally, click should also be installed/uninstalled depending on the given
    requirements.
    """
    installed_keys = {r.key: r for r in installed}
    return list(flat_map(lambda req: dependency_tree(installed_keys, req), PACKAGES_TO_IGNORE))


def merge(requirements, ignore_conflicts):
    by_key = {}

    for ireq in requirements:
        key = ireq.req.key

        if not ignore_conflicts:
            existing_ireq = by_key.get(key)
            if existing_ireq:
                # NOTE: We check equality here since we can assume that the
                # requirements are all pinned
                if ireq.specifier != existing_ireq.specifier:
                    raise IncompatibleRequirements(ireq, existing_ireq)

        # TODO: Always pick the largest specifier in case of a conflict
        by_key[key] = ireq

    return by_key.values()


def diff(requirements, installed):
    """
    Calculate which modules should be installed or uninstalled,
    given a set of requirements and a list of installed modules.
    """
    requirements = {r.req.key: r for r in requirements}

    to_be_installed = set()
    to_be_uninstalled = set()

    satisfied = set()

    dists_to_ignore = get_dists_to_ignore(installed)
    for dist in installed:
        key = dist.key
        if key in dists_to_ignore:
            continue

        if key not in requirements:
            to_be_uninstalled.add(dist.as_requirement())
        elif requirements[key].specifier.contains(dist.version):
            satisfied.add(key)

    for key, requirement in requirements.items():
        if key not in satisfied:
            to_be_installed.add(requirement.req)

    return (to_be_installed, to_be_uninstalled)


def sync(to_be_installed, to_be_uninstalled, verbose=False):
    """
    Install and uninstalls the given sets of modules.
    """

    flags = []

    if not verbose:
        flags.append('-q')

    if to_be_uninstalled:
        pip.main(["uninstall", '-y'] + flags + [str(req) for req in to_be_uninstalled])

    if to_be_installed:
        pip.main(["install"] + flags + [str(req) for req in to_be_installed])
