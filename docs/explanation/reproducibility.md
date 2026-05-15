# Reproducibility

A `requirements.txt` is the start of a reproducible install, not the end. To get builds that two people on
two machines can audit and agree on, you need pinned dependencies, pinned hashes, pinned build
dependencies, and a way to keep all three honest in CI.

## What gets pinned by default

`pip-compile` pins:

- Every transitive runtime dependency of your project, by version.
- Index URLs and find-links if any are configured.

It does not pin, by default:

- Hashes. Without `--generate-hashes`, the resolved versions ride on whatever artifact PyPI happens to
  serve when `pip install` runs. A republish or mirror corruption goes unnoticed.
- Build dependencies. The packages listed in `[build-system].requires`, plus anything the backend asks
  for via `get_requires_for_build_*`, are not in `requirements.txt`. They get installed fresh in an
  isolated environment every time someone builds the project.
- The `pip` and `setuptools` versions used at install time. These get filtered as "unsafe" packages
  unless `--allow-unsafe` is set.

Each of these gaps closes with a flag.

## Closing the hash gap

`--generate-hashes` adds a hash for every artifact of every pinned package:

```text
django==4.2.7 \
    --hash=sha256:abc... \
    --hash=sha256:def...
    # via my-app (pyproject.toml)
```

When `pip install -r` sees hashes, it switches to `--require-hashes` mode: every package must have a hash,
the hash must match, and `pip` refuses to install anything else. A package whose hash changed (republish,
corruption, attack) fails the install loudly.

The cost is wall-clock time. Hash fetching on a fresh compile can dominate runtime. The mitigation is
`--reuse-hashes` (on by default), which copies hashes from the existing `requirements.txt` instead of
re-fetching. See {doc}`/how-to/use-hashes`.

## Closing the build-dep gap

PEP 517 build backends declare static build dependencies in `[build-system].requires`:

```toml
[build-system]
requires = ["setuptools>=63", "setuptools-scm[toml]>=7"]
build-backend = "setuptools.build_meta"
```

Backends can also declare dynamic build deps via `get_requires_for_build_wheel`/`sdist`/`editable`. Both
sets matter: a CI build that happens to install `setuptools 70.0.0` because that was the latest at build
time produces different artifacts from one that installed `setuptools 63.4.1`.

`pip-compile --all-build-deps` pins both sets. The output picks up new lines:

```text
setuptools==69.5.1
    # via my-app (pyproject.toml::build-system.requires)
setuptools-scm==8.0.4
    # via my-app (pyproject.toml::build-system.requires)
hatchling==1.21.0
    # via my-app (pyproject.toml::build-system.backend::wheel)
```

The annotation traces the source: static `build-system.requires`, or the dynamic hook for a specific
build target. {doc}`/how-to/compile-build-deps` walks the worked example.

## Using the lockfile in the build env

`pip` reads `PIP_CONSTRAINT` to constrain its own installs, including the installs it does inside an
isolated build environment. Set the variable to your lockfile and the build backend gets the same pins as
the runtime install:

```console
PIP_CONSTRAINT=requirements.txt python -m build
```

Combine `--all-build-deps --strip-extras` and one lockfile drives both the runtime install (via
`pip install -r`) and the build env (via `PIP_CONSTRAINT`). See {doc}`build-system-integration` for what
`pip-compile` itself does internally with `PIP_CONSTRAINT` when you pass `--upgrade-package`.

## Pinning the installer

Two install-time tools sit beneath `pip install` and shape the result: `pip` itself and `setuptools`. By
default `pip-compile` filters them as "unsafe" packages, on the legacy theory that `pip` cannot upgrade
the package it depends on mid-run. Modern `pip` handles this correctly. The result of the legacy
filter is that two installs of the "same" lockfile pick up two different `pip` versions and produce two
different outputs.

Pass `--allow-unsafe` to add `pip`, `setuptools`, and `distribute` to the lockfile as ordinary entries.
A future `pip-tools` release flips the default. See {doc}`unsafe-packages` for the trade-offs.

## Time-pinning

`--uploaded-prior-to <timestamp>` (requires `pip >= 26.0`) excludes any release uploaded after the given
ISO 8601 timestamp:

```console
pip-compile --uploaded-prior-to 2024-01-01T00:00:00Z
```

The resolver sees only releases that existed at that moment. The lockfile becomes "the project as it
would have resolved on January 1st", reproducible regardless of what PyPI publishes later. Useful for
historical builds, audit reproductions, and bisecting a regression that landed on PyPI before you noticed.
{doc}`/how-to/time-travel-builds` covers the worked case.

## A reproducible-build checklist

Aim for all of:

- `--generate-hashes` (or set in `[tool.pip-tools]`).
- `--all-build-deps` if your project ships an sdist/wheel.
- `--strip-extras` so the file is also usable as a `PIP_CONSTRAINT` target.
- `--allow-unsafe` to pin `pip` and friends.
- `PIP_CONSTRAINT=requirements.txt` set in CI for build steps.
- Optionally `--uploaded-prior-to` for historical reproduction.

A typical config:

```toml
[tool.pip-tools]
generate-hashes = true
all-build-deps = true
strip-extras = true
allow-unsafe = true
```

Then `pip-compile` produces a file that survives audits.
