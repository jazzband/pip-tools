# Deprecations

Three things in `pip-tools` are on a known glide path: two flag defaults change in the next major
release, and one resolver goes away. None require immediate action; all benefit from setting things up
today so the change lands as a no-op.

## `--strip-extras` becomes the default

```{deprecated} 8.0.0
The `--no-strip-extras` default flips. Output drops the bracketed parts of pinned lines, so
`requests[security]==2.31.0` becomes `requests==2.31.0`.
```

Why: `pip` rejects extras in constraint files. Many users rely on the lockfile as both a
`pip install -r` target and a `PIP_CONSTRAINT` target. Leaving extras in breaks the second use.

What to do today: set `strip-extras = true` in `[tool.pip-tools]`. The flag takes effect now and the new
default arrives as a no-op. See {doc}`strip-extras-and-constraints`.

## `--allow-unsafe` becomes the default

```{deprecated} 8.0.0
The `--no-allow-unsafe` default flips. `pip`, `setuptools`, and `distribute` start appearing as ordinary
pinned lines instead of commented-out entries.
```

Why: `--require-hashes` mode demands a hash for every installed package, including `pip` and friends. The
old default produced unhashable warnings on every hashed compile. Reproducible builds also need `pip`
itself pinned, which the old default prevents.

What to do today: set `allow-unsafe = true` in `[tool.pip-tools]`. See {doc}`unsafe-packages`.

## `--resolver=legacy` is being removed

```{deprecated} 7.0
The legacy resolver. `--resolver=legacy` emits a warning on every invocation. A future major release
removes the option entirely; `--resolver=legacy` will become an error.
```

Why: the legacy resolver is round-based and does not backtrack. It can declare success on graphs that
`pip install` later rejects. The backtracking resolver is `pip`'s own, the same one `pip install` uses;
its results match what installs.

What to do today: stop passing `--resolver=legacy`, drop `resolver = "legacy"` from
`[tool.pip-tools]`, and unset `PIP_TOOLS_RESOLVER=legacy` from your environment. Re-run your tests
against the new lockfile. {doc}`/how-to/migrate-off-legacy-resolver` walks the migration step by step.

## `pip` flags `pip-tools` no longer forwards

`pip 25.3` and later removed four flags that `pip-tools` used to forward verbatim:

- `--use-pep517`
- `--no-use-pep517`
- `--global-option`
- `--build-option`

`pip-tools` filters them out of `--pip-args` and warns:

```text
WARNING: --use-pep517 is no longer supported by pip and is deprecated in pip-tools.
```

Replacements: `pip` always uses PEP 517 now (so the first two flags are unnecessary).
`--config-setting` replaces `--global-option` and `--build-option`. Pass
`--config-setting key=value` through `--pip-args` instead.

## A "set it and forget it" config

Adopt this in `[tool.pip-tools]` to stay aligned with both today's recommended behaviour and the
upcoming defaults:

```toml
[tool.pip-tools]
allow-unsafe = true
strip-extras = true
resolver = "backtracking"
```

`pip-compile` reads it on every invocation. The flags work today; the defaults arrive without further
action.
