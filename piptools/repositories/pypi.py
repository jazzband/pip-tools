# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import hashlib
import os
from contextlib import contextmanager
from shutil import rmtree

from .._compat import (
    is_file_url,
    url_to_path,
    PackageFinder,
    RequirementSet,
    Wheel,
    FAVORITE_HASH,
    TemporaryDirectory,
    PyPI
)

from ..cache import CACHE_DIR
from ..exceptions import NoCandidateFound
from ..utils import (fs_str, is_pinned_requirement, lookup_table,
                     make_install_requirement)
from .base import BaseRepository

try:
    from pip._internal.req.req_tracker import RequirementTracker
except ImportError:
    @contextmanager
    def RequirementTracker():
        yield

try:
    from pip._internal.cache import WheelCache
except ImportError:
    from pip.wheel import WheelCache


class PyPIRepository(BaseRepository):
    DEFAULT_INDEX_URL = PyPI.simple_url

    """
    The PyPIRepository will use the provided Finder instance to lookup
    packages.  Typically, it looks up packages on PyPI (the default implicit
    config), but any other PyPI mirror can be used if index_urls is
    changed/configured on the Finder.
    """
    def __init__(self, pip_options, session):
        self.session = session
        self.pip_options = pip_options

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
        self._download_dir = fs_str(os.path.join(CACHE_DIR, 'pkgs'))
        self._wheel_download_dir = fs_str(os.path.join(CACHE_DIR, 'wheels'))

    def freshen_build_caches(self):
        """
        Start with fresh build/source caches.  Will remove any old build
        caches from disk automatically.
        """
        self._build_dir = TemporaryDirectory(fs_str('build'))
        self._source_dir = TemporaryDirectory(fs_str('source'))

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
            candidates = self.finder.find_all_candidates(req_name)
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
            raise NoCandidateFound(ireq, all_candidates, self.finder)
        best_candidate = max(matching_candidates, key=self.finder._candidate_sort_key)

        # Turn the candidate into a pinned InstallRequirement
        return make_install_requirement(
            best_candidate.project, best_candidate.version, ireq.extras, constraint=ireq.constraint
        )

    def resolve_reqs(self, download_dir, ireq, wheel_cache):
        results = None
        try:
            from pip._internal.operations.prepare import RequirementPreparer
            from pip._internal.resolve import Resolver as PipResolver
        except ImportError:
            # Pip 9 and below
            reqset = RequirementSet(
                self.build_dir,
                self.source_dir,
                download_dir=download_dir,
                wheel_download_dir=self._wheel_download_dir,
                session=self.session,
                wheel_cache=wheel_cache
            )
            results = reqset._prepare_file(self.finder, ireq)
        else:
            # pip >= 10
            preparer_kwargs = {
                'build_dir': self.build_dir,
                'src_dir': self.source_dir,
                'download_dir': download_dir,
                'wheel_download_dir': self._wheel_download_dir,
                'progress_bar': 'off',
                'build_isolation': False
            }
            resolver_kwargs = {
                'finder': self.finder,
                'session': self.session,
                'upgrade_strategy': "to-satisfy-only",
                'force_reinstall': False,
                'ignore_dependencies': False,
                'ignore_requires_python': False,
                'ignore_installed': True,
                'isolated': False,
                'wheel_cache': wheel_cache,
                'use_user_site': False
            }
            resolver = None
            preparer = None
            with RequirementTracker() as req_tracker:
                # Pip 18 uses a requirement tracker to prevent fork bombs
                if req_tracker:
                    preparer_kwargs['req_tracker'] = req_tracker
                preparer = RequirementPreparer(**preparer_kwargs)
                resolver_kwargs['preparer'] = preparer
                reqset = RequirementSet()
                ireq.is_direct = True
                reqset.add_requirement(ireq)
                resolver = PipResolver(**resolver_kwargs)
                resolver.require_hashes = False
                results = resolver._resolve_one(reqset, ireq)
                reqset.cleanup_files()

        return set(results)

    def get_dependencies(self, ireq):
        """
        Given a pinned or an editable InstallRequirement, returns a set of
        dependencies (also InstallRequirements, but not necessarily pinned).
        They indicate the secondary dependencies for the given requirement.
        """
        if not (ireq.editable or is_pinned_requirement(ireq)):
            raise TypeError('Expected pinned or editable InstallRequirement, got {}'.format(ireq))

        if ireq not in self._dependencies_cache:
            if ireq.editable and (ireq.source_dir and os.path.exists(ireq.source_dir)):
                # No download_dir for locally available editable requirements.
                # If a download_dir is passed, pip will  unnecessarely
                # archive the entire source directory
                download_dir = None
            elif ireq.link and not ireq.link.is_artifact:
                # No download_dir for VCS sources.  This also works around pip
                # using git-checkout-index, which gets rid of the .git dir.
                download_dir = None
            else:
                download_dir = self._download_dir
                if not os.path.isdir(download_dir):
                    os.makedirs(download_dir)
            if not os.path.isdir(self._wheel_download_dir):
                os.makedirs(self._wheel_download_dir)

            wheel_cache = WheelCache(CACHE_DIR, self.pip_options.format_control)
            prev_tracker = os.environ.get('PIP_REQ_TRACKER')
            try:
                self._dependencies_cache[ireq] = self.resolve_reqs(download_dir, ireq, wheel_cache)
            finally:
                if 'PIP_REQ_TRACKER' in os.environ:
                    if prev_tracker:
                        os.environ['PIP_REQ_TRACKER'] = prev_tracker
                    else:
                        del os.environ['PIP_REQ_TRACKER']
                try:
                    self.wheel_cache.cleanup()
                except AttributeError:
                    pass
        return self._dependencies_cache[ireq]

    def get_hashes(self, ireq):
        """
        Given an InstallRequirement, return a set of hashes that represent all
        of the files for a given requirement. Editable requirements return an
        empty set. Unpinned requirements raise a TypeError.
        """
        if ireq.editable:
            return set()

        if not is_pinned_requirement(ireq):
            raise TypeError(
                "Expected pinned requirement, got {}".format(ireq))

        # We need to get all of the candidates that match our current version
        # pin, these will represent all of the files that could possibly
        # satisfy this constraint.
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
        h = hashlib.new(FAVORITE_HASH)
        with open_local_or_remote_file(location, self.session) as fp:
            for chunk in iter(lambda: fp.read(8096), b""):
                h.update(chunk)
        return ":".join([FAVORITE_HASH, h.hexdigest()])

    @contextmanager
    def allow_all_wheels(self):
        """
        Monkey patches pip.Wheel to allow wheels from all platforms and Python versions.

        This also saves the candidate cache and set a new one, or else the results from the
        previous non-patched calls will interfere.
        """
        def _wheel_supported(self, tags=None):
            # Ignore current platform. Support everything.
            return True

        def _wheel_support_index_min(self, tags=None):
            # All wheels are equal priority for sorting.
            return 0

        original_wheel_supported = Wheel.supported
        original_support_index_min = Wheel.support_index_min
        original_cache = self._available_candidates_cache

        Wheel.supported = _wheel_supported
        Wheel.support_index_min = _wheel_support_index_min
        self._available_candidates_cache = {}

        try:
            yield
        finally:
            Wheel.supported = original_wheel_supported
            Wheel.support_index_min = original_support_index_min
            self._available_candidates_cache = original_cache


@contextmanager
def open_local_or_remote_file(link, session):
    """
    Open local or remote file for reading.

    :type link: pip.index.Link
    :type session: requests.Session
    :raises ValueError: If link points to a local directory.
    :return: a context manager to the opened file-like object
    """
    url = link.url_without_fragment

    if is_file_url(link):
        # Local URL
        local_path = url_to_path(url)
        if os.path.isdir(local_path):
            raise ValueError("Cannot open directory for read: {}".format(url))
        else:
            with open(local_path, 'rb') as local_file:
                yield local_file
    else:
        # Remote URL
        headers = {"Accept-Encoding": "identity"}
        response = session.get(url, headers=headers, stream=True)
        try:
            yield response.raw
        finally:
            response.close()
