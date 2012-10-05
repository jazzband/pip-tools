class NoPackageMatch(Exception):
    pass


class BasePackageManager(object):
    def find_best_match(self, spec):
        raise NotImplementedError('Implement this in a subclass.')

    def get_dependencies(self, name, version):
        raise NotImplementedError('Implement this in a subclass.')


class FakePackageManager(BasePackageManager):
    pass


class PackageManager(BasePackageManager):
    """The default package manager that goes to PyPI and caches locally."""
    pass


if __name__ == '__main__':
    pass
