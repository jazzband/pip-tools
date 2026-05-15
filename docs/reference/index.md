# Reference

Authoritative information on every flag, file format, and environment variable. Use the table of
contents to find a specific switch; use the explanation pages for the why.

- {doc}`cli` lists every flag for `pip-compile` and `pip-sync`, generated from the source.
- {doc}`config-file` lists every key accepted in `.pip-tools.toml` or `[tool.pip-tools]`.
- {doc}`environment-variables` documents `CUSTOM_COMPILE_COMMAND`, `PIP_TOOLS_CACHE_DIR`,
  `PIP_TOOLS_RESOLVER`, and `PIP_CONSTRAINT`.
- {doc}`output-file` walks the anatomy of a generated `requirements.txt`.
- {doc}`sync-ignore-list` lists packages `pip-sync` leaves alone.
- {doc}`cross-environment` explains why a lockfile is specific to one Python and OS.

```{toctree}
:hidden:

cli
config-file
environment-variables
output-file
sync-ignore-list
cross-environment
```
