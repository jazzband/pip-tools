# Use a private index

`pip-compile` accepts every `pip` flag that controls index behaviour. Configure them on the command
line, in the `requirements.in` file, in `pip.conf`, or via environment variables. The choice depends on
where you want the secrets and the configuration to live.

## Index URLs

`--index-url` (`-i`) replaces PyPI as the primary index:

```console
pip-compile --index-url https://my-index.example.com/simple
```

`--extra-index-url` adds a secondary index, queried alongside the primary:

```console
pip-compile --extra-index-url https://my-index.example.com/simple
```

Use `--extra-index-url` when most packages still come from PyPI. Use `--index-url` to redirect everything
to a private mirror.

`--no-index` skips index lookups entirely:

```console
pip-compile --no-index --find-links ./vendor/wheels
```

The compile resolves only against the find-links directory.

## In the requirements file

The same options work in `requirements.in`:

```text
--index-url https://my-index.example.com/simple
--extra-index-url https://pypi.org/simple
--trusted-host my-index.example.com

my-internal-package
django
```

`pip-compile` parses the file with `pip`'s own parser, so the options take effect for the resolve.

## Authentication

Index URLs can carry basic auth. `pip-compile` redacts the password in the lockfile header and in log
output, but the URL still has to come from somewhere. Pick whichever works best for your secrets policy:

::::{tab} CLI flag

```console
pip-compile --index-url https://username:password@my-index.example.com/simple
```

The password gets masked in the lockfile header. Avoid this if your shell history is shared.
::::

::::{tab} `requirements.in`

```text
--index-url https://username:password@my-index.example.com/simple

my-package
```

Same effect as the CLI flag, but the credentials live in the file. Useful only if the file itself is not
checked in.
::::

::::{tab} `pip.conf`

```ini
# ~/.pip/pip.conf
[global]
index-url = https://username:password@my-index.example.com/simple
```

Per-user, never committed, picked up by every `pip-compile` and `pip` invocation.
::::

::::{tab} Environment variables

```console
export PIP_INDEX_URL=https://username:password@my-index.example.com/simple
pip-compile
```

`pip-compile` calls `pip`'s option parser, which honours every `PIP_*` variable. Best for CI: set the
variable in the secrets manager, never write it to disk.
::::

## Stripping URLs from the lockfile

When the lockfile lives in a public repository, you may not want the private index URL embedded:

```console
pip-compile --no-emit-index-url --no-emit-trusted-host
```

The output omits the URLs. Downstream `pip install` needs the URLs from somewhere else (CI env vars,
`pip.conf`, etc.). See {doc}`customize-output`.

## Trusted hosts

For HTTP indexes, or HTTPS indexes with self-signed certs:

```console
pip-compile --trusted-host my-index.example.com
```

The trusted host gets emitted into the lockfile by default:

```text
--trusted-host my-index.example.com
```

`--no-emit-trusted-host` strips it. Combined with the prior tip, the lockfile then assumes the install
environment configures both the URL and the trust.

## Custom certificates

Corporate networks often use a custom CA bundle:

```console
pip-compile --cert /path/to/corp-ca.pem
```

For mTLS, `pip-compile` supports client certs:

```console
pip-compile --client-cert /path/to/client.pem
```

Both flags forward to `pip` unchanged. The `pip` documentation covers the certificate format expected.

## Find-links

`--find-links` (`-f`) adds a directory or HTML page as a candidate source:

```console
pip-compile --find-links ./vendor/wheels
pip-compile --find-links https://download.pytorch.org/whl/cu118
```

Local find-links are common for air-gapped environments. URL find-links are common for distros that ship
custom-built wheels (`pytorch`'s CUDA wheels, `nvidia`'s driver-bound packages).

## A sane corporate setup

```toml
[tool.pip-tools]
no-emit-index-url = true
no-emit-trusted-host = true
no-emit-find-links = true
```

```ini
# Each developer's ~/.pip/pip.conf
[global]
index-url = https://username:password@corp-index.example.com/simple
trusted-host = corp-index.example.com
```

```yaml
# CI (env vars set by the secret manager):
PIP_INDEX_URL: https://username:password@corp-index.example.com/simple
```

The lockfile contains pins only. Each environment supplies the URL.

```{seealso}
- {doc}`customize-output` for the full set of `--no-emit-*` flags.
- {doc}`forward-pip-args` for passing arguments `pip-compile` does not surface natively.
```
