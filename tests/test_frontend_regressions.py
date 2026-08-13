from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


class FrontendRegressionTests(unittest.TestCase):
    def test_web_assets_are_cache_busted(self):
        html = read("web/index.html")

        self.assertIn('href="/styles.css?v=', html)
        self.assertIn('src="/app.js?v=', html)

    def test_web_reasoning_layout_supports_old_and_new_dom_shapes(self):
        css = read("web/styles.css")

        self.assertIn(".msg.tutor > .reasoning", css)
        self.assertIn(".msg.tutor > .bubble", css)
        self.assertIn(".messages.hide-reasoning .reasoning", css)

    def test_web_reasoning_toggle_filters_before_accumulating(self):
        app = read("web/app.js")

        self.assertIn('setReasoningVisibility(state.showReasoning);', app)
        self.assertIn('if (!state.showReasoning) continue;', app)
        self.assertIn('removeReasoningBlocks();', app)

    def test_web_voice_uses_manual_continuous_final_session(self):
        app = read("web/app.js")

        self.assertIn("recognition.interimResults = false;", app)
        self.assertIn("recognition.continuous = true;", app)
        self.assertIn("voiceWanted", app)
        self.assertIn("finishVoiceSession()", app)

    def test_web_is_kid_h5_chat_shell(self):
        html = read("web/index.html")
        css = read("web/styles.css")
        app = read("web/app.js")

        self.assertIn('viewport-fit=cover', html)
        self.assertIn('apple-mobile-web-app-capable', html)
        self.assertIn('id="gearBtn"', html)
        self.assertIn('id="drawer"', html)
        self.assertIn('id="plusBtn"', html)
        self.assertIn('id="attachSheet"', html)
        self.assertNotIn('grid-template-columns: 320px 1fr', css)
        self.assertIn("100dvh", css)
        self.assertIn(".sheet-handle", css)
        self.assertIn("function openDrawer()", app)
        self.assertIn("visualViewport", app)
        self.assertIn('HOST", "0.0.0.0"', read("server/config.py"))


if __name__ == "__main__":
    unittest.main()
