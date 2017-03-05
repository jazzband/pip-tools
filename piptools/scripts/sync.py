# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys

import pip

from .. import click, sync
from ..exceptions import PipToolsError
from ..logging import log
from ..utils import assert_compatible_pip_version, flat_map
from ._repo import get_pip_options_and_pypi_repository

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
@click.option('-q', '--quiet', default=False, is_flag=True, help="Give less output")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, find_links, index_url, extra_index_url, no_index, quiet, src_files):
    """Synchronize virtual environment with requirements.txt."""
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

    (pip_options, repository) = get_pip_options_and_pypi_repository(
        index_url=index_url, extra_index_url=extra_index_url,
        no_index=no_index, find_links=find_links)

    def parse_req_file(filename):
        return pip.req.parse_requirements(
            filename, session=True, finder=repository.finder)

    requirements = flat_map(parse_req_file, src_files)

    try:
        requirements = sync.merge(requirements, ignore_conflicts=force)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    installed_dists = pip.get_installed_distributions(skip=[])
    to_install, to_uninstall = sync.diff(requirements, installed_dists)

    install_flags = []
    for link in repository.finder.find_links or []:
        install_flags.extend(['-f', link])
    if not repository.finder.index_urls:
        install_flags.append('--no-index')
    for (i, index_url) in enumerate(repository.finder.index_urls):
        if i == 0:
            install_flags.extend(['-i', index_url])
        else:
            install_flags.extend(['--extra-index-url', index_url])

    sys.exit(sync.sync(to_install, to_uninstall, verbose=(not quiet), dry_run=dry_run,
                       install_flags=install_flags))
