# Resolvers

`pip-compile` ships two dependency resolvers. Pick the backtracking one. The legacy one stays around for
bug-for-bug compatibility and is on its way out.

## Backtracking (default)

The backtracking resolver wraps `pip._internal.resolution.resolvelib`, the same resolver that backs
`pip install`. Given a constraint pool, it tries a candidate combination, walks the dependency graph, and
on conflict it backtracks and picks a different candidate.

```{mermaid}
flowchart TD
    Start([Resolve N constraints]) --> Pick[Pick candidate versions]
    Pick --> Walk[Walk transitive deps]
    Walk --> Ok{All deps satisfiable?}
    Ok -->|Yes| Done([Pinned set returned])
    Ok -->|No| Back[Backtrack and try a different version]
    Back --> Pick
    Pick --> Existing{Existing pin from<br/>requirements.txt conflicts?}
    Existing -->|Yes| Drop[Discard existing pin<br/>warn: 'Discarding foo to proceed']
    Existing -->|No| Walk
    Drop --> Walk

    style Start fill:#2563eb,stroke:#1d4ed8,color:#fff
    style Done fill:#16a34a,stroke:#15803d,color:#fff
    style Pick fill:#6366f1,stroke:#4f46e5,color:#fff
    style Walk fill:#6366f1,stroke:#4f46e5,color:#fff
    style Back fill:#7c3aed,stroke:#6d28d9,color:#fff
    style Drop fill:#d97706,stroke:#b45309,color:#fff
    style Ok fill:#d97706,stroke:#b45309,color:#fff
    style Existing fill:#d97706,stroke:#b45309,color:#fff
```

When a previously pinned version blocks resolution, the backtracking resolver drops the pin and emits
`Discarding foo==1.2.3 to proceed`. That message tells you which pin moved and why; the new version lands
in the output file.

The whole loop runs at most `--max-rounds` times (default: 10). Hitting the cap means the resolver kept
finding new constraints round after round, which usually points at a flapping dependency or an actual bug.

## Legacy

The legacy resolver predates `resolvelib`. It walks the constraint pool in rounds, picks the first version
that fits each name, then collects that version's transitive dependencies, then repeats until the
constraint pool stops changing.

It has two shortcomings the backtracking resolver fixes:

- It does not backtrack. Once a version is chosen, the only way to change it is to rerun with a tighter
  constraint by hand.
- It can declare success on a graph that `pip install` later rejects, because the two resolvers walk the
  graph differently.

The legacy resolver lives behind `--resolver=legacy` (or `PIP_TOOLS_RESOLVER=legacy`). Each invocation
prints a deprecation warning. A future `pip-tools` major release removes it.

## When the resolvers disagree

A graph that resolves under one resolver may not resolve under the other. The most common case is a
package whose newest version requires a transitive dependency that conflicts with another top-level pin.
Backtracking finds an older version that fits; legacy returns the first match and asks you to fix it.

When migrating from legacy to backtracking, expect the lockfile to change. New transitive packages may
appear (the backtracking resolver explored more of the graph). Some pins may move down (it picked an older
version that satisfies more constraints). Re-run your tests against the new lockfile before merging.
{doc}`/how-to/migrate-off-legacy-resolver` walks the migration step by step.

## Performance

Backtracking is faster on the steady state (no changes since the last compile) because the local pin proxy
short-circuits most index calls. It is slower on a fresh resolve (no existing `requirements.txt`) because
backtracking explores more of the graph. The difference rarely matters; both finish in seconds for typical
projects.

### Why backtracking downloads many versions

When a candidate fails, backtracking picks an older version and walks again. Each candidate's metadata
lives in its wheel file, so testing 20 versions of `botocore` means downloading 20 wheel-metadata blobs.
A graph with `boto3` plus an unconstrained transitive package can produce hundreds of metadata fetches
before the resolver settles. This is normal backtracking behaviour, not a bug. Mitigations:

- Tighten the constraints. `botocore>=1.34` lets the resolver skip everything below.
- Use a local PyPI mirror or caching proxy (`devpi`, `bandersnatch`, `proxpi`). Once the metadata is
  cached locally, repeat compiles are fast.
- Set `--max-rounds` to fail loudly when the resolver thrashes (default 10 is rarely the bottleneck;
  raising it doesn't help and lowering it surfaces the runaway).

See [issue #2044](https://github.com/jazzband/pip-tools/issues/2044) for the canonical example.

### Hashes

The big cost in either case is `--generate-hashes`. Hash fetching dominates. See
{doc}`/how-to/use-hashes` for what to do about it.
