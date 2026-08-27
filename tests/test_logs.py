import unittest

from mirror.logs import EventKind, parse_uxplay_line


class ParseUxplayLineTest(unittest.TestCase):
    def test_ignores_unrelated_output(self):
        self.assertIsNone(parse_uxplay_line("Initialized server socket(s)"))

    def test_extracts_client_from_connection_request(self):
        event = parse_uxplay_line(
            "connection request from iPhone12,3 (iPhone12,3) "
            "with deviceID = bb:bb:bb:bb:bb:bb"
        )

        self.assertEqual(event.kind, EventKind.CLIENT)
        self.assertEqual(event.client, "iPhone12,3")

    def test_mirroring_has_started(self):
        event = parse_uxplay_line("raop_rtp_mirror starting mirroring")

        self.assertEqual(event.kind, EventKind.MIRRORING)

    def test_streaming_started_is_mirroring(self):
        event = parse_uxplay_line("Begin streaming to GStreamer video pipeline")

        self.assertEqual(event.kind, EventKind.MIRRORING)

    def test_connection_closed_returns_to_idle(self):
        event = parse_uxplay_line("Connection closed on socket 3652")

        self.assertEqual(event.kind, EventKind.CLOSED)

    def test_error_lines(self):
        event = parse_uxplay_line(
            "*** ERROR: httpd error in select: 10038"
        )

        self.assertEqual(event.kind, EventKind.ERROR)
        self.assertIn("httpd error", event.message)

    def test_audio_metadata_header(self):
        event = parse_uxplay_line("====================Audio Metadata==================")

        self.assertEqual(event.kind, EventKind.AUDIO)


if __name__ == "__main__":
    unittest.main()
