# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from .base import BaseRepository


class MinimalUpgradeRepository(BaseRepository):
    """
    The MinimalUpgradeRepository uses a provided requirements file as a proxy
    in front of a repository.  If a requirement can be satisfied with
    a version pinned in the requirements file, we use that version as the best
    match.  In all other cases, the proxied repository is used instead.
    """
    def __init__(self, existing_pins, proxied_repository):
        self.repository = proxied_repository
        self.existing_pins = existing_pins

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
