"""Headless walkthrough of the 18 Author-Agent seed cards.

This VPS has no desktop, so Playwright drives Chromium in headless mode,
unlocks the gate, taps 开始玩 / 按住说话 / 换一题 like a phone, and screenshots
each seed. /api/chat is stubbed so the walk does not call the live Tutor model;
the assertion is that each card mounts the right board and the three seeds
in a topic stay distinct.

Ubuntu 26.04 is newer than Playwright 1.55's official host list. The test
sets PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 before launching.
Install with:

    .venv/bin/pip install -r requirements-e2e.txt
    PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 .venv/bin/playwright install chromium
    PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 .venv/bin/playwright install-deps chromium
"""

from __future__ import annotations

import json
import unittest

from server import author, tutor

from tests.e2e.harness import (
    ARTIFACTS,
    BOARD_SELECTOR,
    START_CAPTION,
    HeadlessPhoneTests,
)


class SeedWalkthroughTests(HeadlessPhoneTests):
    def test_gate_redirects_without_cookie(self) -> None:
        page = self._launch()
        try:
            page.unroute("**/api/chat")
            page.goto(self.base + "/", wait_until="domcontentloaded")
            page.wait_for_url("**/gate.html")
            self.assertIn("验证码", page.locator("body").inner_text())
        finally:
            self._close()

    def test_eighteen_seeds_mount_on_phone_viewport(self) -> None:
        catalog = author.generated_seed_catalog()
        self.assertTrue(catalog.get("complete"), "seed catalog must be complete")
        page = self._launch()
        rows = []
        try:
            self._unlock(page)
            for topic in tutor.TOPICS:
                cards = author.seed_variants(topic.key)
                self.assertEqual(len(cards), 3, topic.key)
                try:
                    self._choose_topic(page, topic.name)
                    seen = []
                    for index, card in enumerate(cards, 1):
                        kind = card["board"]["kind"]
                        selector = BOARD_SELECTOR[kind]
                        self._open_next_seed(page)
                        self._wait_seed(page, selector)
                        snap = self._snapshot(page)
                        shot = ARTIFACTS / f"{topic.key}-{index}-{kind}.png"
                        page.screenshot(path=str(shot), full_page=False)
                        self.assertTrue(shot.exists(), shot)
                        self.assertGreater(shot.stat().st_size, 8_000, shot)
                        self.assertNotIn(START_CAPTION, snap["caption"])
                        self.assertTrue(snap["caption"], topic.key)
                        self.assertIn(kind, snap["kind"], (topic.key, index, snap))
                        self.assertNotIn(snap["identity"], seen, (topic.key, index, seen, snap))
                        seen.append(snap["identity"])
                        rows.append(
                            {
                                "topic": topic.key,
                                "index": index,
                                "expected_kind": kind,
                                "hook": card["hook"],
                                "caption": snap["caption"],
                                "screenshot": shot.name,
                            }
                        )
                    self._open_next_seed(page)
                    self._wait_seed(page, BOARD_SELECTOR[cards[0]["board"]["kind"]])
                    wrap = self._snapshot(page)
                    self.assertEqual(
                        wrap["identity"],
                        seen[0],
                        f"{topic.key} 第四次换一题应回到第一题，得到 {wrap}",
                    )
                except Exception:
                    fail = ARTIFACTS / f"fail-{topic.key}.png"
                    try:
                        page.screenshot(path=str(fail), full_page=False)
                    except Exception:
                        pass
                    raise
            (ARTIFACTS / "manifest.json").write_text(
                json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(len(rows), 18)
        finally:
            self._close()


if __name__ == "__main__":
    unittest.main()
