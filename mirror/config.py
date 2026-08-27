from __future__ import annotations

import json
from os import environ
from pathlib import Path

from mirror.command import Settings

_DEFAULTS = Settings()


def default_path() -> Path:
    base = Path(environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "mirror" / "settings.json"


def cache_dir() -> Path:
    base = Path(environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    path = base / "mirror"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_settings(path: Path | None = None) -> Settings:
    target = path or default_path()
    if not target.is_file():
        return _DEFAULTS
    data = json.loads(target.read_text(encoding="utf-8"))
    return Settings(
        name=str(data.get("name") or _DEFAULTS.name),
        password=str(data.get("password") or ""),
        fullscreen_on_connect=bool(data.get("fullscreen_on_connect", False)),
        volume=_clamp_volume(data.get("volume", 1.0)),
    )


def save_settings(settings: Settings, path: Path | None = None) -> None:
    target = path or default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": settings.name,
        "password": settings.password,
        "fullscreen_on_connect": settings.fullscreen_on_connect,
        "volume": _clamp_volume(settings.volume),
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _clamp_volume(value: object) -> float:
    try:
        volume = float(value)
    except (TypeError, ValueError):
        return 1.0
    return max(0.0, min(1.0, volume))
