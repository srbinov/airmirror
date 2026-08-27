from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    name: str = "Mirror"
    password: str = ""
    fullscreen_on_connect: bool = False
    phone_frame: bool = True
    volume: float = 1.0


def build_uxplay_argv(
    settings: Settings,
    rtp_port: int | None = None,
    binary: str = "uxplay",
    *,
    embed: bool = True,
    cover_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> list[str]:
    argv = [
        binary,
        "-n",
        settings.name,
        "-nh",
        "-vol",
        f"{settings.volume:.2f}",
        "-scrsv",
        "1",
    ]
    if embed:
        if rtp_port is None:
            raise ValueError("rtp_port is required when embedding video")
        argv.extend(
            [
                "-vrtp",
                f"config-interval=1 ! udpsink host=127.0.0.1 port={rtp_port}",
            ]
        )
    if cover_path:
        argv.extend(["-ca", str(cover_path)])
    if metadata_path:
        argv.extend(["-md", str(metadata_path)])
    if settings.password:
        argv.extend(["-pw", settings.password])
    return argv
