# Pin to a historical PyPI snapshot

`--uploaded-prior-to <timestamp>` excludes any release uploaded to PyPI after the given ISO 8601
timestamp. The resolver sees only the releases that existed at that moment. The lockfile becomes "the
project as it would have resolved on that date", reproducible regardless of what PyPI publishes later.

```{versionchanged} 7.5.3
Added support for the `--uploaded-prior-to` flag. Requires `pip >= 26.0`; on older `pip` the flag
raises an error.
```

## Basic usage

```console
pip-compile --uploaded-prior-to 2024-01-01T00:00:00Z
```

Every package in the lockfile pins to the latest version that existed on 2024-01-01.

ISO 8601 timestamps with timezone work:

```console
pip-compile --uploaded-prior-to 2024-06-15T14:30:00+00:00
```

Naive datetimes (without `Z` or offset) also work; `pip` interprets them as UTC.

## When to use it

**Reproducing a historical build**. You need to rebuild last year's release. The branch is unchanged, but
the dependencies on PyPI have moved. Pin to a date before the next release window:

```console
git checkout v1.0
pip-compile --uploaded-prior-to 2024-01-15T00:00:00Z -o requirements-frozen.txt
```

**Bisecting a regression that came from PyPI**. A test passed on Tuesday and fails today. Nothing in your
code changed. Compile against several historical timestamps and find the day a dependency moved:

```console
pip-compile --uploaded-prior-to 2024-09-15T00:00:00Z -o /tmp/sept-15.txt
pip-compile --uploaded-prior-to 2024-09-20T00:00:00Z -o /tmp/sept-20.txt
diff /tmp/sept-15.txt /tmp/sept-20.txt
```

The diff names the package whose version moved between the two dates.

**Audit reproducibility**. A compliance audit needs the exact dependency state at a point in time, six
months ago. Lock to that point:

```console
pip-compile --uploaded-prior-to 2024-03-31T23:59:59Z -o requirements-audit.txt
```

## What it does not do

`--uploaded-prior-to` filters by upload time. It does not:

- Roll back yanked releases. A yanked release is still excluded after the timestamp filter.
- Affect the local pin proxy. If `requirements.txt` already has pins, the proxy still prefers them when
  they satisfy. Pass `-U` to force a fresh resolve under the timestamp.
- Apply to URL or VCS dependencies. Direct references with no PyPI version do not get filtered.

## Caveats

```{warning}
The resolver may not find a satisfying graph on every date. Packages whose constraints required a
release that did not yet exist at that date will fail to resolve. The error names the package; pick
a later date or relax the constraint.
```

- The flag requires `pip >= 26.0`. On older pip, `pip-compile` raises `--uploaded-prior-to requires
  pip >= 26.0`. Upgrade pip in the same environment as `pip-tools`.
- Hashes are not affected. `--generate-hashes` works the same way: hashes for the resolved pre-cutoff
  versions get fetched.

## With `-U` for a clean historical compile

A typical historical compile starts from scratch:

```console
rm requirements.txt
pip-compile --uploaded-prior-to 2024-01-01T00:00:00Z --generate-hashes
```

Removing the existing lockfile bypasses the local pin proxy, which would otherwise prefer post-cutoff
pins if they happened to still satisfy. Equivalent:

```console
pip-compile --upgrade --uploaded-prior-to 2024-01-01T00:00:00Z --generate-hashes
```

```{seealso}
- {doc}`/explanation/reproducibility` for the broader picture of historical builds.
- {doc}`update-dependencies` for the regular-cadence upgrade flow.
```
