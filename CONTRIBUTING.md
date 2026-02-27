# Contributing to `pip-tools`

<!-- sphinx-inclusion-post-this-line -->

[![Jazzband](https://jazzband.co/static/img/jazzband.svg)](https://jazzband.co)

This is a [Jazzband](https://jazzband.co) project. By contributing you agree
to abide by the [Contributor Code of Conduct][coc]
and follow the [guidelines](https://jazzband.co/about/guidelines).

[coc]: https://jazzband.co/about/conduct

## Project Contribution Guidelines

Here are a few additional or emphasized guidelines to follow when contributing
to `pip-tools`:

- If you need to have a virtualenv outside of `tox`, it is possible to reuse
  its configuration to provision it with [tox devenv].
- Always provide tests for your changes and run `tox -p all` to make sure they
  are passing the checks locally.
- Give a clear one-line description in the PR (that the maintainers can add to
  [CHANGELOG] afterwards).
- Wait for the review of at least one other contributor before merging (even if
  you're a Jazzband member).
- Before merging, assign the PR to a milestone for a version to help with the
  release process.

The only exception to those guidelines is for trivial changes, such as
documentation corrections or contributions that do not change pip-tools itself.

Contributions following these guidelines are always welcomed, encouraged and
appreciated.

[tox devenv]: <https://tox.wiki/en/latest/reference/cli.html#tox-devenv-(d)>

### LLM Generated Contributions

Contributors are free to use whatever tools they like, but we have some
additional guidance for LLM-assisted contributions.

When interacting in pip-tools spaces (issues, pull requests, matrix, discord, etc.),
do not use LLMs to speak for you, except for translation or grammar edits.
This includes the creation of changelogs and PR descriptions.
Human-to-human communication is foundational to open source communities.

> [!CAUTION]
> In extreme cases, low quality PRs may be closed as spam.

#### Responsibility

Remember that you, not the LLM, are responsible for your contributions.
Be ready to discuss your changes.
Do not submit code you have not reviewed.

Do your best to follow the conventions and standards of the project.
Make sure your code really works.
Be thoughtful about testing and documentation.

Try to make your code brief, and recognize when less is more.

#### Autonomous Code Submissions

The use of agents which write code and submit pull requests without human review
is not permitted.

#### Pull Request Templates

Please do not replace the pull request template, which is part of the
maintainers' process.

### The `good first issue` label

The [`good first issue` label] is used to designate items which are being left
for new contributors.
They're a great way to get onboarded into the project and learn.

These issues should not be handled using LLMs.
Doing so undermines the purpose of these issues.

## Project Release Process

Releases require approval by a member of the [`pip-tools-leads` team].

Commands given below may assume that your fork is named `origin` in git
remotes and the main repo is named `upstream`.

This is the current release process:

- Create a branch for the release. _e.g., `release/v3.4.0`_.
- Use `towncrier` to update the [CHANGELOG], _e.g.,
  `towncrier build --version v3.4.0`_.
- Push the branch to your fork, _e.g.,
  `git push -u origin release/v3.4.0`_, and create a pull request.
- Merge the pull request after the changes are approved.
- Make sure that the tests/CI still pass.
- Fetch the latest changes to `main` locally.
- Create an unsigned tag with the release version number prefixed with a
  `v`, _e.g., `git tag -a v3.4.0 -m v3.4.0`_, and push it to `upstream`.
- Create a GitHub Release, populated with a copy of the changelog and set
  to "Create a discussion for this release" in the `Announcements`
  category.
  Some of the markdown will need to be reformatted into GFM.
  The release title and tag should be the newly created tag.
- The [GitHub Release Workflow] will trigger off of the release to
  publish to PyPI. A member of the [`pip-tools-leads` team] must approve
  the publication step.
- Once the release to PyPI is confirmed, close the milestone.
- Publish any release notifications,
  _e.g., pip-tools matrix channel, discuss.python.org, bluesky, mastodon,
  pypa Discord_.

[changelog]: ./CHANGELOG.md
[GitHub Release Workflow]:
https://github.com/jazzband/pip-tools/actions/workflows/release.yml
[`pip-tools-leads` team]:
https://github.com/orgs/jazzband/teams/pip-tools-leads
[LLM Policy Discussion]:
https://github.com/jazzband/pip-tools/discussions/2278
[`good first issue` label]:
https://github.com/jazzband/pip-tools/labels/good%20first%20issue%22
