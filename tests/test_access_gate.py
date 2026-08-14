"""公网访问验证码：默认 maxim，服务端校验，未通过则进不了页面和对话接口。"""

from __future__ import annotations

import os
import unittest
from contextlib import contextmanager
from dataclasses import replace
from unittest import mock

from fastapi.testclient import TestClient

from server import config
from server.app import app
from server.config import load_settings
from server.gate import COOKIE_NAME, codes_match, is_public_path, sign_cookie, cookie_valid


@contextmanager
def override_access_code(code: str):
    old = config.settings
    config.settings = replace(old, access_code=code)
    try:
        yield
    finally:
        config.settings = old


class AccessCodeSettingsTests(unittest.TestCase):
    def test_default_access_code_is_maxim(self):
        env = {k: v for k, v in os.environ.items() if k != "ACCESS_CODE"}
        with mock.patch.dict(os.environ, env, clear=True):
            settings = load_settings()
        self.assertEqual(settings.access_code, "maxim")
        self.assertTrue(settings.gate_enabled)

    def test_blank_access_code_still_defaults_to_maxim(self):
        with mock.patch.dict(os.environ, {"ACCESS_CODE": "  "}, clear=False):
            settings = load_settings()
        self.assertEqual(settings.access_code, "maxim")

    def test_custom_access_code(self):
        with mock.patch.dict(os.environ, {"ACCESS_CODE": " family "}, clear=False):
            settings = load_settings()
        self.assertEqual(settings.access_code, "family")

    def test_off_disables_gate(self):
        with mock.patch.dict(os.environ, {"ACCESS_CODE": "off"}, clear=False):
            settings = load_settings()
        self.assertEqual(settings.access_code, "")
        self.assertFalse(settings.gate_enabled)


class GateHelpersTests(unittest.TestCase):
    def test_codes_match_is_case_sensitive(self):
        self.assertTrue(codes_match("maxim", "maxim"))
        self.assertFalse(codes_match("Maxim", "maxim"))
        self.assertFalse(codes_match("max", "maxim"))

    def test_cookie_roundtrip(self):
        token = sign_cookie("maxim")
        self.assertTrue(cookie_valid("maxim", token))
        self.assertFalse(cookie_valid("other", token))
        self.assertFalse(cookie_valid("maxim", "forged"))

    def test_public_paths(self):
        self.assertTrue(is_public_path("/gate.html"))
        self.assertTrue(is_public_path("/api/unlock"))
        self.assertTrue(is_public_path("/api/health"))
        self.assertFalse(is_public_path("/"))
        self.assertFalse(is_public_path("/index.html"))
        self.assertFalse(is_public_path("/api/config"))
        self.assertFalse(is_public_path("/api/chat"))


class AccessGateHttpTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, follow_redirects=False)

    def test_gate_page_is_public(self):
        with override_access_code("maxim"):
            resp = self.client.get("/gate.html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("验证码", resp.text)
        self.assertIn('id="codeInput"', resp.text)

    def test_index_redirects_to_gate_without_cookie(self):
        with override_access_code("maxim"):
            resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "/gate.html")

    def test_html_page_redirects_to_gate_without_cookie(self):
        with override_access_code("maxim"):
            resp = self.client.get("/index.html")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["location"], "/gate.html")

    def test_api_config_unauthorized_without_cookie(self):
        with override_access_code("maxim"):
            resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json().get("ok", True))

    def test_chat_unauthorized_without_cookie(self):
        with override_access_code("maxim"):
            resp = self.client.post("/api/chat", json={"messages": []})
        self.assertEqual(resp.status_code, 401)

    def test_wrong_code_is_rejected(self):
        with override_access_code("maxim"):
            resp = self.client.post("/api/unlock", json={"code": "nope"})
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn(COOKIE_NAME, resp.cookies)

    def test_correct_code_sets_cookie_and_unlocks(self):
        with override_access_code("maxim"):
            unlock = self.client.post("/api/unlock", json={"code": "maxim"})
            self.assertEqual(unlock.status_code, 200)
            self.assertTrue(unlock.json()["ok"])
            self.assertIn(COOKIE_NAME, unlock.cookies)
            cfg = self.client.get("/api/config")
            self.assertEqual(cfg.status_code, 200)
            home = self.client.get("/")
            self.assertEqual(home.status_code, 302)
            self.assertIn("index.html", home.headers["location"])

    def test_header_access_code_unlocks_api(self):
        with override_access_code("maxim"):
            resp = self.client.get("/api/config", headers={"X-Access-Code": "maxim"})
        self.assertEqual(resp.status_code, 200)

    def test_disabled_gate_allows_index(self):
        with override_access_code(""):
            resp = self.client.get("/index.html")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
