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
import click  # noqa
from .. import sync  # noqa
from ..exceptions import PipToolsError  # noqa
from ..logging import log  # noqa
from ..utils import flat_map  # noqa

DEFAULT_REQUIREMENTS_FILE = 'requirements.txt'


@click.command()
@click.option('--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.option('--force', is_flag=True, help="Proceed even if conflicts are found")
@click.argument('src_files', required=False, type=click.Path(exists=True), nargs=-1)
def cli(dry_run, force, src_files):
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

    installed = pip.get_installed_distributions()

    to_be_installed, to_be_uninstalled = sync.diff(requirements, installed)

    if not dry_run:
        sync.sync(to_be_installed, to_be_uninstalled, verbose=True)
    else:
        show_dry_run(to_be_installed, to_be_uninstalled)


def show_dry_run(to_be_installed, to_be_uninstalled):
    if not to_be_uninstalled and not to_be_installed:
        click.echo("Everything up-to-date")

    if to_be_uninstalled:
        click.echo("Would uninstall:")
        for module in to_be_uninstalled:
            click.echo("  {}".format(module))

    if to_be_installed:
        click.echo("Would install:")
        for module in to_be_installed:
            click.echo("  {}".format(module))
