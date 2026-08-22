from __future__ import annotations

import unittest

from server import lesson


class LessonStateTests(unittest.TestCase):
    def test_empty_and_normalize(self) -> None:
        blank = lesson.empty_lesson()
        self.assertEqual(blank["rung"], "do")
        self.assertEqual(blank["shrinks"], 0)
        self.assertEqual(blank["discoveries"], [])
        messy = lesson.normalize_lesson(
            {
                "rung": "nope",
                "shrinks": 99,
                "discoveries": [
                    {"insight_key": "equalize_by_half_diff", "child_said": "移一张差少 2"},
                    {"insight_key": "BAD", "child_said": "x"},
                    "skip",
                ],
            }
        )
        self.assertEqual(messy["rung"], "do")
        self.assertEqual(messy["shrinks"], 3)
        self.assertEqual(len(messy["discoveries"]), 1)
        self.assertEqual(messy["discoveries"][0]["child_said"], "移一张差少 2")

    def test_shrink_stays_then_drops_then_caps(self) -> None:
        state = lesson.empty_lesson()
        state["rung"] = "why"
        one = lesson.apply_shrink(state)
        self.assertEqual(one["rung"], "why")
        self.assertEqual(one["shrinks"], 1)
        two = lesson.apply_shrink(one)
        self.assertEqual(two["rung"], "see")
        self.assertEqual(two["shrinks"], 2)
        three = lesson.apply_shrink(two)
        self.assertEqual(three["rung"], "see")
        self.assertEqual(three["shrinks"], 3)
        self.assertEqual(lesson.apply_shrink(three)["shrinks"], 3)

    def test_shrink_on_do_stays_on_do(self) -> None:
        state = lesson.empty_lesson()
        one = lesson.apply_shrink(state)
        two = lesson.apply_shrink(one)
        self.assertEqual(two["rung"], "do")
        self.assertEqual(two["shrinks"], 2)

    def test_reset_keeps_discoveries(self) -> None:
        state = lesson.normalize_lesson(
            {
                "rung": "see",
                "shrinks": 2,
                "discoveries": [
                    {"insight_key": "equalize_by_half_diff", "child_said": "差会少 2", "topic": "wordproblems"}
                ],
            }
        )
        nxt = lesson.reset_for_new_card(state)
        self.assertEqual(nxt["rung"], "do")
        self.assertEqual(nxt["shrinks"], 0)
        self.assertEqual(nxt["discoveries"][0]["child_said"], "差会少 2")

    def test_insight_key_from_seed_hook_and_explicit(self) -> None:
        self.assertEqual(
            lesson.insight_key_of({"hook": "哥哥有8张贴纸，弟弟只有4张"}),
            "equalize_by_half_diff",
        )
        self.assertEqual(
            lesson.insight_key_of({"insight_key": "same_both_sides", "hook": "哥哥有8张贴纸"}),
            "same_both_sides",
        )
        generated = lesson.insight_key_of({"insight": "一个没有目录的道理"})
        self.assertTrue(generated.startswith("idea_"))
        self.assertEqual(generated, lesson.insight_key_of({"insight": "一个没有目录的道理"}))

    def test_leaks_insight_and_harvest(self) -> None:
        insight = "每移过去一张，哥哥这边少一张、弟弟那边多一张，两行的差距一次缩小2"
        self.assertTrue(lesson.leaks_insight(insight, insight))
        self.assertTrue(lesson.leaks_insight("两行的差距一次缩小2，对吧", insight))
        self.assertFalse(lesson.leaks_insight("移一张，差少 2", insight))
        claim = {"accepted_by_child": True, "statement": insight}
        self.assertIsNone(lesson.harvest_discovery(claim, insight, insight, "equalize_by_half_diff"))
        got = lesson.harvest_discovery(claim, "移一张，差少 2", insight, "equalize_by_half_diff", "wordproblems")
        self.assertEqual(got["child_said"], "移一张，差少 2")
        self.assertIsNone(lesson.harvest_discovery({"accepted_by_child": False, "statement": "移一张"}, "移一张", insight, "equalize_by_half_diff"))

    def test_discovery_prompt_only_matching_key(self) -> None:
        card = {
            "topic": "wordproblems",
            "insight_key": "equalize_by_half_diff",
            "insight": "每移过去一张，两行的差距一次缩小2；移的是差的一半",
            "hook": "哥哥有8张贴纸",
        }
        state = {
            "discoveries": [
                {"insight_key": "equalize_by_half_diff", "child_said": "移一张差少 2", "topic": "wordproblems"},
                {"insight_key": "last_jump_recurrence", "child_said": "从前面两级加起来", "topic": "reasoning"},
            ]
        }
        block = lesson.discovery_prompt_block(state, card)
        self.assertIn("移一张差少 2", block)
        self.assertNotIn("从前面两级加起来", block)
        self.assertNotIn("差的一半", block)

    def test_shrink_prompt_and_guidance(self) -> None:
        card = {
            "insight": "移的是差的一半，不是整个差。",
            "insight_key": "equalize_by_half_diff",
            "ladder": [
                {"rung": "do", "ask": "先摆成 8 和 4，再移一张看看。"},
                {"rung": "see", "ask": "每移一张差怎么变？"},
                {"rung": "why", "ask": "为什么不是给 4 张？"},
            ],
            "allowed_views": ["snap_grid", "pair_rows"],
        }
        first = lesson.apply_shrink(lesson.empty_lesson())
        one = lesson.shrink_prompt_block(first, card, "shrink")
        self.assertIn("第 1 档", one)
        self.assertIn("先摆成 8 和 4", one)
        self.assertNotIn("差的一半", one)
        second = lesson.apply_shrink(first)
        two = lesson.shrink_prompt_block(second, card, "shrink")
        self.assertIn("第 2 档", two)
        self.assertIn("削短", two)
        self.assertNotIn(lesson.REGULARITY_ASK, two)
        self.assertTrue(lesson.is_shrink_talk("太难了"))
        self.assertTrue(lesson.is_shrink_talk("再小一点。请把问题削短"))
        self.assertFalse(lesson.is_shrink_talk("一张，两边差会少 2"))
        third = lesson.apply_shrink(second)
        top = lesson.shrink_prompt_block(third, card, "shrink")
        self.assertIn("第 3 档", top)
        self.assertIn("pair_rows", top)
        none = lesson.shrink_prompt_block(third, card, "")
        self.assertEqual(none, "")
        guide = lesson.lesson_guidance(first, card, "shrink")
        self.assertIn("当前层：do", guide)
        self.assertIn("先摆成 8 和 4", guide)
        self.assertNotIn("不是整个差", guide)

    def test_accept_regularity_keeps_child_words(self) -> None:
        card = {
            "insight_key": "equalize_by_half_diff",
            "insight": "每移过去一张，两行的差距一次缩小2；移的是差的一半",
            "misconceptions": ["看到相差4张就答'给4张'，只算了哥哥减少的没算弟弟增加的"],
            "topic": "wordproblems",
        }
        got = lesson.accept_regularity("一张，两边差会少 2", card, "wordproblems")
        self.assertEqual(got["child_said"], "一张，两边差会少 2")
        self.assertIsNone(lesson.accept_regularity("给4张就行了吧", card, "wordproblems"))
        self.assertIsNone(lesson.accept_regularity("两行的差距一次缩小2", card, "wordproblems"))
        self.assertIsNone(lesson.accept_regularity("嗯", card, "wordproblems"))
        self.assertIsNone(lesson.accept_regularity("太难了", card, "wordproblems"))


if __name__ == "__main__":
    unittest.main()
