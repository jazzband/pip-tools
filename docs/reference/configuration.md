# Configuration

You can define project-level defaults for `pip-compile` and `pip-sync` by
writing them to a configuration file in the same directory as your requirements
input files (or the current working directory if piping input from stdin).

Each command-line flag is also a valid configuration key.

## Lookup Order

1. Any path passed to `--config`
2. `.pip-tools.toml` in the directory of the input file
3. `pyproject.toml` in the directory of the input file

When the input is stdin, the current working directory is used.

### `--no-config`

Use the `--no-config` flag to disable all use of configuration files.

## Sections

```toml
[tool.pip-tools]
# configuration for pip-compile and pip-sync

[tool.pip-tools.compile]
# configuration specific to pip-compile

[tool.pip-tools.sync]
# configuration specific to pip-sync
```

For example:

```toml
[tool.pip-tools]
cache-dir = "/tmp/pip-tools-cache"

[tool.pip-tools.compile]
generate-hashes = true
skip-extras = true

[tool.pip-tools.pip-sync]
dry-run = true
```

## Key and Value Syntax

Keys are canonically the same as long option names, but with the leading `--` removed.
Therefore, `--resolver` is configured under the name `resolver`.

> [!NOTE]
> Configuration keys may contain underscores instead of dashes.
> This is allowed but not recommended.

Values may be of any appropriate type, numeric, string, or boolean.
Options which may be used more than once must be defined as TOML arrays.

For example:

```toml
[tool.pip-tools]
extra = ["dev", "docs"]
```
