# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import os
import sys

import pip

from .. import click, sync
from ..exceptions import PipToolsError
from ..logging import log
from ..utils import pip_version_info

# Make sure we're using a reasonably modern version of pip
if not pip_version_info >= (7, 0):
    print('pip-compile requires at least version 7.0 of pip ({} found), '
          'perhaps run `pip install --upgrade pip`?'.format(pip.__version__))
    sys.exit(4)


@click.command()
@click.version_option()
def cli():
    """Make a snapshot of the env"""
    log.verbose = verbose
    sync.make_snapshot()
