# Preview, ask, and force during sync

Three `pip-sync` flags change when and whether the install runs: `--dry-run`, `--ask`, and `--force`.
Use them to add a confirmation step in interactive use, to gate sync in CI, or to break through a safety
check on purpose.

## `--dry-run`: preview without acting

```console
(venv) $ pip-sync --dry-run
Would install:
  django==4.2.7
Would uninstall:
  flask==3.0.0
```

`--dry-run` prints the plan and exits with code 1 if any change would happen, code 0 if the environment
already matches. The non-zero exit makes the flag useful as a CI drift check:

```console
pip-sync --dry-run requirements.txt && echo "in sync" || echo "drift detected"
```

GitHub Actions:

```yaml
- name: Check env drift
  run: pip-sync --dry-run requirements.txt
```

The job fails when the lockfile and the environment disagree.

## `--ask`: prompt before applying

```console
(venv) $ pip-sync --ask
Would install:
  django==4.2.7
Would uninstall:
  flask==3.0.0
Would you like to proceed with these changes? [y/N]:
```

`--ask` prints the plan, asks for confirmation, then applies if you say yes. It implies `--dry-run` for
the preview phase; saying "no" leaves the environment unchanged and exits 1.

Useful for the "I am about to run this in a venv I care about" moment. Quicker than running
`--dry-run` first and then re-running without it.

## `--force`: override safety checks

`pip-sync` rejects two kinds of input by default:

- Files with a `.in` extension (likely a confused `requirements.in` instead of `requirements.txt`).
- Conflicting pins between input files (the same package at different versions).

`--force` accepts both with a warning:

```console
(venv) $ pip-sync --force requirements.in
WARNING: Some input files have the .in extension, which is most likely an error
```

```console
(venv) $ pip-sync --force base.txt overrides.txt
WARNING: Incompatible requirements found: django==4.2.7 and django==5.0.0
```

In the conflict case, the last-occurring pin wins. Order matters; the last file overrides earlier files.

```{warning}
`--force` is rarely the right answer. The usual fix is to compile the inputs together so the conflict
gets resolved, not papered over.
```

## Combining the flags

`--dry-run` and `--ask` together work as expected: `--ask` does its own dry-run-then-confirm flow, so
adding `--dry-run` is redundant but not wrong.

`--force` and `--dry-run` together print the plan including any conflicting state, with the warning at
the top.

`--force` and `--ask` together prompt before applying; the prompt includes the conflict warning so you
see it before saying yes.

## In automation

A typical CI pattern: `--dry-run` to check, fall back to a real sync if the check fails:

```bash
if ! pip-sync --dry-run requirements.txt; then
    pip-sync requirements.txt
    pytest
fi
```

A safer pattern: fail fast on drift in CI, fix it on a developer machine, commit the lockfile.

```{seealso}
- {doc}`sync-environment` for the basic sync flow.
- {doc}`/explanation/stable-output` for why `pip-sync --dry-run` is meaningful.
```
