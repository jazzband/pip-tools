# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sys

import click
import pip

# Make sure we're using a reasonably modern version of pip
if not tuple(int(digit) for digit in pip.__version__.split('.')[:2]) >= (6, 1):
    print('pip-compile requires at least version 6.1 of pip ({} found), '
          'perhaps run `pip install --upgrade pip`?'.format(pip.__version__))
    sys.exit(4)

from .. import sync

DEFAULT_REQUIREMENTS_FILE='requirements.txt'

@click.command()
@click.option('--dry-run', is_flag=True, help="Only show what would happen, don't change anything")
@click.argument('src_file', required=False, type=click.Path(exists=True), default=DEFAULT_REQUIREMENTS_FILE)
def cli(dry_run, src_file):
    requirements = pip.req.parse_requirements(src_file, session=True)
    installed = pip.get_installed_distributions()

    to_be_installed, to_be_uninstalled = sync.diff(requirements, installed)

    if not dry_run:
        sync.sync(to_be_installed, to_be_uninstalled, verbose=True)
    else:
        show_dry_run(to_be_installed, to_be_uninstalled)


def show_dry_run(to_be_installed, to_be_uninstalled):
    if not to_be_uninstalled and not to_be_installed:
        print("Everything up-to-date")

    if to_be_uninstalled:
        print("Would uninstall:")
        for module in to_be_uninstalled:
            print("  {}".format(module))

    if to_be_installed:
        print("Would install:")
        for module in to_be_installed:
            print("  {}".format(module))
