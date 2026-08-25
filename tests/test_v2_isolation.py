"""V2 may add /v2, but V1 routes, gate, and web assets must stay the same."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from server import config
from server.app import app
from server.gate import COOKIE_NAME, sign_cookie


@contextmanager
def override_access_code(code: str):
    old = config.settings
    config.settings = replace(old, access_code=code)
    try:
        yield
    finally:
        config.settings = old

ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


class V2IsolationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, follow_redirects=False)

    def test_v2_is_mounted_before_v1_static(self):
        src = read("server/app.py")
        self.assertLess(src.find("mount_v2(app)"), src.find('app.mount("/", StaticFiles'))

    def test_v1_home_still_redirects_to_kid_h5(self):
        with override_access_code(""):
            home = self.client.get("/")
        self.assertEqual(home.status_code, 302)
        self.assertIn("index.html", home.headers["location"])
        self.assertIn("activity-stage", home.headers["location"])

    def test_v1_index_is_still_the_phone_shell(self):
        with override_access_code(""):
            page = self.client.get("/index.html")
        self.assertEqual(page.status_code, 200)
        self.assertIn("小欧 · 手机版", page.text)
        self.assertIn('id="voiceTalkBtn"', page.text)
        self.assertNotIn('data-v2="workshop"', page.text)

    def test_api_config_shape_stays_v1(self):
        with override_access_code(""):
            resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("configured", body)
        self.assertIn("topics", body)
        self.assertIn("levels", body)
        self.assertNotIn("director", body)
        self.assertNotIn("workshop", body)

    def test_v2_shares_the_v1_gate_cookie(self):
        with override_access_code("maxim"):
            locked = self.client.get("/v2/")
            self.assertEqual(locked.status_code, 302)
            self.assertEqual(locked.headers["location"], "/gate.html?next=/v2/")
            self.client.cookies.set(COOKIE_NAME, sign_cookie("maxim"))
            opened = self.client.get("/v2/")
        self.assertEqual(opened.status_code, 200)
        self.assertIn('data-v2="workshop"', opened.text)
        self.assertIn("小欧数学世界", opened.text)

    def test_disabled_gate_serves_v2(self):
        with override_access_code(""):
            resp = self.client.get("/v2/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data-v2="workshop"', resp.text)

    def test_v2_asks_phones_to_rotate_and_explains_the_task(self):
        html = read("v2/apps/web/index.html")
        css = read("v2/apps/web/src/styles.css")
        js = read("v2/apps/web/src/app.ts")
        self.assertIn("把手机横过来", html)
        self.assertIn("按住一堆积木", html)
        self.assertIn("id=\"rotateGate\"", html)
        self.assertIn("id=\"hintBar\"", html)
        self.assertNotIn("把平板横过来", html)
        self.assertNotIn("orientation: portrait", css)
        self.assertIn("is-landscape", js)
        self.assertIn("force-landscape-cw", js)

    def test_v1_web_assets_do_not_import_v2(self):
        for rel in ("web/index.html", "web/styles.css", "web/app.js"):
            text = read(rel)
            self.assertNotIn("/v2/", text)
            self.assertNotIn("data-v2", text)


if __name__ == "__main__":
    unittest.main()
