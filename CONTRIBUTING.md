[![Jazzband](https://jazzband.co/static/img/jazzband.svg)](https://jazzband.co/)

This is a [Jazzband](https://jazzband.co/) project. By contributing you agree
to abide by the [Contributor Code of Conduct](https://jazzband.co/about/conduct)
and follow the [guidelines](https://jazzband.co/about/guidelines).

## Project Contribution Guidelines

Here are a few additional or emphasized guidelines to follow when contributing to `pip-tools`:

- If you need to have a virtualenv outside of `tox`, it is possible to reuse its configuration to provision it as [described in the docs](https://tox.readthedocs.io/en/latest/example/devenv.html#creating-development-environments-using-the-devenv-option).
- Always provide tests for your changes and run `tox -p all` to make sure they are passing the checks locally.
- Give a clear one-line description in the PR (that the maintainers can add to [CHANGELOG] afterwards).
- Wait for the review of at least one other contributor before merging (even if you're a Jazzband member).
- Before merging, assign the PR to a milestone for a version to help with the release process.

The only exception to those guidelines is for trivial changes, such as
documentation corrections or contributions that do not change pip-tools itself.

Contributions following these guidelines are always welcomed, encouraged and appreciated.

## Project Release Process

Jazzband aims to give full access to all members, including performing releases, as described in the
[Jazzband Releases documentation](https://jazzband.co/about/releases).

To help keeping track of the releases and their changes, here's the current release process:

- Check to see if any recently merged PRs are missing from the milestone of the version about to be released.
- Create a branch for the release. _Ex: release-3.4.0_.
- Update the [CHANGELOG] with the version, date and add the text from [drafter release](https://github.com/jazzband/pip-tools/releases).
- Push the branch to your fork and create a pull request.
- Merge the pull request after the changes being approved.
- Make sure that the tests/CI still pass.
- Once ready, go to `Github pip-tools Homepage > releases tab > Draft a new release` and type in:
  - _Tag version:_ The exact version number, following [Semantic Versioning](https://blog.versioneye.com/2014/01/16/semantic-versioning/). _Ex: 3.4.0_
  - _Target:_ master. As a general rule, the HEAD commit of the master branch should be the release target.
  - _Release title:_ Same as the tag. _Ex: 3.4.0_
- Publish release. This will push a tag on the HEAD of master, trigger the CI pipeline and
  deploy a pip-tools release in the **Jazzband private package index** upon success.
- The pip-tools "lead" project members will receive an email notification to review the release and
  deploy it to the public PyPI if all is correct.
- Once the release to the public PyPI is confirmed, close the milestone.

Please be mindful of other before and when performing a release, and use this access responsibly.

Do not hesitate to ask questions if you have any before performing a release.

[changelog]: https://github.com/jazzband/pip-tools/blob/master/CHANGELOG.md
