from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from gi.repository import GLib

from mirror.command import Settings, build_uxplay_argv
from mirror.config import cache_dir
from mirror.logs import Event, EventKind, parse_uxplay_line
from mirror.process import reap_stale_uxplay


class UxPlayNotFoundError(RuntimeError):
    pass


class UxPlayService:
    def __init__(self, on_event: Callable[[Event], None]) -> None:
        self._on_event = on_event
        self._proc: subprocess.Popen[str] | None = None
        self._stopping = False
        self._log_file = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(
        self,
        settings: Settings,
        rtp_port: int | None = None,
        *,
        embed: bool = True,
        cover_path: Path | None = None,
        metadata_path: Path | None = None,
    ) -> None:
        if self.running:
            return
        binary = shutil.which("uxplay")
        if not binary:
            raise UxPlayNotFoundError(
                "UxPlay is not installed. Install it with: sudo apt install uxplay"
            )
        reap_stale_uxplay()
        self._stopping = False
        argv = build_uxplay_argv(
            settings,
            rtp_port,
            binary=binary,
            embed=embed,
            cover_path=cover_path,
            metadata_path=metadata_path,
        )
        if shutil.which("stdbuf"):
            argv = ["stdbuf", "-oL", "-eL", *argv]
        log_path = cache_dir() / "uxplay.log"
        self._log_file = log_path.open("w", encoding="utf-8")
        self._proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        thread = threading.Thread(target=self._read_output, daemon=True)
        thread.start()

    def stop(self) -> None:
        proc = self._proc
        if proc is None:
            return
        self._stopping = True
        self._kill_group(proc)
        self._proc = None
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None

    def _kill_group(self, proc: subprocess.Popen[str]) -> None:
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            proc.wait(timeout=2)

    def _read_output(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            if self._log_file is not None:
                self._log_file.write(line)
                self._log_file.flush()
            event = parse_uxplay_line(line)
            if event is not None:
                GLib.idle_add(self._on_event, event)
        code = proc.wait()
        self._proc = None
        if self._stopping:
            return
        if code != 0:
            GLib.idle_add(
                self._on_event,
                Event(EventKind.ERROR, message=f"UxPlay exited ({code})"),
            )
        else:
            GLib.idle_add(self._on_event, Event(EventKind.CLOSED))
