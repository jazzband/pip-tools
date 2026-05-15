# Pin to a Git commit, branch, or URL

`pip-compile` accepts every direct-reference syntax `pip` accepts. Use it to pull in a fork from GitHub,
pin to a specific commit, install a wheel from a private archive, or include an editable local
checkout.

## Pin to a Git commit

The most reproducible shape: a 40-character SHA on the right side of `@`:

```text
# requirements.in
my-package @ git+https://github.com/example/my-package.git@4f8a3b9c2d5e7f1a8b2c4d6e9f0a3b5c7d8e1f2a
```

Compile:

```console
pip-compile
```

The resulting `requirements.txt` keeps the direct reference verbatim, so `pip install -r` checks out the
exact commit.

Alternative legacy syntax with `#egg=`:

```text
git+https://github.com/example/my-package.git@4f8a3b9c2d5e7f1a8b2c4d6e9f0a3b5c7d8e1f2a#egg=my-package
```

Pip 21+ prefers the `name @ url` form. Both work; pick one and stick with it.

## Pin to a branch or tag

Drop the SHA, append a branch name or tag:

```text
my-package @ git+https://github.com/example/my-package.git@main
my-package @ git+https://github.com/example/my-package.git@v1.2.3
```

```{warning}
Branches move. A branch reference resolves to whatever commit `main` points at when `pip install` runs,
not when you compiled. The lockfile records the URL but not the commit. For reproducible builds, pin to
a SHA.
```

Tags are immutable in convention but not in protocol; a force-push to a tag silently changes what
`v1.2.3` resolves to. SHAs are the only fully reproducible choice.

## Use other VCS backends

`pip` understands `git+`, `hg+`, `svn+`, and `bzr+`:

```text
my-package @ hg+https://example.com/my-package@abc123
other-package @ svn+https://example.com/svn/other-package@1234
```

The same SHA-vs-branch trade-off applies.

## Install from a remote URL

For a wheel or sdist served from a static URL:

```text
my-package @ https://example.com/wheels/my_package-1.0.0-py3-none-any.whl
```

```{tip}
Append a hash fragment so `pip-compile --generate-hashes` can use it without a re-fetch:
`my-package @ https://example.com/.../my_package.whl#sha256=abc123...`
```

## Editable installs

Use `-e` for a local checkout that you actively develop alongside the lockfile:

```text
# requirements.in
-e ./local-package
-e file:///absolute/path/to/another-package
```

`pip-compile` preserves `-e <link>` in the output. The line is not pinned (editables track whatever's at
the path) and `pip-sync` reinstalls them every run.

## Use a fork temporarily

A common pattern: you submitted a fix upstream, the maintainer has not merged yet, and you need the fix
in production today. Point at your fork:

```text
my-package @ git+https://github.com/your-handle/my-package.git@my-fix
```

When the upstream merges, switch back:

```text
my-package
```

Re-run `pip-compile` and the lockfile picks up the upstream version.

## Authentication

Private Git URLs work with HTTPS basic auth:

```text
my-package @ git+https://user:token@github.com/private-org/my-package.git@<sha>
```

Or with SSH (assumes the host has SSH keys configured):

```text
my-package @ git+ssh://git@github.com/private-org/my-package.git@<sha>
```

For shareable lockfiles, prefer SSH or a token in the environment instead of credentials in the file. See
{doc}`private-indexes` for index-level credentials.

## Hashes and Git URLs

`--generate-hashes` cannot hash a Git checkout; the source code at a SHA is reproducible by virtue of the
SHA itself. The lockfile gets a warning:

```text
# WARNING: pip install will require the following package to be hashed.
# Consider using a hashable URL like https://github.com/jazzband/pip-tools/archive/SOMECOMMIT.zip
my-package @ git+https://github.com/example/my-package.git@<sha>
```

The fix the warning suggests works: replace the `git+` URL with the corresponding archive URL:

```text
my-package @ https://github.com/example/my-package/archive/4f8a3b9c2d5e7f1a8b2c4d6e9f0a3b5c7d8e1f2a.zip
```

Now `--generate-hashes` can fetch the archive and hash it.

```{seealso}
- {doc}`compile-from-requirements-in` for general `requirements.in` syntax.
- {doc}`use-hashes` for hash-mode trade-offs.
```
