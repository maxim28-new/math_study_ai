# 探索学具台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把探索模式改成学具台（立刻可拖的 3×3、活盘钉住、聊天进「对话」），带题模式保持现有聊天壳，方便家长在体验分支上试用。

**Architecture:** 规则函数仍放在无 Konva 的 `web/activity/state.js`。`web/index.html` 增加学具台、旁白、开始玩、对话/帮忙底栏；`web/app.js` 在探索模式把唯一的 live `mountSnapGrid` 挂到 `#stageHost`。带题仍把消息列表当作主列。

**Tech Stack:** 现有原生 JS H5、Konva 9、FastAPI 静态托管、`unittest` + Node assert。

---

### File map

- Create: `docs/superpowers/specs/2026-08-14-explore-stage-design.md`（已写）
- Modify: `web/activity/state.js` — `tutorCaption` / `trayCountLabel` / `sameSnapGrid` / `DEFAULT_SNAP_GRID`
- Modify: `web/activity/snap-grid.js` — 更大格子、`undo`
- Modify: `web/index.html` / `web/styles.css` / `web/app.js`
- Modify: `server/app.py` — 缓存戳 `activity-stage`
- Modify: `tests/activity_state_test.js` / `tests/test_frontend_regressions.py`

---

### Task 1: 规则函数（TDD）

**Files:**
- Test: `tests/activity_state_test.js`
- Modify: `web/activity/state.js`

- [ ] **Step 1: Write failing assertions** in `tests/activity_state_test.js` for `tutorCaption`, `trayCountLabel`, `sameSnapGrid`, `DEFAULT_SNAP_GRID`.
- [ ] **Step 2: Run** `node tests/activity_state_test.js` — expect missing function.
- [ ] **Step 3: Implement** the four helpers in `web/activity/state.js`.
- [ ] **Step 4: Re-run** until `activity_state_test.js ok`.

`tutorCaption` must strip fenced blocks (including unclosed), drop JSON lines containing `"type"`, strip markdown markers, and return the opening sentence(s) ≤ 90 chars.

---

### Task 2: 壳层回归测试（TDD）

**Files:**
- Test: `tests/test_frontend_regressions.py`

- [ ] **Step 1: Add** `test_explore_stage_shell` asserting:
  - html ids: `exploreStage`, `startPlayBtn`, `tutorCaption`, `stageHost`, `talkBtn`, `historySheet`, `helpSheet`, `modeSelect`, `undoTileBtn`, `trayCount`
  - start button text `开始玩`
  - topbar has no `id="modeSwitch"`
  - `v=activity-stage` redirect in `server/app.py`
  - css `.layout-explore` and `.play-stage`
  - app.js has `remountStage` / `startPlay` / `tutorCaption`
- [ ] **Step 2: Run** `python3 -m unittest tests.test_frontend_regressions.FrontendRegressionTests.test_explore_stage_shell -v` — expect FAIL.
- [ ] **Step 3: Do not implement the shell until Task 3–4.** Keep this test red until the DOM exists.

Also update `test_web_assets_are_cache_busted` is already generic (`?v=`). Change redirect and asset query to `activity-stage` / `20260814-stage`.

---

### Task 3: snap_grid undo + 更大格子

**Files:**
- Modify: `web/activity/snap-grid.js`
- Test: `tests/test_frontend_regressions.py` (`test_snap_grid_undo_api`)

- [ ] Assert `snap-grid.js` returns `undo` and `canUndo`, and uses cell cap `72`.
- [ ] Implement undo stack on `dragend`/`settle`; `undo()` moves last tile back to tray and calls `onSettled`.
- [ ] Size cells with `Math.min(72, ...)` using `stageHost.clientWidth`.

---

### Task 4: 学具台 DOM + CSS + app.js

**Files:**
- Modify: `web/index.html`, `web/styles.css`, `web/app.js`, `server/app.py`

- [ ] Topbar: brand + topic chip + gear. Mode switch removed.
- [ ] Drawer: `modeSelect` 一起探索 / 带题来问.
- [ ] `exploreStage`: caption, 对话 button, startPlay, stageHost, toast, trayCount, undo.
- [ ] Sheets: `historySheet` (teleport `#messages`), `helpSheet` (quick actions + 换一题).
- [ ] Composer: `talkBtn`；探索默认收起 input-row；`helpBtn`.
- [ ] Attach sheet: `homeworkBtn` 我有作业 → `switchMode("bring")`.
- [ ] `applyModeUI`: toggle `layout-explore` / `layout-bring`; empty explore shows startPlay, no welcome essay.
- [ ] `startPlay`: remount default 3×3, caption 先随便摆摆, `streamAssistant(true)`.
- [ ] After stream: `syncStageFromTutor(acc)` using `sameSnapGrid`.
- [ ] Live Konva only on `#stageHost` in explore; history bubbles stay SVG.
- [ ] Milestone `board_full` shows toast `摆好了` before send.
- [ ] Redirect `/` → `/index.html?v=activity-stage`.

---

### Task 5: 全量测试与提交

- [ ] `node tests/activity_state_test.js`
- [ ] `python3 -m unittest tests.test_frontend_regressions -v`
- [ ] Commit and push `cursor/explore-stage-d734`

Manual (parent): `python3 run.py`, open `/` (jumps to `?v=activity-stage`), 探索点「开始玩」，应立刻能拖；点「对话」能看记录；齿轮里可切带题。
