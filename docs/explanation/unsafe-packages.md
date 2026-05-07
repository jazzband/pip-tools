# "Unsafe" packages

Three package names are special to `pip-compile`: `setuptools`, `pip`, and `distribute`. By default they
do not appear in the output as installable lines. The flag that controls this is `--allow-unsafe`. The
default is moving.

## What "unsafe" means here

The packages above sit underneath `pip` itself: `pip` cannot install without them, and reinstalling them
mid-resolution can break the running interpreter. Pinning them in a `requirements.txt` and feeding the
file to a `pip install -r` then asks `pip` to upgrade the packages it depends on, sometimes mid-run.
The historical fallout was bad enough that the original `pip-tools` author chose to filter them out and
print them as a comment:

```text
# The following packages are considered to be unsafe in a requirements file:
# pip
# setuptools
```

This is the default today.

## What `--allow-unsafe` does

Pass `--allow-unsafe` and the same packages appear as ordinary pinned lines:

```text
pip==24.0
setuptools==69.5.1
```

`pip install -r` installs them like anything else. On modern `pip` (>= 22.x) this is safe because `pip`
itself runs from a temporary copy during install and can replace its own packages without crashing
mid-flight. The original concern is no longer load-bearing.

## Why the default is moving

A future `pip-tools` major release flips the default to `allow-unsafe`. Two pressures push that direction:

- **Reproducibility**. If `pip` and `setuptools` are not pinned, two installs of the "same" lockfile pick
  up two different versions. That defeats the purpose of pinning.
- **Hash-mode requirements**. With `--generate-hashes`, `pip` enforces `--require-hashes`. Every
  installable line needs a hash. Unsafe packages without hashes get flagged with
  `# WARNING: pip install will require the following package to be hashed`. The fix is to pin them, which
  means turning `--allow-unsafe` on.

Today, every `pip-compile` run that omits `--allow-unsafe` prints a warning telling you the default is
about to flip. The warning goes away when you set `--allow-unsafe` (or `--no-allow-unsafe` to keep the
existing behaviour explicitly).

## Customising the unsafe set

`--unsafe-package <name>` adds a name to the filter list. It replaces the built-in default; pass it once
per package you want filtered. This is rare. The use case is "an internal tool whose package version
should not bleed into application lockfiles", for example a private build helper installed alongside the
project but managed separately.

```console
pip-compile --unsafe-package my-internal-tool --unsafe-package my-other-tool
```

`--unsafe-package` does *not* opt out of the `--allow-unsafe` toggle: those packages still get filtered
unless `--allow-unsafe` is also set. The two flags compose:

| `--allow-unsafe` | `--unsafe-package foo` | Result |
|---|---|---|
| not set | not set | `setuptools`, `pip`, `distribute` filtered |
| not set | set | `setuptools`, `pip`, `distribute`, `foo` filtered |
| set | not set | nothing filtered |
| set | set | `foo` still appears (allow-unsafe wins per-package) |

The composition rule lives in `piptools.utils`: the `UNSAFE_PACKAGES` constant defaults to
`{setuptools, distribute, pip}`, and `--unsafe-package` overrides the default rather than extending it.

## Recommendation

Set `allow-unsafe = true` in `[tool.pip-tools]` for new projects. Set it for existing projects the next
time you bump `pip-tools`. The lockfile becomes more reproducible, the warning goes away, and the new
default arrives as a no-op when it lands.
