"""Headless checks for the V2 workshop phone landscape gate."""

from __future__ import annotations

import time
import unittest

from tests.e2e.harness import HeadlessPhoneTests
from server.config import settings


SHELL_JS = """() => {
  const root = document.documentElement;
  const app = document.getElementById('app');
  const stage = document.getElementById('stage');
  const canvas = document.getElementById('workshop');
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
  };
  return {
    landscape: root.classList.contains('is-landscape'),
    portrait: root.classList.contains('is-portrait'),
    cw: root.classList.contains('force-landscape-cw'),
    ccw: root.classList.contains('force-landscape-ccw'),
    gateHidden: !!(document.getElementById('rotateGate')?.hidden),
    gateDisplay: getComputedStyle(document.getElementById('rotateGate')).display,
    hintHidden: !!(document.getElementById('hintBar')?.hidden),
    hintText: (document.getElementById('hintBar')?.innerText || '').trim(),
    inner: { w: window.innerWidth, h: window.innerHeight },
    app: box(app),
    stage: box(stage),
    canvasCss: box(canvas),
    canvasBuf: canvas ? { w: canvas.width, h: canvas.height } : null,
  };
}"""

IOS_LIE_JS = """
(() => {
  const widthDesc = Object.getOwnPropertyDescriptor(Window.prototype, 'innerWidth')
    || Object.getOwnPropertyDescriptor(window, 'innerWidth');
  const heightDesc = Object.getOwnPropertyDescriptor(Window.prototype, 'innerHeight')
    || Object.getOwnPropertyDescriptor(window, 'innerHeight');
  const readW = () => widthDesc.get.call(window);
  const readH = () => heightDesc.get.call(window);
  const lying = () => document.documentElement.classList.contains('force-landscape-cw')
    || document.documentElement.classList.contains('force-landscape-ccw');
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    get() {
      const w = readW();
      const h = readH();
      return lying() ? Math.max(w, h) : w;
    },
  });
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    get() {
      const w = readW();
      const h = readH();
      return lying() ? Math.min(w, h) : h;
    },
  });
  if (window.visualViewport) {
    const vvW = Object.getOwnPropertyDescriptor(VisualViewport.prototype, 'width');
    const vvH = Object.getOwnPropertyDescriptor(VisualViewport.prototype, 'height');
    if (vvW && vvH) {
      Object.defineProperty(window.visualViewport, 'width', {
        configurable: true,
        get() { return lying() ? Math.max(readW(), readH()) : vvW.get.call(window.visualViewport); },
      });
      Object.defineProperty(window.visualViewport, 'height', {
        configurable: true,
        get() { return lying() ? Math.min(readW(), readH()) : vvH.get.call(window.visualViewport); },
      });
    }
  }
  const origMM = window.matchMedia.bind(window);
  window.matchMedia = (query) => {
    const media = origMM(query);
    if (String(query).includes('orientation: landscape')) {
      return new Proxy(media, {
        get(target, prop) {
          if (prop === 'matches') return lying() || target.matches;
          const value = Reflect.get(target, prop);
          return typeof value === 'function' ? value.bind(target) : value;
        },
      });
    }
    return media;
  };
  const fire = () => {
    window.dispatchEvent(new Event('resize'));
    window.visualViewport?.dispatchEvent(new Event('resize'));
  };
  new MutationObserver(fire).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['class'],
  });
})();
"""


class V2WorkshopPhoneTests(HeadlessPhoneTests):
    def _open_v2(self, page):
        page.goto(self.base + "/v2/", wait_until="domcontentloaded")
        if "gate.html" in page.url:
            page.fill("#codeInput", settings.access_code or "maxim")
            page.click("#unlockBtn")
            page.wait_for_url("**/v2/**")
        page.wait_for_selector("#workshop")

    def _shell_signature(self, item: dict) -> tuple:
        return (
            item["landscape"],
            item["portrait"],
            item["cw"],
            item["ccw"],
            item["gateHidden"],
            item["hintHidden"],
        )

    def _assert_forced_landscape(self, last: dict) -> None:
        self.assertTrue(last["landscape"], last)
        self.assertFalse(last["portrait"], last)
        self.assertTrue(last["cw"] or last["ccw"], last)
        self.assertTrue(last["gateHidden"], last)
        self.assertEqual(last["gateDisplay"], "none")
        self.assertFalse(last["hintHidden"], last)
        self.assertIn("按住一堆积木", last["hintText"])
        self.assertIsNotNone(last["app"])
        self.assertLess(last["app"]["w"], last["app"]["h"])
        self.assertGreater(last["canvasBuf"]["w"], last["canvasBuf"]["h"])

    def test_portrait_shows_rotate_gate(self) -> None:
        page = self._launch()
        try:
            self._open_v2(page)
            page.locator("#confirmLandscapeBtn").wait_for(state="visible")
            self.assertIn("把手机横过来", page.locator("#rotateGate").inner_text())
            self._shot(page, "v2-portrait-gate.png")
        finally:
            self._close()

    def test_confirm_landscape_does_not_flicker(self) -> None:
        page = self._launch()
        try:
            self._open_v2(page)
            page.locator("#confirmLandscapeBtn").click()
            samples = []
            deadline = time.time() + 2.4
            while time.time() < deadline:
                samples.append(page.evaluate(SHELL_JS))
                page.wait_for_timeout(200)
            signatures = {self._shell_signature(item) for item in samples}
            self.assertEqual(len(signatures), 1, samples)
            self._assert_forced_landscape(samples[-1])
            self._shot(page, "v2-forced-landscape.png")
        finally:
            self._close()

    def test_confirm_landscape_survives_ios_layout_lie(self) -> None:
        page = self._launch()
        try:
            page.add_init_script(IOS_LIE_JS)
            self._open_v2(page)
            page.locator("#confirmLandscapeBtn").wait_for(state="visible")
            page.locator("#confirmLandscapeBtn").click()
            samples = []
            deadline = time.time() + 3.2
            while time.time() < deadline:
                samples.append(page.evaluate(SHELL_JS))
                page.wait_for_timeout(160)
            signatures = {self._shell_signature(item) for item in samples}
            self.assertEqual(len(signatures), 1, samples)
            self._assert_forced_landscape(samples[-1])
            self.assertEqual(samples[0]["inner"]["w"], samples[-1]["inner"]["w"])
            self._shot(page, "v2-forced-landscape-ios-lie.png")
        finally:
            self._close()

    def test_native_landscape_skips_the_gate(self) -> None:
        page = self._launch()
        try:
            page.set_viewport_size({"width": 844, "height": 390})
            self._open_v2(page)
            page.wait_for_timeout(400)
            shell = page.evaluate(SHELL_JS)
            self.assertTrue(shell["landscape"])
            self.assertFalse(shell["cw"])
            self.assertFalse(shell["ccw"])
            self.assertTrue(shell["gateHidden"] or shell["gateDisplay"] == "none")
            self.assertFalse(shell["hintHidden"])
            self._shot(page, "v2-native-landscape.png")
        finally:
            self._close()


if __name__ == "__main__":
    unittest.main()
