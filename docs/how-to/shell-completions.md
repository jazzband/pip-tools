# Enable shell completions

`pip-compile` and `pip-sync` use [Click](https://click.palletsprojects.com/), which ships built-in
shell-completion scripts. Generate them once, drop them in the right location for your shell, and tab
completion works for every flag.

## Bash

```console
_PIP_COMPILE_COMPLETE=bash_source pip-compile > ~/.pip-compile-complete.bash
_PIP_SYNC_COMPLETE=bash_source pip-sync > ~/.pip-sync-complete.bash
```

Source them from `~/.bashrc`:

```bash
. ~/.pip-compile-complete.bash
. ~/.pip-sync-complete.bash
```

## Zsh

System-wide:

```console
_PIP_COMPILE_COMPLETE=zsh_source pip-compile | sudo tee /usr/share/zsh/site-functions/_pip-compile
_PIP_SYNC_COMPLETE=zsh_source pip-sync | sudo tee /usr/share/zsh/site-functions/_pip-sync
```

Per-user:

```console
mkdir -p ~/.zsh/completions
_PIP_COMPILE_COMPLETE=zsh_source pip-compile > ~/.zsh/completions/_pip-compile
_PIP_SYNC_COMPLETE=zsh_source pip-sync > ~/.zsh/completions/_pip-sync
```

Add to `~/.zshrc`:

```bash
fpath=(~/.zsh/completions $fpath)
autoload -U compinit && compinit
```

## Fish

```console
_PIP_COMPILE_COMPLETE=fish_source pip-compile > ~/.config/fish/completions/pip-compile.fish
_PIP_SYNC_COMPLETE=fish_source pip-sync > ~/.config/fish/completions/pip-sync.fish
```

Fish picks them up the next time you start a shell.

## How it works

The `_PIP_COMPILE_COMPLETE` and `_PIP_SYNC_COMPLETE` environment variables tell Click to print the
completion script for a given shell instead of running the command. The script is shell-specific; Click
supports `bash_source`, `zsh_source`, and `fish_source`.

When the env var is set and you press tab, your shell calls `pip-compile` or `pip-sync` with the same env
var set to a different value (`complete_bash`, `complete_zsh`, etc.) and a partial argument; Click
returns the matching completions. The mechanism stays in sync with the actual flags because the script
introspects the live command.

## Caveats

- The completion script is generated against the version of `pip-compile` you ran. After upgrading
  `pip-tools`, regenerate it if new flags appeared.
- Powershell support is not built into Click. Use a shell wrapper or wait for upstream Click to add it.
- The completion does not enumerate package names from PyPI (too slow, too unbounded). It completes flag
  names, file paths, and choice-typed flag values.

```{seealso}
- [Click's shell-completion docs](https://click.palletsprojects.com/en/stable/shell-completion/) for
  the underlying mechanism.
```
