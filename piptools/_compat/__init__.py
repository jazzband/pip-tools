# coding: utf-8
# flake8: noqa
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six

if six.PY2:
    from contextlib2 import ExitStack
    from .tempfile import TemporaryDirectory
else:
    from contextlib import ExitStack
    from tempfile import TemporaryDirectory
