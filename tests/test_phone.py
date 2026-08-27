import unittest

from mirror.phone import (
    StreamKind,
    bottom_right_origin,
    classify_stream,
    clamp_origin,
    default_frame_height,
    fit_frame_height,
    frame_layout,
    glass_size,
    hit_resize_edge,
    resize_origin_and_height,
    should_open_phone_shell,
    should_show_phone_frame,
)


class ClassifyStreamTest(unittest.TestCase):
    def test_portrait_iphone_uses_upright_phone(self):
        self.assertEqual(classify_stream(1170, 2532), StreamKind.PORTRAIT)

    def test_landscape_iphone_uses_sideways_phone(self):
        self.assertEqual(classify_stream(2532, 1170), StreamKind.LANDSCAPE)

    def test_mac_widescreen_skips_the_phone(self):
        self.assertEqual(classify_stream(1920, 1080), StreamKind.WIDESCREEN)

    def test_unknown_size_defaults_to_portrait(self):
        self.assertEqual(classify_stream(0, 0), StreamKind.PORTRAIT)


class ShouldShowPhoneFrameTest(unittest.TestCase):
    def test_portrait_stream_uses_phone_when_enabled(self):
        self.assertTrue(
            should_show_phone_frame(
                enabled=True,
                fullscreen=False,
                width=1170,
                height=2532,
            )
        )

    def test_fullscreen_wins_over_phone_frame(self):
        self.assertFalse(
            should_show_phone_frame(
                enabled=True,
                fullscreen=True,
                width=1170,
                height=2532,
            )
        )

    def test_disabled_setting_stays_in_the_window(self):
        self.assertFalse(
            should_show_phone_frame(
                enabled=False,
                fullscreen=False,
                width=1170,
                height=2532,
            )
        )

    def test_widescreen_stays_in_the_window(self):
        self.assertFalse(
            should_show_phone_frame(
                enabled=True,
                fullscreen=False,
                width=1920,
                height=1080,
            )
        )


class ShouldOpenPhoneShellTest(unittest.TestCase):
    def test_stop_does_not_open_the_phone(self):
        self.assertFalse(
            should_open_phone_shell(
                receiver_running=False,
                enabled=True,
                fullscreen=False,
                width=1170,
                height=2532,
            )
        )

    def test_unknown_size_while_stopped_stays_in_the_window(self):
        self.assertFalse(
            should_open_phone_shell(
                receiver_running=False,
                enabled=True,
                fullscreen=False,
                width=0,
                height=0,
            )
        )

    def test_live_portrait_stream_still_opens_the_phone(self):
        self.assertTrue(
            should_open_phone_shell(
                receiver_running=True,
                enabled=True,
                fullscreen=False,
                width=1170,
                height=2532,
            )
        )


class FrameLayoutTest(unittest.TestCase):
    def test_portrait_keeps_the_native_screen_hole(self):
        width, height, rect = frame_layout(StreamKind.PORTRAIT, max_height=1024)
        self.assertEqual((width, height), (516, 1024))
        self.assertEqual(rect, (33, 32, 450, 960))

    def test_landscape_rotates_the_screen_hole(self):
        width, height, rect = frame_layout(StreamKind.LANDSCAPE, max_height=516)
        self.assertEqual((width, height), (1024, 516))
        self.assertEqual(rect, (32, 33, 960, 450))


class GlassSizeTest(unittest.TestCase):
    def test_portrait_fits_the_short_side(self):
        width, height = glass_size(1170, 2532, max_short=360)
        self.assertEqual(width, 360)
        self.assertEqual(height, round(360 * 2532 / 1170))

    def test_landscape_fits_the_short_side(self):
        width, height = glass_size(2532, 1170, max_short=360)
        self.assertEqual(height, 360)
        self.assertEqual(width, round(360 * 2532 / 1170))


class SpawnGeometryTest(unittest.TestCase):
    def test_default_height_is_thirty_percent_smaller_than_before(self):
        legacy = max(420, int(1080 * 0.82))
        spawn = default_frame_height(1080)
        self.assertAlmostEqual(spawn / legacy, 0.7, delta=0.02)

    def test_bottom_right_leaves_a_margin_above_the_dock_edge(self):
        x, y = bottom_right_origin(1920, 1040, 312, 620, margin=16)
        self.assertEqual((x, y), (1920 - 312 - 16, 1040 - 620 - 16))

    def test_clamp_keeps_the_phone_on_screen(self):
        self.assertEqual(clamp_origin(800, 600, 300, 500, 900, 400), (500, 100))

    def test_fit_shrinks_a_landscape_frame_to_the_work_area(self):
        height = fit_frame_height(StreamKind.LANDSCAPE, 900, 800, 500, margin=16)
        width, fitted, _rect = frame_layout(StreamKind.LANDSCAPE, max_height=height)
        self.assertLessEqual(width, 800 - 32)
        self.assertLessEqual(fitted, 500 - 32)

    def test_corner_hit_uses_the_bezel_grip(self):
        self.assertEqual(hit_resize_edge(2, 2, 300, 600), "nw")
        self.assertEqual(hit_resize_edge(150, 300, 300, 600), None)

    def test_northwest_resize_keeps_the_bottom_right_pinned(self):
        x, y, height = resize_origin_and_height(100, 100, 200, 400, -20, -40, "nw")
        width = round(200 * height / 400)
        self.assertEqual((x + width, y + height), (300, 500))


if __name__ == "__main__":
    unittest.main()
