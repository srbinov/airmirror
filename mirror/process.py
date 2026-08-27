from __future__ import annotations

import os
import signal
import time
from pathlib import Path


def is_uxplay_instance(cmdline: list[str], name: str | None = None) -> bool:
    if "uxplay" not in [Path(part).name for part in cmdline]:
        return False
    if name is None:
        return True
    try:
        index = cmdline.index("-n")
        return cmdline[index + 1] == name
    except (ValueError, IndexError):
        return False


def _proc_cmdline(pid: int) -> list[str]:
    raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]


def stale_uxplay_pids(name: str | None = None, *, exclude: int | None = None) -> list[int]:
    pids: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == exclude:
            continue
        try:
            cmdline = _proc_cmdline(pid)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if is_uxplay_instance(cmdline, name=name):
            pids.append(pid)
    return pids


def reap_stale_uxplay(name: str | None = None, *, exclude: int | None = None) -> None:
    for pid in stale_uxplay_pids(name, exclude=exclude):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and stale_uxplay_pids(name, exclude=exclude):
        time.sleep(0.05)
    for pid in stale_uxplay_pids(name, exclude=exclude):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and stale_uxplay_pids(name, exclude=exclude):
        time.sleep(0.05)
