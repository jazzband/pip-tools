# How `pip-compile` works

`pip-compile` is a small orchestrator around `pip`'s own resolver. The hard work, finding compatible
versions and parsing metadata, sits inside `pip`. `pip-compile`'s job is to collect the right inputs, hand
them to `pip` in the right shape, and write the result back as a deterministic file.

## The pipeline

```{mermaid}
flowchart TD
    Start([pip-compile invoked]) --> Source[Discover input sources]
    Source --> Type{Source type?}
    Type -->|requirements.in| ParseReq[Parse via pip's parser]
    Type -->|setup.py / setup.cfg| Backend[Invoke PEP 517 backend]
    Type -->|pyproject.toml| Static{Static parse possible?}
    Static -->|Yes, deps not dynamic| FastPath[Read project.dependencies directly]
    Static -->|No, dynamic deps or build-deps requested| Backend
    ParseReq --> Pool[Constraint pool]
    FastPath --> Pool
    Backend --> Pool
    Pool --> Existing{Existing requirements.txt?}
    Existing -->|Yes, no --upgrade| Local[Wrap repository as<br/>LocalRequirementsRepository]
    Existing -->|No, or --upgrade| PyPI[Use PyPIRepository directly]
    Local --> Resolve[Run resolver until stable]
    PyPI --> Resolve
    Resolve --> Hashes{--generate-hashes?}
    Hashes -->|Yes| GetHashes[Fetch and reuse hashes]
    Hashes -->|No| Write
    GetHashes --> Write[OutputWriter formats and writes]
    Write --> Done([requirements.txt updated])

    style Start fill:#2563eb,stroke:#1d4ed8,color:#fff
    style Done fill:#16a34a,stroke:#15803d,color:#fff
    style Write fill:#16a34a,stroke:#15803d,color:#fff
    style FastPath fill:#16a34a,stroke:#15803d,color:#fff
    style Type fill:#d97706,stroke:#b45309,color:#fff
    style Static fill:#d97706,stroke:#b45309,color:#fff
    style Existing fill:#d97706,stroke:#b45309,color:#fff
    style Hashes fill:#d97706,stroke:#b45309,color:#fff
    style Source fill:#6366f1,stroke:#4f46e5,color:#fff
    style ParseReq fill:#6366f1,stroke:#4f46e5,color:#fff
    style Backend fill:#6366f1,stroke:#4f46e5,color:#fff
    style Pool fill:#6366f1,stroke:#4f46e5,color:#fff
    style Local fill:#7c3aed,stroke:#6d28d9,color:#fff
    style PyPI fill:#6366f1,stroke:#4f46e5,color:#fff
    style Resolve fill:#6366f1,stroke:#4f46e5,color:#fff
    style GetHashes fill:#6366f1,stroke:#4f46e5,color:#fff
```

Five stages, one section each.

## Discovering input sources

When you run `pip-compile` with no positional arguments, it walks the following names in order and takes
the first that exists:

1. `requirements.in`
2. `setup.py`
3. `pyproject.toml`
4. `setup.cfg`

You override this by passing one or more paths. With multiple paths, you must provide `--output-file`
because `pip-compile` cannot derive an output name from more than one input.

The path `-` reads from standard input. That case requires `--output-file` even with one input.

## Extracting top-level requirements

For `requirements.in` files, `pip-compile` calls `pip`'s requirement-file parser. Anything `pip install -r`
accepts works here: VCS URLs, direct URLs, `--index-url`, `--extra-index-url`, `--find-links`,
`--no-binary`, `-c constraints.txt`. Options inside the file flow into the finder alongside flags from the
command line.

For `pyproject.toml`, `pip-compile` first attempts a **static parse**. When the project metadata declares
both `dependencies` and `optional-dependencies` outright (neither is in `dynamic`), it reads them from the
TOML directly. No build backend, no subprocess, no isolated environment. This path is much faster.

Otherwise, and always for `setup.py`, `setup.cfg`, dynamic dependencies, or any `--build-deps-for` /
`--all-build-deps` flag, `pip-compile` runs the project's PEP 517 build backend in an isolated environment,
calls `prepare_metadata_for_build_wheel`, and reads the requirements from the generated metadata. See
{doc}`build-system-integration` for what that costs.

## Choosing the repository

`pip-compile` resolves against a *repository*. Two exist:

- **`PyPIRepository`** talks to PyPI, or to whatever index `--index-url` points at.
- **`LocalRequirementsRepository`** wraps a `PyPIRepository` and intercepts every "find best match" call:
  if the package is already pinned in the existing `requirements.txt` and that pin satisfies the
  constraint, it returns the existing pin; otherwise it asks PyPI.

The local proxy is what makes `pip-compile` runs deterministic across team members. Without it, every run
picks the latest matching version on PyPI and your lockfile changes on every machine. With it, versions
move when the constraint that picks them moves. {doc}`stable-output` covers this in detail.

`pip-compile` chooses the local proxy when an output file exists and `--upgrade` is not set.
`-P/--upgrade-package` excludes specific packages from the proxy so it can re-resolve them.

## Resolving until stable

Resolution goes through one of two resolvers:

- The **backtracking resolver** is the default. It is `pip`'s own `resolvelib`-based resolver, the same
  one `pip install` uses. On an unsatisfiable graph it backtracks and tries another version combination.
- The **legacy resolver** is the round-based first-fit approach. It is deprecated, kept for bug-for-bug
  compatibility, and emits a warning on every run.

Both run in a loop bounded by `--max-rounds` (default: 10) and produce a set of pinned requirements. On
conflict, backtracking drops existing pins from the local proxy with a warning of the form
`Discarding foo==1.2.3 to proceed`. Legacy raises if the round count exceeds the bound, which usually
points to a cycle in the constraint pool.

See {doc}`resolvers` for which to pick. The short answer: never use legacy on new work.

## Optionally fetching hashes

When you pass `--generate-hashes`, `pip-compile` walks every pinned package and asks the index for hashes
for every compatible artifact (wheel and sdist). With `--reuse-hashes` (on by default), it copies hashes
already present in the existing `requirements.txt` instead of fetching them again. Hash fetching dominates
the runtime of a hashed compile, so this difference matters in CI.

URL requirements that point at a remote file get hashed inline. URL requirements that point at a local
directory cannot be hashed and produce a `# WARNING: pip install will require the following package to be
hashed` comment in the output.

## Writing the file

`OutputWriter` produces a deterministic structure:

1. The header (the comment that names `pip-compile` and the command line that produced the file).
2. Index options (`--index-url`, `--extra-index-url`, `--find-links`, `--trusted-host`, format controls).
3. The pinned packages, editables first, then alphabetised.
4. The unsafe-packages section when `--allow-unsafe` is set.

Names are PEP 503 canonicalised (lowercased, hyphens). Annotations under each pinned line, the `# via foo`
comments, list the packages and source files that asked for it. The whole flow lives in `piptools.writer`.
{doc}`/reference/output-file` walks the file field by field.

## Why this shape

The five stages above stay cleanly separated for one reason: each is an extension surface for someone
else's tool. `pip-compile-multi` uses the constraint pool. Dependabot-style bots parse the output file.
`pre-commit` hooks invoke the CLI. Keeping the stages close to `pip`'s data structures avoids custom
intermediate formats, which keeps `pip-compile` cheap to integrate and easy to audit.
