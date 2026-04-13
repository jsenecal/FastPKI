"""Organization commands."""

import typer

from cli import client
from cli.output import (
    display_detail,
    display_list,
    output_option,
    set_format_override,
)

app = typer.Typer(no_args_is_help=True)

ORG_LIST_COLUMNS = ["ID", "Name", "Description", "Created At"]
ORG_LIST_KEYS = ["id", "name", "description", "created_at"]

ORG_DETAIL_FIELDS = [
    ("ID", "id"),
    ("Name", "name"),
    ("Description", "description"),
    ("Created At", "created_at"),
    ("Updated At", "updated_at"),
]

USER_LIST_COLUMNS = ["ID", "Username", "Email", "Role", "Active"]
USER_LIST_KEYS = ["id", "username", "email", "role", "is_active"]


def _callback(output: str | None = output_option()) -> None:
    set_format_override(output)


app.callback(invoke_without_command=True)(_callback)


@app.command("list")
def list_orgs() -> None:
    """List organizations."""
    data = client.get("/api/v1/organizations/").json()
    display_list(data, ORG_LIST_COLUMNS, keys=ORG_LIST_KEYS, title="Organizations")


@app.command()
def show(org_id: int = typer.Argument(..., help="Organization ID")) -> None:
    """Show organization details."""
    data = client.get(f"/api/v1/organizations/{org_id}").json()
    display_detail(data, ORG_DETAIL_FIELDS, title=f"Organization #{org_id}")


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", prompt=True),
    description: str | None = typer.Option(None, "--description", "-d"),
) -> None:
    """Create a new organization."""
    payload: dict[str, object] = {"name": name}
    if description is not None:
        payload["description"] = description
    data = client.post("/api/v1/organizations/", json=payload).json()
    display_detail(data, ORG_DETAIL_FIELDS, title="Organization Created")


@app.command()
def update(
    org_id: int = typer.Argument(..., help="Organization ID"),
    name: str | None = typer.Option(None, "--name", "-n"),
    description: str | None = typer.Option(None, "--description", "-d"),
) -> None:
    """Update an organization."""
    payload: dict[str, object] = {}
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    if not payload:
        typer.echo("Nothing to update. Provide --name or --description.")
        raise typer.Exit(1)
    data = client.put(f"/api/v1/organizations/{org_id}", json=payload).json()
    display_detail(data, ORG_DETAIL_FIELDS, title=f"Organization #{org_id} Updated")


@app.command()
def delete(
    org_id: int = typer.Argument(..., help="Organization ID"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an organization."""
    if not force:
        typer.confirm(f"Delete organization #{org_id}?", abort=True)
    client.delete(f"/api/v1/organizations/{org_id}")
    typer.echo(f"Organization #{org_id} deleted.")


@app.command("add-user")
def add_user(
    org_id: int = typer.Argument(..., help="Organization ID"),
    user_id: int = typer.Argument(..., help="User ID"),
) -> None:
    """Add a user to an organization."""
    data = client.post(f"/api/v1/organizations/{org_id}/users/{user_id}").json()
    typer.echo(f"User {data['username']} added to organization #{org_id}.")


@app.command("remove-user")
def remove_user(
    org_id: int = typer.Argument(..., help="Organization ID"),
    user_id: int = typer.Argument(..., help="User ID"),
) -> None:
    """Remove a user from an organization."""
    data = client.delete(f"/api/v1/organizations/{org_id}/users/{user_id}").json()
    typer.echo(f"User {data['username']} removed from organization #{org_id}.")


@app.command()
def users(org_id: int = typer.Argument(..., help="Organization ID")) -> None:
    """List users in an organization."""
    data = client.get(f"/api/v1/organizations/{org_id}/users").json()
    display_list(
        data,
        USER_LIST_COLUMNS,
        keys=USER_LIST_KEYS,
        title=f"Users in Organization #{org_id}",
    )
