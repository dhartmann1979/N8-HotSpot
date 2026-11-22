"""Site icons of the link menu: origin rules, SSRF guard, image checks and the SQLite cache (network mocked)."""
import tempfile
import unittest
from pathlib import Path

try:
    from dashboard import siteicons as si          # HBlink4-FreeRadioID
except ImportError:                                  # N8-HotSpot
    from n8hotspot import siteicons as si

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


class TestSiteIcons(unittest.TestCase):
    def setUp(self):
        self.orig_get = si._get
        self.cache = si.IconCache(Path(tempfile.mkdtemp()) / "icons.db")

    def tearDown(self):
        si._get = self.orig_get

    def test_origin_rules(self):
        self.assertEqual(si.origin_for("https://Example.org/a/b?c"), "https://example.org")
        for bad in ("ftp://x.org/", "https://user:pw@x.org/", "https://x.org:8443/", "javascript:alert(1)", "/local"):
            self.assertIsNone(si.origin_for(bad), bad)
        self.assertEqual(si.key_for("https://example.org/x"), si.key_for("https://example.org/y"))

    def test_private_targets_are_not_fetched(self):
        for url in ("http://127.0.0.1/", "http://192.168.1.10/", "http://[::1]/", "http://10.0.0.1/favicon.ico"):
            self.assertFalse(si._public_target(url), url)

    def test_image_checks(self):
        self.assertEqual(si._image_type(PNG), "image/png")
        self.assertEqual(si._image_type(b"<svg xmlns='x'><circle r='3'/></svg>"), "image/svg+xml")
        self.assertEqual(si._image_type(b"<svg onload='alert(1)'></svg>"), "")
        self.assertEqual(si._image_type(b"<html>nope</html>"), "")

    def test_cache_hit_and_miss(self):
        calls = []
        def fake(url, accept):
            calls.append(url)
            return (PNG, "") if url.endswith("/favicon.ico") else (None, "404")
        si._get = fake
        self.assertTrue(self.cache.refresh_one("https://example.org/page"))
        key = si.key_for("https://example.org")
        self.assertEqual(self.cache.cached(key)["content_type"], "image/png")
        n = len(calls)
        self.assertTrue(self.cache.refresh_one("https://example.org/other"))
        self.assertEqual(len(calls), n)                      # served from the cache

    def test_icon_advertised_in_page(self):
        def fake(url, accept):
            if url.endswith("/"):
                return b'<html><head><link rel="icon" href="/static/i.png"></head></html>', ""
            if url.endswith("/static/i.png"):
                return PNG, ""
            return None, "404"
        si._get = fake
        self.assertTrue(self.cache.refresh_one("https://example.net/"))

    def test_no_icon_is_remembered(self):
        si._get = lambda url, accept: (None, "404")
        self.assertFalse(self.cache.refresh_one("https://none.example/"))
        st = self.cache.status(si.key_for("https://none.example/"))
        self.assertFalse(st["ok"])


if __name__ == "__main__":
    unittest.main()
