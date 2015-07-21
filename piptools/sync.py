import pip

EXCEPTIONS = [
    'pip',
    'pip-tools',
    'setuptools',
    'wheel',
]


def diff(requirements, installed):
    """
    Calculate which modules should be installed or uninstalled,
    given a set of requirements and a list of installed modules.
    """

    requirements = {r.req.key: r for r in requirements}

    to_be_installed = set()
    to_be_uninstalled = set()

    satisfied = set()

    for module in installed:
        key = module.key

        if key in EXCEPTIONS:
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
