# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .base import BaseRepository


class LocalRequirementsRepository(BaseRepository):
    """
    The LocalRequirementsRepository proxied the _real_ repository by first
    checking if a requirement can be satisfied by existing pins (i.e. the
    result of a previous compile step).

    In effect, if a requirement can be satisfied with a version pinned in the
    requirements file, we prefer that version over the best match found in
    PyPI.  This keeps updates to the requirements.txt down to a minimum.
    """
    def __init__(self, existing_pins, proxied_repository):
        self.repository = proxied_repository
        self.existing_pins = existing_pins

    @property
    def finder(self):
        return self.repository.finder

    @property
    def session(self):
        return self.repository.session

    @property
    def DEFAULT_INDEX_URL(self):
        return self.repository.DEFAULT_INDEX_URL

    def clear_caches(self):
        self.repository.clear_caches()

    def freshen_build_caches(self):
        self.repository.freshen_build_caches()

    def find_best_match(self, ireq, prereleases=None):
        existing_pin = self.existing_pins.get(ireq.req.project_name.lower())
        if existing_pin and existing_pin.req.specs[0][1] in ireq.req:
            return existing_pin
        else:
            return self.repository.find_best_match(ireq, prereleases)

    def get_dependencies(self, ireq):
        return self.repository.get_dependencies(ireq)
