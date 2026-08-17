"""出题卡：解析、主题校验、思考参数、接口门禁。"""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from server.app import app
from server import author, author_jobs, tutor
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
        self.assertIsNone(author.normalize_card(NINE, "geometry"))

    def test_nine_square_ok_for_square_arithmetic(self):
        card = dict(NINE)
        card["topic"] = "arithmetic"
        card["insight"] = "连续奇数相加会得到平方数"
        normalized = author.normalize_card(card, "arithmetic")
        self.assertIsNotNone(normalized)
        self.assertIsNone(author.validate_card(normalized, "arithmetic"))

    def test_layer_sum_semantic_board_overrides_legacy_diagram(self):
        raw = {
            "topic": "arithmetic",
            "hook": "仓库里的罐子堆成三角小山",
            "insight": "第 n 层有 n 罐，前 n 层加起来是三角形数",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "representation": "dots",
            "diagram": {"type": "dots", "rows": 5, "cols": 5, "caption": "前5层的小山，像台阶"},
            "semantic_board": {
                "schema": 2,
                "kind": "layer_sum",
                "layers": [1, 2, 3, 4, 5],
                "item": "罐",
                "ask": "total",
                "purpose": "count_layers",
                "reveal": "items_without_total",
            },
            "first_question": "前5层一共多少罐？",
            "ladder": [
                {"rung": "do", "ask": "先数最上面一层有几罐。"},
                {"rung": "see", "ask": "每一层比上一层多几罐？"},
                {"rung": "why", "ask": "为什么可以一层一层加起来？"},
            ],
        }
        card = author.normalize_card(raw, "arithmetic")
        self.assertIsNotNone(card)
        self.assertEqual(card["representation"], "board_v3")
        self.assertIsNone(card["diagram"])
        self.assertIsNone(card["semantic_board"])
        self.assertEqual(card["board"]["kind"], "layer_sum")
        self.assertEqual(card["board"]["model"]["layers"], [1, 2, 3, 4, 5])
        self.assertEqual(
            card["first_question"],
            "从上到下每层分别有 1、2、3、4、5 罐，这些层一共有多少罐？",
        )

    def test_semantic_board_is_source_of_truth_for_question_numbers(self):
        raw = {
            "topic": "reasoning",
            "hook": "青蛙从 0 跳到 4",
            "insight": "把所有走法不重不漏地列出来",
            "axiom": "先列举，再检查。",
            "representation": "semantic_board",
            "semantic_board": {
                "schema": 2,
                "kind": "path_count",
                "start": 0,
                "target": 4,
                "moves": [1, 2],
                "ask": "number_of_paths",
                "reveal": "rules_only",
            },
            "diagram": None,
            "first_question": "先到第 2 级有几种走法？",
            "ladder": [
                {"rung": "do", "ask": "先走一次。"},
                {"rung": "see", "ask": "还有别的走法吗？"},
                {"rung": "why", "ask": "怎样保证不漏？"},
            ],
        }
        card = author.normalize_card(raw, "reasoning")
        self.assertIn("第 4 级", card["first_question"])
        self.assertNotIn("第 2 级", card["first_question"])

    def test_keyword_does_not_rewrite_legacy_diagram(self):
        raw = {
            "topic": "arithmetic",
            "hook": "罐子小山",
            "insight": "一层比一层多 1",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "representation": "dots",
            "diagram": {"type": "dots", "rows": 4, "cols": 4, "caption": "4 层台阶"},
            "first_question": "这 4 层一共多少罐？",
            "ladder": [
                {"rung": "do", "ask": "先数第一层。"},
                {"rung": "see", "ask": "每层多几罐？"},
                {"rung": "why", "ask": "为什么是三角形数？"},
            ],
        }
        card = author.normalize_card(raw, "arithmetic")
        self.assertEqual(card["board"]["model"]["diagram"]["type"], "dots")
        self.assertEqual(card["representation"], "board_v3")
        self.assertIsNone(card["semantic_board"])
        self.assertIsNone(card["diagram"])

    def test_invalid_semantic_board_rejects_card_instead_of_guessing(self):
        raw = {
            "topic": "reasoning",
            "hook": "青蛙跳台阶",
            "insight": "把所有走法不重不漏地列出来",
            "axiom": "先列举，再检查。",
            "representation": "stairs",
            "semantic_board": {
                "schema": 2,
                "kind": "path_count",
                "start": 0,
                "target": 2,
                "moves": [0, 2],
                "ask": "number_of_paths",
                "reveal": "rules_only",
            },
            "diagram": {"type": "stairs", "rows": 2},
            "first_question": "一共有几种走法？",
            "ladder": [
                {"rung": "do", "ask": "先走一次。"},
                {"rung": "see", "ask": "还有别的走法吗？"},
                {"rung": "why", "ask": "怎样保证不漏？"},
            ],
        }
        self.assertIsNone(author.normalize_card(raw, "reasoning"))

    def test_square_dots_stay_square(self):
        raw = {
            "topic": "arithmetic",
            "hook": "九块积木",
            "insight": "连续奇数相加会得到平方数",
            "axiom": "把两堆合在一起数，就是加法；无论先数哪一堆，结果都一样。",
            "representation": "dots",
            "diagram": {"type": "dots", "rows": 3, "cols": 3, "caption": "3×3 正方形"},
            "first_question": "这 9 块能摆成正方形吗？",
            "ladder": [
                {"rung": "do", "ask": "先摆摆看。"},
                {"rung": "see", "ask": "外面一圈有几块？"},
                {"rung": "why", "ask": "为什么包一圈会变成更大的正方形？"},
            ],
        }
        card = author.normalize_card(raw, "arithmetic")
        self.assertIsNotNone(card)
        self.assertEqual(card["board"]["model"]["diagram"]["type"], "dots")
        self.assertEqual(card["representation"], "board_v3")

    def test_geometry_triangle_is_not_stairs(self):
        raw = {
            "topic": "geometry",
            "hook": "三根小棒围三角形",
            "insight": "两边加起来必须比第三边长，才能围住",
            "axiom": "任意两点之间，可以画一条直线段。",
            "representation": "dots",
            "diagram": {"type": "dots", "rows": 1, "cols": 3, "caption": "三根小棒"},
            "first_question": "2、3、6 还能围成三角形吗？",
            "ladder": [
                {"rung": "do", "ask": "先拿 2、3、4 试一试。"},
                {"rung": "see", "ask": "哪两边加起来还不够？"},
                {"rung": "why", "ask": "为什么围不住？"},
            ],
        }
        card = author.normalize_card(raw, "geometry")
        self.assertIsNotNone(card)
        self.assertEqual(card["board"]["model"]["diagram"]["type"], "dots")

    def test_unknown_geometry_demo_is_rejected_at_author_boundary(self):
        raw = {
            "topic": "geometry",
            "hook": "圆规画三角形",
            "insight": "三边一样长",
            "axiom": "同圆半径相等",
            "representation": "dots",
            "diagram": {"type": "geometry_demo", "steps": []},
            "first_question": "试试看？",
            "ladder": [
                {"rung": "do", "ask": "先画。"},
                {"rung": "see", "ask": "再看。"},
                {"rung": "why", "ask": "为什么？"},
            ],
        }
        self.assertIsNone(author.normalize_card(raw, "geometry"))

    def test_reasoning_seed_uses_color_sequence(self):
        card = author.seed_card("reasoning", "middle")
        self.assertEqual(card["board"]["kind"], "color_sequence")
        self.assertEqual(card["board"]["model"]["unit"], ["red", "red", "blue"])
        self.assertEqual(card["board"]["view"]["reveal"], "hide_last")
        self.assertIn("红", card["first_question"])
        self.assertIn("蓝", card["first_question"])

    def test_legacy_pattern_dots_card_upgrades_to_color_sequence(self):
        raw = {
            "topic": "reasoning",
            "hook": "花朵颜色的规律",
            "insight": "先多看几个例子再猜",
            "axiom": "找规律时，先多列几个具体例子，再猜规律，最后想办法验证。",
            "representation": "dots",
            "diagram": {
                "type": "dots",
                "rows": 1,
                "cols": 6,
                "newLastRowCol": True,
                "caption": "前面几朵按规律排，下一朵会是什么？",
            },
            "first_question": "红红蓝、红红蓝……第六朵会是什么颜色？",
            "ladder": [
                {"rung": "do", "ask": "先把前五朵的颜色按顺序说出来。"},
                {"rung": "see", "ask": "每几朵重复一次？"},
                {"rung": "why", "ask": "你怎么证明第六朵一定是这个颜色？"},
            ],
        }
        card = author.normalize_card(raw, "reasoning")
        self.assertIsNotNone(card)
        self.assertEqual(card["board"]["kind"], "color_sequence")
        self.assertEqual(card["board"]["model"]["unit"], ["red", "red", "blue"])

    def test_geometry_seed_uses_v3_compass_activity(self):
        card = author.seed_card("geometry", "middle")
        self.assertEqual(card["representation"], "board_v3")
        self.assertEqual(card["board"]["schema"], 3)
        self.assertEqual(card["board"]["kind"], "geometry_compass")

    def test_author_falls_back_to_seed_after_one_short_attempt(self):
        src = Path(__file__).resolve().parents[1].joinpath("server/author.py").read_text(encoding="utf-8")
        self.assertIn("httpx.Timeout(timeout)", src)
        self.assertIn("timeout: float = 120.0", src)
        self.assertNotIn("for _ in range(2):", src)

    def test_v3_tutor_prompt_has_no_competing_draw_command(self):
        card = author.seed_card("geometry", "middle")
        prompt = tutor.build_system_prompt("geometry", "middle", mode="explore", card=card)
        self.assertIn("BoardSpec V3", prompt)
        self.assertNotIn("每一轮回复都要配一张", prompt)
        self.assertNotIn("每一轮回复都必须", prompt)
        self.assertIn("你只输出孩子能听懂的自然语言", prompt)
        self.assertIn("叫“圆心”", prompt)
        seen = tutor.build_system_prompt(
            "geometry", "middle", mode="explore", card=card, seen_terms=["center"]
        )
        self.assertIn("圆心", seen)
        self.assertIn("已经点开看过", seen)

    def test_seed_card_matches_topic_and_is_not_nine_square(self):
        for topic in ("arithmetic", "wordproblems", "geometry", "reasoning", "fractions", "algebra"):
            card = author.seed_card(topic, "middle")
            self.assertEqual(card["topic"], topic)
            self.assertIsNone(author.validate_card(card, topic))
            self.assertFalse(author.is_nine_square(card))
        arithmetic = author.seed_card("arithmetic", "middle")
        self.assertEqual(arithmetic["board"]["kind"], "layer_sum")
        self.assertEqual(arithmetic["board"]["model"]["layers"], [1, 3, 5])
        self.assertEqual(arithmetic["board"]["view"]["reveal"], "stepwise")
        self.assertNotEqual(arithmetic["board"]["kind"], "static_diagram")

    def test_each_topic_has_three_distinct_seed_variants(self):
        for topic, raws in author.SEED_VARIANTS.items():
            self.assertEqual(len(raws), 3, topic)
            cards = author.seed_variants(topic)
            self.assertEqual(len(cards), 3, topic)
            hooks = [card["hook"] for card in cards]
            self.assertEqual(len(set(hooks)), 3, hooks)
            for card in cards:
                self.assertEqual(card["topic"], topic)
                self.assertIsNone(author.validate_card(card, topic), card.get("hook"))
                self.assertFalse(author.is_nine_square(card))
                self.assertTrue(card.get("first_question"))
        first = author.seed_card("arithmetic", "middle")
        second = author.seed_card("arithmetic", "middle", [first["hook"]])
        third = author.seed_card("arithmetic", "middle", [first["hook"], second["hook"]])
        self.assertNotEqual(first["hook"], second["hook"])
        self.assertNotEqual(second["hook"], third["hook"])
        self.assertNotEqual(first["hook"], third["hook"])

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
        author_jobs.reset()
        self.client = TestClient(app, follow_redirects=False)

    def test_author_requires_gate(self):
        resp = self.client.post("/api/author", json={"topic": "geometry"})
        self.assertEqual(resp.status_code, 401)

    def test_author_jobs_require_gate(self):
        resp = self.client.post("/api/author/jobs", json={"topic": "geometry"})
        self.assertEqual(resp.status_code, 401)
        resp = self.client.get("/api/author/jobs/job_missing")
        self.assertEqual(resp.status_code, 401)

    def test_config_lists_author_engines_after_unlock(self):
        self.client.post("/api/unlock", json={"code": "maxim"})
        cfg = self.client.get("/api/config").json()
        keys = [e["key"] for e in cfg["author_engines"]]
        self.assertEqual(keys, ["glm", "deepseek"])
        self.assertIn(cfg["default_author"], ("glm", "deepseek"))
        self.assertEqual(len(cfg["seed_cards"]), 6)
        for topic, cards in cfg["seed_cards"].items():
            self.assertEqual(len(cards), 3, topic)

    def test_seed_only_returns_seed_card(self):
        self.client.post("/api/unlock", json={"code": "maxim"})
        resp = self.client.post("/api/author", json={"topic": "reasoning", "seed_only": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["engine"], "seed")
        self.assertEqual(data["card"]["topic"], "reasoning")
        self.assertFalse(author.is_nine_square(data["card"]))
        self.assertIsNone(data.get("job_id"))

    def test_author_returns_seed_immediately_and_starts_job(self):
        self.client.post("/api/unlock", json={"code": "maxim"})
        called = {}

        async def fake_request(topic, level, recent, engine, timeout=120.0):
            called["timeout"] = timeout
            called["topic"] = topic
            return author.seed_card(topic, level, list(recent or []) + ["__used__"])

        with mock.patch.object(author, "engine_ready", return_value=True), mock.patch.object(
            author, "request_author_card", side_effect=fake_request
        ):
            resp = self.client.post("/api/author", json={"topic": "geometry", "recent": ["旧题"]})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["ok"])
            self.assertEqual(data["engine"], "seed")
            self.assertTrue(data["job_id"])
            self.assertEqual(data["card"]["topic"], "geometry")
            job = self.client.get("/api/author/jobs/" + data["job_id"])
            self.assertEqual(job.status_code, 200)
            body = job.json()
            self.assertEqual(body["status"], "done")
            self.assertTrue(body["card"])
            self.assertEqual(called.get("timeout"), 120.0)
            self.assertEqual(called.get("topic"), "geometry")

    def test_author_job_poll_returns_generated_card(self):
        self.client.post("/api/unlock", json={"code": "maxim"})

        async def fake_request(topic, level, recent, engine, timeout=120.0):
            return author.seed_card(topic, level, list(recent or []) + ["__used__"])

        with mock.patch.object(author, "engine_ready", return_value=True), mock.patch.object(
            author, "request_author_card", side_effect=fake_request
        ):
            started = self.client.post("/api/author/jobs", json={"topic": "reasoning", "level": "middle"})
            self.assertEqual(started.status_code, 200)
            job_id = started.json()["job_id"]
            self.assertTrue(job_id)
            polled = self.client.get("/api/author/jobs/" + job_id)
            self.assertEqual(polled.status_code, 200)
            body = polled.json()
            self.assertEqual(body["status"], "done")
            self.assertEqual(body["card"]["topic"], "reasoning")
            self.assertIsNone(author.validate_card(body["card"], "reasoning"))

    def test_failed_author_job_never_substitutes_a_seed(self):
        self.client.post("/api/unlock", json={"code": "maxim"})

        async def fail_request(*args, **kwargs):
            raise ValueError("GLM failed")

        with mock.patch.object(author, "engine_ready", return_value=True), mock.patch.object(
            author, "request_author_card", side_effect=fail_request
        ):
            started = self.client.post(
                "/api/author/jobs", json={"topic": "geometry", "level": "middle"}
            )
            job_id = started.json()["job_id"]
            body = self.client.get("/api/author/jobs/" + job_id).json()
            self.assertFalse(body["ok"])
            self.assertEqual(body["status"], "failed")
            self.assertNotIn("card", body)
            self.assertNotEqual(body.get("engine"), "seed")

    def test_pending_jobs_are_reused_for_same_topic(self):
        first = author_jobs.create("geometry", "middle", ["a"], "glm")
        second = author_jobs.create("geometry", "middle", ["b"], "glm")
        self.assertEqual(first["id"], second["id"])
        other = author_jobs.create("arithmetic", "middle", [], "glm")
        self.assertNotEqual(first["id"], other["id"])


if __name__ == "__main__":
    unittest.main()
