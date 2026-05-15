# Pipe input in or write output to stdout

`pip-compile` accepts `-` as a positional input to read from standard input, and accepts `--output-file=-`
to write to standard output. Both together let you treat `pip-compile` as a stream filter.

## Reading from stdin

When `pip-compile` reads from stdin, you must pass `--output-file` because there is no source filename to
derive an output name from:

```console
echo "django" | pip-compile - --output-file=requirements.txt
```

The input gets buffered to a temporary file (`pip` requires filenames, not streams) and parsed as a
`requirements.in`. The temp file is cleaned up automatically.

A here-doc works the same way:

```console
$ pip-compile - --output-file=requirements.txt <<EOF
django
requests
EOF
```

## Writing to stdout

`--output-file=-` writes the resolved lockfile to standard output:

```console
pip-compile --output-file=- pyproject.toml
```

Useful for scripting, for piping into another tool, or for capturing without a file:

```console
pip-compile --output-file=- pyproject.toml | grep django
```

## Both at once

```console
pip-compile - --output-file=- < requirements.in > requirements.txt
```

The cycle ends with `requirements.txt` written from stdout, sourced from `requirements.in` on stdin. Use
this when the file paths are awkward, when you want to trim the output before saving, or when wiring up a
generator script.

## A useful shell pattern

Combining several inputs into a transient compile:

```console
cat base.in extra.in extras-for-ci.in | pip-compile - --output-file=ci-requirements.txt
```

The same effect as listing the three files explicitly, but without forcing the files to live next to one
another or asking the resolver to deal with overlap warnings.

## Caveats

```{warning}
`--output-file=-` is the only way to write to standard output. A path like `--output-file=/dev/stdout`
or a named FIFO blocks indefinitely because the underlying `click.File` opens the path with
`atomic=True`, which expects a regular file it can rename atomically. See
[issue #2012](https://github.com/jazzband/pip-tools/issues/2012).
```

- `--upgrade-package` warns when the output file is empty (which happens whenever stdout is the output
  and you redirect it to a fresh file). The warning is informational; the compile still runs.
- The tempfile lives only for the duration of the run. If `pip-compile` crashes midway, no cleanup is
  needed.
- Annotations in the output reference `-r requirements.in` for stdin inputs, since `pip-compile` does not
  know the original filename.
