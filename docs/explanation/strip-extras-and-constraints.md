# `--strip-extras` and constraints

`pip-compile` writes packages with their extras attached: `requests[security]==2.31.0`. That syntax works
when you feed the file to `pip install -r`. It does not work when you feed it to `pip install -c`. The
`--strip-extras` flag removes the bracketed parts so the same file works as a constraints file.

## What extras look like in the output

Without `--strip-extras`:

```text
requests[security]==2.31.0
    # via my-app (pyproject.toml)
```

With `--strip-extras`:

```text
requests==2.31.0
    # via my-app (pyproject.toml)
```

The annotation tracks the source either way; only the requirement line changes.

## Why `pip` rejects extras in constraint files

A constraint, in `pip`'s vocabulary, is "if this package gets pulled in, here is the version to use".
Constraints are not requirements. They do not pull packages in by themselves. Extras, on the other hand,
*are* requirement modifiers: `requests[security]` means "install `requests` and also pull in everything
under the `security` extra". Asking `pip` to apply that as a constraint mixes the two roles.

`pip` solves the ambiguity by raising:

```text
Constraints cannot have extras.
```

So if you want to use the same file for both `pip install -r requirements.txt` and
`PIP_CONSTRAINT=requirements.txt`, you need it without extras.

## Why the default is moving

Today `--strip-extras` defaults to off. Without it, every compile that prints an extras-bearing line
prints a warning:

```text
WARNING: --strip-extras is becoming the default in version 8.0.0.
```

The old default exists because at the time `pip-tools` was written, no one used the output as a constraint
file. The transitive package set is the contract; extras only matter at the top level. The old default
preserves the top-level extras for human readability of the `requirements.txt`.

The new default exists because constraint reuse turned out to be common: as a `PIP_CONSTRAINT` for
reproducible builds, as a constraint when installing tools alongside the project, as a contract handed to
downstream packagers. People hit the "constraints cannot have extras" wall every time.

## What to do today

Three options:

1. Pass `--strip-extras` on every invocation. The warning goes away. The lockfile becomes constraint-safe.
2. Add it to the config file:

   ```toml
   [tool.pip-tools]
   strip-extras = true
   ```

   The flag now applies to every `pip-compile` run in the project.
3. Pin `pip-tools < 8` and pass `--no-strip-extras` to keep the old behaviour. Fine as a stop-gap, not as a
   long-term plan.

Option 2 is the recommended path. New projects should adopt it from day one. Existing projects should
switch when they next need to bump `pip-tools` anyway.

## What changes when you flip it

The `requirements.txt` diff on the next compile shows the bracketed parts disappearing:

```diff
-requests[security]==2.31.0
+requests==2.31.0
```

Nothing else moves. The transitive package set stays the same; the resolver still pulled in everything the
extra required, those packages already appear as separate entries. The only loss is the human-readable
trace of which extras were active at the top level. The `# via` annotations cover that gap.

`pip install -r requirements.txt` still works. `pip install -c requirements.txt` works too.
