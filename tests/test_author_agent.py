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
            any("只换了标签或文案" in issue for issue in result["issues"]),
            result,
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
