from pip.index import PackageFinder
from pip.req import InstallRequirement


def find_best_package_url(spec):
    """Searches PyPI for the best package URL matching the spec."""
    line = str(spec)
    req = InstallRequirement.from_line(line)
    finder = PackageFinder(
        find_links=[],
        index_urls=['http://pypi.python.org/simple/'],
        use_mirrors=True,
        mirrors=[],
    )
    link = finder.find_requirement(req, False)
    return link
