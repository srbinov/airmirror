from dataclasses import dataclass
from enum import Enum
import re


class EventKind(Enum):
    CLIENT = "client"
    MIRRORING = "mirroring"
    AUDIO = "audio"
    CLOSED = "closed"
    ERROR = "error"


@dataclass(frozen=True)
class Event:
    kind: EventKind
    client: str | None = None
    message: str = ""


@dataclass(frozen=True)
class TrackInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""

    @property
    def present(self) -> bool:
        return bool(self.title or self.artist or self.album)


_CLIENT_RE = re.compile(
    r"connection request from\s+(.+?)\s+\(",
    re.IGNORECASE,
)


def parse_uxplay_line(line: str) -> Event | None:
    text = line.strip()
    if not text:
        return None

    if text.startswith("*** ERROR") or text.startswith("ERROR:"):
        message = text.lstrip("* ").removeprefix("ERROR:").strip()
        return Event(EventKind.ERROR, message=message)

    if "connection request from" in text.lower():
        match = _CLIENT_RE.search(text)
        client = match.group(1).strip() if match else "Apple device"
        return Event(EventKind.CLIENT, client=client)

    if "starting mirroring" in text or "Begin streaming to GStreamer video" in text:
        return Event(EventKind.MIRRORING)

    if "Audio Metadata" in text:
        return Event(EventKind.AUDIO)

    if text.startswith("Connection closed"):
        return Event(EventKind.CLOSED)

    return None


def parse_metadata_text(text: str) -> TrackInfo:
    fields = {"title": "", "artist": "", "album": "", "genre": ""}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        if key in fields:
            fields[key] = value.strip()
    return TrackInfo(**fields)
