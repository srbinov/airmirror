import unittest

from mirror.command import Settings, build_uxplay_argv


class BuildUxplayArgvTest(unittest.TestCase):
    def test_names_the_receiver_without_hostname_suffix(self):
        argv = build_uxplay_argv(
            Settings(name="Living Room", password="", volume=1.0),
            rtp_port=5004,
        )

        self.assertEqual(argv[0], "uxplay")
        self.assertIn("-n", argv)
        self.assertEqual(argv[argv.index("-n") + 1], "Living Room")
        self.assertIn("-nh", argv)

    def test_forwards_h264_to_localhost_rtp_port(self):
        argv = build_uxplay_argv(Settings(name="Mirror"), rtp_port=61234)

        vrtp = argv[argv.index("-vrtp") + 1]
        self.assertIn("udpsink host=127.0.0.1 port=61234", vrtp)
        self.assertIn("config-interval=1", vrtp)

    def test_omits_password_flag_when_empty(self):
        argv = build_uxplay_argv(Settings(name="Mirror", password=""), rtp_port=9)

        self.assertNotIn("-pw", argv)

    def test_passes_password_and_volume(self):
        argv = build_uxplay_argv(
            Settings(name="Mirror", password="secret", volume=0.4),
            rtp_port=9,
        )

        self.assertEqual(argv[argv.index("-pw") + 1], "secret")
        self.assertEqual(argv[argv.index("-vol") + 1], "0.40")

    def test_inhibits_screensaver_while_running(self):
        argv = build_uxplay_argv(Settings(name="Mirror"), rtp_port=9)

        self.assertEqual(argv[argv.index("-scrsv") + 1], "1")

    def test_can_skip_embedded_video(self):
        argv = build_uxplay_argv(Settings(name="Mirror"), embed=False)

        self.assertNotIn("-vrtp", argv)

    def test_writes_cover_art_and_metadata_files(self):
        argv = build_uxplay_argv(
            Settings(name="Mirror"),
            rtp_port=9,
            cover_path="/tmp/mirror-cover.jpg",
            metadata_path="/tmp/mirror-meta.txt",
        )

        self.assertEqual(argv[argv.index("-ca") + 1], "/tmp/mirror-cover.jpg")
        self.assertEqual(argv[argv.index("-md") + 1], "/tmp/mirror-meta.txt")


if __name__ == "__main__":
    unittest.main()
