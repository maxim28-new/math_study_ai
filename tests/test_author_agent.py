from __future__ import annotations

import unittest

from server import author, author_agent


class AuthorAgentValidationTests(unittest.TestCase):
    def candidates(self, topic: str) -> list[dict]:
        return [
            {"concept_key": f"concept_{index}", "card": raw}
            for index, raw in enumerate(author.SEED_VARIANTS[topic], 1)
        ]

    def test_accepts_three_structurally_distinct_cards(self):
        result = author_agent.validate_seed_batch("arithmetic", self.candidates("arithmetic"))
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["cards"]), 3)
        self.assertEqual(len(result["preview"]), 3)

    def test_rejects_same_geometry_problem_with_renamed_points(self):
        result = author_agent.validate_seed_batch("geometry", self.candidates("geometry"))
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("只换了标签或文案" in issue or "最多一题" in issue for issue in result["issues"]),
            result,
        )

    def test_rejects_numberline_as_a_geometry_seed(self):
        candidates = [
            {"concept_key": "equilateral_from_circles", "card": author.SEED_VARIANTS["geometry"][0]},
            {
                "concept_key": "length_is_difference",
                "card": author.SEED_VARIANTS["wordproblems"][1] | {"topic": "geometry"},
            },
            {"concept_key": "tile_count_is_area", "card": author.SEED_VARIANTS["arithmetic"][2]},
        ]
        result = author_agent.validate_seed_batch("geometry", candidates)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("不能用数轴" in issue or "尺规作图或拼方块" in issue for issue in result["issues"]),
            result,
        )

    def test_rejects_two_compass_constructions_in_geometry(self):
        tiling = author.SEED_VARIANTS["arithmetic"][2]
        candidates = [
            {"concept_key": "equilateral_from_circles", "card": author.SEED_VARIANTS["geometry"][0]},
            {"concept_key": "equilateral_renamed", "card": author.SEED_VARIANTS["geometry"][1]},
            {"concept_key": "tile_count_is_area", "card": tiling},
        ]
        result = author_agent.validate_seed_batch("geometry", candidates)
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("最多一题" in issue or "只换了标签" in issue for issue in result["issues"]),
            result,
        )

    def test_accepts_compass_plus_two_distinct_tilings(self):
        tiling_b = {
            "hook": "十二块方砖铺地面",
            "insight": "同样多的方砖可以铺成瘦长或矮胖的长方形，块数不变，周长会变",
            "axiom": "所有的直角都一样大。",
            "board": {
                "schema": 3,
                "kind": "snap_grid",
                "model": {"rows": 4, "cols": 6, "tray": 12},
                "task": {
                    "action": "arrange",
                    "ask": "observe",
                    "prompt": "用 12 块铺出不同的长方形。",
                },
                "view": {"reveal": "empty_grid_and_tiles"},
            },
            "ladder": [
                {"rung": "do", "ask": "先铺成 3 行 4 列。"},
                {"rung": "see", "ask": "再铺成 2 行 6 列，块数变了吗？"},
                {"rung": "why", "ask": "为什么角都是直角就能拼严实？"},
            ],
            "misconceptions": ["以为换形状就必须换块数"],
        }
        candidates = [
            {"concept_key": "equilateral_from_circles", "card": author.SEED_VARIANTS["geometry"][0]},
            {"concept_key": "six_tiles_fill_grid", "card": author.SEED_VARIANTS["arithmetic"][2]},
            {"concept_key": "twelve_tiles_two_rectangles", "card": tiling_b},
        ]
        result = author_agent.validate_seed_batch("geometry", candidates)
        self.assertTrue(result["ok"], result)
        self.assertEqual(
            [row["board_kind"] for row in result["preview"]],
            ["geometry_compass", "snap_grid", "snap_grid"],
        )

    def test_rejects_duplicate_concept_keys(self):
        candidates = self.candidates("arithmetic")
        for candidate in candidates:
            candidate["concept_key"] = "same_concept"
        result = author_agent.validate_seed_batch("arithmetic", candidates)
        self.assertFalse(result["ok"])
        self.assertIn("三题的 concept_key 必须代表三个不同的数学发现", result["issues"])

    def test_rejects_color_prediction_as_a_fraction_seed(self):
        candidates = self.candidates("fractions")
        candidates[2] = {
            "concept_key": "fraction_as_share",
            "card": author.SEED_VARIANTS["reasoning"][0] | {
                "topic": "fractions",
                "insight": "红花占全部的三分之二",
            },
        }
        result = author_agent.validate_seed_batch("fractions", candidates)
        self.assertFalse(result["ok"])
        self.assertTrue(any("只会问颜色规律" in issue for issue in result["issues"]), result)

    def test_rejects_caption_that_would_be_truncated(self):
        candidates = self.candidates("wordproblems")
        candidates[0]["card"]["board"]["model"]["diagram"]["caption"] = "很长" * 50
        result = author_agent.validate_seed_batch("wordproblems", candidates)
        self.assertFalse(result["ok"])
        self.assertTrue(any("caption 超过 80 字" in issue for issue in result["issues"]), result)

    def test_every_accepted_card_mounts_as_tutor_workspace(self):
        result = author_agent.validate_seed_batch("reasoning", self.candidates("reasoning"))
        self.assertTrue(result["ok"], result)
        self.assertEqual(
            [row["board_kind"] for row in result["preview"]],
            ["color_sequence", "color_sequence", "path_count"],
        )


if __name__ == "__main__":
    unittest.main()
