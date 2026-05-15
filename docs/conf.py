"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib.metadata import version as get_version
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

PROJECT_ROOT_DIR = Path(__file__).parents[1].resolve()
IS_RELEASE_ON_RTD = (
    os.getenv("READTHEDOCS", "False") == "True"
    and os.environ["READTHEDOCS_VERSION_TYPE"] == "tag"
)

project = "pip-tools"
author = f"{project} Contributors"
copyright = f"The {author}"

release = get_version(project)
version = ".".join(release.split(".")[:3])

logger.info("%s version: %s", project, version)
logger.info("%s release: %s", project, release)

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "click_extra.sphinx",
    "myst_parser",
    "sphinx_click",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinx_issues",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.towncrier.ext",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

html_theme = "furo"
html_title = f"<nobr>{project}</nobr> documentation v{release}"
html_last_updated_fmt = datetime.now(tz=timezone.utc).isoformat()
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_show_sourcelink = False

autoclass_content = "both"
autodoc_member_order = "bysource"
autosectionlabel_prefix_document = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/stable", None),
    "pip": ("https://pip.pypa.io/en/stable", None),
    "click": ("https://click.palletsprojects.com/en/stable", None),
    "build": ("https://build.pypa.io/en/stable", None),
    "importlib_metadata": ("https://importlib-metadata.readthedocs.io/en/latest", None),
}

issues_github_path = "jazzband/pip-tools"

towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = True
towncrier_draft_working_directory = PROJECT_ROOT_DIR
towncrier_draft_config_path = "towncrier.toml"

default_role = "any"
nitpicky = True

linkcheck_ignore = [
    r"^https://matrix\.to/#",
    r"^https://img.shields.io/matrix",
    r"^https://results\.pre-commit\.ci/latest/github/jazzband/pip-tools/",
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
    ("py:class", "InstallRequirement"),
    ("py:exc", "click.*"),
    ("any", "Requires-Python"),
]

suppress_warnings = [
    "myst.xref_missing",
    "myst.header",
    "autosectionlabel.*",
]

apidoc_excluded_paths: list[str] = []
apidoc_extra_args = [
    "--implicit-namespaces",
    "--private",
]
apidoc_module_first = False
apidoc_module_dir = "../piptools"
apidoc_output_dir = "pkg"
apidoc_separate_modules = True
apidoc_toc_file = None

myst_enable_extensions = {
    "colon_fence",
    "deflist",
    "linkify",
    "smartquotes",
}
myst_heading_anchors = 3

copybutton_prompt_text = r">>> |\.\.\. |\$ |\(.*\) \$ |# "
copybutton_prompt_is_regexp = True

mermaid_output_format = "raw"


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register project-local Sphinx extension-API customizations."""
    if IS_RELEASE_ON_RTD:
        app.tags.add("is_release")

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": release,
    }
