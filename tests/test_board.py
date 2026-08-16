"""语义画板 v2 协议测试。"""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from server import board


ROOT = Path(__file__).resolve().parents[1]


class SemanticBoardTests(unittest.TestCase):
    def test_v3_shared_contract_fixtures(self):
        fixtures = json.loads((ROOT / "tests" / "board_v3_fixtures.json").read_text(encoding="utf-8"))
        for raw in fixtures["valid"]:
            with self.subTest(kind=raw["kind"]):
                normalized = board.normalize_board_v3(raw)
                self.assertEqual(normalized, raw)
                self.assertIsNone(board.validate_board_v3(normalized))
        for raw in fixtures["invalid"]:
            with self.subTest(kind=raw["kind"]):
                self.assertIsNone(board.normalize_board_v3(raw))

    def test_v3_color_sequence_question_uses_unit_colors(self):
        spec = board.normalize_board_v3(
            {
                "schema": 3,
                "kind": "color_sequence",
                "model": {"item": "花", "unit": ["red", "red", "blue"], "count": 6},
                "task": {
                    "action": "predict",
                    "ask": "color_at_end",
                    "prompt": "不要信任这句里的颜色。",
                },
                "view": {"reveal": "hide_last"},
            }
        )
        question = board.first_question_for_v3(spec)
        self.assertIn("红、红、蓝", question)
        self.assertIn("第6朵", question)
        self.assertNotIn("不要信任", question)
        self.assertEqual(
            board.expand_color_sequence(spec["model"]["unit"], spec["model"]["count"])[-1],
            "blue",
        )

    def test_upgrades_monochrome_pattern_dots_to_color_sequence(self):
        raw = {
            "schema": 3,
            "kind": "static_diagram",
            "model": {
                "diagram": {
                    "type": "dots",
                    "rows": 1,
                    "cols": 6,
                    "newLastRowCol": True,
                    "caption": "前面几朵按规律排，下一朵会是什么？",
                }
            },
            "task": {
                "action": "observe",
                "ask": "notice",
                "prompt": "红红蓝、红红蓝……第六朵会是什么颜色？",
            },
            "view": {"reveal": "model_only"},
        }
        upgraded = board.upgrade_legacy_pattern_board(raw)
        self.assertEqual(upgraded["kind"], "color_sequence")
        self.assertEqual(upgraded["model"]["unit"], ["red", "red", "blue"])
        self.assertEqual(upgraded["view"]["reveal"], "hide_last")

    def test_v3_geometry_question_comes_from_model(self):
        spec = board.normalize_board_v3(
            {
                "schema": 3,
                "kind": "geometry_compass",
                "model": {"construction": "equilateral_triangle", "labels": ["A", "B", "P"]},
                "task": {
                    "action": "construct",
                    "ask": "compare_three_sides",
                    "prompt": "不要信任这句里的数字。",
                },
                "view": {"reveal": "stepwise"},
            }
        )
        question = board.first_question_for_v3(spec)
        self.assertIn("PA、PB 和 AB", question)
        self.assertNotIn("不要信任", question)

    def test_normalizes_layer_sum_without_answer(self):
        spec = board.normalize_semantic_board(
            {
                "schema": 2,
                "kind": "layer_sum",
                "layers": [1, 2, 3, 4, 5],
                "item": "罐子",
                "ask": "total",
                "reveal": "items_without_total",
                "answer": 15,
            }
        )
        self.assertEqual(
            spec,
            {
                "schema": 2,
                "kind": "layer_sum",
                "layers": [1, 2, 3, 4, 5],
                "item": "罐子",
                "ask": "total",
                "purpose": "count_layers",
                "reveal": "items_without_total",
            },
        )
        self.assertNotIn("answer", spec)

    def test_odd_square_layers_use_stepwise_reveal(self):
        spec = board.normalize_board_v3(
            {
                "schema": 3,
                "kind": "layer_sum",
                "model": {"layers": [1, 3, 5], "item": "积木"},
                "task": {"action": "count", "ask": "total", "prompt": "看一看。"},
                "view": {"reveal": "items_without_total"},
            }
        )
        self.assertEqual(spec["view"]["reveal"], "stepwise")
        self.assertEqual(spec["model"]["layers"], [1, 3, 5])
        question = board.first_question_for_v3(spec)
        self.assertIn("加上下一层", question)
        self.assertIn("正方形", question)

    def test_normalizes_path_count(self):
        spec = board.normalize_semantic_board(
            {
                "schema": 2,
                "kind": "path_count",
                "start": 0,
                "target": 5,
                "moves": [2, 1],
                "ask": "number_of_paths",
                "reveal": "rules_only",
            }
        )
        self.assertEqual(spec["moves"], [1, 2])
        self.assertEqual(spec["purpose"], "explore_choices")
        question = board.first_question_for_board(spec)
        self.assertIn("第 5 级", question)
        self.assertIn("1 级或2 级", question)

    def test_layer_question_comes_from_validated_counts(self):
        spec = board.normalize_semantic_board(
            {
                "schema": 2,
                "kind": "layer_sum",
                "layers": [1, 2, 3],
                "item": "罐",
                "ask": "total",
                "reveal": "items_without_total",
            }
        )
        self.assertEqual(
            board.first_question_for_board(spec),
            "从上到下每层分别有 1、2、3 罐，这些层一共有多少罐？",
        )

    def test_rejects_unknown_or_unsafe_specs(self):
        bad = [
            {"schema": 1, "kind": "layer_sum", "layers": [1], "ask": "total"},
            {"schema": 2, "kind": "stairs", "rows": 5},
            {"schema": 2, "kind": "layer_sum", "layers": [1, 0], "ask": "total"},
            {
                "schema": 2,
                "kind": "path_count",
                "start": 0,
                "target": 2,
                "moves": [1, 2],
                "ask": "number_of_paths",
                "reveal": "all_paths",
            },
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                self.assertIsNone(board.normalize_semantic_board(raw))


if __name__ == "__main__":
    unittest.main()
