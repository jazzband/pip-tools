# Configuration file

`pip-compile` and `pip-sync` read defaults from a TOML configuration file. Every command-line flag is
also a valid configuration key.

## Lookup order

`pip-tools` searches for the first matching file:

1. The path passed to `--config`.
2. `.pip-tools.toml` in the directory of the input file.
3. `pyproject.toml` in the directory of the input file.

When the input is stdin (`-`), the search starts from the current working directory.

`--no-config` skips the lookup entirely.

## Sections

`.pip-tools.toml`:

```toml
[tool.pip-tools]
# global keys: apply to both pip-compile and pip-sync

[tool.pip-tools.compile]
# pip-compile-only overrides

[tool.pip-tools.sync]
# pip-sync-only overrides
```

In `pyproject.toml`, the same sections live under `[tool.pip-tools]`:

```toml
[tool.pip-tools]
generate-hashes = true

[tool.pip-tools.compile]
strip-extras = true

[tool.pip-tools.sync]
ask = true
```

Command-specific values override global values. The command running selects which subsection applies.

## Key syntax

Configuration keys are command-line flag names without the leading `--`, with `-` or `_` accepted:

```toml
[tool.pip-tools]
generate-hashes = true        # the same as
generate_hashes = true
```

Both forms work.

## Negative options

Some flags are negative on the CLI (`--no-allow-unsafe`, `--no-emit-index-url`). In configuration, drop
the `no-` prefix and use a boolean:

```toml
[tool.pip-tools]
allow-unsafe = false          # equivalent to passing --no-allow-unsafe
emit-index-url = false        # equivalent to --no-emit-index-url
```

The exception is `--no-index`. There is no positive `--index` form, so the configuration accepts
`no-index` as written:

```toml
[tool.pip-tools]
no-index = true
```

## Multi-value options

Flags accepted multiple times on the CLI (`--extra`, `--upgrade-package`, `--unsafe-package`,
`--constraint`, `--build-deps-for`, `--find-links`, `--extra-index-url`, `--trusted-host`) take a list:

```toml
[tool.pip-tools]
extra = ["dev", "docs"]
upgrade-package = ["django", "requests"]
constraint = ["constraints/base.txt", "constraints/overrides.txt"]
```

A list with one entry is fine:

```toml
[tool.pip-tools]
extra = ["dev"]
```

## All keys

Every flag from {doc}`cli` works as a configuration key. Common ones:

```toml
[tool.pip-tools]
generate-hashes = true
strip-extras = true
allow-unsafe = true
resolver = "backtracking"
annotation-style = "split"
newline = "preserve"
cache-dir = "~/.cache/pip-tools"
emit-index-url = true
emit-find-links = true
emit-trusted-host = true
emit-options = true
header = true
annotate = true
build-isolation = true
reuse-hashes = true
max-rounds = 10
```

Any key that does not match a known flag raises `NoSuchOption` with a did-you-mean hint:

```text
Error: No such config key 'genrate-hashes'. Did you mean 'generate-hashes'?
```

A value that does not pass the flag's type check raises `BadOptionUsage` with the underlying type error.

## Setting `src_files` from config

The positional argument `src_files` is also a configuration key:

```toml
[tool.pip-tools.compile]
src-files = ["pyproject.toml"]
```

Compile then becomes a no-arg invocation:

```console
pip-compile
```

A positional argument on the command line takes precedence over the configuration value.

## Environment variables

Three options accept environment variables in addition to the flag and config form:

- `--cache-dir` reads `PIP_TOOLS_CACHE_DIR`.
- `--resolver` reads `PIP_TOOLS_RESOLVER`.
- `CUSTOM_COMPILE_COMMAND` rewrites the command shown in the file header.

See {doc}`environment-variables`.

```{seealso}
- {doc}`cli` for every flag's full description.
- {doc}`/how-to/customize-output` for the configuration that produces a clean diff and audit-friendly
  output.
```
