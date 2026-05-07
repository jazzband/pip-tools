# Use `pip-compile` as a pre-commit hook

`pip-tools` ships a [pre-commit](https://pre-commit.com/) hook that re-runs `pip-compile` whenever a
`requirements.in` or `requirements.txt` file changes. The hook ensures the lockfile and the source file
never diverge in a commit.

## Minimal setup

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/jazzband/pip-tools
    rev: 7.5.3
    hooks:
      - id: pip-compile
```

Pin the `rev` to a release; `pre-commit` does not auto-update.

The hook's defaults:

```yaml
- id: pip-compile
  entry: pip-compile
  files: ^requirements\.(in|txt)$
  pass_filenames: false
```

It triggers when `requirements.in` or `requirements.txt` changes, then runs `pip-compile` with no
arguments (so `pip-compile` discovers the input itself).

## Custom arguments

Pass `pip-compile` flags via the `args` field:

```yaml
- repo: https://github.com/jazzband/pip-tools
  rev: 7.5.3
  hooks:
    - id: pip-compile
      args: [--generate-hashes, --strip-extras, --allow-unsafe]
```

Arguments compose with the hook's existing ones. The hook still discovers the input automatically.

## A specific input file

If your project does not use `requirements.in` at the project root, name the input explicitly:

```yaml
- id: pip-compile
  args: [requirements/production.in]
  files: ^requirements/production\.(in|txt)$
```

The `files` pattern controls when the hook fires; the `args` control what `pip-compile` sees.

## Multiple lockfiles

A project with several lockfiles needs one hook per lockfile. `pre-commit` runs them sequentially:

```yaml
- repo: https://github.com/jazzband/pip-tools
  rev: 7.5.3
  hooks:
    - id: pip-compile
      name: pip-compile (production)
      args: [requirements/production.in]
      files: ^requirements/production\.(in|txt)$

    - id: pip-compile
      name: pip-compile (dev)
      args: [requirements/dev.in]
      files: ^requirements/dev\.(in|txt)$

    - id: pip-compile
      name: pip-compile (lint)
      args: [requirements/lint.in]
      files: ^requirements/lint\.(in|txt)$
```

Each hook gets a unique `name` so the pre-commit log lists them clearly. The `files` pattern scopes each
hook to one lockfile pair.

For layered files (where the dev layer reads the production layer as a constraint), the hook order
matters: production first, then the layers that depend on it. `pre-commit` runs hooks in declaration
order.

## CI and local dev

The hook runs locally on every commit. `pre-commit.ci` runs it on every pull request. Both flag the same
problem: a `requirements.in` change without a matching `requirements.txt` re-compile, or vice versa.

To run the hook outside of a commit:

```console
pre-commit run pip-compile --all-files
```

To run a single named hook:

```console
pre-commit run "pip-compile (dev)" --all-files
```

## A common mistake

```{warning}
The hook fires when `requirements.txt` changes, not just when `requirements.in` changes. Editing the
lockfile by hand triggers a re-compile that overwrites your edit. Update the source
(`requirements.in` or `pyproject.toml`) and let `pip-compile` regenerate.
```

If you genuinely need to commit a lockfile change without re-compiling (rare; usually a hash refresh from
a hash-mode bump), use `--no-verify` to skip pre-commit for that one commit. Do not disable the hook
project-wide.

```{seealso}
- {doc}`/how-to/forward-pip-args` for hook arguments that include `--pip-args`.
- {doc}`/how-to/customize-output` for typical hook arg sets.
```
