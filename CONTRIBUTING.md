[![Jazzband](https://jazzband.co/static/img/jazzband.svg)](https://jazzband.co/)

This is a [Jazzband](https://jazzband.co/) project. By contributing you agree
to abide by the [Contributor Code of Conduct](https://jazzband.co/about/conduct)
and follow the [guidelines](https://jazzband.co/about/guidelines).

## Project Contribution Guidelines

Here are a few additional or emphasized guidelines to follow when contributing to `pip-tools`:

- If you need to have a virtualenv outside of `tox`, it is possible to reuse its configuration to provision it with [tox devenv](<https://tox.wiki/en/latest/cli_interface.html#tox-devenv-(d)>).
- Always provide tests for your changes and run `tox -p all` to make sure they are passing the checks locally.
- Give a clear one-line description in the PR (that the maintainers can add to [CHANGELOG] afterwards).
- Wait for the review of at least one other contributor before merging (even if you're a Jazzband member).
- Before merging, assign the PR to a milestone for a version to help with the release process.

The only exception to those guidelines is for trivial changes, such as
documentation corrections or contributions that do not change pip-tools itself.

Contributions following these guidelines are always welcomed, encouraged and appreciated.

## Project Release Process

Releases require approval by a member of the [`pip-tools-leads` team].

Commands given below may assume that your fork is named `origin` in git remotes and the main repo is named `upstream`.

This is the current release process:

- Create a branch for the release. _e.g., `release/v3.4.0`_.
- Use `towncrier` to update the [CHANGELOG], _e.g., `towncrier build --version v3.4.0`_.
- Push the branch to your fork, _e.g., `git push -u origin release/v3.4.0`_,
  and create a pull request.
- Merge the pull request after the changes are approved.
- Make sure that the tests/CI still pass.
- Fetch the latest changes to `main` locally.
- Create an unsigned tag with the release version number prefixed with a `v`,
  _e.g., `git tag -a v3.4.0 -m v3.4.0`_, and push it to `upstream`.
- Create a GitHub Release, populated with a copy of the changelog and set to
  "Create a discussion for this release" in the `Announcements` category.
  Some of the markdown will need to be reformatted into GFM.
  The release title and tag should be the newly created tag.
- The [GitHub Release Workflow] will trigger off of the release to publish to PyPI.
  A member of the [`pip-tools-leads` team] must approve the publication step.
- Once the release to PyPI is confirmed, close the milestone.
- Publish any release notifications,
  _e.g., pip-tools matrix channel, discuss.python.org, bluesky, mastodon, pypa Discord_.

[changelog]: ./CHANGELOG.md
[GitHub Release Workflow]: https://github.com/jazzband/pip-tools/actions/workflows/release.yml
[`pip-tools-leads` team]: https://github.com/orgs/jazzband/teams/pip-tools-leads
