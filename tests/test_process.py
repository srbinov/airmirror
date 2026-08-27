import unittest

from mirror.process import is_uxplay_instance


class IsUxplayInstanceTest(unittest.TestCase):
    def test_matches_named_receiver(self):
        self.assertTrue(
            is_uxplay_instance(
                ["/usr/bin/uxplay", "-n", "Mirror", "-nh"],
                name="Mirror",
            )
        )

    def test_ignores_other_receiver_name(self):
        self.assertFalse(
            is_uxplay_instance(
                ["/usr/bin/uxplay", "-n", "Living Room"],
                name="Mirror",
            )
        )

    def test_matches_stdbuf_wrapper(self):
        self.assertTrue(
            is_uxplay_instance(
                ["stdbuf", "-oL", "-eL", "/usr/bin/uxplay", "-n", "Mirror"],
                name="Mirror",
            )
        )

    def test_any_uxplay_when_name_omitted(self):
        self.assertTrue(is_uxplay_instance(["/usr/bin/uxplay", "-n", "X"]))
        self.assertFalse(is_uxplay_instance(["python3", "-m", "mirror"]))
