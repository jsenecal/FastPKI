"""Audit log commands."""

import typer

from cli import client
from cli.output import display_list, output_option, set_format_override

app = typer.Typer(no_args_is_help=True)

AUDIT_COLUMNS = [
    "ID",
    "Action",
    "User",
    "Resource Type",
    "Resource ID",
    "Detail",
    "Created At",
]
AUDIT_KEYS = [
    "id",
    "action",
    "username",
    "resource_type",
    "resource_id",
    "detail",
    "created_at",
]


def _callback(output: str | None = output_option()) -> None:
    set_format_override(output)


app.callback(invoke_without_command=True)(_callback)


@app.command("list")
def list_logs(
    action: str | None = typer.Option(
        None, "--action", "-a", help="Filter by action type"
    ),
    user_id: int | None = typer.Option(None, "--user", "-u", help="Filter by user ID"),
    resource_type: str | None = typer.Option(None, "--resource-type", "-t"),
    resource_id: int | None = typer.Option(None, "--resource-id", "-r"),
    since: str | None = typer.Option(None, "--since", help="ISO datetime"),
    until: str | None = typer.Option(None, "--until", help="ISO datetime"),
    skip: int = typer.Option(0, "--skip"),
    limit: int = typer.Option(100, "--limit"),
) -> None:
    """List audit log entries."""
    params: dict[str, object] = {"skip": skip, "limit": limit}
    if action is not None:
        params["action"] = action
    if user_id is not None:
        params["user_id"] = user_id
    if resource_type is not None:
        params["resource_type"] = resource_type
    if resource_id is not None:
        params["resource_id"] = resource_id
    if since is not None:
        params["since"] = since
    if until is not None:
        params["until"] = until

    data = client.get("/api/v1/audit-logs/", params=params).json()
    display_list(data, AUDIT_COLUMNS, keys=AUDIT_KEYS, title="Audit Logs")
