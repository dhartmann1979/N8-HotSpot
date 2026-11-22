import unittest
from n8hotspot.n8theme import normalize, ThemeError, DEFAULT


class TestN8Theme(unittest.TestCase):
    def test_defaults_and_clamp(self):
        self.assertEqual(normalize(None), DEFAULT)
        t = normalize({"preset": "ocean", "accent": "#AABBCC", "glow": 999, "glass": -5, "radius": "12", "blur": "false"})
        self.assertEqual((t["preset"], t["accent"], t["glow"], t["glass"], t["radius"], t["blur"]), ("ocean", "#aabbcc", 150, 0, 12, False))

    def test_bad_colour(self):
        self.assertEqual(normalize({"accent": "red"})["accent"], "")
        with self.assertRaises(ThemeError):
            normalize({"accent": "url(javascript:x)"}, strict=True)

    def test_legacy_presets(self):
        self.assertEqual(normalize({"preset": "light"})["preset"], "daylight")
        self.assertEqual(normalize({"preset": "midnight"})["preset"], "n8")


if __name__ == "__main__":
    unittest.main()
