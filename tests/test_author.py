"""出题卡：解析、主题校验、思考参数、接口门禁。"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from server.app import app
from server import author
from server.config import thinking_request_extras, load_settings


NINE = {
    "topic": "geometry",
    "hook": "九块积木",
    "insight": "奇数相加得平方",
    "axiom": "数是用来数东西的",
    "representation": "snap_grid",
    "diagram": {"type": "snap_grid", "cols": 3, "rows": 3, "tray": 9},
    "first_question": "这 9 块能不能摆成正方形？",
    "ladder": [
        {"rung": "do", "ask": "先摆摆看"},
        {"rung": "see", "ask": "你发现了什么"},
        {"rung": "why", "ask": "为什么是正方形"},
    ],
    "misconceptions": ["把长方形也当成正方形"],
}


class AuthorCardTests(unittest.TestCase):
    def test_extract_json_from_fence(self):
        data = author.extract_json_object('好的\n```json\n{"topic":"geometry","hook":"小棒"}\n```\n')
        self.assertEqual(data["hook"], "小棒")

    def test_normalize_requires_ladder(self):
        card = author.normalize_card({"topic": "geometry", "first_question": "能围起来吗？"}, "geometry")
        self.assertIsNone(card)

    def test_nine_square_rejected_for_geometry(self):
        err = author.validate_card(NINE, "geometry")
        self.assertIsNotNone(err)
        self.assertIn("9", err)

    def test_nine_square_ok_for_square_arithmetic(self):
        card = dict(NINE)
        card["topic"] = "arithmetic"
        card["insight"] = "连续奇数相加会得到平方数"
        self.assertIsNone(author.validate_card(card, "arithmetic"))

    def test_seed_card_matches_topic_and_is_not_nine_square(self):
        for topic in ("wordproblems", "geometry", "reasoning", "fractions", "algebra"):
            card = author.seed_card(topic, "middle")
            self.assertEqual(card["topic"], topic)
            self.assertIsNone(author.validate_card(card, topic))
            self.assertFalse(author.is_nine_square(card))

    def test_glm_thinking_cannot_be_disabled(self):
        extras = thinking_request_extras(
            "https://api.z.ai/api/coding/paas/v4", "glm-5.3", False, "high"
        )
        self.assertEqual(extras.get("thinking"), {"type": "enabled"})
        self.assertEqual(extras.get("reasoning_effort"), "high")

    def test_deepseek_author_thinking_enabled(self):
        extras = thinking_request_extras(
            "https://api.deepseek.com", "deepseek-v4-pro", True, "high"
        )
        self.assertEqual(extras.get("thinking"), {"type": "enabled"})
        self.assertEqual(extras.get("reasoning_effort"), "high")


class AuthorSettingsTests(unittest.TestCase):
    def test_default_author_is_glm_and_glm_uses_zai_coding(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("DEEPSEEK") and not k.startswith("ZHIPU") and k != "LLM_AUTHOR"}
        with mock.patch.dict(os.environ, env, clear=True):
            settings = load_settings()
        self.assertEqual(settings.author_engine, "glm")
        self.assertEqual(settings.deepseek_model, "deepseek-v4-pro")
        self.assertIn("api.z.ai", settings.zhipu_base_url)
        self.assertIn("coding/paas/v4", settings.zhipu_base_url)
        self.assertEqual(settings.zhipu_model, "glm-5.3")


class AuthorHttpTests(unittest.TestCase):
    def setUp(self):
        from server.gate import reset_unlock_limiter
        reset_unlock_limiter()
        self.client = TestClient(app, follow_redirects=False)

    def test_author_requires_gate(self):
        resp = self.client.post("/api/author", json={"topic": "geometry"})
        self.assertEqual(resp.status_code, 401)

    def test_config_lists_author_engines_after_unlock(self):
        self.client.post("/api/unlock", json={"code": "maxim"})
        cfg = self.client.get("/api/config").json()
        keys = [e["key"] for e in cfg["author_engines"]]
        self.assertEqual(keys, ["glm", "deepseek"])
        self.assertIn(cfg["default_author"], ("glm", "deepseek"))


if __name__ == "__main__":
    unittest.main()
