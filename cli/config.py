"""CLI configuration management using XDG base directories."""

import json
import os
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    d = base / "fastpki"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_path() -> Path:
    return _config_dir() / "config.json"


def load_config() -> dict[str, Any]:
    path = _config_path()
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_config(cfg: dict[str, Any]) -> None:
    path = _config_path()
    path.write_text(json.dumps(cfg, indent=2) + "\n")


def get_value(key: str) -> Any | None:
    cfg = load_config()
    parts = key.split(".")
    obj: Any = cfg
    for part in parts:
        if isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    return obj


def set_value(key: str, value: Any) -> None:
    cfg = load_config()
    parts = key.split(".")
    obj = cfg
    for part in parts[:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value
    save_config(cfg)


def delete_value(key: str) -> bool:
    cfg = load_config()
    parts = key.split(".")
    obj = cfg
    for part in parts[:-1]:
        if isinstance(obj, dict) and part in obj:
            obj = obj[part]
        else:
            return False
    if isinstance(obj, dict) and parts[-1] in obj:
        del obj[parts[-1]]
        save_config(cfg)
        return True
    return False


def get_server_url() -> str:
    return get_value("server.url") or "http://localhost:8000"


def get_token() -> str | None:
    return get_value("auth.token")


def set_token(token: str) -> None:
    set_value("auth.token", token)


def clear_token() -> None:
    delete_value("auth.token")


def get_default(key: str, fallback: Any = None) -> Any:
    return get_value(f"defaults.{key}") or fallback
