import unittest

from mirror.logs import parse_metadata_text


class ParseMetadataTextTest(unittest.TestCase):
    def test_reads_title_artist_album(self):
        info = parse_metadata_text(
            "====================Audio Metadata==================\n"
            "Album: Hands On\n"
            "Artist: Jeff Hamilton Trio\n"
            "Genre: Jazz\n"
            "Title: 3.000 Miles Ago\n"
        )

        self.assertEqual(info.title, "3.000 Miles Ago")
        self.assertEqual(info.artist, "Jeff Hamilton Trio")
        self.assertEqual(info.album, "Hands On")

    def test_empty_when_uxplay_placeholder(self):
        info = parse_metadata_text("no data\n")

        self.assertEqual(info.title, "")
        self.assertEqual(info.artist, "")
