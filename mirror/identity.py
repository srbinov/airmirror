"""Set process identity before GTK starts so the taskbar can find our .desktop icon."""

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

APP_ID = "app.mirror.Mirror"
APP_NAME = "Mirror"

_applied = False


def apply() -> None:
    global _applied
    if _applied:
        return
    GLib.set_prgname(APP_ID)
    GLib.set_application_name(APP_NAME)
    _applied = True
