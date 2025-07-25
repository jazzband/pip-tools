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

- Include a byline, `` `-- by {user}`github-username` ``

You can preview the changelog by running `tox run -e build-docs` and viewing
the changelog in the docs.

### Categories

The categories for change notes are defined as follows.

- `bugfix`: A fix for something we deemed improper or undesired behavior.

- `feature`: A new behavior, such as a new flag or environment variable.

- `deprecation`: A declaration of future removals and breaking changes in behavior.

- `breaking`: A change in behavior which changes or violates established user expectations. e.g., Removing a flag or changing output formatting.

- `doc`: Notable updates to the documentation structure or build process.

- `packaging`: Changes in how `pip-tools` itself is packaged and tested which may impact downstreams and redistributors.

- `contrib`: Changes to the contributor experience. e.g., Running tests, building the docs, or setting up a development environment.

- `misc`: Changes that don't fit any of the other categories.

Sometimes it's not clear which category to use for a change.
Do your best and a maintainer can discuss this with you during review.

### Examples

Example bugfix, `2082.bugfix.md`:

```md
Fixed the ordering of format controls to preserve underlying `pip` behavior
-- by {user}`sethmlarson`.
```

Example contributor update, `2202.contrib.md`:

```md
`pip-tools` now uses [`sphinx-issues`](https://github.com/sloria/sphinx-issues)
to link to issues, PRs, commits, and user accounts
-- by {user}`sirosen`.
```

### Rationale

When somebody makes a change, they must record the bits that would affect end-users only including information that would be useful to them.
Then, when the maintainers publish a new release, they'll automatically use these records to compose a change log for the respective version.

We write change notes in the past tense because this suits the users who will be reading these notes.
Combined with others, the notes will be a part of the "news digest" telling the readers what **changed** in a specific version of the library since the previous version.

This methodology has several benefits, including those covered by the
[Towncrier Philosophy](https://towncrier.readthedocs.io/en/stable/#philosophy):

- Change notes separate the user-facing description of changes from the implementation details.
  Details go into the git history, but users aren't expected to care about them.

- The release engineer may not have been involved in each issue and pull request.
  Writing the notes early in the process involves the developers in the best position to write good notes.

- Describing a change can help during code review.
  The reviewer can better identify which effects of a change were intentional and which were not.
