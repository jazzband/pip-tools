import pip
import collections
from .utils import flat_map

EXCEPTIONS = [
    'pip',
    'pip-tools',
    'setuptools',
    'wheel',
]

def dependency_tree(installed, root_name):
    """
    Calculate the dependency tree based on module 'root'
    and return a collection of all its dependencies.
    Uses a DFS traversal algorithm.
    """
    dependencies = set()
    queue = collections.deque()

    if root_name in installed:
        dep = installed[root_name]
        queue.append(dep)

    while queue:
        v = queue.popleft()

        if v.key in dependencies:
            continue

        dependencies.add(v.key)

        for dep_specifier in v.requires():
            dep_name = dep_specifier.key
            if dep_name in installed:
                dep = installed[dep_name]

                if dep_specifier.specifier.contains(dep.version):
                    queue.append(dep)

    return dependencies


def exceptions_with_dependencies(installed):
    installed = {r.key: r for r in installed}

    return list(flat_map(lambda req: dependency_tree(installed, req), EXCEPTIONS))


def diff(requirements, installed):
    """
    Calculate which modules should be installed or uninstalled,
    given a set of requirements and a list of installed modules.
    """

    requirements = {r.req.key: r for r in requirements}

    to_be_installed = set()
    to_be_uninstalled = set()

    satisfied = set()

    full_exceptions = exceptions_with_dependencies(installed)

    for module in installed:
        key = module.key

        if key in full_exceptions:
            pass
        elif key not in requirements:
            to_be_uninstalled.add(module.as_requirement())
        elif requirements[key].specifier.contains(module.version):
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
