"""Tests for browser.cookie_manager"""

import json
import os
import tempfile
import unittest

from browser.cookie_manager import CookieManager


class TestCookieManager(unittest.TestCase):

    def test_load_from_json_file(self):
        cookies = [
            {"name": "auth_token", "value": "abc123", "domain": ".x.com", "path": "/"},
            {"name": "ct0", "value": "def456", "domain": ".x.com", "path": "/"},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(cookies, f)
            tmp_path = f.name

        try:
            cm = CookieManager()
            loaded = cm.load_from_json(tmp_path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["name"], "auth_token")
        finally:
            os.unlink(tmp_path)

    def test_load_from_netscape_file(self):
        netscape_content = (
            "# Netscape HTTP Cookie File\n"
            ".x.com\tTRUE\t/\tTRUE\t0\tauth_token\tabc123\n"
            ".x.com\tTRUE\t/\tTRUE\t0\tct0\tdef456\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(netscape_content)
            tmp_path = f.name

        try:
            cm = CookieManager()
            loaded = cm.load_from_netscape(tmp_path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["name"], "auth_token")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
