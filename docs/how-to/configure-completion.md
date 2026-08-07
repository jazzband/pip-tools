# Configure Shell Completion

`pip-compile` and `pip-sync` both support shell completion, but it needs to be
explicitly enabled.

Completions are output by special invocations of `pip-compile` and `pip-sync`.
You can either get completions by evaluating this output each time your shell
starts, or by writing the output to files and sourcing those files.

## Completion Using eval

::::{tab-set}

:::{tab-item} Bash

Add this to `~/.bashrc`:

```shell
eval "$(_PIP_COMPILE_COMPLETE=bash_source pip-compile)"
eval "$(_PIP_SYNC_COMPLETE=bash_source pip-sync)"
```

:::

:::{tab-item} Zsh

Add this to `~/.zshrc`:

```shell
eval "$(_PIP_COMPILE_COMPLETE=zsh_source pip-compile)"
eval "$(_PIP_SYNC_COMPLETE=zsh_source pip-sync)"
```

:::

:::{tab-item} PowerShell

Add this to your PowerShell profile (`$PROFILE`):

```shell
$env:_PIP_COMPILE_COMPLETE = 'powershell_source'
pip-compile | Out-String | Invoke-Expression
Remove-Item Env:_PIP_COMPILE_COMPLETE
$env:_PIP_SYNC_COMPLETE = 'powershell_source'
pip-sync | Out-String | Invoke-Expression
Remove-Item Env:_PIP_SYNC_COMPLETE
```

:::

::::

## Completions from Sourced Files

The eval-style method of completion means that `pip-compile` and `pip-sync` are
invoked each time a shell is started, which can be slow.
Simply saving the output to a file and sourcing that file can make completions
faster -- this is also the primary way that `fish` shell completions work.

::::{tab-set}

:::{tab-item} Bash

Save completions to a file somewhere:

```shell
_PIP_COMPILE_COMPLETE=bash_source pip-compile > ~/.pip-tools-complete.bash
_PIP_SYNC_COMPLETE=bash_source pip-sync >> ~/.pip-tools-complete.bash
```

Add this to `~/.bashrc`:

```shell
. ~/.pip-tools-complete.bash
```

:::

:::{tab-item} Zsh

Save completions to a file somewhere:

```shell
_PIP_COMPILE_COMPLETE=zsh_source pip-compile > ~/.pip-tools-complete.zsh
_PIP_SYNC_COMPLETE=zsh_source pip-sync >> ~/.pip-tools-complete.zsh
```

Add this to `~/.zshrc`:

```shell
. ~/.pip-tools-complete.zsh
```

:::

:::{tab-item} Fish

Save completions into `~/.config/fish/completions/`:

```shell
_PIP_COMPILE_COMPLETE=fish_source pip-compile > ~/.config/fish/completions/pip-tools.fish
_PIP_SYNC_COMPLETE=fish_source pip-sync >> ~/.config/fish/completions/pip-tools.fish
```

:::

:::{tab-item} PowerShell

Save completions to a file somewhere:

```shell
$env:_PIP_COMPILE_COMPLETE = 'powershell_source'
pip-compile | Out-File -Encoding utf8 ~/.pip-tools-complete.ps1
Remove-Item Env:_PIP_COMPILE_COMPLETE
$env:_PIP_SYNC_COMPLETE = 'powershell_source'
pip-sync | Out-File -Append -Encoding utf8 ~/.pip-tools-complete.ps1
Remove-Item Env:_PIP_SYNC_COMPLETE
```

Add this to your PowerShell profile (`$PROFILE`):

```shell
. ~/.pip-tools-complete.ps1
```

:::

::::
