"""Certificate commands."""

import typer

from cli import client
from cli.config import get_default
from cli.output import (
    display_detail,
    display_list,
    output_option,
    set_format_override,
)

app = typer.Typer(no_args_is_help=True)

CERT_LIST_COLUMNS = [
    "ID",
    "Common Name",
    "Type",
    "Status",
    "Serial",
    "Issuer",
    "Not After",
]
CERT_LIST_KEYS = [
    "id",
    "common_name",
    "certificate_type",
    "status",
    "serial_number",
    "issuer_id",
    "not_after",
]

CERT_DETAIL_FIELDS = [
    ("ID", "id"),
    ("Common Name", "common_name"),
    ("Subject DN", "subject_dn"),
    ("Type", "certificate_type"),
    ("Status", "status"),
    ("Serial Number", "serial_number"),
    ("Key Size", "key_size"),
    ("Valid Days", "valid_days"),
    ("Not Before", "not_before"),
    ("Not After", "not_after"),
    ("Revoked At", "revoked_at"),
    ("Issuer CA", "issuer_id"),
    ("Organization", "organization_id"),
    ("Created By", "created_by_user_id"),
    ("Created At", "created_at"),
    ("Updated At", "updated_at"),
]


def _callback(output: str | None = output_option()) -> None:
    set_format_override(output)


app.callback(invoke_without_command=True)(_callback)


@app.command("list")
def list_certs(
    ca_id: int | None = typer.Option(None, "--ca", "-c", help="Filter by issuing CA"),
    skip: int = typer.Option(0, "--skip"),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    """List certificates."""
    params: dict[str, object] = {"skip": skip, "limit": limit}
    if ca_id is not None:
        params["ca_id"] = ca_id
    data = client.get("/api/v1/certificates/", params=params).json()
    display_list(data, CERT_LIST_COLUMNS, keys=CERT_LIST_KEYS, title="Certificates")


@app.command()
def show(cert_id: int = typer.Argument(..., help="Certificate ID")) -> None:
    """Show certificate details."""
    data = client.get(f"/api/v1/certificates/{cert_id}").json()
    display_detail(data, CERT_DETAIL_FIELDS, title=f"Certificate #{cert_id}")


@app.command()
def create(
    ca_id: int = typer.Option(..., "--ca", "-c", help="Issuing CA ID", prompt=True),
    common_name: str = typer.Option(..., "--cn", "-n", help="Common name", prompt=True),
    subject_dn: str = typer.Option(..., "--subject-dn", "-s", prompt=True),
    cert_type: str = typer.Option(
        "server", "--type", "-t", help="Certificate type: server, client, ca"
    ),
    key_size: int | None = typer.Option(None, "--key-size", "-k"),
    valid_days: int | None = typer.Option(None, "--valid-days", "-v"),
    no_private_key: bool = typer.Option(
        False, "--no-private-key", help="Don't generate private key"
    ),
) -> None:
    """Issue a new certificate."""
    payload: dict[str, object] = {
        "common_name": common_name,
        "subject_dn": subject_dn,
        "certificate_type": cert_type,
        "include_private_key": not no_private_key,
    }
    ks = key_size or get_default("cert_key_size")
    if ks:
        payload["key_size"] = int(ks)
    vd = valid_days or get_default("cert_valid_days")
    if vd:
        payload["valid_days"] = int(vd)

    data = client.post(f"/api/v1/certificates/?ca_id={ca_id}", json=payload).json()
    fields = [*CERT_DETAIL_FIELDS, ("Certificate", "certificate")]
    if not no_private_key:
        fields = [*fields, ("Private Key", "private_key")]
    display_detail(data, fields, title="Certificate Created")


@app.command()
def revoke(
    cert_id: int = typer.Argument(..., help="Certificate ID"),
    reason: str | None = typer.Option(None, "--reason", "-r"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Revoke a certificate."""
    if not force:
        typer.confirm(f"Revoke certificate #{cert_id}?", abort=True)
    payload: dict[str, object] = {}
    if reason:
        payload["reason"] = reason
    data = client.post(f"/api/v1/certificates/{cert_id}/revoke", json=payload).json()
    display_detail(data, CERT_DETAIL_FIELDS, title=f"Certificate #{cert_id} Revoked")


@app.command("private-key")
def private_key(cert_id: int = typer.Argument(..., help="Certificate ID")) -> None:
    """Show certificate with private key."""
    data = client.get(f"/api/v1/certificates/{cert_id}/private-key").json()
    fields = [
        *CERT_DETAIL_FIELDS,
        ("Certificate", "certificate"),
        ("Private Key", "private_key"),
    ]
    display_detail(data, fields, title=f"Certificate #{cert_id} (with private key)")
