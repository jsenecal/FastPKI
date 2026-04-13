"""CLI configuration commands."""

import json

import typer
from rich.console import Console

from cli.config import (
    _config_path,
    delete_value,
    get_value,
    load_config,
    set_value,
)

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def show() -> None:
    """Show all configuration."""
    cfg = load_config()
    if not cfg:
        console.print("[yellow]No configuration set.[/yellow]")
        console.print(f"Config file: {_config_path()}")
        return
    console.print_json(json.dumps(cfg, indent=2))
    console.print(f"\n[dim]Config file: {_config_path()}[/dim]")


@app.command("get")
def get_cmd(
    key: str = typer.Argument(..., help="Config key (dot-separated, e.g. server.url)"),
) -> None:
    """Get a configuration value."""
    value = get_value(key)
    if value is None:
        console.print(f"[yellow]{key} is not set.[/yellow]")
        raise typer.Exit(1)
    if isinstance(value, dict):
        console.print_json(json.dumps(value, indent=2))
    else:
        typer.echo(value)


@app.command("set")
def set_cmd(
    key: str = typer.Argument(..., help="Config key (dot-separated)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value.

    Common keys:
      server.url           API server URL
      defaults.output_format   table or json
      defaults.ca_key_size     Default CA key size
      defaults.ca_valid_days   Default CA validity
      defaults.cert_key_size   Default cert key size
      defaults.cert_valid_days Default cert validity
    """
    # Try to parse as int/bool/null
    parsed: object
    if value.lower() == "true":
        parsed = True
    elif value.lower() == "false":
        parsed = False
    elif value.lower() == "null":
        parsed = None
    else:
        try:
            parsed = int(value)
        except ValueError:
            parsed = value

    set_value(key, parsed)
    console.print(f"[green]{key} = {parsed}[/green]")


@app.command("unset")
def unset_cmd(key: str = typer.Argument(..., help="Config key to remove")) -> None:
    """Remove a configuration value."""
    if delete_value(key):
        console.print(f"[yellow]{key} removed.[/yellow]")
    else:
        console.print(f"[yellow]{key} was not set.[/yellow]")


@app.command()
def path() -> None:
    """Show the config file path."""
    typer.echo(_config_path())
