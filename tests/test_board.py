"""语义画板 v2 协议测试。"""

from __future__ import annotations

import unittest

from server import board


class SemanticBoardTests(unittest.TestCase):
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
