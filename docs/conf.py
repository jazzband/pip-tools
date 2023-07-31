# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import os
import sys
from importlib.metadata import version as get_version
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.console import bold

# Add the docs/ directory to sys.path to be able to import utils
docs_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, docs_dir)

logger = logging.getLogger(__name__)

# -- Path setup --------------------------------------------------------------

PROJECT_ROOT_DIR = Path(__file__).parents[1].resolve()


# -- Project information -----------------------------------------------------

project = "pip-tools"
author = f"{project} Contributors"
copyright = f"The {author}"

# The full version, including alpha/beta/rc tags
release = get_version(project)

# The short X.Y version
version = ".".join(release.split(".")[:3])

logger.info(bold("%s version: %s"), project, version)
logger.info(bold("%s release: %s"), project, release)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["myst_parser", "sphinxcontrib.programoutput"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_title = f"<nobr>{project}</nobr> documentation v{release}"


# -------------------------------------------------------------------------
default_role = "any"
nitpicky = True

linkcheck_ignore = [
    r"^https://matrix\.to/#",
]

suppress_warnings = ["myst.xref_missing"]


def setup(app: Sphinx) -> None:
    from docs.utils import TransformSectionIdToName

    app.add_transform(TransformSectionIdToName)
