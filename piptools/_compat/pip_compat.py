# -*- coding=utf-8 -*-
from __future__ import absolute_import

import pip
from pip._vendor.packaging.version import parse as parse_version

PIP_VERSION = tuple(map(int, parse_version(pip.__version__).base_version.split(".")))
