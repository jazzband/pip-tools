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

Releases require approval by a member of the `pip-tools-leads` team.

This is the current release process:

- Create a branch for the release. _e.g., `release-3.4.0`_.
- Use `towncrier` to update the [CHANGELOG], _e.g., `towncrier build --version v3.4.0`_.
- Push the branch to your fork and create a pull request.
- Merge the pull request after the changes are approved.
- Make sure that the tests/CI still pass.
- Pull the latest changes to `main` locally.
- Create an unsigned tag with the release version number prefixed with a `v`, _e.g., `git tag v3.4.0`_, and push.
- Create a GitHub Release, populated with a copy of the changelog. Some of the markdown will need to be reformatted into GFM.
  The release title and tag should be the newly created tag.
- A GitHub Workflow will trigger off of the release to publish to PyPI. A member of `pip-tools-leads` must approve the publication step.
- Once the release to PyPI is confirmed, close the milestone.
- Publish any release notifications, _e.g., discuss.python.org, social media, pypa Discord_.

[changelog]: https://github.com/jazzband/pip-tools/blob/main/CHANGELOG.md
