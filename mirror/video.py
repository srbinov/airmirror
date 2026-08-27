from __future__ import annotations

import socket
from collections.abc import Callable

import gi

gi.require_version("Gst", "1.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gst, Gtk


class VideoSurface:
    def __init__(self) -> None:
        self.picture = Gtk.Picture(
            hexpand=True,
            vexpand=True,
            content_fit=Gtk.ContentFit.CONTAIN,
        )
        self.picture.add_css_class("video-stage")
        self.pipeline: Gst.Element | None = None
        self.port = 0
        self._on_frame: Callable[[], None] | None = None
        self._on_error: Callable[[str], None] | None = None

    def prepare(
        self,
        on_frame: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> int:
        self.shutdown()
        self._on_frame = on_frame
        self._on_error = on_error
        if Gst.ElementFactory.find("gtk4paintablesink") is None:
            raise RuntimeError(
                "Missing gstreamer1.0-gtk4. Install it with: sudo apt install gstreamer1.0-gtk4"
            )
        self.port = _free_udp_port()
        description = (
            f"udpsrc address=127.0.0.1 port={self.port} "
            'caps="application/x-rtp, media=video, clock-rate=90000, '
            'encoding-name=H264, payload=96" '
            "! rtph264depay ! h264parse ! decodebin ! videoconvert ! "
            "gtk4paintablesink name=videosink sync=false"
        )
        pipeline = Gst.parse_launch(description)
        sink = pipeline.get_by_name("videosink")
        if sink is None:
            raise RuntimeError("Could not create the video sink")
        paintable = sink.get_property("paintable")
        self.picture.set_paintable(paintable)
        paintable.connect("invalidate-contents", self._emit_frame)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus)
        self.pipeline = pipeline
        pipeline.set_state(Gst.State.PLAYING)
        return self.port

    def shutdown(self) -> None:
        self._on_frame = None
        self._on_error = None
        if self.pipeline is None:
            return
        bus = self.pipeline.get_bus()
        bus.remove_signal_watch()
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.port = 0
        self.picture.set_paintable(None)

    def _emit_frame(self, *_args) -> None:
        if self._on_frame is not None:
            self._on_frame()

    def _on_bus(self, _bus, message) -> None:
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            text = err.message if err is not None else "GStreamer error"
            if debug:
                text = f"{text} ({debug})"
            if self._on_error is not None:
                self._on_error(text)


def _free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
