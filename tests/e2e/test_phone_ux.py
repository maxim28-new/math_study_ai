"""Phone UX cases: talk dock, doodle send, board controls, layout probe.

Chat is stubbed. These tests check what a child can actually tap, and whether
the board / composer stay usable on a 390×844 viewport.
"""

from __future__ import annotations

import json
import unittest

from tests.e2e.harness import ARTIFACTS, HeadlessPhoneTests


PROBE_CARDS = (
    ("arithmetic", 1, "layer_sum"),
    ("arithmetic", 3, "static_diagram"),
    ("wordproblems", 2, "snap_grid"),
    ("wordproblems", 3, "path_count"),
    ("geometry", 1, "geometry_compass"),
    ("geometry", 3, "snap_grid_4x4"),
    ("reasoning", 1, "color_sequence"),
)


class PhoneUxTests(HeadlessPhoneTests):
    def test_wrong_access_code_stays_on_gate(self) -> None:
        page = self._launch()
        try:
            page.unroute("**/api/chat")
            page.goto(self.base + "/", wait_until="domcontentloaded")
            page.wait_for_url("**/gate.html")
            page.fill("#codeInput", "not-the-code")
            page.click("#unlockBtn")
            page.wait_for_function(
                "() => (document.querySelector('#errBox')?.textContent || '').length > 0",
                timeout=8000,
            )
            self.assertIn("验证码", page.locator("#errBox").inner_text())
            self.assertIn("gate.html", page.url)
            self._shot(page, "ux-gate-wrong-code.png")
        finally:
            self._close()

    def test_talk_dock_reveals_plus_send_board_stays_disabled(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "wordproblems", 2)
            closed = self._layout(page)
            self.assertTrue(closed["talkVisible"], closed)
            self.assertFalse(closed["plusVisible"], "换一题入口应藏在我想说后面")
            self.assertTrue(closed["sendVisible"], closed)
            self.assertTrue(closed["sendDisabled"], "没画一笔时发画板应是灰的")
            self._shot(page, "ux-talk-closed.png")

            self._open_talk(page)
            opened = self._layout(page)
            self.assertTrue(opened["talkOpen"], opened)
            self.assertTrue(opened["plusVisible"], opened)
            self.assertTrue(opened["sendDisabled"], opened)
            page.locator("#plusBtn").click()
            page.locator("#newQuestionBtn").wait_for(state="visible")
            self.assertTrue(page.locator("#hintBtn").is_visible())
            self._shot(page, "ux-talk-open-attach.png")
        finally:
            self._close()

    def test_doodle_enables_send_board_and_posts_image(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "wordproblems", 2)
            kickoffs = [row for row in self.chat_posts if row["kickoff"]]
            self.assertEqual(len(kickoffs), 1, self.chat_posts)
            before = len(self.chat_posts)

            page.locator("#boardDrawBtn").click()
            page.wait_for_function(
                "() => document.querySelector('.play-stage')?.classList.contains('is-drawing')",
            )
            canvas = page.locator("#doodleCanvas")
            box = canvas.bounding_box()
            self.assertIsNotNone(box)
            x, y = box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.35
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 90, y + 70, steps=12)
            page.mouse.up()
            page.wait_for_function(
                "() => !document.querySelector('#doodleSendBtn')?.disabled",
                timeout=8000,
            )
            self._shot(page, "ux-doodle-before-send.png")
            page.locator("#doodleSendBtn").click()
            page.wait_for_timeout(1200)
            sent = self.chat_posts[before:]
            self.assertTrue(any(row["has_image"] and not row["kickoff"] for row in sent), sent)
            self.assertIn("画板", sent[-1]["text"])
        finally:
            self._close()

    def test_snap_grid_drag_updates_tray_without_calling_tutor(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "wordproblems", 2)
            before = len(self.chat_posts)
            tray_before = page.locator("#trayCount").inner_text()
            pts = page.evaluate(
                """() => {
                  const host = document.querySelector('.snap-grid-stage');
                  const stage = (window.Konva && Konva.stages || []).find(
                    (s) => host && host.contains(s.container())
                  );
                  if (!stage) return null;
                  const groups = stage.find('Group').filter((g) => g.draggable());
                  if (!groups.length) return null;
                  const tile = groups.slice().sort((a, b) => b.y() - a.y())[0];
                  const layer = stage.getLayers()[0];
                  const cells = layer.find('Rect').filter((r) => r.getParent() === layer);
                  if (!cells.length) return null;
                  const origin = stage.container().getBoundingClientRect();
                  const tb = tile.getClientRect();
                  const cb = cells[0].getClientRect();
                  return {
                    from: { x: origin.left + tb.x + tb.width / 2, y: origin.top + tb.y + tb.height / 2 },
                    to: { x: origin.left + cb.x + cb.width / 2, y: origin.top + cb.y + cb.height / 2 },
                  };
                }"""
            )
            self.assertIsNotNone(pts, "Konva snap-grid stage missing")
            page.mouse.move(pts["from"]["x"], pts["from"]["y"])
            page.mouse.down()
            page.mouse.move(pts["to"]["x"], pts["to"]["y"], steps=16)
            page.mouse.up()
            page.wait_for_timeout(700)
            tray_after = page.locator("#trayCount").inner_text()
            self._shot(page, "ux-snap-grid-after-drag.png")
            self.assertNotEqual(tray_after, tray_before, (tray_before, tray_after))
            self.assertEqual(len(self.chat_posts), before, self.chat_posts)
            self.assertTrue(page.locator("#doodleSendBtn").is_disabled())
        finally:
            self._close()

    def test_path_board_jump_updates_status(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "reasoning", 2)
            before = page.locator(".path-board-status").inner_text()
            btn = page.locator(".path-move-btn").first
            label = btn.inner_text()
            btn.click()
            page.wait_for_function(
                "prev => (document.querySelector('.path-board-status')?.textContent || '') !== prev",
                arg=before,
            )
            after = page.locator(".path-board-status").inner_text()
            self.assertIn("现在在第", after)
            self.assertRegex(label, r"跳 \d+ 级")
            self._shot(page, "ux-path-after-jump.png")
        finally:
            self._close()

    def test_compass_steps_through_construction(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "geometry", 1)
            status = page.locator(".geometry-compass-status")
            next_btn = page.locator(".geometry-next-btn")
            self.assertIn("线段", status.inner_text())
            self.assertIn("夹住", next_btn.inner_text())
            next_btn.click()
            page.wait_for_function(
                "() => (document.querySelector('.geometry-compass-status')?.textContent || '').includes('夹成')",
            )
            self.assertIn("画圆", next_btn.inner_text())
            next_btn.click()
            page.wait_for_selector("circle.geometry-circle-a")
            self._shot(page, "ux-compass-after-first-circle.png")
        finally:
            self._close()

    def test_topic_switch_returns_to_start_play(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "arithmetic", 1)
            self.assertFalse(page.locator("#startPlayWrap").is_visible())
            self._choose_topic(page, "几何与图形")
            page.locator("#startPlayWrap").wait_for(state="visible")
            self.assertIn("点开始玩", page.locator("#tutorCaption").inner_text())
            self._shot(page, "ux-topic-switch-start.png")
        finally:
            self._close()

    def test_history_sheet_opens(self) -> None:
        page = self._launch()
        try:
            self._unlock(page)
            self._play_nth(page, "arithmetic", 1)
            page.locator("#historyOpenBtn").click()
            page.locator("#historySheet").wait_for(state="visible")
            self.assertIn("刚才的对话", page.locator("#historySheet").inner_text())
            self._shot(page, "ux-history-sheet.png")
        finally:
            self._close()

    def test_layout_probe_across_board_kinds(self) -> None:
        page = self._launch()
        rows = []
        try:
            self._unlock(page)
            for topic_key, index, label in PROBE_CARDS:
                self._play_nth(page, topic_key, index)
                closed = self._layout(page)
                self._shot(page, f"ux-probe-{label}-closed.png")
                self._open_talk(page)
                opened = self._layout(page)
                self._shot(page, f"ux-probe-{label}-talk.png")
                self._close_talk(page)
                rows.append(
                    {
                        "label": label,
                        "topic": topic_key,
                        "index": index,
                        "closed": closed,
                        "talkOpen": opened,
                    }
                )
                self.assertFalse(closed["fallbackVisible"], label)
                self.assertGreater(closed["boardBox"]["h"], 80, (label, closed["boardBox"]))
                self.assertTrue(closed["caption"], label)
                self.assertTrue(closed["talkVisible"], label)
                self.assertFalse(closed["plusVisible"], label)
                self.assertTrue(opened["plusVisible"], label)
                if label == "snap_grid_4x4":
                    self.assertFalse(
                        closed["boardClippedByViewport"],
                        f"4×4 点格在收起我想说时应完整可见: {closed}",
                    )
            (ARTIFACTS / "layout-probe.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        finally:
            self._close()


if __name__ == "__main__":
    unittest.main()
