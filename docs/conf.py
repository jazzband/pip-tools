# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import os
from importlib.metadata import version as get_version
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.console import bold

logger = logging.getLogger(__name__)

PROJECT_ROOT_DIR = Path(__file__).parents[1].resolve()
IS_RELEASE_ON_RTD = (
    os.getenv("READTHEDOCS", "False") == "True"
    and os.environ["READTHEDOCS_VERSION_TYPE"] == "tag"
)


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
extensions = [
    # Stdlib extensions:
    "sphinx.ext.intersphinx",
    # Third-party extensions:
    "myst_parser",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.programoutput",
    "sphinxcontrib.towncrier.ext",  # provides `.. towncrier-draft-entries::`
    "sphinx_issues",
]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_title = f"<nobr>{project}</nobr> documentation v{release}"


# -- Options for intersphinx ----------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

issues_github_path = "jazzband/pip-tools"

towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = True
towncrier_draft_working_directory = PROJECT_ROOT_DIR
towncrier_draft_config_path = "towncrier.toml"  # relative to cwd

# -------------------------------------------------------------------------
default_role = "any"
nitpicky = True

linkcheck_ignore = [
    r"^https://matrix\.to/#",
    r"^https://img.shields.io/matrix",
    r"^https://results\.pre-commit\.ci/latest/github/jazzband/pip-tools/",
    # checking sphinx-issues links to GitHub results in rate limiting errors
    # skip any username validation and pip-tools link checking
    # (this also means we won't get spurious errors when users delete their GitHub accounts)
    r"^https://github\.com/jazzband/pip-tools/(issues|pull|commit)/",
    r"^https://github\.com/sponsors/",
]

nitpick_ignore_regex = [
    ("py:class", "pip.*"),
    ("py:class", "pathlib.*"),
    ("py:class", "click.*"),
    ("py:class", "build.*"),
    ("py:class", "optparse.*"),
    ("py:class", "_ImportLibDist"),
    ("py:class", "PackageMetadata"),
    ("py:class", "importlib.*"),
    ("py:class", "IndexContent"),
    ("py:exc", "click.*"),
]

suppress_warnings = [
    "myst.xref_missing",
    # MyST erroneously flags the draft changelog as having improper header levels
    # because it starts at H2 instead of H1.
    # However, it is written only for inclusion in a broader doc, so the heading
    # levels are actually correct.
    "myst.header",
]

# -- Apidoc options -------------------------------------------------------

apidoc_excluded_paths: list[str] = []
apidoc_extra_args = [
    "--implicit-namespaces",
    "--private",  # include “_private” modules
]
apidoc_module_first = False
apidoc_module_dir = "../piptools"
apidoc_output_dir = "pkg"
apidoc_separate_modules = True
apidoc_toc_file = None


# -- Sphinx extension-API `setup()` hook


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register project-local Sphinx extension-API customizations.

    :param app: Initialized Sphinx app instance.
    :returns: Extension metadata.
    """
    if IS_RELEASE_ON_RTD:
        app.tags.add("is_release")

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": release,
    }
