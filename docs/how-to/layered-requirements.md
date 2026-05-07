# Layered requirements

Production, development, test, and CI environments often share most dependencies. Layered requirement
files keep the shared pins consistent without re-declaring them in every file.

The pattern: a base `requirements.in` produces a base `requirements.txt`, then a child `dev-requirements.in`
constrains itself against the base output before resolving its own additions.

## The layout

```text
requirements.in
dev-requirements.in
requirements.txt          # generated
dev-requirements.txt      # generated
```

`requirements.in`:

```text
django<4.3
```

`dev-requirements.in`:

```text
-c requirements.txt
django-debug-toolbar
```

The `-c requirements.txt` line tells `pip-compile` "if any of the packages already pinned in
`requirements.txt` get pulled in by my new dependencies, use those exact versions". `django` itself does
not get pulled in by `dev-requirements.in` directly, but `django-debug-toolbar` depends on it, so the
constraint kicks in.

## Compiling

Compile the base first:

```console
pip-compile
```

Output (`requirements.txt`):

```text
asgiref==3.7.2
    # via django
django==4.2.7
    # via -r requirements.in
sqlparse==0.4.4
    # via django
```

Now compile the dev layer:

```console
pip-compile dev-requirements.in
```

Output (`dev-requirements.txt`):

```text
asgiref==3.7.2
    # via
    #   -c requirements.txt
    #   django
django==4.2.7
    # via
    #   -c requirements.txt
    #   django-debug-toolbar
django-debug-toolbar==4.2.0
    # via -r dev-requirements.in
sqlparse==0.4.4
    # via
    #   -c requirements.txt
    #   django
```

`django` keeps the version from `requirements.txt`, even though a newer one might exist on PyPI. The
`# via` annotation traces both sources.

## Installing

Production:

```console
pip-sync requirements.txt
```

Development:

```console
pip-sync requirements.txt dev-requirements.txt
```

`pip-sync` accepts multiple input files and merges them. Conflicts (same package pinned to different
versions across the layers) raise an error; pass `--force` to use the last-wins resolution if you accept
the risk.

## More than two layers

Extend the same pattern. A common four-layer setup:

```text
requirements.in
dev-requirements.in       # imports requirements.txt as constraint
test-requirements.in      # imports requirements.txt as constraint
ci-requirements.in        # imports test-requirements.txt as constraint
```

Each child layer pulls in the parent's pins via `-c`. Compile in dependency order:

```console
pip-compile
pip-compile dev-requirements.in
pip-compile test-requirements.in
pip-compile ci-requirements.in
```

`pip-sync` accepts the union:

```console
pip-sync requirements.txt dev-requirements.txt test-requirements.txt
```

## Updating

Updating the base means re-compiling the base, then re-compiling each layer that depends on it:

```console
pip-compile --upgrade-package django
pip-compile dev-requirements.in
pip-compile test-requirements.in
```

If the base pin moved, the layered files pick up the new version on their next compile via the `-c`
constraint.

## When to layer versus when to use extras

Layered files are right when the dependency sets are conceptually distinct: production runs without test
tooling, dev needs ipython but CI does not, etc. Each file describes one install scenario.

Extras under `[project.optional-dependencies]` are right when the project itself owns the optional
dependency set. Extras propagate via PyPI metadata; layered files do not.

You can mix the two: declare extras in `pyproject.toml`, compile each extra into its own
`requirements.txt`, and layer them with `-c`. The mechanics compose.

```{seealso}
- {doc}`compile-from-pyproject` for compiling extras from `[project.optional-dependencies]`.
- {doc}`update-dependencies` for moving pins safely across layers.
- {doc}`sync-environment` for installing one or several layered files.
```
