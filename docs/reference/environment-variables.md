# Environment variables

`pip-tools` reads four environment variables of its own and propagates `pip`'s.

## `pip-tools` variables

`CUSTOM_COMPILE_COMMAND`
: Replaces the command shown in the `pip-compile` output header. Useful when a wrapper script invokes
`pip-compile` and the lockfile should record the wrapper's name. Has no effect on `pip-compile`'s actual
behaviour. {doc}`/how-to/custom-compile-command` covers the use case.

`PIP_TOOLS_CACHE_DIR`
: Overrides the `--cache-dir` default. Affects where `pip-compile` writes the dependency JSON cache and
where it expects to find downloaded wheels. Equivalent to passing `--cache-dir <path>` on every
invocation. {doc}`/explanation/caching` covers what lives in the cache.

`PIP_TOOLS_RESOLVER`
: Sets the default for `--resolver`. Accepts `backtracking` or `legacy`. Setting it to `legacy` opts the
project into the deprecated resolver and produces a warning on every run. Setting it to `backtracking`
makes the choice explicit; it is also the default if the variable is unset.
{doc}`/how-to/migrate-off-legacy-resolver` covers leaving `legacy` behind.

`PIP_CONSTRAINT`
: Read by `pip` itself, not by `pip-tools`. `pip-tools` sets it internally when invoking PEP 517 build
backends with `--upgrade-package`, so the build environment honours the upgrade. You can also set it
yourself in production CI to constrain `pip install` against your lockfile:
`PIP_CONSTRAINT=requirements.txt pip install foo`. {doc}`/explanation/reproducibility` covers the
build-time use case.

## `pip` variables that affect `pip-tools`

`pip-compile` instantiates `pip`'s `InstallCommand` to parse arguments, which means `pip`'s environment
variables propagate. The most relevant ones:

`PIP_INDEX_URL`
: Default for `--index-url`. The lockfile records the resolved URL (with passwords redacted).

`PIP_EXTRA_INDEX_URL`
: Default for `--extra-index-url`. Multiple URLs separated by spaces.

`PIP_FIND_LINKS`
: Default for `--find-links`.

`PIP_TRUSTED_HOST`
: Default for `--trusted-host`.

`PIP_NO_BUILD_ISOLATION`
: Default for `--no-build-isolation` (set to `true` to disable build isolation by default).

`PIP_PRE`
: Default for `--pre` (set to `true` to allow prereleases).

`PIP_CACHE_DIR`
: `pip`'s own cache directory. Separate from `PIP_TOOLS_CACHE_DIR`; both apply to different caches.

The full list of `PIP_*` variables lives in [`pip`'s documentation](https://pip.pypa.io/en/stable/topics/configuration/#environment-variables).

## Variables you might wish existed

- There is no `PIP_TOOLS_CONFIG` to set the configuration file. Use `--config <path>` per invocation.
- There is no `PIP_TOOLS_OUTPUT_FILE`. Use `--output-file` per invocation, or set `output-file` in
  `[tool.pip-tools.compile]`.
- There is no environment variable to disable the legacy-resolver deprecation warning. The fix is to
  stop using the legacy resolver.

```{seealso}
- {doc}`config-file` for the file-based equivalent of these variables.
- {doc}`/explanation/caching` for what `PIP_TOOLS_CACHE_DIR` controls.
```
