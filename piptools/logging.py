# coding: utf-8
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging

import coloredlogs


def configure_logging(verbose=False):
    """Setup a colored logger to write to the console."""
    logger = logging.getLogger('piptools')
    if verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    level_styles = dict(coloredlogs.DEFAULT_LEVEL_STYLES)
    level_styles.update(debug={})   # reset debug to be the default style
    fmt = '%(message)s'
    coloredlogs.install(level=level, logger=logger, level_styles=level_styles,
                        fmt=fmt)
