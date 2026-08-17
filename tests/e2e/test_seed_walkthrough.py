"""Headless walkthrough of the 18 Author-Agent seed cards.

This VPS has no desktop, so Playwright drives Chromium in headless mode,
unlocks the gate, taps 开始玩 / 我想说 / 换一题 like a phone, and screenshots
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
import os
import socket
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("PLAYWRIGHT_HOST_PLATFORM_OVERRIDE", "ubuntu24.04-x64")

from uvicorn import Config, Server

from server.app import app
from server import author, tutor
from server.config import settings

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

BOARD_SELECTOR = {
    "geometry_compass": ".geometry-compass-board",
    "snap_grid": ".snap-grid-stage, figure.diagram.snap-grid, #stageHost canvas",
    "layer_sum": ".layer-pile-board",
    "static_diagram": "figure.diagram, #stageHost svg",
    "color_sequence": ".color-seq-board",
    "path_count": ".path-board",
}

START_CAPTION = "点开始玩，把方块拖进格子"


def playwright_mod():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


def wait_port(port: int, timeout: float = 8.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"test server did not start on {port}")


class SeedWalkthroughTests(unittest.TestCase):
    server = None
    thread = None
    port = 0
    base = ""

    @classmethod
    def setUpClass(cls) -> None:
        if playwright_mod() is None:
            raise unittest.SkipTest("playwright 未安装：pip install -r requirements-e2e.txt")
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        config = Config(app=app, host="127.0.0.1", port=cls.port, log_level="warning")
        cls.server = Server(config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        wait_port(cls.port)
        cls.base = f"http://127.0.0.1:{cls.port}"
        ARTIFACTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server is not None:
            cls.server.should_exit = True

    def _launch(self):
        pw_cm = playwright_mod()()
        self._pw = pw_cm.__enter__()
        try:
            browser = self._pw.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
        except Exception as exc:
            pw_cm.__exit__(None, None, None)
            raise unittest.SkipTest(f"Chromium 无法启动: {exc}") from exc
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            locale="zh-CN",
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()
        page.set_default_timeout(15000)
        page.route("**/api/chat", self._stub_chat)
        self._pw_cm = pw_cm
        self._browser = browser
        self._context = context
        return page

    def _close(self) -> None:
        try:
            self._context.close()
            self._browser.close()
        finally:
            self._pw_cm.__exit__(None, None, None)

    @staticmethod
    def _stub_chat(route) -> None:
        route.fulfill(
            status=200,
            headers={"content-type": "text/event-stream; charset=utf-8"},
            body=":\n\n",
        )

    def _unlock(self, page) -> None:
        page.goto(self.base + "/", wait_until="domcontentloaded")
        page.wait_for_url("**/gate.html")
        page.fill("#codeInput", settings.access_code or "maxim")
        page.click("#unlockBtn")
        page.wait_for_selector("#startPlayBtn", timeout=15000)
        page.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("#startPlayBtn", timeout=15000)

    def _wait_idle(self, page) -> None:
        page.wait_for_function(
            "() => !document.querySelector('#sendBtn')?.disabled",
            timeout=15000,
        )

    def _close_talk(self, page) -> None:
        page.evaluate(
            """() => {
                const app = document.querySelector('.app');
                const btn = document.querySelector('#talkBtn');
                if (app && btn && app.classList.contains('talk-open')) btn.click();
            }"""
        )
        page.wait_for_timeout(200)

    def _choose_topic(self, page, name: str) -> None:
        self._wait_idle(page)
        self._close_talk(page)
        page.locator("#topicChip").click()
        page.locator("#topicList .topic-option", has_text=name).click()
        page.wait_for_function(
            "name => document.querySelector('#topicLine')?.textContent.includes(name)",
            arg=name,
            timeout=8000,
        )
        page.wait_for_timeout(400)

    def _open_next_seed(self, page) -> None:
        self._wait_idle(page)
        wrap = page.locator("#startPlayWrap")
        if wrap.is_visible():
            page.locator("#startPlayBtn").click()
            return
        plus = page.locator("#plusBtn")
        if not plus.is_visible():
            talk = page.locator("#talkBtn")
            talk.wait_for(state="visible", timeout=8000)
            talk.click()
            plus.wait_for(state="visible", timeout=8000)
        plus.click()
        nxt = page.locator("#newQuestionBtn")
        nxt.wait_for(state="visible", timeout=8000)
        nxt.click()

    def _wait_seed(self, page, selector: str) -> None:
        page.wait_for_selector(".play-stage.is-playing", timeout=12000)
        page.wait_for_function(
            """() => {
                const cap = document.querySelector('#tutorCaption');
                const host = document.querySelector('#stageHost');
                const fallback = document.querySelector('.board-safe-fallback');
                const text = (cap && cap.textContent || '').trim();
                return text && !text.includes('点开始玩') && host && host.childElementCount > 0
                    && !(fallback && fallback.offsetParent !== null);
            }""",
            timeout=12000,
        )
        page.wait_for_selector(selector, timeout=12000)
        self._wait_idle(page)
        self._close_talk(page)
        page.wait_for_timeout(500)

    def _snapshot(self, page) -> dict[str, str]:
        return page.evaluate(
            """() => {
                const cap = (document.querySelector('#tutorCaption')?.innerText || '').trim();
                const host = document.querySelector('#stageHost');
                const kinds = [];
                if (host?.querySelector('.geometry-compass-board')) kinds.push('geometry_compass');
                if (host?.querySelector('.snap-grid-stage, figure.diagram.snap-grid')) kinds.push('snap_grid');
                if (host?.querySelector('.layer-pile-board')) kinds.push('layer_sum');
                if (host?.querySelector('.color-seq-board')) kinds.push('color_sequence');
                if (host?.querySelector('.path-board')) kinds.push('path_count');
                if (host?.querySelector('figure.diagram') && !kinds.includes('snap_grid')) kinds.push('static_diagram');
                return {
                    caption: cap,
                    kind: kinds.join(',') || 'unknown',
                    identity: cap + '|' + kinds.join(','),
                };
            }"""
        )

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
