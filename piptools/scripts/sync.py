# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import os
import sys

import pip

from .. import click, sync
from ..exceptions import PipToolsError
from ..logging import configure_logging
from ..utils import assert_compatible_pip_version, flat_map

# Make sure we're using a compatible version of pip
assert_compatible_pip_version()

DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'
logger = logging.getLogger(__name__)


@click.command()
@click.version_option()
@click.option('-n', '--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--force', is_flag=True, help="Proceed even if conflicts are found")
@click.option('-f', '--find-links', multiple=True, help="Look for archives in this directory or on this HTML page", envvar='PIP_FIND_LINKS')  # noqa
@click.option('-i', '--index-url', help="Change index URL (defaults to PyPI)", envvar='PIP_INDEX_URL')
@click.option('--extra-index-url', multiple=True, help="Add additional index URL to search", envvar='PIP_EXTRA_INDEX_URL')  # noqa
@click.option('--no-index', is_flag=True, help="Ignore package index (only looking at --find-links URLs instead)")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, find_links, index_url, extra_index_url, no_index, src_files):
    """Synchronize virtual environment with requirements.txt."""
    configure_logging()
    if not src_files:
        if os.path.exists(DEFAULT_REQUIREMENTS_FILE):
            src_files = (DEFAULT_REQUIREMENTS_FILE,)
        else:
            logger.error(
                'No requirement files given and no %s found in the current directory',
                DEFAULT_REQUIREMENTS_FILE)
            sys.exit(2)

    if any(src_file.endswith('.in') for src_file in src_files):
        msg = ('Some input files have the .in extension, which is most likely an error and can '
               'cause weird behaviour.  You probably meant to use the corresponding *.txt file?')
        if force:
            logger.warning(msg)
        else:
            logger.error(msg)
            sys.exit(2)

    requirements = flat_map(lambda src: pip.req.parse_requirements(src, session=True),
                            src_files)

    try:
        requirements = sync.merge(requirements, ignore_conflicts=force)
    except PipToolsError as e:
        logger.exception(str(e))
        sys.exit(2)

    installed_dists = pip.get_installed_distributions(skip=[])
    to_install, to_uninstall = sync.diff(requirements, installed_dists)

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

    sys.exit(sync.sync(to_install, to_uninstall, verbose=True, dry_run=dry_run,
                       install_flags=install_flags))
