# Environment Variables

`pip-tools` supports a number of environment variables as ways of customizing behavior.

## `pip` Environment Variables

{external+pip:doc}`pip <index>` is used inside of `pip-tools`.

As a result, all of the environment variables supported by `pip` are supported
when using `pip-tools`.
For example, `PIP_BUILD_CONSTRAINT` can be used to control the environment used
for package builds.

See the
[`pip` documentation on environment variables][pip-env-vars]
for full details.

[pip-env-vars]: https://pip.pypa.io/en/stable/topics/configuration/#environment-variables

## `pip-tools` Environment Variables

`CUSTOM_COMPILE_COMMAND`
: This setting controls the command printed in the header for files generated
and updated by `pip-compile`. Set it in order to replace the default behavior --
which is to use the command which was run -- with a custom command.

`PIP_TOOLS_CACHE_DIR`
: The directory to use for `pip-tools`' caching. Defaults to a directory named
`pip-tools/` inside of the user's cache directory.
This can also be set by the `--cache-dir` option.

`PIP_TOOLS_RESOLVER`
: Select which resolver to use, either `legacy` or `backtracking`. The legacy
resolver will be removed in a future release.
This can also be set by the `--resolver` option.
