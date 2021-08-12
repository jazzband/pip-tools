# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""

from functools import partial
from pathlib import Path

from setuptools_scm import get_version

# -- Path setup --------------------------------------------------------------

PROJECT_ROOT_DIR = Path(__file__).parents[1].resolve()
get_scm_version = partial(get_version, root=PROJECT_ROOT_DIR)


# -- Project information -----------------------------------------------------

project = "pip-tools"
author = f"{project} Contributors"
copyright = f"The {author}"

# The short X.Y version
version = ".".join(
    get_scm_version(local_scheme="no-local-version",).split(
        "."
    )[:3],
)

# The full version, including alpha/beta/rc tags
release = get_scm_version()


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["myst_parser"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"


# -------------------------------------------------------------------------
default_role = "any"
nitpicky = True
