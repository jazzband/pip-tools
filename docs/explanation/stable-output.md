# Why re-compiling is stable

Run `pip-compile` twice in a row and the second run produces the same `requirements.txt` as the first,
even when newer versions of your dependencies got published in between. This is by design, and it is the
property that makes `pip-compile` usable in a team.

## The problem

A naive lockfile generator picks, on every invocation, the latest version that matches each constraint.
That gives you:

- Two engineers running the tool on the same day produce different lockfiles, because PyPI moved between
  their runs.
- A green CI build turns red because a dependency released a new version.
- A `requirements.txt` diff becomes unreadable, because every line might have moved.

`pip-compile` avoids all of that by treating the existing `requirements.txt` as a set of preferred pins
that the resolver should keep using as long as nothing has changed.

## How

When `pip-compile` runs and an output file exists, it parses the existing pinned versions and wraps the
PyPI repository in a `LocalRequirementsRepository`. Every "find the best version of `foo`" call goes
through this wrapper:

```{mermaid}
flowchart TD
    Start([Resolver asks for best match of foo]) --> Existing{foo pinned in<br/>existing requirements.txt?}
    Existing -->|No| AskPyPI[Ask PyPI for the best match]
    Existing -->|Yes| Satisfies{Pin satisfies the<br/>current constraint?}
    Satisfies -->|Yes| Reuse[Return the existing pin]
    Satisfies -->|No| AskPyPI
    Reuse --> Done([Best match returned])
    AskPyPI --> Done

    style Start fill:#2563eb,stroke:#1d4ed8,color:#fff
    style Done fill:#16a34a,stroke:#15803d,color:#fff
    style Reuse fill:#16a34a,stroke:#15803d,color:#fff
    style AskPyPI fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Existing fill:#d97706,stroke:#b45309,color:#fff
    style Satisfies fill:#d97706,stroke:#b45309,color:#fff
```

The PyPI call happens when one of two things is true:

1. The package is new. There is no existing pin for it.
2. The constraint the resolver is now applying is incompatible with the existing pin. You tightened a
   version range, or the resolver had to backtrack.

In every other case, the resolver gets back the version that was already in the file, and the output stays
unchanged.

## Hashes ride along

`--reuse-hashes` (on by default) extends the same idea to `--generate-hashes`. When the existing pin still
satisfies, `pip-compile` reads the hash list from the existing `requirements.txt` instead of fetching it
again from PyPI. Hash fetching dominates the runtime of a hashed compile. Reuse turns "slow but correct"
into "usable in CI".

To force a hash refresh, for example when PyPI corrected a hash mid-release, pass `--no-reuse-hashes`.

## Forcing a re-resolve

Three flags break out of the local-proxy behaviour, in increasing order of aggression:

- `-P django` (`--upgrade-package django`) re-resolves `django` only and leaves all other pins alone. Use
  this to bump a single dependency.
- `-U` (`--upgrade`) disables the local proxy. Every package gets re-resolved against PyPI. Every pin is
  fair game. Use this to see what's out there.
- `--rebuild` clears the dependency cache before resolving. You almost never need this. It exists for
  cases where a yanked version left the cache stale. See {doc}`caching`.

## What this means for reviewers

A `requirements.txt` diff in a `pip-compile` project is meaningful: each changed line corresponds to
something you or a teammate asked to change. New transitive dependencies appear when a top-level package
gets a new dependency in its newest version, and you ran `-U` or `-P` to pull it in. Removed lines mean a
top-level requirement got removed, or a transitive dependency is no longer needed by any pinned package.

`pip-compile` will not tell you "package `foo` has a new version available, want to upgrade?". You opt
in. The pay-off is that the diff matches the change.
