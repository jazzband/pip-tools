# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

import pip

# Make sure we're using a reasonably modern version of pip
if not tuple(int(digit) for digit in pip.__version__.split('.')[:2]) >= (6, 1):
    print('pip-compile requires at least version 6.1 of pip ({} found), '
          'perhaps run `pip install --upgrade pip`?'.format(pip.__version__))
    sys.exit(4)

import os  # noqa
from .. import click  # noqa
from .. import sync  # noqa
from ..exceptions import PipToolsError  # noqa
from ..logging import log  # noqa
from ..utils import flat_map  # noqa

DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'


@click.command()
@click.option('-n', '--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--force', is_flag=True, help="Proceed even if conflicts are found")
@click.option('-f', '--find-links', multiple=True, help="Look for archives in this directory or on this HTML page", envvar='PIP_FIND_LINKS')  # noqa
@click.option('-i', '--index-url', help="Change index URL (defaults to PyPI)", envvar='PIP_INDEX_URL')
@click.option('--extra-index-url', multiple=True, help="Add additional index URL to search", envvar='PIP_EXTRA_INDEX_URL')  # noqa
@click.option('--no-index', is_flag=True, help="Ignore package index (only looking at --find-links URLs instead)")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, find_links, index_url, extra_index_url, no_index, src_files):
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

    requirements = flat_map(lambda src: pip.req.parse_requirements(src, session=True),
                            src_files)

    try:
        requirements = sync.merge(requirements, ignore_conflicts=force)
    except PipToolsError as e:
        log.error(str(e))
        sys.exit(2)

    installed_dists = pip.get_installed_distributions(skip=[])
    to_install, to_uninstall = sync.diff(requirements, installed_dists)

    pip_flags = []
    for link in find_links or []:
        pip_flags.extend(['-f', link])
    if no_index:
        pip_flags.append('--no-index')
    if index_url:
        pip_flags.extend(['-i', index_url])
    if extra_index_url:
        for extra_index in extra_index_url:
            pip_flags.extend(['--extra-index-url', extra_index])

    sys.exit(sync.sync(to_install, to_uninstall, verbose=True, dry_run=dry_run,
                       pip_flags=pip_flags))
