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

    def test_explore_kickoff_follows_author_card(self):
        tutor = read("server/tutor.py")
        self.assertIn("EXPLORE_KICKOFF_WITH_CARD", tutor)
        self.assertIn("不要所有主题都从 9 块摆正方形开始", tutor)
        self.assertIn("有题卡时以题卡为准", tutor)

    def test_activity_state_js_rules(self):
        proc = subprocess.run(
            ["node", str(ROOT / "tests" / "activity_state_test.js")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("activity_state_test.js ok", proc.stdout)

    def test_semantic_board_state_js_rules(self):
        proc = subprocess.run(
            ["node", str(ROOT / "tests" / "semantic_board_test.js")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("semantic_board_test.js ok", proc.stdout)

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
        self.assertIn('{"type":"stairs"', guide)
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
        self.assertIn("XiaoouSemanticBoard.formatSnapshot", app)
        self.assertIn("contentForModel", app)

    def test_explore_stage_shell(self):
        html = read("web/index.html")
        css = read("web/styles.css")
        app = read("web/app.js")
        for token in (
            'id="exploreStage"',
            'id="startPlayBtn"',
            'id="tutorCaption"',
            'id="captionBar"',
            'id="stageHost"',
            'id="historyOpenBtn"',
            'id="talkBtn"',
            'id="historySheet"',
            'id="historyMount"',
            'id="attachSheet"',
            'id="hintBtn"',
            'id="newQuestionBtn"',
            'id="doodleCanvas"',
            'id="doodleToolbar"',
            'id="doodleSendBtn"',
            'id="doodleEraserBtn"',
            'id="doodleResetBtn"',
            'id="boardInteractBtn"',
            'id="boardDrawBtn"',
            'id="modeSelect"',
            'id="undoTileBtn"',
            'id="trayCount"',
            "开始玩",
        ):
            self.assertIn(token, html)
        self.assertNotIn('id="modeSwitch"', html)
        self.assertNotIn('id="helpSheet"', html)
        self.assertNotIn('id="homeworkBtn"', html)
        self.assertNotIn("我有作业", html)
        self.assertNotIn("打开画板", html)
        self.assertIn(".layout-explore", css)
        self.assertIn("solve-workspace", html)
        self.assertIn(".play-stage", css)
        self.assertIn(".play-stage.is-drawing", css)
        self.assertIn(".caption-scroll", css)
        self.assertIn("flex: 3 1 0", css)
        self.assertIn("flex: 7 1 0", css)
        self.assertIn("#tutorCaption {\n  margin: 0;\n  font-size: 13px;", css)
        self.assertIn(".stage-host .diagram figcaption { display: none; }", css)
        self.assertIn("flex: 1 1 0", css)
        self.assertIn(".doodle-canvas", css)
        self.assertIn(".doodle-toolbar", css)
        self.assertIn(".child-dock", css)
        self.assertIn("function remountStage(", app)
        self.assertIn("function setBoardMode(", app)
        self.assertIn("function captureBoardImage(", app)
        self.assertIn("function sendDoodleToTutor(", app)
        self.assertIn("function closeAttachSheet(", app)
        self.assertIn('classList.toggle("is-drawing"', app)
        self.assertIn("function startPlay(", app)
        self.assertIn("tutorCaption", app)
        self.assertIn("activity-stage", read("server/app.py"))
        self.assertIn("v=20260816-boardv3j", html)
        self.assertIn("html2canvas", html)
        self.assertIn("function initDoodle(", app)
        self.assertIn('id="boardViewport"', html)
        self.assertIn('id="doodleLineBtn"', html)
        self.assertIn('id="doodleFitBtn"', html)
        self.assertIn('id="doodleToolboxBtn"', html)
        self.assertIn("doodle-toolbox", html)
        self.assertIn("doodle-width", html)
        self.assertIn("function setDoodleToolboxOpen(", app)
        self.assertIn("function applyWorldTransform(", app)
        self.assertIn("function clientToWorld(", app)
        self.assertIn("function worldToCanvas(", app)
        self.assertIn("function doodleAnchorEl(", app)
        self.assertIn("function applyPinch(", app)
        self.assertIn("widthNorm: currentDoodleWidthNorm()", app)
        self.assertIn("resetDoodleView()", app[app.find("async function sendDoodleToTutor"):app.find("function initDoodle")])
        self.assertIn('kind: doodle.tool === "line" ? "line" : "pen"', app)
        self.assertIn(".explore-stage.is-drawing .play-stage { flex: 8.6 1 0; }", css)
        self.assertNotIn("padding-bottom: 54px", css)
        self.assertIn("看全图", html)
        self.assertIn("直线", html)
        self.assertIn('id="voiceUndoBtn"', html)
        self.assertIn("function undoLastVoice(", app)
        self.assertIn("清空", html)
        self.assertIn(".voice-row", css)
        self.assertIn(".voice-clear-btn", css)
        self.assertNotIn("说错了，撤销刚才", html)
        self.assertIn("小提示", html)
        self.assertIn("拍给我", html)
        self.assertIn("发给小欧", html)
        self.assertNotIn('id="historyBtn"', html)
        self.assertIn("刚才的对话", html)
        self.assertNotIn('aria-label="放大画板"', html)
        self.assertNotIn("展开全文", html)
        self.assertIn("function openHistorySheet(", app)
        self.assertNotIn("function toggleCaptionOpen(", app)
        self.assertIn(".app.layout-explore > .messages { display: none; }", css)
        self.assertIn(".say-panel", css)
        self.assertIn("小欧说", html)
        self.assertIn("我想说", html)
        self.assertIn("发画板", html)
        self.assertNotIn("小欧在说", html)
        self.assertNotIn("想跟小欧说", html)
        self.assertNotIn('id="talkCloseBtn"', html)
        self.assertNotIn(".app.layout-explore.talk-open .talk-btn { display: none; }", css)
        self.assertNotIn('id="expandStageBtn"', html)
        self.assertNotIn("function toggleStageExpand(", app)
        self.assertNotIn("captionSheetBody", html)
        self.assertNotIn("plusHelpGroup", html)
        self.assertNotIn("换种方法", html)
        self.assertIn('id="authorSelect"', html)
        self.assertIn("/api/author", app)
        self.assertIn("function fetchAuthorCard(", app)
        self.assertIn("function friendlyAuthorError(", app)
        self.assertIn("这道题再想一会儿，点开始玩再试一次。", app)
        self.assertIn("seed_only", app)
        start = app[app.find("async function startPlay"):app.find("function placeMessages")]
        self.assertIn("fetchAuthorCard", start)
        self.assertIn("friendlyAuthorError", start)
        self.assertIn("alreadyStarted", start)
        self.assertNotIn("DEFAULT_SNAP_GRID", start)
        self.assertIn("function rememberCurrentWorkspace(", app)
        self.assertIn("function applyWorkspace(", app)
        self.assertIn("function chooseTopic(", app)
        self.assertIn("topicWorkspaces", app)
        self.assertNotIn("换主题会开始新的探究", app)
        self.assertIn("45000", app)
        self.assertNotIn("70000", app)
        choose = app[app.find("function chooseTopic"):app.find("function openAttachSheet")]
        self.assertIn("rememberCurrentWorkspace", choose)
        self.assertIn("applyWorkspace", choose)
        self.assertNotIn("prefetchAuthor", choose)
        self.assertNotIn("problemCard = null", choose)
        self.assertIn('location.replace("/gate.html")', app)
        self.assertNotIn("Load failed", start)

    def test_board_v3_assets_and_renderers(self):
        html = read("web/index.html")
        app = read("web/app.js")
        css = read("web/styles.css")
        board_state = read("web/board/state.js")
        layer_pile = read("web/board/layer-pile.js")
        path_board = read("web/board/path-board.js")
        geometry_board = read("web/board/geometry-compass.js")
        color_seq = read("web/board/color-sequence.js")
        self.assertIn("/board/state.js", html)
        self.assertIn("/board/layer-pile.js", html)
        self.assertIn("/board/path-board.js", html)
        self.assertIn("/board/geometry-compass.js", html)
        self.assertIn("/board/color-sequence.js", html)
        self.assertIn("/terms/glossary.js", html)
        self.assertIn("/terms/scaffold.js", html)
        self.assertLess(html.find("/terms/glossary.js"), html.find("/terms/scaffold.js"))
        self.assertLess(html.find("/terms/scaffold.js"), html.find("/app.js"))
        self.assertLess(html.find("/board/state.js"), html.find("/board/layer-pile.js"))
        self.assertLess(html.find("/board/layer-pile.js"), html.find("/board/path-board.js"))
        self.assertLess(html.find("/board/path-board.js"), html.find("/board/geometry-compass.js"))
        self.assertLess(html.find("/board/geometry-compass.js"), html.find("/board/color-sequence.js"))
        self.assertLess(html.find("/board/color-sequence.js"), html.find("/app.js"))
        self.assertIn("function mountBoardV3(", app)
        self.assertIn("card.board", app)
        self.assertIn("upgradeLegacyPatternBoard", app)
        self.assertNotIn("function coerceStairsSpec(", app)
        self.assertIn("layer_sum", board_state)
        self.assertIn("path_count", board_state)
        self.assertIn("geometry_compass", board_state)
        self.assertIn("color_sequence", board_state)
        self.assertIn("document.createElement", layer_pile)
        self.assertNotIn("<svg", layer_pile)
        self.assertIn("new Konva.Stage", path_board)
        self.assertIn("mountGeometryCompass", geometry_board)
        self.assertIn("equilateral_triangle", geometry_board)
        self.assertIn('preserveAspectRatio: "xMidYMid meet"', geometry_board)
        self.assertIn('viewBox: "-70 -20 500 360"', geometry_board)
        self.assertIn(".layer-pile-item", css)
        self.assertIn(".path-board-canvas", css)
        self.assertIn(".geometry-compass-canvas", css)
        self.assertIn(".color-seq-item", css)
        self.assertIn(".color-seq-item.is-hidden", css)
        self.assertIn("#e23b3b", color_seq)
        self.assertIn("#3b6be2", color_seq)
        self.assertIn("mountColorSequence", color_seq)
        self.assertIn('unit: ["red", "red", "blue"]', color_seq)
        self.assertIn(".stage-host:has(.semantic-board) { align-items: stretch; }", css)
        self.assertIn("preserveAspectRatio", read("web/board/geometry-compass.js"))
        self.assertIn("function highlight(", geometry_board)
        self.assertIn(".term-chip", css)
        self.assertIn('id="termCard"', html)
        self.assertIn("function formatCaption(", read("web/terms/scaffold.js"))
        self.assertIn("圆心", read("web/terms/glossary.js"))
        self.assertIn("seen_terms", app)

    def test_semantic_cards_disable_model_draw_commands(self):
        tutor = read("server/tutor.py")
        author = read("server/author.py")
        self.assertIn("SEMANTIC_BOARD_GUIDE", tutor)
        self.assertIn("不要输出任何 xiaoou-draw", tutor)
        self.assertIn("涂鸦直接发给你", tutor)
        self.assertIn("数学画板 V3", author)
        self.assertIn('"kind":"layer_sum"', author)
        self.assertIn('"kind":"path_count"', author)
        self.assertIn('"kind":"geometry_compass"', author)
        self.assertIn('"kind":"color_sequence"', author)
        self.assertIn("不允许输出旧 semantic_board", author)
        self.assertNotIn("STAIR_HINTS", author)

    def test_explore_board_protocol_is_single_source_and_hidden_from_chat(self):
        app = read("web/app.js")
        author = read("server/author.py")
        tutor = read("server/tutor.py")
        stream = app[app.find("async function streamAssistant"):app.find("function setStreaming")]
        self.assertIn("stripBoardProtocol", stream)
        self.assertNotIn("syncStageFromTutor(acc)", stream)
        self.assertIn("parseBoardLikeJson", app)
        self.assertIn("board-safe-fallback", app)
        self.assertIn("validate_board_v3", author)
        self.assertIn("_board_controlled_prompt", tutor)

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
        self.assertIn("function diagramStairs(", app)
        self.assertIn('"stairs"', app)
        stairs = app[app.find("function diagramStairs"):app.find("function layerHighlight")]
        self.assertIn("tileRect(", stairs)
        self.assertNotIn("<circle", stairs)

    def test_explore_refresh_restores_last_caption(self):
        app = read("web/app.js")
        html = read("web/index.html")
        self.assertEqual(app.count("function lastTutorCaption("), 1)
        self.assertIn("function restoreExploreCaption(", app)
        self.assertIn("function messagePlainText(", app)
        self.assertIn("caption: state.caption || lastTutorCaption()", app)
        self.assertIn("caption: state.caption || lastTutorCaption(),", app)
        hist = app[app.find("function renderHistory"):app.find("async function loadConfig")]
        self.assertIn("restoreExploreCaption()", hist)
        self.assertIn("mountFromCard(state.problemCard)", hist)
        card_branch = hist.split("if (state.messages.length === 0)")[0]
        self.assertIn("restoreExploreCaption()", card_branch)
        self.assertNotIn("resetExploreEmpty()", card_branch)
        self.assertNotIn("syncStageFromTutor(", hist)
        restore = app[app.find("function restoreExploreCaption"):app.find("function showStartPlay")]
        self.assertIn("setCaption(cap)", restore)
        self.assertIn("点开始玩，把方块拖进格子", app)
        self.assertNotIn('setCaption("点开始玩，把方块拖进格子")', hist)
        self.assertIn("v=20260816-boardv3j", html)

    def test_workspace_keeps_full_prompt_and_history_available(self):
        css = read("web/styles.css")
        app = read("web/app.js")
        state_js = read("web/activity/state.js")
        self.assertIn("#tutorCaption", css)
        cap_css = css[css.find("#tutorCaption"):css.find("#tutorCaption .katex")]
        self.assertNotIn("7.4em", cap_css)
        self.assertIn("white-space: normal", cap_css)
        self.assertIn(".caption-scroll", css)
        self.assertIn("function openHistorySheet(", app)
        self.assertIn("function setBoardMode(", app)
        self.assertNotIn("captionSheetBody", app)
        self.assertNotIn("function toggleCaptionOpen(", app)
        self.assertNotIn("zoomFromCaption", app)
        self.assertIn('id="captionBar"', read("web/index.html"))
        self.assertIn("tutorCaption", app)
        self.assertIn("el.innerHTML", app)
        self.assertIn("softenBareLatex", state_js)
        self.assertIn("function parseDiagramJson(", state_js)
        self.assertIn("parseDiagramJson", app)

    def test_snap_grid_undo_api(self):
        src = read("web/activity/snap-grid.js")
        self.assertIn("undo:", src)
        self.assertIn("canUndo:", src)
        self.assertIn("Math.min(cellCap", src)
        self.assertIn('classList.contains("is-playing")', src)


if __name__ == "__main__":
    unittest.main()
