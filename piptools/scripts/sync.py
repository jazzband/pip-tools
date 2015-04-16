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


@click.command()
def cli():
    click.echo('TODO: Implement')
