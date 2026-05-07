# Migrate off the legacy resolver

```{deprecated} 7.0
`--resolver=legacy` and `PIP_TOOLS_RESOLVER=legacy`. Every invocation prints a warning. A future major
release removes the option entirely.
```

This page walks through moving an existing project to the backtracking resolver.

## Step 1: find your invocation

The legacy resolver gets selected three ways:

- `--resolver=legacy` on the command line.
- `resolver = "legacy"` in `[tool.pip-tools]`.
- `PIP_TOOLS_RESOLVER=legacy` in the environment (often in CI).

Search:

```console
grep -rn "legacy" .pip-tools.toml pyproject.toml
git grep "PIP_TOOLS_RESOLVER"
git grep -- "--resolver=legacy"
```

CI configurations, Makefiles, and shell aliases are common hiding places.

## Step 2: re-compile

Drop the legacy selector and re-compile from scratch:

```console
rm requirements.txt
pip-compile -o requirements.txt pyproject.toml
```

The fresh compile uses the backtracking resolver. The output may differ from the legacy output. Two kinds
of changes are normal:

- New transitive packages appear because backtracking explored more of the graph.
- Some pins move down because backtracking picked an older version that satisfies more constraints.

The output may also be smaller, because the legacy resolver's round-based scheme sometimes pinned things
that backtracking skips.

## Step 3: run your tests

Run your full test suite against the new lockfile:

```console
pip-sync requirements.txt
pytest
```

Test failures point at packages whose versions moved. The two usual fixes:

- A new pin breaks a test. Tighten the constraint in `pyproject.toml` or `requirements.in`:
  `package>=A,<B`.
- A new transitive dependency breaks an import. Look at the `# via` annotation to find the package that
  pulled it in; either tighten that package's pin or add an explicit dependency on the new package.

Most projects need no fixes. The backtracking resolver picks compatible versions where the legacy
resolver picked first matches, and "first match" is rarely worse than "compatible match".

## Step 4: remove the legacy selector

Drop the resolver setting everywhere you found it. Optionally pin the new default:

```toml
[tool.pip-tools]
resolver = "backtracking"
```

Setting the value, even though it matches the default, makes the choice visible to readers and stops a
future default change from silently affecting your project.

## Step 5: clean up the cache

The legacy resolver populates the `depcache-{impl}{X.Y}.json` file under the cache directory. The
backtracking resolver does not use it. The file is harmless but orphaned. Delete it if you want a clean
state:

```console
rm ~/.cache/pip-tools/depcache-cp3.13.json
```

Or remove the whole cache directory:

```console
rm -rf ~/.cache/pip-tools/
```

The next compile recreates whatever it needs.

## When the new resolve fails

If backtracking fails with `ResolutionImpossible`, the constraint pool genuinely has no solution. The
legacy resolver was masking the conflict by picking first matches without checking the full graph.

Read the error. It names the packages whose constraints conflict. Two paths:

- Loosen one of the constraints. If you said `requests<2.30`, see if `<3` would work.
- Drop a transitive constraint. The lockfile-as-constraint pattern (`-c requirements.txt`) sometimes
  carries old pins forward. Compile without the constraint, see if the result is acceptable.

## Why now

The backtracking resolver is `pip`'s own. The same resolver that runs when you `pip install -r
requirements.txt`. Compiling with the same resolver that installs means a successful compile is a
guarantee that the install will work. Compiling with the legacy resolver gives no such guarantee:
`pip install` may reject what `pip-compile --resolver=legacy` produced.

That mismatch is rare in practice but real. The cost of moving to backtracking is one re-compile and a
test run. The cost of staying is a flag that disappears on the next major release.
