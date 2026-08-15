from pathlib import Path
import subprocess
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

    def test_web_voice_uses_tap_to_talk_dock(self):
        html = read("web/index.html")
        css = read("web/styles.css")
        app = read("web/app.js")
        self.assertIn('id="voiceDock"', html)
        self.assertIn('id="voiceTalkBtn"', html)
        self.assertIn(".voice-talk-btn", css)
        self.assertIn("function initVoice(", app)
        self.assertIn("MediaRecorder", app)
        self.assertIn("/api/transcribe", app)
        self.assertIn("点一下，跟小欧说", html)

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
        self.assertIn("手机版", html)
        self.assertIn("no-store", read("server/app.py"))
        self.assertIn("RedirectResponse", read("server/app.py"))
        self.assertIn('HOST", "0.0.0.0"', read("server/config.py"))
        self.assertIn('id="topicChip"', html)
        self.assertIn('id="topicSheet"', html)
        self.assertIn(".topic-chip", css)
        self.assertIn("function openTopicSheet(", app)
        self.assertNotIn("选好左边的主题", app)

    def test_explore_kickoff_prefers_snap_grid(self):
        tutor = read("server/tutor.py")
        self.assertIn("第一问优先用可动手的 snap_grid", tutor)
        self.assertIn('"type":"snap_grid"', tutor)

    def test_activity_state_js_rules(self):
        proc = subprocess.run(
            ["node", str(ROOT / "tests" / "activity_state_test.js")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("activity_state_test.js ok", proc.stdout)

    def test_activity_state_js_has_no_konva(self):
        src = read("web/activity/state.js")
        self.assertNotIn("Konva", src)
        self.assertIn("parseSnapGrid", src)
        self.assertIn("detectMilestone", src)

    def test_web_snap_grid_assets_are_wired(self):
        html = read("web/index.html")
        self.assertIn("cdn.jsdelivr.net/npm/konva@9", html)
        self.assertIn('src="/activity/state.js?v=', html)
        self.assertIn('src="/activity/snap-grid.js?v=', html)
        self.assertIn('src="/app.js?v=', html)
        konva_at = html.find("konva@9")
        state_at = html.find("/activity/state.js")
        snap_at = html.find("/activity/snap-grid.js")
        app_at = html.find("/app.js")
        self.assertTrue(0 < konva_at < state_at < snap_at < app_at)

    def test_drawing_guide_teaches_snap_grid(self):
        guide = read("server/tutor.py")
        self.assertIn('"type":"snap_grid"', guide)
        self.assertIn("board_full", guide)
        self.assertIn("tiles_exhausted", guide)
        self.assertIn("不要祝贺", guide)
        self.assertIn('{"type":"dots"', guide)
        self.assertIn('{"type":"square_layers"', guide)
        self.assertIn('{"type":"bars"', guide)

    def test_app_js_routes_snap_grid(self):
        app = read("web/app.js")
        self.assertIn('"snap_grid"', app)
        self.assertIn("renderSnapGridPlaceholder", app)
        css = read("web/styles.css")
        self.assertIn(".snap-grid-stage", css)
        self.assertIn("touch-action: none", css)

    def test_app_js_hydrates_and_freezes_snap_grid(self):
        app = read("web/app.js")
        css = read("web/styles.css")
        self.assertIn("function hydrateSnapGrids(", app)
        self.assertIn("function freezeLiveActivities(", app)
        self.assertIn("onSnapGridSettled", app)
        self.assertIn("MILESTONE_DEBOUNCE_MS = 400", app)
        self.assertIn("function sendActivityMilestone(", app)
        self.assertIn("activity-status", app)
        self.assertIn("function clearActivitySession(", app)
        self.assertIn("clearActivitySession()", app)
        self.assertIn("renderMilestoneStatus", app)
        self.assertIn("if (hasGrid) freezeLiveActivities()", app)
        self.assertIn(".msg.child .bubble .activity-status", css)

    def test_app_js_appends_board_note_on_typed_send(self):
        app = read("web/app.js")
        self.assertIn("当前学具盘面", app)
        self.assertIn("contentForModel", app)

    def test_explore_stage_shell(self):
        html = read("web/index.html")
        css = read("web/styles.css")
        app = read("web/app.js")
        for token in (
            'id="exploreStage"',
            'id="startPlayBtn"',
            'id="tutorCaption"',
            'id="stageHost"',
            'id="talkBtn"',
            'id="historySheet"',
            'id="helpSheet"',
            'id="modeSelect"',
            'id="undoTileBtn"',
            'id="expandStageBtn"',
            'id="trayCount"',
            "开始玩",
        ):
            self.assertIn(token, html)
        self.assertNotIn('id="modeSwitch"', html)
        self.assertIn(".layout-explore", css)
        self.assertIn(".play-stage", css)
        self.assertIn(".play-stage.is-expanded", css)
        self.assertIn("function remountStage(", app)
        self.assertIn("function toggleStageExpand(", app)
        self.assertIn("function startPlay(", app)
        self.assertIn("tutorCaption", app)
        self.assertIn("activity-stage", read("server/app.py"))
        self.assertIn("v=20260815-caption", html)
        self.assertIn('location.replace("/gate.html")', app)

    def test_static_block_diagrams_use_rounded_squares(self):
        app = read("web/app.js")
        dots = app[app.find("function diagramDots"):app.find("function layerHighlight")]
        layers = app[app.find("function drawSquareDots"):app.find("function diagramSquareLayers")]
        self.assertIn("<rect", dots)
        self.assertNotIn("<circle", dots)
        self.assertIn("tileRect(", layers)
        self.assertNotIn("<circle", layers)
        self.assertIn("function softenBareLatex(", app)
        self.assertIn("function tileRect(", app)

    def test_caption_shows_full_math_text(self):
        css = read("web/styles.css")
        app = read("web/app.js")
        state_js = read("web/activity/state.js")
        self.assertIn("#tutorCaption", css)
        cap_css = css[css.find("#tutorCaption"):css.find("#tutorCaption .katex")]
        self.assertNotIn("7.4em", cap_css)
        self.assertNotIn("max-height", cap_css)
        self.assertIn("el.innerHTML", app)
        self.assertIn("softenBareLatex", state_js)
        self.assertIn("function parseDiagramJson(", state_js)
        self.assertIn("parseDiagramJson", app)

    def test_snap_grid_undo_api(self):
        src = read("web/activity/snap-grid.js")
        self.assertIn("undo:", src)
        self.assertIn("canUndo:", src)
        self.assertIn("Math.min(cellCap", src)


if __name__ == "__main__":
    unittest.main()
