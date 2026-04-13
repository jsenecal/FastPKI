"""Export commands for downloading certificates and keys as PEM files."""

from pathlib import Path

import typer
from rich.console import Console

from cli import client

app = typer.Typer(no_args_is_help=True)
console = Console()


def _write_file(data: bytes, path: Path) -> None:
    path.write_bytes(data)
    console.print(f"[green]Saved to {path}[/green]")


@app.command("ca-cert")
def ca_cert(
    ca_id: int = typer.Argument(..., help="CA ID"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download CA certificate as PEM."""
    data = client.download(f"/api/v1/export/ca/{ca_id}/certificate")
    out = output or Path(f"ca_{ca_id}_certificate.pem")
    _write_file(data, out)


@app.command("ca-key")
def ca_key(
    ca_id: int = typer.Argument(..., help="CA ID"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download CA private key as PEM."""
    data = client.download(f"/api/v1/export/ca/{ca_id}/private-key")
    out = output or Path(f"ca_{ca_id}_private_key.pem")
    _write_file(data, out)


@app.command("cert")
def cert(
    cert_id: int = typer.Argument(..., help="Certificate ID"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download certificate as PEM."""
    data = client.download(f"/api/v1/export/certificate/{cert_id}")
    out = output or Path(f"certificate_{cert_id}.pem")
    _write_file(data, out)


@app.command("cert-key")
def cert_key(
    cert_id: int = typer.Argument(..., help="Certificate ID"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download certificate private key as PEM."""
    data = client.download(f"/api/v1/export/certificate/{cert_id}/private-key")
    out = output or Path(f"certificate_{cert_id}_private_key.pem")
    _write_file(data, out)


@app.command("cert-chain")
def cert_chain(
    cert_id: int = typer.Argument(..., help="Certificate ID"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Download full certificate chain as PEM."""
    data = client.download(f"/api/v1/export/certificate/{cert_id}/chain")
    out = output or Path(f"certificate_{cert_id}_chain.pem")
    _write_file(data, out)
