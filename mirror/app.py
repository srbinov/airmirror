from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gst", "1.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, Gst, Gtk

from mirror.identity import APP_ID, apply as apply_identity
from mirror.window import MirrorWindow

ICON_NAME = APP_ID
_ICONS = Path(__file__).resolve().parent.parent / "data" / "icons" / "hicolor"


class MirrorApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self.connect("startup", self._on_startup)
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

    def _on_startup(self, *_args) -> None:
        Gst.init(None)
        display = Gdk.Display.get_default()
        if display is not None and _ICONS.is_dir():
            theme = Gtk.IconTheme.get_for_display(display)
            theme.add_search_path(str(_ICONS))
        Gtk.Window.set_default_icon_name(ICON_NAME)

    def _on_activate(self, *_args) -> None:
        main = next((w for w in self.get_windows() if isinstance(w, MirrorWindow)), None)
        if main is None:
            main = MirrorWindow(self)
            main.set_icon_name(ICON_NAME)
        main.present_for_activate()

    def _on_shutdown(self, *_args) -> None:
        for window in self.get_windows():
            if isinstance(window, MirrorWindow):
                window.stop_receiver()


def main() -> int:
    apply_identity()
    app = MirrorApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
