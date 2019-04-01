# coding: utf-8
# flake8: noqa
from __future__ import absolute_import, division, print_function, unicode_literals

import six

from .pip_compat import (
    DEV_PKGS,
    FAVORITE_HASH,
    Command,
    FormatControl,
    InstallRequirement,
    PackageFinder,
    PyPI,
    RequirementSet,
    Wheel,
    cmdoptions,
    get_installed_distributions,
    install_req_from_editable,
    install_req_from_line,
    is_file_url,
    parse_requirements,
    stdlib_pkgs,
    url_to_path,
    user_cache_dir,
)

if six.PY2:
    from .tempfile import TemporaryDirectory
else:
    from tempfile import TemporaryDirectory
