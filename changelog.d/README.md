## Adding Change Notes with PRs

It is important to maintain a changelog to explain to users what changed
between versions.

To avoid merge conflicts, we use
[Towncrier](https://towncrier.readthedocs.io/en/stable/) to maintain our
changelog.

Towncrier uses separate files, "news fragments", for each pull request.
On release, those fragments are compiled into the changelog.

You don't need to install Towncrier to contribute, you just have to follow some
simple rules!

- In your pull request, add a new file into `changelog.d/` with a filename
  formatted as `$NUMBER.$CATEGORY.md`.

  - The number is the PR number or issue number which your PR addresses.

  - The category is `bugfix`, `feature`, `deprecation`, `breaking`, `doc`,
    `packaging`, `contrib`, or `misc`.

  - For example, if your PR fixes bug #404, the change notes should be named
    `changelog.d/404.bugfix.md`.

- If multiple issues are addressed, create a symlink to the change notes with
  another issue number in the name.
  Towncrier will automatically merge files into one entry with multiple links.

- Prefer the simple past or constructions with "now".

You can preview the changelog by running `tox run -e build-docs` and viewing
the changelog in the docs.
