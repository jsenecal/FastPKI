"""Authentication commands."""

import typer
from rich.console import Console

from cli import client
from cli.config import clear_token, get_server_url, get_token, set_token

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def login(
    username: str = typer.Option(..., "--username", "-u", prompt=True),
    password: str = typer.Option(..., "--password", "-p", prompt=True, hide_input=True),
    server: str | None = typer.Option(
        None, "--server", "-s", help="Server URL (saves to config)"
    ),
) -> None:
    """Authenticate and store the access token."""
    if server:
        from cli.config import set_value

        set_value("server.url", server.rstrip("/"))

    resp = client.post(
        "/api/v1/auth/token",
        auth=False,
        data={"username": username, "password": password},
    )
    token = resp.json()["access_token"]
    set_token(token)
    console.print(f"[green]Logged in as {username}[/green] at {get_server_url()}")


@app.command()
def logout() -> None:
    """Clear the stored access token."""
    clear_token()
    console.print("[yellow]Logged out.[/yellow]")


@app.command()
def status() -> None:
    """Show current authentication status."""
    token = get_token()
    if not token:
        console.print("[yellow]Not authenticated.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]Server:[/bold] {get_server_url()}")

    try:
        resp = client.get("/api/v1/users/me")
        user = resp.json()
        console.print(f"[bold]User:[/bold]   {user['username']}")
        console.print(f"[bold]Role:[/bold]   {user['role']}")
        console.print(f"[bold]Email:[/bold]  {user['email']}")
        if user.get("organization_id"):
            console.print(f"[bold]Org ID:[/bold] {user['organization_id']}")
        console.print("[green]Token is valid.[/green]")
    except SystemExit:
        console.print(
            "[red]Token is invalid or expired. Run 'fastpki auth login'.[/red]"
        )
