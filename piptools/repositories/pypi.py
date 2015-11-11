# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
from shutil import rmtree

from pip.download import PipSession
from pip.index import PackageFinder
from pip.req import InstallRequirement
from pip.req.req_set import RequirementSet

from ..cache import CACHE_DIR
from ..exceptions import NoCandidateFound
from ..utils import is_pinned_requirement, is_link_requirement, lookup_table
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
    def __init__(self, pip_options, session=None):
        self.session = session or PipSession()

        if pip_options.client_cert:
            self.session.cert = pip_options.client_cert

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
        self._available_versions_cache = {}

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

    def find_all_versions(self, req_name):
        if req_name not in self._available_versions_cache:
            self._available_versions_cache[req_name] = self.finder._find_all_versions(req_name)
        return self._available_versions_cache[req_name]

    def find_best_match(self, ireq, prereleases=None):
        """
        Returns a Version object that indicates the best match for the given
        InstallRequirement according to the external repository.
        """
        if ireq.editable:
            return ireq  # return itself as the best match

        all_candidates = self.find_all_versions(ireq.name)
        candidates_by_version = lookup_table(all_candidates, key=lambda c: c.version, unique=True)
        matching_versions = ireq.specifier.filter((candidate.version for candidate in all_candidates),
                                                  prereleases=prereleases)

        # Reuses pip's internal candidate sort key to sort
        matching_candidates = [candidates_by_version[ver] for ver in matching_versions]
        if not matching_candidates:
            raise NoCandidateFound(ireq, all_candidates)
        best_candidate = max(matching_candidates, key=self.finder._candidate_sort_key)

        # Turn the candidate into a pinned InstallRequirement
        return InstallRequirement.from_line('{}=={}'.format(best_candidate.project, str(best_candidate.version)))

    def get_dependencies(self, ireq):
        """
        Given a pinned or an editable InstallRequirement, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """
        if not (is_link_requirement(ireq) or is_pinned_requirement(ireq)):
            raise TypeError('Expected pinned or editable InstallRequirement, got {}'.format(ireq))

        if not os.path.isdir(self._download_dir):
            os.makedirs(self._download_dir)
        if not os.path.isdir(self._wheel_download_dir):
            os.makedirs(self._wheel_download_dir)

        reqset = RequirementSet(self.build_dir,
                                self.source_dir,
                                download_dir=self._download_dir,
                                wheel_download_dir=self._wheel_download_dir,
                                session=self.session)
        dependencies = reqset._prepare_file(self.finder, ireq)
        return set(dependencies)
