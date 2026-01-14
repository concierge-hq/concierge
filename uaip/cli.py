"""UAIP CLI."""
import shutil
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import click

TEMPLATE_NAME = "mini_store"


def _style():
    def dim(s): return click.style(s, dim=True)
    def green(s): return click.style(s, fg="green")
    def cyan(s): return click.style(s, fg="cyan")
    def bold(s): return click.style(s, bold=True)
    return dim, green, cyan, bold


def _copy_template(dest: Path) -> None:
    src_root = Path(__file__).parent / "templates" / TEMPLATE_NAME
    if not src_root.exists():
        raise RuntimeError(f"Template not found: {src_root}")
    shutil.copytree(src_root, dest, dirs_exist_ok=False)


def _cli_version() -> str:
    try:
        return f"UAIP CLI {version('uaip')}"
    except PackageNotFoundError:
        return "UAIP CLI"


@click.group()
def cli():
    """UAIP command line tools."""
    pass


@cli.command()
@click.argument("name")
def init(name: str):
    """Scaffold a minimal UAIP workflow project."""
    dim, green, cyan, bold = _style()
    dest = Path(name).resolve()
    if dest.exists():
        raise click.ClickException(f"Path already exists: {dest}")

    click.echo()
    click.echo(_cli_version())
    click.echo(f"Scaffolding project {green('✓')}")

    _copy_template(dest)

    click.echo(f"> Success! Initialized {bold(name)} in {dim(str(dest))}")
    click.echo()
    click.echo("To run:")
    click.echo(f"  {dim('$')} cd {cyan(str(dest))}")
    click.echo(f"  {dim('$')} python main.py")
    click.echo()


if __name__ == "__main__":
    cli()
