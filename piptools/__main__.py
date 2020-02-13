import click

from piptools.scripts import check, compile, sync


@click.group()
def cli():
    pass


cli.add_command(check.cli, "check")
cli.add_command(compile.cli, "compile")
cli.add_command(sync.cli, "sync")


# Enable ``python -m piptools ...``.
if __name__ == "__main__":  # pragma: no branch
    cli()
