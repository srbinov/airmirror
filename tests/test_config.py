import tempfile
import unittest
from pathlib import Path

from mirror.command import Settings
from mirror.config import load_settings, save_settings


class ConfigTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            original = Settings(
                name="Studio",
                password="abc",
                fullscreen_on_connect=True,
                phone_frame=False,
                volume=0.25,
            )
            save_settings(original, path)

            loaded = load_settings(path)

            self.assertEqual(loaded, original)

    def test_missing_file_uses_defaults(self):
        loaded = load_settings(Path("/no/such/mirror-settings.json"))

        self.assertEqual(loaded.name, "Mirror")
        self.assertEqual(loaded.password, "")
        self.assertFalse(loaded.fullscreen_on_connect)
        self.assertTrue(loaded.phone_frame)
        self.assertEqual(loaded.volume, 1.0)


if __name__ == "__main__":
    unittest.main()
