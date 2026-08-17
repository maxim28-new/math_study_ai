"""Shared Playwright phone-viewport harness for kid H5 checks."""

from __future__ import annotations

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

LAYOUT_JS = """() => {
  const vis = (el) => !!(el && el.getClientRects().length);
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      bottom: Math.round(r.bottom), right: Math.round(r.right),
    };
  };
  const cap = document.querySelector('#tutorCaption');
  const vp = document.querySelector('#boardViewport');
  const host = document.querySelector('#stageHost');
  const app = document.querySelector('.app');
  const talk = document.querySelector('#talkBtn');
  const plus = document.querySelector('#plusBtn');
  const send = document.querySelector('#doodleSendBtn');
  const boardEl = host && (
    host.querySelector('canvas') || host.querySelector('svg') || host.querySelector('.semantic-board') || host
  );
  const capBox = box(cap);
  const vpBox = box(vp);
  const boardBox = box(boardEl);
  const vh = window.innerHeight;
  return {
    viewport: { w: window.innerWidth, h: vh },
    talkOpen: !!(app && app.classList.contains('talk-open')),
    caption: (cap && cap.innerText || '').trim(),
    captionBox: capBox,
    captionClipped: !!(cap && cap.scrollHeight > cap.clientHeight + 2),
    viewportBox: vpBox,
    boardBox,
    boardClippedByViewport: !!(vpBox && boardBox && (
      boardBox.bottom > vpBox.bottom + 6 || boardBox.right > vpBox.right + 6
    )),
    boardClippedByWindow: !!(boardBox && boardBox.bottom > vh + 6),
    talkVisible: vis(talk),
    plusVisible: vis(plus),
    sendVisible: vis(send),
    sendDisabled: !!(send && send.disabled),
    startPlayVisible: vis(document.querySelector('#startPlayWrap')),
    fallbackVisible: vis(document.querySelector('.board-safe-fallback')),
    tray: (document.querySelector('#trayCount') || {}).textContent || '',
    pathStatus: (document.querySelector('.path-board-status') || {}).textContent || '',
    compassStatus: (document.querySelector('.geometry-compass-status') || {}).textContent || '',
  };
}"""


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


def _last_user_blob(body: dict) -> dict:
    messages = body.get("messages") or []
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        has_image = False
        text = ""
        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "image_url":
                    has_image = True
                if part.get("type") == "text":
                    text = str(part.get("text") or "")
        elif isinstance(content, str):
            text = content
        return {"has_image": has_image, "text": text}
    return {"has_image": False, "text": ""}


class HeadlessPhoneTests(unittest.TestCase):
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
        self.chat_posts = []
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

    def _stub_chat(self, route) -> None:
        if route.request.method == "POST":
            try:
                body = route.request.post_data_json() or {}
            except Exception:
                body = {}
            blob = _last_user_blob(body)
            self.chat_posts.append(
                {
                    "kickoff": bool(body.get("kickoff")),
                    "has_image": blob["has_image"],
                    "text": blob["text"][:180],
                }
            )
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

    def _open_talk(self, page) -> None:
        plus = page.locator("#plusBtn")
        if plus.is_visible():
            return
        talk = page.locator("#talkBtn")
        talk.wait_for(state="visible", timeout=8000)
        talk.click()
        plus.wait_for(state="visible", timeout=8000)

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
            self._open_talk(page)
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
        page.wait_for_timeout(400)

    def _play_nth(self, page, topic_key: str, index: int = 1) -> dict:
        topic = next(item for item in tutor.TOPICS if item.key == topic_key)
        cards = author.seed_variants(topic_key)
        self.assertGreaterEqual(len(cards), index, topic_key)
        line = page.locator("#topicLine").inner_text()
        playing = (
            page.locator(".play-stage.is-playing").count() > 0
            and not page.locator("#startPlayWrap").is_visible()
        )
        if playing and topic.name in line:
            other = next(item for item in tutor.TOPICS if item.key != topic_key)
            self._choose_topic(page, other.name)
        self._choose_topic(page, topic.name)
        for step in range(index):
            kind = cards[step]["board"]["kind"]
            self._open_next_seed(page)
            self._wait_seed(page, BOARD_SELECTOR[kind])
        return cards[index - 1]

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

    def _layout(self, page) -> dict:
        return page.evaluate(LAYOUT_JS)

    def _shot(self, page, name: str) -> Path:
        path = ARTIFACTS / name
        page.screenshot(path=str(path), full_page=False)
        return path
