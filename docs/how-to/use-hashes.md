# Use hashes

`--generate-hashes` adds a hash for every artifact of every pinned package. When `pip install -r` sees
hashes, it switches to `--require-hashes` mode: every package must have a hash, the hash must match, and
`pip` refuses to install anything else.

## Generate hashes

```console
pip-compile --generate-hashes pyproject.toml
```

Output:

```text
django==4.2.7 \
    --hash=sha256:abc... \
    --hash=sha256:def...
    # via my-app (pyproject.toml)
asgiref==3.7.2 \
    --hash=sha256:111... \
    --hash=sha256:222...
    # via django
```

Each pinned package carries one hash per artifact. PyPI typically serves a wheel and a sdist; both get
hashed. If the package ships per-platform wheels, the file may have several `--hash` lines per package.

## Reuse hashes between runs

Hash fetching dominates the runtime of a hashed compile. The first run on a new project is slow;
subsequent runs reuse hashes from the existing `requirements.txt` and finish in seconds.

`--reuse-hashes` is on by default. To disable it (for example, after a hash you suspect was corrupt):

```console
pip-compile --generate-hashes --no-reuse-hashes pyproject.toml
```

## Set hashes as the default

Add to your config:

```toml
[tool.pip-tools]
generate-hashes = true
```

Now every `pip-compile` invocation produces hashes. The flag stays on for the project; new contributors
do not need to remember it.

## Installing with hashes

```console
pip install -r requirements.txt
```

`pip` enters `--require-hashes` mode automatically when it sees any hash in the file. From there:

- Every line must have a hash. Adding an unhashed line later breaks the install.
- The hash must match the artifact `pip` downloaded. Mismatches fail loudly.
- `pip install foo` (without `-r`) cannot be combined with hash mode in the same run.

## Hash warnings

`pip-compile` emits a warning comment for any package it could not hash:

```text
# WARNING: pip install will require the following package to be hashed.
# Consider using a hashable URL like https://github.com/.../archive/COMMIT.zip
foo @ file:///local/path/foo
```

Unhashable cases:

- Local directory paths (`-e ./mypkg`, `file:///path/to/dir`). `pip-compile` cannot hash a directory tree.
- VCS sources without a pinned commit. Pin to a 40-character SHA to make the URL hashable.
- Some private indexes that do not expose hashes via the JSON API.

The warning appears in the file, and `pip install -r` fails when it sees the unhashed line. Either add
the hash by hand or rework the source to be hashable.

## Hash mode and `--allow-unsafe`

`--require-hashes` insists every package have a hash. The "unsafe" packages (`pip`, `setuptools`,
`distribute`) are filtered out by default and do not get hashes. With hashes enabled, `pip-compile`
flags this:

```text
# WARNING: The following packages were not pinned, but pip requires them to be
# pinned when the requirements file includes hashes and the requirement is not
# satisfied by a package already installed. Consider using the --allow-unsafe flag.
```

The fix is `--allow-unsafe`. Set it in the config:

```toml
[tool.pip-tools]
generate-hashes = true
allow-unsafe = true
```

The "unsafe" packages then appear as ordinary pinned lines with hashes. See {doc}`/explanation/unsafe-packages`.

## CI usage

A typical CI invocation:

```console
pip-compile --generate-hashes --strip-extras --allow-unsafe -o requirements.txt pyproject.toml
pip install --require-hashes -r requirements.txt
```

The first line generates the lockfile with all the safety flags on. The second installs strictly. CI
fails if any package's hash drifted, which is what you want.

```{seealso}
- {doc}`/explanation/reproducibility` for hashes in the broader context of reproducible builds.
- {doc}`/explanation/unsafe-packages` for the hash-mode interaction with `pip` and `setuptools`.
```
