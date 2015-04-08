import json
import operator
import os
import shutil
import subprocess
import sys
import re
import tarfile
import tempfile
import zipfile

try:
    import cPickle as pickle
except ImportError:
    import pickle as pickle  # noqa

from functools import partial
from six.moves.urllib.parse import urlsplit, urlunsplit, quote

#from pip.backwardcompat import ConfigParser
from pip.download import get_file_content, unpack_vcs_link, PipSession
from pip.index import Link, PackageFinder
#from pip.locations import default_config_file
from pip.req import InstallRequirement
try:
    from pip.utils import splitext
except ImportError:
    from pip.util import splitext
from pip.vcs import vcs


from .logging import logger
from .datastructures import Spec, first
from .version import NormalizedVersion  # PEP386 compatible version numbers


def find_file(root_dir, filename):
    """Searches given file in root_dir's subdirectories.
    Returns path to first occurence or None if nothing found."""
    tree = os.walk(root_dir)
    for dir_name, subdirs, files in tree:
        if filename in files:
            return os.path.join(dir_name, filename)


def url_without_fragment(link):
    """Included here for compatibility reasons with pip<1.2, which does not
    have the Link.url_without_fragment() method.
    """
    assert isinstance(link, Link), 'Argument should be a pip.index.Link instance.'
    try:
        return link.url_without_fragment
    except AttributeError:
        scheme, netloc, path, query, fragment = urlsplit(link.url)
        return urlunsplit((scheme, netloc, path, query, None))


class NoPackageMatch(Exception):
    pass


class BasePackageManager(object):
    def find_best_match(self, spec):
        """Return a version string that indicates the best match for the given
        Spec.
        """
        raise NotImplementedError('Implement this in a subclass.')

    def get_dependencies(self, pinned_spec):
        """Return a list of Spec instances, representing the dependencies of
        the specific package version indicated by the args.  This method only
        returns the direct (next-level) dependencies of the package.
        The Spec instances don't require sources to be set by this method.
        """
        raise NotImplementedError('Implement this in a subclass.')

    @staticmethod
    def package_to_requirement(package_name):
        """Translate a name like Foo-1.2 to Foo==1.3.
        This is taken from pip, where it has been removed in
        https://github.com/pypa/pip/pull/2055.
        """
        match = re.search(r'^(.*?)-(dev|\d.*)', package_name)
        if match:
            name = match.group(1)
            version = match.group(2)
        else:
            name = package_name
            version = ''
        if version:
            return '%s==%s' % (name, version)
        else:
            return name


class FakePackageManager(BasePackageManager):
    def __init__(self, fake_contents):
        """Creates a fake package manager index, for easy testing.  The
        fake_contents argument is a dictionary containing 'name-version' keys
        and lists-of-specs values.

        Example:

            {
                'foo-0.1': ['bar', 'qux'],
                'bar-0.2': ['qux>0.1'],
                'qux-0.1': [],
                'qux-0.2': [],
            }
        """
        # Sanity check (parsing will return errors if content is wrongly
        # formatted)
        for pkg_key, list_of_specs in fake_contents.items():
            try:
                _, _ = self.parse_package_key(pkg_key)
            except ValueError:
                raise ValueError('Invalid index entry: %s' % (pkg_key,))
            assert isinstance(list_of_specs, list)

        self._contents = fake_contents

    def parse_package_key(self, pkg_key):
        try:
            return self.package_to_requirement(pkg_key).split('==')
        except ValueError:
            raise ValueError('Invalid package key: %s (required format: "name-version")' % (pkg_key,))

    def iter_package_versions(self):
        """Iters over all package versions, returning key-value pairs."""
        for key in self._contents:
            yield self.parse_package_key(key)

    def iter_versions(self, given_name):
        """Will return all versions available for the current package name."""
        for name, version in self.iter_package_versions():
            if name == given_name:
                yield version

    def matches_pred(self, version, pred):
        """Returns whether version matches the given predicate."""
        qual, value = pred
        ops = {
            '==': operator.eq,
            '!=': operator.ne,
            '<': operator.lt,
            '>': operator.gt,
            '<=': operator.le,
            '>=': operator.ge,
        }
        return ops[qual](NormalizedVersion(version), NormalizedVersion(value))

    def pick_highest(self, list_of_versions):
        """Picks the highest version from a list, according to PEP386 logic."""
        return str(max(map(NormalizedVersion, list_of_versions)))

    def find_best_match(self, spec):
        """This requires a bit of reverse engineering of PyPI's logic that
        finds a pacakge for a given spec, but it's not too hard.
        """
        versions = list(self.iter_versions(spec.name))
        for pred in spec.preds:
            is_version_match = partial(self.matches_pred, pred=pred)
            versions = list(filter(is_version_match, versions))
        if len(versions) == 0:
            raise NoPackageMatch('No package found for %s' % (spec,))
        return self.pick_highest(versions)

    def get_dependencies(self, pinned_spec):
        pkg_key = '%s-%s' % (pinned_spec.name, pinned_spec.version)
        specs = []
        for specline in self._contents[pkg_key]:
            specs.append(Spec.from_line(specline))
        return specs


class PersistentCache(object):
    def __init__(self, cache_file):
        """Creates a new persistent cache, retrieving/storing cached key-value
        pairs from/to the given filename.
        """
        self._cache_file = cache_file
        self._cache = None

    @property
    def cache(self):
        """The dictionary that is the actual in-memory cache.  This property
        lazily loads the cache from disk.
        """
        if self._cache is None:
            self.read_cache()
        return self._cache

    def read_cache(self):
        """Reads the cached contents into memory."""
        if os.path.exists(self._cache_file):
            with open(self._cache_file, 'rb') as f:
                self._cache = pickle.load(f)
        else:
            # Create a new, empty cache otherwise (store a __format__ field
            # that can be used to version the file, should we need to make
            # changes to its internals)
            self._cache = {'__format__': 1}

    def write_cache(self):
        """Writes (pickles) the cache to disk."""
        with open(self._cache_file, 'wb') as f:
            pickle.dump(self._cache, f)

    def __contains__(self, item):
        return item in self.cache

    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.write_cache()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class PackageManager(BasePackageManager):
    """The default package manager that goes to PyPI and caches locally."""
    piptools_root = os.path.expanduser(os.environ.get('PIPTOOLS_ROOT', '~/.pip-tools'))
    dep_cache_file = os.path.join(piptools_root, 'dependencies.pickle')
    download_cache_root = os.path.join(piptools_root, 'cache')

    def __init__(self, index_url=None, extra_index_urls=[], find_links=[], allow_all_prereleases=False):
        # TODO: provide options for pip, such as index URL or use-mirrors
        if index_url is None:
            index_url = 'https://pypi.python.org/simple/'
        if not os.path.exists(self.download_cache_root):
            os.makedirs(self.download_cache_root)
        self._link_cache = {}
        self._dep_cache = PersistentCache(self.dep_cache_file)
        self._dep_call_cache = {}
        self._best_match_call_cache = {}
        self._find_links = find_links[:]
        self._allow_all_prereleases = allow_all_prereleases
        self._index_urls = []
        if index_url:
            self._index_urls.append(index_url)
        self._index_urls.extend(extra_index_urls)
        self._extra_index_urls = extra_index_urls
        try:
            # Try to pass/set retries with pip 1.6 (default: 0).
            self._session = PipSession(retries=3)
        except TypeError:
            self._session = PipSession()

        # In-memory (non-persistent) cache of unpacked VCS URLs
        self._unpacked_vcs_urls = set()

    # BasePackageManager interface
    def find_best_match(self, spec):
        # TODO: if the spec is pinned, we might be able to go straight to the
        # local cache without having to use the PackageFinder. Cached file
        # names look like this:
        # https%3A%2F%2Fpypi.python.org%2Fpackages%2Fsource%2Fs%2Fsix%2Fsix-1.2.0.tar.gz
        # This is easy to guess from a package==version spec but requires the
        # package to be actually hosted on pypi, which is not the case for
        # everything (e.g. redis).
        #
        # Option 1: make this work for packages hosted on PyPI and accept
        # external packages to be slower.
        #
        # Option 2: only use the last part of the URL as a file name
        # (six-1.2.0.tar.gz). This makes it easy to check the local cache for
        # any pinned spec but *might* lead to inconsistencies for people
        # maintaining their own PyPI servers and adding their modified
        # packages as the same names/versions as the originals on the
        # canonical PyPI. The shouldn't do it, and this is probably an edge
        # case but it's still worth making a decision.

        def _find_cached_match(spec):
            if spec.is_pinned:
                # If this is a pinned spec, we can take a shortcut: if it is
                # found in the dependency cache, we can safely assume it has
                # been downloaded before, and thus must exist.  We can know
                # this without every reaching out to PyPI and avoid the
                # network overhead.
                name, version = spec.name, first(spec.preds)[1]
                if (name, version) in self._dep_cache:
                    source = 'dependency cache'
                    return version, source

            # Try the link cache, and otherwise, try PyPI
            if specline in self._link_cache:
                link = self._link_cache[specline]
                source = 'link cache'
            else:
                if spec.url:
                    # TODO : remove
                    requirement = InstallRequirement.from_editable(specline)
                else:
                    requirement = InstallRequirement.from_line(specline)

                finder = PackageFinder(
                    find_links=self._find_links,
                    index_urls=self._index_urls,
                    allow_all_external=True,
                    session=self._session,
                    allow_all_prereleases=self._allow_all_prereleases
                    # this parameter down not supported anymore
                    # all insecure package should be enumerated
                    # allow_all_insecure=True,
                )
                link = finder.find_requirement(requirement, False)
                self._link_cache[specline] = link
                source = 'PyPI'

            filename, ext = splitext(link.filename)

            if ext == '.whl':
                # then remove implementation tags like language, abi and platform
                # like described at:
                # http://legacy.python.org/dev/peps/pep-0427/#file-name-convention
                filename = re.sub(r'-[\w.]+-[\w.]+-[\w.]+$', '', filename)
            _, version = self.package_to_requirement(filename).split('==')

            # Take this moment to smartly insert the pinned variant of this
            # spec into the link_cache, too
            pinned_spec = spec.pin(version)
            if pinned_spec not in self._link_cache:
                self._link_cache[str(pinned_spec)] = link
            return version, source

        specline = str(spec)
        if spec.url:
            self._link_cache[specline] = Link(spec.vcs_url)

            path = self.get_or_download_package(spec)
            version = self.get_vcs_revision(path)
            pinned_spec = spec.pin(version)
            self._link_cache[str(pinned_spec)] = Link(pinned_spec.vcs_url)
        else:
            if '==' not in specline or specline not in self._best_match_call_cache:
                logger.debug('- Finding best package matching %s' % [specline])
            with logger.indent():
                version, source = _find_cached_match(spec)
            if '==' not in specline or specline not in self._best_match_call_cache:
                logger.debug('  Found best match: %s (from %s)' % (version, source))

        self._best_match_call_cache[specline] = True
        return version

    def get_vcs_revision(self, path):
        backend_cls = vcs.get_backend_from_location(path)
        backend = backend_cls(path)
        return backend.get_revision(path)

    def get_dependencies(self, pinned_spec):
        name = pinned_spec.name
        version = pinned_spec.version

        key = '{0}-{1}'.format(name, version)
        if key not in self._dep_call_cache:
            logger.debug('- Getting dependencies for %s-%s' % (name, version))
        with logger.indent():
            deps = self._dep_cache.get((name, version))
            if deps is not None:
                source = 'dependency cache'
            else:
                path = self.get_or_download_package(pinned_spec)
                deps = self.extract_dependencies(path)
                self._dep_cache[(name, version)] = deps
                source = 'package archive'
        if key not in self._dep_call_cache:
            logger.debug('  Found: %s (from %s)' % (deps, source))
        self._dep_call_cache[key] = True
        return [Spec.from_line(dep) for dep in deps]


    # Helper methods
    def get_local_package_path(self, url):  # noqa
        """Returns the full local path name for a given URL.  This
        does not require the package archive to exist locally.  In fact, this
        can be used to calculate the destination path for a download.
        """
        cache_key = quote(url, '')
        fullpath = os.path.join(self.download_cache_root, cache_key)
        return fullpath

    def get_or_download_package(self, spec):
        """Returns the local path from the package cache, downloading as
        needed.
        """
        logger.debug('- Getting package location for %s' % (spec,))
        with logger.indent():
            link = self._link_cache[str(spec)]
            fullpath = self.get_local_package_path(url_without_fragment(link))

            if spec.vcs_url:
                # We don't use a persistent cache for VCS urls: the branch
                # could have been updated since the previous pip-compile call.
                if link not in self._unpacked_vcs_urls:
                    unpack_vcs_link(link, fullpath, only_download=False)
                    self._unpacked_vcs_urls.add(link)
            else:
                if os.path.exists(fullpath):
                    logger.debug('  Archive cache hit: {0}'.format(link.filename))
                    return fullpath

                logger.debug('  Archive cache miss, downloading {0}...'.format(
                    link.filename
                ))
                self.download_package(link, fullpath)

            return fullpath

    # def get_pip_cache_root():
    #     """Returns pip's cache root, or None if no such cache root is
    #     configured.
    #     """
    #     pip_config = ConfigParser.RawConfigParser()
    #     pip_config.read([default_config_file])
    #     download_cache = None
    #     try:
    #         for key, value in pip_config.items('global'):
    #             if key == 'download-cache':
    #                 download_cache = value
    #                 break
    #     except ConfigParser.NoSectionError:
    #         pass
    #     if download_cache is not None:
    #         download_cache = os.path.expanduser(download_cache)
    #     return download_cache

    def download_package(self, link, destination):
        """Downloads the given package link contents to the local
        package cache. Overwrites anything that's in the cache already.
        """
        # TODO integrate pip's download-cache
        #pip_cache_root = self.get_pip_cache_root()
        #if pip_cache_root:
        #    cache_path = os.path.join(pip_cache_root, cache_key)
        #    if os.path.exists(cache_path):
        #        # pip has a cached version, copy it
        #        shutil.copyfile(cache_path, fullpath)
        #else:
        #    actually download the requirement
        url = url_without_fragment(link)
        logger.debug('- Downloading package from %s' % (url,))
        with logger.indent():
            _, content = get_file_content(url, link, session=self._session)
            with open(destination, 'wb') as f:
                f.write(content)

    def unpack_archive(self, path, target_directory):
        logger.debug('- Unpacking %s' % (path,))
        with logger.indent():
            if any(path.endswith(ext) for ext in {'.tar.gz', '.tar', '.tar.bz2', '.tgz'}):
                archive = tarfile.open(path)
            elif any(path.endswith(ext) for ext in {'.zip', '.whl'}):
                archive = zipfile.ZipFile(path)
            else:
                assert False, "Unsupported archive file: {}".format(path)

            try:
                archive.extractall(target_directory)
            except IOError:
                logger.error("Error extracting %s" % (path,))
                raise
            finally:
                archive.close()

    def get_egg_info_requires(self, dist_dir):
        """Generates egg-info directory and it was successful, returns
        path to requires.txt file."""
        logger.debug('- Running egg_info in %s' % (dist_dir,))
        logger.debug('  (This can take a while.)')
        with logger.indent():
            try:
                process = subprocess.Popen([sys.executable, 'setup.py', 'egg_info'],
                                           cwd=dist_dir, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                process.wait()

                for line in process.stdout.readlines():
                    if 'egg-info/requires.txt' in line:
                        return os.path.join(dist_dir, line.rsplit(None, 1)[1])
            except subprocess.CalledProcessError:
                logger.debug("  egg_info failed for {0}".format(
                    dist_dir.rsplit('/', 1)[-1]
                ))

    def read_package_requires_file(self, setup_py_path):
        """Returns a list of dependencies for an unpacked package dir."""
        dist_dir = os.path.dirname(setup_py_path)
        deps = []
        requirements = self.get_egg_info_requires(dist_dir)

        if not requirements:
            return []

        with open(requirements, 'r') as requirements:
            for requirement in requirements.readlines():
                dep = requirement.strip()
                if dep == '[test]' or not dep:
                    break
                deps.append(dep)
        return deps

    def read_wheel_requires(self, pydist_json_path):
        with open(pydist_json_path) as f:
            data = json.load(f)

        deps = []
        for may_requirement in data.get('run_requires', []):
            # here we ignore requirements with 'extra' and 'environment'
            # because usually they are for specific environments like unittesting
            if 'extra' not in may_requirement and 'environment' not in may_requirement:
                for name in may_requirement['requires']:
                    deps.append(re.sub(u'[ ()]', u'', name).encode('utf-8'))

        return deps

    def extract_dependencies(self, path):
        """Returns a list of string representations of dependencies for
        a given distribution.
        """
        deps = []
        logger.debug('- Extracting dependencies for %s' % (path,))
        with logger.indent():
            if os.path.isdir(path):
                # this is a directory in case if path is pointing to
                # VCS checkout
                deps = self.read_package_requires_file(path)
            else:
                build_dir = tempfile.mkdtemp()
                unpack_dir = os.path.join(build_dir, 'build')
                try:
                    self.unpack_archive(path, unpack_dir)

                    # first, check if archive was a wheel
                    name = (find_file(unpack_dir, 'pydist.json') or
                            find_file(unpack_dir, 'metadata.json'))
                    if name:
                        deps = self.read_wheel_requires(name)
                    else:
                        name = find_file(unpack_dir, 'setup.py')
                        if name:
                            deps = self.read_package_requires_file(name)

                finally:
                    shutil.rmtree(build_dir)
        logger.debug('Found: %s' % (deps,))
        return deps


if __name__ == '__main__':
    pass
