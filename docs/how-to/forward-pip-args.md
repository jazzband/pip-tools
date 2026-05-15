# Forward arguments to `pip`

`--pip-args` passes a string of arguments straight through to the underlying `pip` invocation. Use it
for flags `pip-compile` and `pip-sync` do not surface natively, or when you want to set an option without
making it part of your project's permanent config.

## Basic usage

```console
pip-compile --pip-args "--retries 10 --timeout 30"
```

The string gets tokenised with `shlex` and appended to the `pip` command line. Quoted multi-word values
work:

```console
pip-compile --pip-args "--retries 10 --timeout 30 --proxy 'http://user:pass@proxy.example.com:8080'"
```

## Common flags

Network tuning:

```console
pip-compile --pip-args "--timeout 60 --retries 5"
```

Per-package format control beyond what `pip-compile` exposes:

```console
pip-compile --pip-args "--prefer-binary"
```

Build backend config settings (replaces the deprecated `--global-option` and `--build-option`):

```console
pip-compile --pip-args "--config-setting=editable_mode=compat"
```

## With `pip-sync`

```console
pip-sync --pip-args "--no-cache-dir --no-deps"
```

`pip-sync` runs both `pip install` and `pip uninstall`. The argument string applies to both. Most flags
that make sense for one make sense for the other; `--no-deps` is a notable example that affects only
install.

## Filtering deprecated flags

`pip 25.3` and later removed four flags that older `pip-tools` users sometimes pass:

- `--use-pep517`
- `--no-use-pep517`
- `--global-option`
- `--build-option`

`pip-tools` strips them from `--pip-args` and warns:

```text
WARNING: --use-pep517 is no longer supported by pip and is deprecated in pip-tools.
```

`pip-tools` does not pass the stripped arguments to `pip`. The compile or sync continues without them.
The fix is to drop them from your config. PEP 517 is now `pip`'s only build path; `--config-setting`
replaces the option-passing flags.

## What `--pip-args` does not let you do

`--pip-args` cannot:

- Override `pip-tools`'s own internal flags (the resolver, the cache directory, the build isolation
  setting). Those need to use the dedicated `pip-tools` flags.
- Change the lockfile format. The output is determined by `pip-compile`, not by `pip`.
- Inject arguments before `pip-tools`'s own. The string always appends.

## When the flag exists in `pip-compile` directly

If `pip-compile` has a native flag, prefer it over `--pip-args`:

```console
pip-compile --cert /path/to/ca.pem
pip-compile --pip-args "--cert /path/to/ca.pem"
```

The two have the same effect on the underlying `pip` call. The native flag is more readable and lets
`pip-compile` know what the value is (so it can be redacted in the lockfile header, for instance).

```{seealso}
- {doc}`private-indexes` for index, certificate, and trusted-host options.
- {doc}`customize-output` for the `--no-emit-*` flags that control what ends up in the file.
```
