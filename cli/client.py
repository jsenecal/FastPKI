"""HTTP client wrapper for FastPKI API calls."""

from typing import Any

import httpx
import typer
from rich.console import Console

from cli.config import get_server_url, get_token

err_console = Console(stderr=True)


def _base_url() -> str:
    return get_server_url().rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = get_token()
    if not token:
        err_console.print(
            "[red]Not authenticated. Run 'fastpki auth login' first.[/red]"
        )
        raise typer.Exit(1)
    return {"Authorization": f"Bearer {token}"}


def _handle_response(resp: httpx.Response) -> httpx.Response:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        err_console.print(f"[red]Error {resp.status_code}:[/red] {detail}")
        raise typer.Exit(1)
    return resp


def get(
    path: str, *, auth: bool = True, params: dict[str, Any] | None = None
) -> httpx.Response:
    headers = _auth_headers() if auth else {}
    with httpx.Client(base_url=_base_url(), headers=headers) as c:
        return _handle_response(c.get(path, params=params))


def post(
    path: str,
    *,
    auth: bool = True,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> httpx.Response:
    headers = _auth_headers() if auth else {}
    with httpx.Client(base_url=_base_url(), headers=headers) as c:
        return _handle_response(c.post(path, json=json, data=data))


def patch(path: str, *, json: dict[str, Any] | None = None) -> httpx.Response:
    with httpx.Client(base_url=_base_url(), headers=_auth_headers()) as c:
        return _handle_response(c.patch(path, json=json))


def put(path: str, *, json: dict[str, Any] | None = None) -> httpx.Response:
    with httpx.Client(base_url=_base_url(), headers=_auth_headers()) as c:
        return _handle_response(c.put(path, json=json))


def delete(path: str) -> httpx.Response:
    with httpx.Client(base_url=_base_url(), headers=_auth_headers()) as c:
        return _handle_response(c.delete(path))


def download(path: str, *, auth: bool = True) -> bytes:
    headers = _auth_headers() if auth else {}
    with httpx.Client(base_url=_base_url(), headers=headers) as c:
        resp = _handle_response(c.get(path))
        return resp.content
