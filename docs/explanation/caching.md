# Caching

`pip-tools` keeps three caches. Knowing what each holds tells you what `--rebuild` clears, why a re-run
sometimes misses a freshly released version, and where to look when something goes wrong.

## Where caches live

By default everything goes under `pip-tools`'s user cache directory:

- macOS: `~/Library/Caches/pip-tools/`
- Linux: `~/.cache/pip-tools/`
- Windows: `%LOCALAPPDATA%\pip-tools\Cache`

Override the location with `--cache-dir <path>` or the environment variable `PIP_TOOLS_CACHE_DIR`. The
internal helper that picks this directory is `pip._internal.utils.appdirs.user_cache_dir`, the same one
`pip` uses for its own cache.

## The three caches

```{mermaid}
flowchart LR
    Cache[(pip-tools cache dir)]
    Cache --> Dep[Dependency cache<br/>depcache-cp3.13.json<br/>JSON file per Python impl+version]
    Cache --> Pkgs[Wheel/download cache<br/>pkgs/ab/cd/ef/...<br/>downloaded wheels and sdists]
    Mem[In-memory caches<br/>per-invocation only] --> Cand[Candidate cache<br/>per-name version lists]
    Mem --> Deps2[Dependency cache<br/>per-ireq dependency sets]

    style Cache fill:#2563eb,stroke:#1d4ed8,color:#fff
    style Mem fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Dep fill:#6366f1,stroke:#4f46e5,color:#fff
    style Pkgs fill:#6366f1,stroke:#4f46e5,color:#fff
    style Cand fill:#6366f1,stroke:#4f46e5,color:#fff
    style Deps2 fill:#6366f1,stroke:#4f46e5,color:#fff
```

### Dependency cache (JSON)

Path: `{cache_dir}/depcache-{impl}{X.Y}.json`, for example `depcache-cp3.13.json`.

Format: a single JSON file mapping `package` to `version` to a list of dependency strings. The legacy
resolver consults this to skip downloading the same package twice during a multi-round resolve. The
backtracking resolver does not use it; it relies on `pip`'s own resolve graph instead.

`--rebuild` truncates this file. Most users rarely benefit from clearing it. The dominant reason to do so
is a yanked release: PyPI removed a version after `pip-tools` cached its dependency list, and you want the
next compile to see only valid candidates.

### Wheel and download cache

Path: `{cache_dir}/pkgs/{salt[:2]}/{salt[2:4]}/{salt[4:6]}/{salt[6:]}/`. The directory salt comes from a
SHA-224 of the artifact URL.

Contents: every wheel or sdist that `pip-compile` had to download to inspect metadata. `pip-tools` does not
build wheels itself; it asks `pip` to do so, and `pip` writes them here. On the next compile the wheel is
already on disk and `pip` skips the network round-trip.

`--rebuild` does not delete this tree. Only the legacy resolver's `clear_caches()` removes the `pkgs/`
directory. To force a clean wheel cache, delete the directory by hand, or invoke with a fresh
`--cache-dir`.

### In-memory caches

`PyPIRepository` keeps two dictionaries on the instance for the duration of a single `pip-compile` run:

- `_available_candidates_cache` maps a package name to the list of `InstallationCandidate` objects PyPI
  reported for it. Asking PyPI a second time for the same name returns the same list.
- `_dependencies_cache` maps an `InstallRequirement` to its set of dependency `InstallRequirement` objects.
  This avoids walking the same wheel metadata multiple times in a single resolve.

These get thrown away when the process exits. `--rebuild` is not needed; rerunning `pip-compile` already
starts both empty.

## What `--rebuild` does

`--rebuild` clears two things:

1. The dependency JSON cache (`depcache-{impl}{X.Y}.json` is truncated to `{}`).
2. The finder's candidate cache inside `pip` (a `lru_cache`-decorated method on older `pip`, plain
   instance dicts on `pip >= 25.1`). This forces the next index lookup to re-fetch candidate lists.

It does not touch the wheel cache, the user's `pip` cache (`~/.cache/pip`), or any in-memory state. If you
think you need a true blank slate, delete the cache directory and run with a fresh `--cache-dir`.

## When a fresh run doesn't see a new version

Three usual suspects:

- **Index caching, not `pip-tools` caching.** PyPI's CDN serves cached HTML. A version pushed in the last
  minute may not appear yet. Wait, or refresh your local index mirror.
- **The local pin proxy.** Without `-U` or `-P`, `pip-compile` reuses the existing pin if it still
  satisfies. New versions on PyPI never get considered. See {doc}`stable-output`.
- **Stale dependency JSON.** When the legacy resolver decided that `foo==1.2.3` requires `bar<2`, that
  decision sticks until you `--rebuild` or upgrade past the cached version. The backtracking resolver does
  not have this issue.

## What is not cached

`pip-compile` never caches the resolution result itself, only its inputs. There is no "lockfile cache".
Every invocation re-runs the resolver. That keeps the lockfile honest: if you change a constraint, the
resolver sees it.
