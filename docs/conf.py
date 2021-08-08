# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""


# -- Project information -----------------------------------------------------

project = "pip-tools"
author = "Jazzband Contributors"
copyright = f"2021, {author}"


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
