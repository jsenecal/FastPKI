"""Output formatting helpers for CLI commands."""

import json as json_lib
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from cli.config import get_default

console = Console()

# Global state for output format override
_format_override: str | None = None


def set_format_override(fmt: str | None) -> None:
    global _format_override
    _format_override = fmt


def _output_format() -> str:
    if _format_override:
        return _format_override
    return get_default("output_format", "table")


def print_json(data: Any) -> None:
    console.print_json(json_lib.dumps(data, indent=2, default=str))


def print_table(
    columns: list[str], rows: list[list[Any]], title: str | None = None
) -> None:
    table = Table(title=title, show_lines=False)
    for col in columns:
        table.add_column(col, overflow="fold")
    for row in rows:
        table.add_row(*[str(v) if v is not None else "" for v in row])
    console.print(table)


def print_record(fields: list[tuple[str, Any]], title: str | None = None) -> None:
    """Print a single record as a key-value table."""
    table = Table(title=title, show_header=False, show_lines=False)
    table.add_column("Field", style="bold cyan", min_width=18)
    table.add_column("Value")
    for key, value in fields:
        table.add_row(key, str(value) if value is not None else "")
    console.print(table)


def display_list(
    data: list[dict[str, Any]],
    columns: list[str],
    *,
    keys: list[str] | None = None,
    title: str | None = None,
) -> None:
    """Display a list of records as table or JSON depending on config."""
    if _output_format() == "json":
        print_json(data)
        return
    field_keys = keys or [c.lower().replace(" ", "_") for c in columns]
    rows = [[item.get(k) for k in field_keys] for item in data]
    print_table(columns, rows, title=title)


def display_detail(
    data: dict[str, Any], fields: list[tuple[str, str]], *, title: str | None = None
) -> None:
    """Display a single record as key-value pairs or JSON."""
    if _output_format() == "json":
        print_json(data)
        return
    pairs = [(label, data.get(key)) for label, key in fields]
    print_record(pairs, title=title)


def output_option() -> Any:
    """Reusable typer Option for --output flag."""
    return typer.Option(None, "--output", "-o", help="Output format: table, json")
