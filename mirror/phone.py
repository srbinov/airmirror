from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Graphene, Gsk, Gtk


class StreamKind(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    WIDESCREEN = "widescreen"


_LANDSCAPE_PHONE_RATIO = 1.9
_DEFAULT_SHORT = 360
_FRAME_PATH = Path(__file__).resolve().parent.parent / "data" / "iphone-15.png"
_NATIVE_W = 516
_NATIVE_H = 1024
_SCREEN = (33, 32, 450, 960)
_FRAME_BBOX = (21, 23, 474, 977)
_LEGACY_HEIGHT_RATIO = 0.82
_SPAWN_SCALE = 0.70
_MARGIN = 16
_EDGE = 14
_MIN_HEIGHT = 280
_EDGE_CURSORS = {
    "n": "n-resize",
    "s": "s-resize",
    "e": "e-resize",
    "w": "w-resize",
    "ne": "ne-resize",
    "nw": "nw-resize",
    "se": "se-resize",
    "sw": "sw-resize",
}

_CSS = b"""
window.phone-shell-window,
window.phone-shell-window.background {
  background-color: transparent;
  background-image: none;
}

window.phone-shell-window > overlay,
window.phone-shell-window > fixed {
  background-color: transparent;
}
"""

_css_loaded = False


def classify_stream(width: int, height: int) -> StreamKind:
    if width <= 0 or height <= 0:
        return StreamKind.PORTRAIT
    if height >= width:
        return StreamKind.PORTRAIT
    if width / height >= _LANDSCAPE_PHONE_RATIO:
        return StreamKind.LANDSCAPE
    return StreamKind.WIDESCREEN


def should_show_phone_frame(
    *,
    enabled: bool,
    fullscreen: bool,
    width: int,
    height: int,
) -> bool:
    if not enabled or fullscreen:
        return False
    return classify_stream(width, height) is not StreamKind.WIDESCREEN


def should_open_phone_shell(
    *,
    receiver_running: bool,
    enabled: bool,
    fullscreen: bool,
    width: int,
    height: int,
) -> bool:
    if not receiver_running:
        return False
    return should_show_phone_frame(
        enabled=enabled,
        fullscreen=fullscreen,
        width=width,
        height=height,
    )


def glass_size(width: int, height: int, *, max_short: int = _DEFAULT_SHORT) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        width, height = 393, 852
    if height >= width:
        scale = max_short / width
    else:
        scale = max_short / height
    return round(width * scale), round(height * scale)


def frame_layout(kind: StreamKind, *, max_height: int) -> tuple[int, int, tuple[int, int, int, int]]:
    if kind is StreamKind.LANDSCAPE:
        native_w, native_h = _NATIVE_H, _NATIVE_W
        sx, sy, sw, sh = _SCREEN
        screen = (_NATIVE_H - sy - sh, sx, sh, sw)
    else:
        native_w, native_h = _NATIVE_W, _NATIVE_H
        screen = _SCREEN
    scale = max_height / native_h
    window = (round(native_w * scale), round(native_h * scale))
    sx, sy, sw, sh = screen
    rect = (
        round(sx * scale),
        round(sy * scale),
        round(sw * scale),
        round(sh * scale),
    )
    return window[0], window[1], rect


def default_frame_height(area_height: int) -> int:
    return max(_MIN_HEIGHT, int(area_height * _LEGACY_HEIGHT_RATIO * _SPAWN_SCALE))


def clamp_origin(
    container_w: int,
    container_h: int,
    child_w: int,
    child_h: int,
    x: int,
    y: int,
) -> tuple[int, int]:
    max_x = max(0, container_w - child_w)
    max_y = max(0, container_h - child_h)
    return max(0, min(x, max_x)), max(0, min(y, max_y))


def bottom_right_origin(
    container_w: int,
    container_h: int,
    child_w: int,
    child_h: int,
    *,
    margin: int = _MARGIN,
) -> tuple[int, int]:
    return clamp_origin(
        container_w,
        container_h,
        child_w,
        child_h,
        container_w - child_w - margin,
        container_h - child_h - margin,
    )


def fit_frame_height(
    kind: StreamKind,
    desired_height: int,
    container_w: int,
    container_h: int,
    *,
    margin: int = _MARGIN,
) -> int:
    usable_w = max(1, container_w - 2 * margin)
    usable_h = max(1, container_h - 2 * margin)
    height = max(1, min(desired_height, usable_h))
    width, height, _rect = frame_layout(kind, max_height=height)
    if width <= usable_w and height <= usable_h:
        return height
    scale = min(usable_w / max(1, width), usable_h / max(1, height))
    return max(1, round(height * scale))


def hit_resize_edge(
    x: float,
    y: float,
    width: int,
    height: int,
    *,
    grip: int = _EDGE,
) -> str | None:
    if width <= 0 or height <= 0:
        return None
    left = x <= grip
    right = x >= width - grip
    top = y <= grip
    bottom = y >= height - grip
    if top and left:
        return "nw"
    if top and right:
        return "ne"
    if bottom and left:
        return "sw"
    if bottom and right:
        return "se"
    if top:
        return "n"
    if bottom:
        return "s"
    if left:
        return "w"
    if right:
        return "e"
    return None


def resize_origin_and_height(
    start_x: int,
    start_y: int,
    start_w: int,
    start_h: int,
    dx: float,
    dy: float,
    edge: str,
) -> tuple[int, int, int]:
    if start_w <= 0 or start_h <= 0:
        return start_x, start_y, start_h
    flags = set(edge)
    scales: list[float] = []
    if "e" in flags:
        scales.append((start_w + dx) / start_w)
    if "w" in flags:
        scales.append((start_w - dx) / start_w)
    if "s" in flags:
        scales.append((start_h + dy) / start_h)
    if "n" in flags:
        scales.append((start_h - dy) / start_h)
    scale = sum(scales) / len(scales) if scales else 1.0
    new_h = max(1, round(start_h * max(0.05, scale)))
    new_w = max(1, round(start_w * new_h / start_h))
    x = start_x + start_w - new_w if "w" in flags else start_x
    y = start_y + start_h - new_h if "n" in flags else start_y
    return x, y, new_h


def _load_css() -> None:
    global _css_loaded
    if _css_loaded:
        return
    display = Gdk.Display.get_default()
    if display is None:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(_CSS)
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER,
    )
    _css_loaded = True


class RoundedPicture(Gtk.Picture):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._radius = 42.0

    def set_corner_radius(self, radius: float) -> None:
        self._radius = radius
        self.queue_draw()

    def do_snapshot(self, snapshot: Gtk.Snapshot) -> None:
        width = float(self.get_width())
        height = float(self.get_height())
        if width <= 0 or height <= 0:
            return
        rect = Graphene.Rect().init(0, 0, width, height)
        rounded = Gsk.RoundedRect()
        rounded.init_from_rect(rect, self._radius)
        snapshot.push_rounded_clip(rounded)
        Gtk.Picture.do_snapshot(self, snapshot)
        snapshot.pop()


class PhoneWindow(Gtk.Window):
    def __init__(self, app: Gtk.Application, on_dismiss: Callable[[], None]) -> None:
        super().__init__(application=app, title="iPhone")
        self._on_dismiss = on_dismiss
        self._portrait_texture: Gdk.Texture | None = None
        self._landscape_texture: Gdk.Texture | None = None
        self._kind = StreamKind.PORTRAIT
        self._paintable: Gdk.Paintable | None = None
        self._phone_x = 0
        self._phone_y = 0
        self._phone_w = 0
        self._phone_h = 0
        self._user_placed = False
        self._user_resized = False
        self._drag_edge: str | None = None
        self._drag_start = (0, 0, 0, 0)
        self.set_decorated(False)
        self.set_resizable(True)
        self.add_css_class("phone-shell-window")
        self.remove_css_class("background")
        _load_css()

        self._video = RoundedPicture(
            content_fit=Gtk.ContentFit.COVER,
            hexpand=False,
            vexpand=False,
        )
        self._frame = Gtk.Picture(
            content_fit=Gtk.ContentFit.FILL,
            hexpand=True,
            vexpand=True,
        )
        self._frame.set_can_target(False)

        self._fixed = Gtk.Fixed()
        self._stage = Gtk.Overlay()
        self._stage.set_child(self._fixed)
        self._stage.add_overlay(self._frame)
        self._root = Gtk.Fixed()
        self.set_child(self._root)

        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)
        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)
        self.connect("close-request", self._on_close)
        self.connect("map", self._on_map)
        self.connect("notify::maximized", self._on_maximized)

    def show_stream(
        self,
        paintable: Gdk.Paintable | None,
        kind: StreamKind,
        width: int,
        height: int,
    ) -> None:
        del width, height
        fresh = not self.get_visible()
        if fresh:
            self._user_placed = False
            self._user_resized = False
        self._paintable = paintable
        self._kind = kind
        self.maximize()
        self.present()
        self._layout_phone()
        GLib.idle_add(self._layout_phone)

    def dismiss(self) -> None:
        self._video.set_paintable(None)
        self._paintable = None
        self._user_placed = False
        self._user_resized = False
        self.set_visible(False)

    def _texture_for(self, kind: StreamKind) -> Gdk.Texture | None:
        if not _FRAME_PATH.is_file():
            return None
        if kind is StreamKind.LANDSCAPE:
            if self._landscape_texture is None:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(_FRAME_PATH))
                rotated = pixbuf.rotate_simple(GdkPixbuf.PixbufRotation.CLOCKWISE)
                self._landscape_texture = Gdk.Texture.new_for_pixbuf(rotated)
            return self._landscape_texture
        if self._portrait_texture is None:
            self._portrait_texture = Gdk.Texture.new_from_filename(str(_FRAME_PATH))
        return self._portrait_texture

    def _area_size(self) -> tuple[int, int]:
        return self.get_width(), self.get_height()

    def _layout_phone(self) -> bool:
        if not self.get_visible():
            return False
        area_w, area_h = self._area_size()
        if area_w <= 1 or area_h <= 1:
            self.maximize()
            return True
        desired = self._phone_h if self._user_resized else default_frame_height(area_h)
        desired = fit_frame_height(
            self._kind,
            max(_MIN_HEIGHT, desired) if not self._user_resized else desired,
            area_w,
            area_h,
        )
        win_w, win_h, (sx, sy, sw, sh) = frame_layout(self._kind, max_height=desired)
        if self._user_placed:
            x, y = clamp_origin(area_w, area_h, win_w, win_h, self._phone_x, self._phone_y)
        else:
            x, y = bottom_right_origin(area_w, area_h, win_w, win_h)
        self._apply_phone_geometry(x, y, win_w, win_h, (sx, sy, sw, sh))
        return False

    def _apply_phone_geometry(
        self,
        x: int,
        y: int,
        win_w: int,
        win_h: int,
        screen: tuple[int, int, int, int],
    ) -> None:
        sx, sy, sw, sh = screen
        self._phone_x, self._phone_y = x, y
        self._phone_w, self._phone_h = win_w, win_h
        self._fixed.set_size_request(win_w, win_h)
        self._stage.set_size_request(win_w, win_h)
        self._frame.set_size_request(win_w, win_h)
        if self._stage.get_parent() is None:
            self._root.put(self._stage, x, y)
        else:
            self._root.move(self._stage, x, y)
        if self._video.get_parent() is None:
            self._fixed.put(self._video, sx, sy)
        else:
            self._fixed.move(self._video, sx, sy)
        self._video.set_size_request(sw, sh)
        self._video.set_paintable(self._paintable)
        self._video.set_corner_radius(min(sw, sh) * 0.12)
        self._frame.set_paintable(self._texture_for(self._kind))
        self._update_input_region()

    def _on_map(self, *_args) -> None:
        self.remove_css_class("background")
        self.maximize()
        GLib.idle_add(self._layout_phone)

    def _on_maximized(self, *_args) -> None:
        if self.is_maximized():
            GLib.idle_add(self._layout_phone)

    def _update_input_region(self) -> bool:
        surface = self.get_surface()
        if surface is None or self._phone_w <= 0 or self._phone_h <= 0:
            return False
        empty = cairo.Region()
        surface.set_opaque_region(empty)
        landscape = self._kind is StreamKind.LANDSCAPE
        native_h = _NATIVE_W if landscape else _NATIVE_H
        scale = self._phone_h / native_h
        bx, by, bw, bh = _FRAME_BBOX
        if landscape:
            bx, by, bw, bh = (_NATIVE_H - by - bh, bx, bh, bw)
        body = cairo.RectangleInt(
            self._phone_x + round(bx * scale),
            self._phone_y + round(by * scale),
            max(1, round(bw * scale)),
            max(1, round(bh * scale)),
        )
        surface.set_input_region(cairo.Region(body))
        return False

    def _local_point(self, x: float, y: float) -> tuple[float, float] | None:
        lx = x - self._phone_x
        ly = y - self._phone_y
        if lx < 0 or ly < 0 or lx > self._phone_w or ly > self._phone_h:
            return None
        return lx, ly

    def _on_motion(self, _controller, x: float, y: float) -> None:
        local = self._local_point(x, y)
        if local is None:
            self.set_cursor(None)
            return
        edge = hit_resize_edge(local[0], local[1], self._phone_w, self._phone_h)
        name = _EDGE_CURSORS.get(edge or "", "grab")
        self.set_cursor(Gdk.Cursor.new_from_name(name))

    def _on_drag_begin(self, _gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        local = self._local_point(x, y)
        if local is None:
            self._drag_edge = None
            return
        self._drag_edge = hit_resize_edge(local[0], local[1], self._phone_w, self._phone_h)
        self._drag_start = (self._phone_x, self._phone_y, self._phone_w, self._phone_h)

    def _on_drag_update(self, _gesture: Gtk.GestureDrag, dx: float, dy: float) -> None:
        start_x, start_y, start_w, start_h = self._drag_start
        if start_w <= 0 or start_h <= 0:
            return
        area_w, area_h = self._area_size()
        if self._drag_edge:
            x, y, height = resize_origin_and_height(
                start_x, start_y, start_w, start_h, dx, dy, self._drag_edge
            )
            height = fit_frame_height(
                self._kind,
                max(_MIN_HEIGHT, height),
                area_w,
                area_h,
            )
            win_w, win_h, rect = frame_layout(self._kind, max_height=height)
            if "w" in set(self._drag_edge):
                x = start_x + start_w - win_w
            if "n" in set(self._drag_edge):
                y = start_y + start_h - win_h
            x, y = clamp_origin(area_w, area_h, win_w, win_h, x, y)
            self._user_resized = True
            self._user_placed = True
            self._apply_phone_geometry(x, y, win_w, win_h, rect)
            return
        x, y = clamp_origin(
            area_w,
            area_h,
            start_w,
            start_h,
            round(start_x + dx),
            round(start_y + dy),
        )
        self._user_placed = True
        self._root.move(self._stage, x, y)
        self._phone_x, self._phone_y = x, y
        self._update_input_region()

    def _on_drag_end(self, *_args) -> None:
        self._drag_edge = None

    def _on_key(self, _controller, keyval: int, _keycode: int, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self._on_close()
            return True
        return False

    def _on_close(self, *_args) -> bool:
        self.dismiss()
        self._on_dismiss()
        return True
