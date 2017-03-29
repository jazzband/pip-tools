# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import hashlib
import os
from shutil import rmtree

from pip.download import unpack_url
from pip.index import PackageFinder
from pip.req.req_set import RequirementSet
try:
    from pip.utils.hashes import FAVORITE_HASH
except ImportError:
    FAVORITE_HASH = 'sha256'

from ..cache import CACHE_DIR
from ..exceptions import NoCandidateFound
from ..utils import (is_pinned_requirement, lookup_table,
                     make_install_requirement, pip_version_info)
from .base import BaseRepository

try:
    from tempfile import TemporaryDirectory  # added in 3.2
except ImportError:
    from .._compat import TemporaryDirectory


class PyPIRepository(BaseRepository):
    DEFAULT_INDEX_URL = 'https://pypi.python.org/simple'

    """
    The PyPIRepository will use the provided Finder instance to lookup
    packages.  Typically, it looks up packages on PyPI (the default implicit
    config), but any other PyPI mirror can be used if index_urls is
    changed/configured on the Finder.
    """
    def __init__(self, pip_options, session):
        self.session = session

        index_urls = [pip_options.index_url] + pip_options.extra_index_urls
        if pip_options.no_index:
            index_urls = []

        self.finder = PackageFinder(
            find_links=pip_options.find_links,
            index_urls=index_urls,
            trusted_hosts=pip_options.trusted_hosts,
            allow_all_prereleases=pip_options.pre,
            process_dependency_links=pip_options.process_dependency_links,
            session=self.session,
        )

        # Caches
        # stores project_name => InstallationCandidate mappings for all
        # versions reported by PyPI, so we only have to ask once for each
        # project
        self._available_candidates_cache = {}

        # stores InstallRequirement => list(InstallRequirement) mappings
        # of all secondary dependencies for the given requirement, so we
        # only have to go to disk once for each requirement
        self._dependencies_cache = {}

        # Setup file paths
        self.freshen_build_caches()
        self._download_dir = os.path.join(CACHE_DIR, 'pkgs')
        self._wheel_download_dir = os.path.join(CACHE_DIR, 'wheels')

    def freshen_build_caches(self):
        """
        Start with fresh build/source caches.  Will remove any old build
        caches from disk automatically.
        """
        self._build_dir = TemporaryDirectory('build')
        self._source_dir = TemporaryDirectory('source')

    @property
    def build_dir(self):
        return self._build_dir.name

    @property
    def source_dir(self):
        return self._source_dir.name

    def clear_caches(self):
        rmtree(self._download_dir, ignore_errors=True)
        rmtree(self._wheel_download_dir, ignore_errors=True)

    def find_all_candidates(self, req_name):
        if req_name not in self._available_candidates_cache:
            # pip 8 changed the internal API, making this a public method
            if pip_version_info >= (8, 0):
                candidates = self.finder.find_all_candidates(req_name)
            else:
                candidates = self.finder._find_all_versions(req_name)
            self._available_candidates_cache[req_name] = candidates
        return self._available_candidates_cache[req_name]

    def find_best_match(self, ireq, prereleases=None):
        """
        Returns a Version object that indicates the best match for the given
        InstallRequirement according to the external repository.
        """
        if ireq.editable:
            return ireq  # return itself as the best match

        all_candidates = self.find_all_candidates(ireq.name)
        candidates_by_version = lookup_table(all_candidates, key=lambda c: c.version, unique=True)
        matching_versions = ireq.specifier.filter((candidate.version for candidate in all_candidates),
                                                  prereleases=prereleases)

        # Reuses pip's internal candidate sort key to sort
        matching_candidates = [candidates_by_version[ver] for ver in matching_versions]
        if not matching_candidates:
            raise NoCandidateFound(ireq, all_candidates)
        best_candidate = max(matching_candidates, key=self.finder._candidate_sort_key)

        # Turn the candidate into a pinned InstallRequirement
        return make_install_requirement(
            best_candidate.project, best_candidate.version, ireq.extras
        )

    def get_dependencies(self, ireq):
        """
        Given a pinned or an editable InstallRequirement, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """
        if not (ireq.editable or is_pinned_requirement(ireq)):
            raise TypeError('Expected pinned or editable InstallRequirement, got {}'.format(ireq))

        if ireq not in self._dependencies_cache:

            if not os.path.isdir(self._download_dir):
                os.makedirs(self._download_dir)
            if not os.path.isdir(self._wheel_download_dir):
                os.makedirs(self._wheel_download_dir)

            reqset = RequirementSet(self.build_dir,
                                    self.source_dir,
                                    download_dir=self._download_dir,
                                    wheel_download_dir=self._wheel_download_dir,
                                    session=self.session)
            self._dependencies_cache[ireq] = reqset._prepare_file(self.finder, ireq)
        return set(self._dependencies_cache[ireq])

    def get_hashes(self, ireq):
        """
        Given a pinned InstallRequire, returns a set of hashes that represent
        all of the files for a given requirement. It is not acceptable for an
        editable or unpinned requirement to be passed to this function.
        """
        if ireq.editable or not is_pinned_requirement(ireq):
            raise TypeError(
                "Expected pinned requirement, not unpinned or editable, got {}".format(ireq))

        # We need to get all of the candidates that match our current version
        # pin, these will represent all of the files that could possibly
        # satisify this constraint.
        all_candidates = self.find_all_candidates(ireq.name)
        candidates_by_version = lookup_table(all_candidates, key=lambda c: c.version)
        matching_versions = list(
            ireq.specifier.filter((candidate.version for candidate in all_candidates)))
        matching_candidates = candidates_by_version[matching_versions[0]]

        return {
            self._get_file_hash(candidate.location)
            for candidate in matching_candidates
        }

    def _get_file_hash(self, location):
        with TemporaryDirectory() as tmpdir:
            unpack_url(
                location, self.build_dir,
                download_dir=tmpdir, only_download=True, session=self.session
            )
            files = os.listdir(tmpdir)
            assert len(files) == 1
            filename = os.path.abspath(os.path.join(tmpdir, files[0]))

            h = hashlib.new(FAVORITE_HASH)
            with open(filename, "rb") as fp:
                for chunk in iter(lambda: fp.read(8096), b""):
                    h.update(chunk)

        return ":".join([FAVORITE_HASH, h.hexdigest()])
