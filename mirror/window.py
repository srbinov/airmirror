from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Adw, Gdk, GLib, Gtk

from mirror.command import Settings
from mirror.config import cache_dir, load_settings, save_settings
from mirror.logs import Event, EventKind, TrackInfo, parse_metadata_text
from mirror.service import UxPlayNotFoundError, UxPlayService
from mirror.video import VideoSurface


class MirrorWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="Mirror")
        self.set_default_size(1020, 660)
        self.settings = load_settings()
        self.video = VideoSurface()
        self.service = UxPlayService(self._on_uxplay_event)
        self._client: str | None = None
        self._did_fullscreen = False
        self._applying_ui = False
        self._has_video = False
        self._poll_id = 0
        self._cover_path = cache_dir() / "cover.jpg"
        self._meta_path = cache_dir() / "now-playing.txt"

        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .video-stage { background: #0b0b0c; }
            .now-playing { background: #121214; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        toasts = Adw.ToastOverlay()
        self._toasts = toasts
        split = Adw.NavigationSplitView(
            min_sidebar_width=188,
            sidebar_width_fraction=0.22,
        )
        split.set_sidebar(Adw.NavigationPage(child=self._build_sidebar(), title="Mirror"))
        split.set_content(Adw.NavigationPage(child=self._build_content(), title="Receiver"))
        toasts.set_child(split)
        self.set_content(toasts)

        self.connect("close-request", self._on_close)
        self._select_sidebar(0)
        self._set_chrome(running=False)

    def _build_sidebar(self) -> Gtk.Widget:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_title_widget(Adw.WindowTitle(title="Mirror", subtitle="AirPlay"))
        toolbar.add_top_bar(header)

        self._list = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.SINGLE,
            css_classes=["navigation-sidebar"],
            vexpand=True,
        )
        self._list.append(_nav_row("Receiver", "video-display-symbolic"))
        self._list.append(_nav_row("Settings", "emblem-system-symbolic"))
        self._list.connect("row-selected", self._on_sidebar)
        toolbar.set_content(self._list)
        return toolbar

    def _build_content(self) -> Gtk.Widget:
        toolbar = Adw.ToolbarView()
        self._header = Adw.HeaderBar()
        self._header.set_show_start_title_buttons(False)
        self._title = Adw.WindowTitle(
            title=self.settings.name,
            subtitle="Receiver is off",
        )
        self._header.set_title_widget(self._title)

        self._start_btn = Gtk.Button(label="Start")
        self._start_btn.add_css_class("suggested-action")
        self._start_btn.connect("clicked", lambda *_: self.start_receiver())
        self._stop_btn = Gtk.Button(label="Stop")
        self._stop_btn.add_css_class("destructive-action")
        self._stop_btn.connect("clicked", lambda *_: self.stop_receiver())
        self._header.pack_end(self._start_btn)
        self._header.pack_end(self._stop_btn)
        toolbar.add_top_bar(self._header)

        self._stack = Gtk.Stack(hexpand=True, vexpand=True)
        self._stack.add_named(self._build_receiver(), "receiver")
        self._stack.add_named(self._build_settings(), "settings")
        toolbar.set_content(self._stack)
        return toolbar

    def _build_receiver(self) -> Gtk.Widget:
        overlay = Gtk.Overlay()
        overlay.set_child(self.video.picture)

        self._idle_layer = Gtk.Box(hexpand=True, vexpand=True)
        self._idle_layer.add_css_class("background")
        self._status = Adw.StatusPage(
            icon_name="app.mirror.Mirror",
            title="Receiver is off",
            description="Start to appear on iPhone and Mac as an AirPlay screen.",
            hexpand=True,
            vexpand=True,
        )
        self._idle_layer.append(self._status)
        overlay.add_overlay(self._idle_layer)

        self._now_layer = self._build_now_playing()
        self._now_layer.set_visible(False)
        overlay.add_overlay(self._now_layer)
        return overlay

    def _build_now_playing(self) -> Gtk.Widget:
        layer = Gtk.Box(hexpand=True, vexpand=True, css_classes=["now-playing"])
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            hexpand=True,
            vexpand=True,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.CENTER,
            margin_start=32,
            margin_end=32,
        )
        self._cover = Gtk.Picture(
            content_fit=Gtk.ContentFit.CONTAIN,
            can_shrink=True,
        )
        self._cover.set_size_request(280, 280)
        self._track = Gtk.Label(
            wrap=True,
            justify=Gtk.Justification.CENTER,
            css_classes=["title-1"],
        )
        self._artist = Gtk.Label(
            wrap=True,
            justify=Gtk.Justification.CENTER,
            css_classes=["title-3"],
        )
        self._album = Gtk.Label(
            wrap=True,
            justify=Gtk.Justification.CENTER,
            css_classes=["dim-label"],
        )
        box.append(self._cover)
        box.append(self._track)
        box.append(self._artist)
        box.append(self._album)
        layer.append(box)
        return layer

    def _build_settings(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(
            title="This computer",
            description="These apply the next time you start the receiver.",
        )

        self._name_row = Adw.EntryRow(title="Name")
        self._name_row.set_text(self.settings.name)
        self._name_row.connect("changed", self._on_settings_changed)
        group.add(self._name_row)

        self._password_row = Adw.PasswordEntryRow(title="Password")
        self._password_row.set_text(self.settings.password)
        self._password_row.set_show_apply_button(False)
        self._password_row.connect("changed", self._on_settings_changed)
        group.add(self._password_row)

        self._fs_row = Adw.SwitchRow(
            title="Full screen when someone connects",
            subtitle="Uses this window, not a second video window",
            active=self.settings.fullscreen_on_connect,
        )
        self._fs_row.connect("notify::active", self._on_settings_changed)
        group.add(self._fs_row)

        adjustment = Gtk.Adjustment(
            lower=0,
            upper=1,
            step_increment=0.05,
            page_increment=0.1,
            value=self.settings.volume,
        )
        self._volume_row = Adw.SpinRow(
            title="Starting volume",
            subtitle="Sent to the iPhone or Mac when it connects",
            adjustment=adjustment,
            digits=2,
        )
        self._volume_row.connect("notify::value", self._on_settings_changed)
        group.add(self._volume_row)

        page.add(group)
        return page

    def _on_sidebar(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        page = "receiver" if row.get_index() == 0 else "settings"
        self._stack.set_visible_child_name(page)

    def _select_sidebar(self, index: int) -> None:
        row = self._list.get_row_at_index(index)
        if row is not None:
            self._list.select_row(row)

    def _on_settings_changed(self, *_args) -> None:
        if self._applying_ui:
            return
        name = self._name_row.get_text().strip() or "Mirror"
        password = self._password_row.get_text()
        if password and len(password) < 6:
            self._password_row.set_title("Password (need 6+ characters)")
            password = ""
        else:
            self._password_row.set_title("Password")
        self.settings = Settings(
            name=name,
            password=password,
            fullscreen_on_connect=self._fs_row.get_active(),
            volume=float(self._volume_row.get_value()),
        )
        save_settings(self.settings)
        if not self.service.running:
            self._title.set_title(self.settings.name)

    def start_receiver(self) -> None:
        embed = True
        port: int | None = None
        self._has_video = False
        try:
            port = self.video.prepare(
                on_frame=self._on_video_frame,
                on_error=self._toast,
            )
        except (RuntimeError, GLib.Error) as exc:
            embed = False
            self.video.shutdown()
            self._toast(str(exc))
        try:
            self.service.start(
                self.settings,
                port,
                embed=embed,
                cover_path=self._cover_path,
                metadata_path=self._meta_path,
            )
        except UxPlayNotFoundError as exc:
            self.video.shutdown()
            self._toast(str(exc))
            return
        self._client = None
        self._set_chrome(running=True)
        waiting = (
            f"On iPhone or Mac, open Control Center, tap Screen Mirroring "
            f"or play a song, and choose {self.settings.name}."
        )
        self._show_status("Waiting for AirPlay", waiting)
        self._start_media_poll()

    def stop_receiver(self) -> None:
        self._stop_media_poll()
        self.service.stop()
        self.video.shutdown()
        self._client = None
        self._has_video = False
        if self._did_fullscreen:
            self.unfullscreen()
            self._did_fullscreen = False
        self._set_chrome(running=False)
        self._show_status(
            "Receiver is off",
            "Start to appear on iPhone and Mac as an AirPlay screen.",
        )

    def _on_uxplay_event(self, event: Event) -> None:
        if event.kind == EventKind.CLIENT:
            self._client = event.client
            self._title.set_subtitle(f"{event.client} connected")
            return
        if event.kind == EventKind.MIRRORING:
            self._show_video()
            return
        if event.kind == EventKind.AUDIO:
            self._refresh_now_playing()
            return
        if event.kind == EventKind.CLOSED:
            if self._did_fullscreen:
                self.unfullscreen()
                self._did_fullscreen = False
            self._client = None
            self._has_video = False
            if self.service.running:
                self._show_status(
                    "Waiting for AirPlay",
                    f"On iPhone or Mac, open Control Center, tap Screen Mirroring "
                    f"or play a song, and choose {self.settings.name}.",
                )
                self._title.set_subtitle("Waiting for AirPlay")
            else:
                self.stop_receiver()
            return
        if event.kind == EventKind.ERROR:
            self._toast(event.message or "UxPlay reported an error")

    def _on_video_frame(self) -> None:
        if self._has_video:
            return
        self._has_video = True
        GLib.idle_add(self._show_video)

    def _show_video(self) -> None:
        self._has_video = True
        self._idle_layer.set_visible(False)
        self._now_layer.set_visible(False)
        label = f"{self._client} · mirroring" if self._client else "Mirroring"
        self._title.set_subtitle(label)
        if self.settings.fullscreen_on_connect and not self.is_fullscreen():
            self.fullscreen()
            self._did_fullscreen = True

    def _show_now_playing(self, info: TrackInfo) -> None:
        if self._has_video:
            return
        self._idle_layer.set_visible(False)
        self._now_layer.set_visible(True)
        self._track.set_label(info.title or "Now playing")
        self._artist.set_label(info.artist)
        self._album.set_label(info.album)
        subtitle = info.title or "Playing audio"
        if info.artist:
            subtitle = f"{info.artist} · {info.title}" if info.title else info.artist
        self._title.set_subtitle(subtitle)
        self._reload_cover()

    def _show_status(self, title: str, description: str) -> None:
        self._status.set_title(title)
        self._status.set_description(description)
        self._idle_layer.set_visible(True)
        self._now_layer.set_visible(False)

    def _start_media_poll(self) -> None:
        self._stop_media_poll()
        self._poll_id = GLib.timeout_add(700, self._refresh_now_playing)

    def _stop_media_poll(self) -> None:
        if self._poll_id:
            GLib.source_remove(self._poll_id)
            self._poll_id = 0

    def _refresh_now_playing(self) -> bool:
        if self._has_video or not self.service.running:
            return True
        info = TrackInfo()
        if self._meta_path.is_file():
            info = parse_metadata_text(
                self._meta_path.read_text(encoding="utf-8", errors="replace")
            )
        cover_ready = (
            self._cover_path.is_file() and self._cover_path.stat().st_size > 200
        )
        if info.present or cover_ready:
            self._show_now_playing(info)
        return True

    def _reload_cover(self) -> None:
        if not self._cover_path.is_file() or self._cover_path.stat().st_size < 200:
            return
        try:
            self._cover.set_paintable(
                Gdk.Texture.new_from_filename(str(self._cover_path))
            )
        except GLib.Error:
            return

    def _set_chrome(self, *, running: bool) -> None:
        self._start_btn.set_visible(not running)
        self._stop_btn.set_visible(running)
        self._title.set_title(self.settings.name)
        self._title.set_subtitle("Waiting for AirPlay" if running else "Receiver is off")

    def _toast(self, message: str) -> None:
        self._toasts.add_toast(Adw.Toast(title=message, timeout=6))

    def _on_close(self, *_args) -> bool:
        self.stop_receiver()
        return False


def _nav_row(title: str, icon_name: str) -> Adw.ActionRow:
    return Adw.ActionRow(title=title, icon_name=icon_name)
