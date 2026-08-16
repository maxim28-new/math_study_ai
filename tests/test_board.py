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
