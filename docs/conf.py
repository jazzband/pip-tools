# https://www.sphinx-doc.org/en/master/usage/configuration.html
"""Configuration file for the Sphinx documentation builder."""

from __future__ import annotations

import os
from importlib.metadata import version as get_version
from pathlib import Path

from docutils.nodes import Element, reference
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.domains.python import PythonDomain
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import Options
from sphinx.util import logging

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

logger.info("%s version: %s", project, version)
logger.info("%s release: %s", project, release)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # Stdlib extensions:
    "sphinx.ext.intersphinx",
    # Third-party extensions:
    "click_extra.sphinx",  # provides GitHub-flavored admonition syntax
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

# Bare references in autodoc-rendered annotations (e.g., ``def f(x: Marker)``)
# carry no module prefix, so intersphinx cannot resolve them against the
# dotted upstream targets. Remap each one through a ``PythonDomain.resolve_xref``
# override (see ``setup`` below) so the rendered docs link to the upstream
# documentation instead of dropping the cross-ref.
_XREF_REMAP: dict[str, str] = {
    "Marker": "packaging.markers.Marker",
    "UndefinedComparison": "packaging.markers.UndefinedComparison",
    "UndefinedEnvironmentName": "packaging.markers.UndefinedEnvironmentName",
    "NormalizedName": "packaging.utils.NormalizedName",
    "InvalidName": "packaging.utils.InvalidName",
    "datetime": "datetime.datetime",
    "BadParameter": "click.BadParameter",
}

nitpick_ignore_regex: list[tuple[str, str]] = [
    # pip's intersphinx inventory only publishes the public API surface;
    # private internals (``pip._internal.*``, ``pip._vendor.*``) appear
    # in inherited pip-wrapper docstrings with no public doc target to
    # resolve against, so aliasing is impossible.
    ("py:class", r"pip\._internal\..*"),
    ("py:class", r"pip\._vendor\..*"),
    # ``importlib.metadata._meta.PackageMetadata`` is a private protocol;
    # importlib_metadata's intersphinx covers the public re-export but
    # not the underscored alias the inherited docstring uses.
    ("py:class", r"importlib\.metadata\._meta\..*"),
    # ``_ImportLibDist`` is a piptools-internal protocol shim with no
    # separate doc target.
    ("py:class", "_ImportLibDist"),
    # Recursive ``_t.TypeAlias`` strings cannot be resolved as classes.
    ("py:class", "_ToolValue"),
    ("py:class", "PerVariantMap"),
    ("py:class", "ForwardDeps"),
    # TypeVars render as class references with no resolvable target.
    ("py:class", r"piptools\.[\w.]+\._[A-Z]+"),
    # ``click.utils.LazyFile`` is a click utility that the upstream docs
    # do not expose in their intersphinx inventory, so the remap has no
    # target and the bare reference cannot resolve.
    ("py:class", r"click\.utils\..*"),
    ("py:class", "LazyFile"),
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


# -- myst_parser options --------------------------------------------------
myst_enable_extensions = {
    "colon_fence",
}


# -- Sphinx extension-API `setup()` hook


def _skip_hyphenated_members(
    app: Sphinx,
    what: str,
    name: str,
    obj: object,
    skip: bool,
    options: Options,
) -> bool | None:
    # TypedDicts in piptools.pylock use hyphenated keys (e.g. "lock-version") that
    # match PEP 751 TOML field names but are not valid Python identifiers. Autodoc
    # cannot generate attribute signatures for them, so skip them. ``obj`` stays
    # typed as ``object`` because Sphinx's callback receives the actual member
    # being documented (which is genuinely arbitrary) and we only inspect ``name``.
    # Blast radius is structurally bounded: Python's lexer rejects ``-`` in
    # identifiers, so no real attribute, function, or method can have a name
    # this matches — only TypedDict string keys do.
    return True if "-" in name else None


class _RemappingPythonDomain(PythonDomain):
    """Resolve bare cross-refs through ``_XREF_REMAP`` before falling back to the default."""

    def resolve_xref(  # noqa: PLR0913
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        type: str,  # noqa: A002
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> reference | None:
        if (remapped := _XREF_REMAP.get(target)) is not None:
            target = node["reftarget"] = remapped
        return super().resolve_xref(
            env, fromdocname, builder, type, target, node, contnode
        )


def setup(app: Sphinx) -> dict[str, bool | str]:
    """Register project-local Sphinx extension-API customizations.

    :param app: Initialized Sphinx app instance.
    :returns: Extension metadata.
    """
    if IS_RELEASE_ON_RTD:
        app.tags.add("is_release")

    app.connect("autodoc-skip-member", _skip_hyphenated_members)
    app.add_domain(_RemappingPythonDomain, override=True)

    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
        "version": release,
    }
