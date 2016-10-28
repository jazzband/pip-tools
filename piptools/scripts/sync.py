# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys

import pip
from itertools import chain

from .. import click, sync
from ..exceptions import PipToolsError
from ..logging import log
from ..utils import assert_compatible_pip_version, flat_map

# Make sure we're using a compatible version of pip
assert_compatible_pip_version()

DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'


@click.command()
@click.version_option()
@click.option('-n', '--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--force', is_flag=True, help="Proceed even if conflicts are found")
@click.option('-f', '--find-links', multiple=True, help="Look for archives in this directory or on this HTML page", envvar='PIP_FIND_LINKS')  # noqa
@click.option('-i', '--index-url', help="Change index URL (defaults to PyPI)", envvar='PIP_INDEX_URL')
@click.option('--extra-index-url', multiple=True, help="Add additional index URL to search", envvar='PIP_EXTRA_INDEX_URL')  # noqa
@click.option('--no-index', is_flag=True, help="Ignore package index (only looking at --find-links URLs instead)")
@click.option('--phased', is_flag=True, help="Install each provided file as a separate pip operation (but uninstall unused packages as usual)")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, find_links, index_url, extra_index_url, no_index, phased, src_files):
    if not src_files:
        if os.path.exists(DEFAULT_REQUIREMENTS_FILE):
            src_files = (DEFAULT_REQUIREMENTS_FILE,)
        else:
            msg = 'No requirement files given and no {} found in the current directory'
            log.error(msg.format(DEFAULT_REQUIREMENTS_FILE))
            sys.exit(2)

    if any(src_file.endswith('.in') for src_file in src_files):
        msg = ('Some input files have the .in extension, which is most likely an error and can '
               'cause weird behaviour.  You probably meant to use the corresponding *.txt file?')
        if force:
            log.warning('WARNING: ' + msg)
        else:
            log.error('ERROR: ' + msg)
            sys.exit(2)

    # N.B. Using 'session=True' is safe because this is always installing from a local file,
    # rather than a url.
    requirements = [list(pip.req.parse_requirements(src, session=True)) for src in src_files]

    try:
        merged_requirements = sync.merge(chain.from_iterable(requirements), ignore_conflicts=force)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    installed_dists = pip.get_installed_distributions(skip=[])
    to_install, to_uninstall = sync.diff(merged_requirements, installed_dists)

    install_flags = []
    for link in find_links or []:
        install_flags.extend(['-f', link])
    if no_index:
        install_flags.append('--no-index')
    if index_url:
        install_flags.extend(['-i', index_url])
    if extra_index_url:
        for extra_index in extra_index_url:
            install_flags.extend(['--extra-index-url', extra_index])

    if phased:
        pkg_to_install = {
            req.name: str(req.link or req.req)
            for req in merged_requirements
        }
        already_installed = set()

        sync.sync([], to_uninstall, verbose=True, dry_run=dry_run, install_flags=install_flags)
        for req_set in requirements:
            this_phase = set(pkg_to_install[req.name] for req in req_set)
            actual_reqs = (this_phase & to_install) - already_installed
            sync.sync(actual_reqs, [], verbose=True, dry_run=dry_run, install_flags=install_flags)
            already_installed |= actual_reqs
    else:
        sys.exit(sync.sync(to_install, to_uninstall, verbose=True, dry_run=dry_run,
                           install_flags=install_flags))
