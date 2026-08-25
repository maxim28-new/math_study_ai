"""Headless checks for the V2 workshop phone landscape gate."""

from __future__ import annotations

import time
import unittest

from tests.e2e.harness import HeadlessPhoneTests
from server.config import settings


SHELL_JS = """() => ({
  landscape: document.documentElement.classList.contains('is-landscape'),
  portrait: document.documentElement.classList.contains('is-portrait'),
  cw: document.documentElement.classList.contains('force-landscape-cw'),
  ccw: document.documentElement.classList.contains('force-landscape-ccw'),
  gateHidden: !!(document.getElementById('rotateGate')?.hidden),
  gateDisplay: getComputedStyle(document.getElementById('rotateGate')).display,
  hintHidden: !!(document.getElementById('hintBar')?.hidden),
  hintText: (document.getElementById('hintBar')?.innerText || '').trim(),
  inner: { w: window.innerWidth, h: window.innerHeight },
  app: (() => {
    const el = document.getElementById('app');
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  })(),
})"""


class V2WorkshopPhoneTests(HeadlessPhoneTests):
    def _open_v2(self, page):
        page.goto(self.base + "/v2/", wait_until="domcontentloaded")
        if "gate.html" in page.url:
            page.fill("#codeInput", settings.access_code or "maxim")
            page.click("#unlockBtn")
            page.wait_for_url("**/v2/**")
        page.wait_for_selector("#workshop")

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
            signatures = {
                (
                    item["landscape"],
                    item["portrait"],
                    item["cw"],
                    item["ccw"],
                    item["gateHidden"],
                    item["hintHidden"],
                )
                for item in samples
            }
            self.assertEqual(len(signatures), 1, samples)
            last = samples[-1]
            self.assertTrue(last["landscape"])
            self.assertFalse(last["portrait"])
            self.assertTrue(last["cw"] or last["ccw"])
            self.assertTrue(last["gateHidden"])
            self.assertEqual(last["gateDisplay"], "none")
            self.assertFalse(last["hintHidden"])
            self.assertIn("按住一堆积木", last["hintText"])
            self._shot(page, "v2-forced-landscape.png")
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
