# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

from importlib.metadata import version as get_version
from pathlib import Path

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

linkcheck_ignore = [
    r"^https://matrix\.to/#",
]

suppress_warnings = ["myst.xref_missing"]
