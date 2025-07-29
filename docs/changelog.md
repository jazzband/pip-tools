# Changelog

```{eval-rst}

.. MyST doesn't support the "only" directive correctly. It always evaluates to
.. true.
..
.. But if we drop into sphinx eval-rst, it works fine.
.. We then need to include our draft changelog content as markdown.
..
.. We're making a "MyST sandwich", with RST for the `{only}` directive in the
.. middle.
..
.. Using `include` with a `parser` is documented here:
.. https://myst-parser.readthedocs.io/en/latest/faq/index.html#include-rst-files-into-a-markdown-file

.. only:: not is_release

    .. include:: ../changelog.d/.draft_changelog_partial.md
        :parser: myst_parser.sphinx_

```

```{include} ../CHANGELOG.md

```
