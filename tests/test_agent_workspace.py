"""Math Workspace 与受控工具测试。"""

from __future__ import annotations

import unittest

from server.agent import tools, validators, workspace as WS


ODD_CARD = {
    "hook": "连续奇数能围成正方形吗",
    "insight": "连续奇数相加得到平方数",
    "first_question": "中间这一块，你看见了什么？",
    "board": {
        "schema": 3,
        "kind": "layer_sum",
        "model": {"layers": [1, 3, 5], "item": "积木"},
        "task": {"action": "count", "ask": "total", "prompt": "先数前两层"},
        "view": {"reveal": "stepwise"},
    },
}


class WorkspaceToolTests(unittest.TestCase):
    def test_odd_square_starts_with_one_tile(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        self.assertEqual(len(validators.tiles(ws, placed_only=True)), 1)
        check = validators.forms_square(ws)
        self.assertTrue(check["ok"])
        self.assertEqual(check["side"], 1)
        snap = WS.visible_snapshot(ws)
        self.assertEqual(snap["tile_count"], 1)
        self.assertNotIn(5, [obj.get("attrs", {}).get("layer") for obj in snap["objects"]])

    def test_add_tiles_and_outer_ring_makes_2x2(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        added = tools.execute_tool("board_add_tiles", ws, {"count": 3})
        self.assertTrue(added["ok"], added)
        pending = validators.pending_tile_ids(ws)
        self.assertEqual(len(pending), 3)
        arranged = tools.execute_tool("board_arrange", ws, {"layout": "outer_ring"})
        self.assertTrue(arranged["ok"], arranged)
        check = validators.forms_square(ws)
        self.assertTrue(check["ok"])
        self.assertEqual(check["side"], 2)
        self.assertEqual(check["tile_count"], 4)
        self.assertEqual(ws["version"], 3)

    def test_second_ring_makes_3x3(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        self.assertTrue(tools.add_next_odd_ring(ws)["ok"])
        result = tools.add_next_odd_ring(ws)
        self.assertTrue(result["ok"], result)
        check = validators.forms_square(ws)
        self.assertEqual(check["side"], 3)
        self.assertEqual(check["tile_count"], 9)

    def test_outer_ring_rejects_wrong_count(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        tools.execute_tool("board_add_tiles", ws, {"count": 2})
        arranged = tools.execute_tool("board_arrange", ws, {"layout": "outer_ring"})
        self.assertFalse(arranged["ok"])
        placed = validators.tiles(ws, placed_only=True)
        self.assertEqual(validators.square_side(placed), 1)

    def test_fourth_ring_rejected_for_this_problem(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        tools.add_next_odd_ring(ws)
        tools.add_next_odd_ring(ws)
        failed = tools.add_next_odd_ring(ws)
        self.assertFalse(failed["ok"])
        self.assertEqual(validators.forms_square(ws)["tile_count"], 9)

    def test_unknown_tool_and_object_fail_closed(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        self.assertFalse(tools.execute_tool("board.explode", ws, {})["ok"])
        self.assertFalse(tools.execute_tool("board_highlight", ws, {"object_ids": ["nope"]})["ok"])
        self.assertEqual(ws["version"], 1)

    def test_hide_excluded_from_visible_snapshot(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        hidden = tools.execute_tool("board_hide", ws, {"object_ids": ["tile_1"]})
        self.assertTrue(hidden["ok"])
        snap = WS.visible_snapshot(ws)
        self.assertEqual(snap["tile_count"], 0)
        full = tools.execute_tool("workspace_inspect", ws, {})
        self.assertEqual(len(full["data"]["objects"]), 1)
        vis = tools.execute_tool("workspace_inspect_visible", ws, {})
        self.assertEqual(len(vis["data"]["objects"]), 0)

    def test_check_claim_forms_square(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        result = tools.execute_tool("math_check_claim", ws, {"claim": "forms_square"})
        self.assertTrue(result["claim"]["ok"])
        tools.execute_tool("board_add_tiles", ws, {"count": 3})
        result = tools.execute_tool("math_check_claim", ws, {"claim": "forms_square"})
        self.assertFalse(result["claim"]["ok"])

    def test_version_conflict(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        result = tools.execute_tool(
            "board_highlight",
            ws,
            {"object_ids": ["tile_1"], "expected_workspace_version": 9},
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "version_conflict")

    def test_resolve_prefers_newer_client_child_action(self):
        seeded = WS.seed_from_card(ODD_CARD, "arithmetic")
        client = WS.clone(seeded)
        tools.add_next_odd_ring(client)
        resolved = WS.resolve_workspace(seeded, client, ODD_CARD, "arithmetic")
        self.assertEqual(validators.forms_square(resolved)["side"], 2)

    def test_highlight_does_not_change_tile_count(self):
        ws = WS.seed_from_card(ODD_CARD, "arithmetic")
        tools.execute_tool("board_highlight", ws, {"object_ids": ["tile_1"]})
        self.assertEqual(validators.forms_square(ws)["tile_count"], 1)
        self.assertEqual(ws["visibility"]["emphasis"], ["tile_1"])


if __name__ == "__main__":
    unittest.main()
