# Snap-grid H5 Activity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an 8-year-old drag tiles on a snap grid inside the H5 chat, and only then ping 小欧 when the board is clearly finished.

**Architecture:** Keep the vanilla chat shell. Add a Konva-free rule module (`web/activity/state.js`) plus a Konva widget (`web/activity/snap-grid.js`). Markdown still emits a placeholder figure; after a tutor bubble finishes streaming, hydrate the last `snap_grid` as live and freeze every older one. Milestone reports are extra user messages — `/api/chat` does not change.

**Tech Stack:** Vanilla JS (no bundler), Konva 9 via jsDelivr, existing FastAPI SSE chat, Python unittest + Node for rule tests.

**Spec:** `docs/superpowers/specs/2026-08-14-snap-grid-activity-design.md`

---

## File map

| File | Responsibility |
|---|---|
| `web/activity/state.js` | Parse/clamp `snap_grid` JSON, snapshots, `detectMilestone`, model/child copy, static placeholder HTML. No Konva. |
| `web/activity/snap-grid.js` | Konva board: drag, snap, freeze, occupancy restore. Calls `state.js` only. |
| `web/app.js` | Treat `snap_grid` as a diagram type; hydrate/freeze; 400ms milestone send; append board note when the child types. |
| `web/index.html` | Script order: Konva → `state.js` → `snap-grid.js` → `app.js`. Cache-bust `20260814-snap-grid`. |
| `web/styles.css` | Stage, frozen/live, status chip. |
| `server/tutor.py` | `DRAWING_GUIDE` only. |
| `tests/activity_state_test.js` | Node asserts for rules. |
| `tests/test_frontend_regressions.py` | Cache-bust, Konva, no Konva in `state.js`, DRAWING_GUIDE strings, runs Node tests. |
| `README.md` | One paragraph: H5 tiles are playable; miniprogram still static. |

Do not modify `miniprogram/`. Do not add React, JSXGraph, or a bundler.

**Public API on `globalThis.XiaoouActivity` (lock these names):**

- `parseSnapGrid(raw) -> spec|null`
- `makeSnapshot(spec, filled, trayLeft) -> snapshot`
- `detectMilestone(prev, next) -> "board_full"|"tiles_exhausted"|null`
- `milestoneHolds(eventName, snapshot) -> boolean`
- `formatBoardNote(snapshot, eventName|null) -> string`
- `childLabel(eventName, snapshot) -> string`
- `renderSnapGridPlaceholder(spec) -> html string`
- `mountSnapGrid(hostEl, spec, options) -> { freeze, destroy, getSnapshot, getOccupancy }`

`spec` shape: `{ type:"snap_grid", cols, rows, tray, goal:"fill", caption }`.  
`snapshot` shape: `{ type:"snap_grid", cols, rows, filled, empty, tray_left, goal }`.  
`options`: `{ interactive, occupied, onSettled(snapshot, eventName) }`. `occupied` is `[{r,c}, ...]`.

---

### Task 1: Rule module (TDD)

**Files:**
- Create: `tests/activity_state_test.js`
- Create: `web/activity/state.js`
- Modify: `tests/test_frontend_regressions.py`

- [ ] **Step 1: Write the Node test file**

Create `tests/activity_state_test.js`:

```javascript
"use strict";
const assert = require("assert");
const path = require("path");
const A = require(path.join(__dirname, "..", "web", "activity", "state.js"));

function spec(over) {
  return Object.assign({ type: "snap_grid", cols: 3, rows: 3, tray: 9, goal: "fill", caption: "" }, over || {});
}
function snap(filled, trayLeft, over) {
  return A.makeSnapshot(spec(over), filled, trayLeft);
}

assert.strictEqual(A.parseSnapGrid("nope"), null);
assert.strictEqual(A.parseSnapGrid({ type: "dots" }), null);
assert.strictEqual(A.parseSnapGrid({ type: "snap_grid", cols: 0, rows: 3 }), null);
assert.strictEqual(A.parseSnapGrid("{"), null);

const d = A.parseSnapGrid({ type: "snap_grid" });
assert.strictEqual(d.cols, 3);
assert.strictEqual(d.rows, 3);
assert.strictEqual(d.tray, 9);
assert.strictEqual(d.goal, "fill");

const clamped = A.parseSnapGrid({ type: "snap_grid", cols: 99, rows: 1, tray: 3, goal: "other", caption: "x" });
assert.strictEqual(clamped.cols, 8);
assert.strictEqual(clamped.tray, 3);
assert.strictEqual(clamped.goal, "fill");
assert.strictEqual(clamped.caption, "x");

const s0 = snap(0, 9);
const s8 = snap(8, 1);
const s9 = snap(9, 0);
const s9extra = snap(9, 3);
const s7empty = snap(7, 0);

assert.strictEqual(A.detectMilestone(s0, s8), null);
assert.strictEqual(A.detectMilestone(s8, s9), "board_full");
assert.strictEqual(A.detectMilestone(s9, s8), null);
assert.strictEqual(A.detectMilestone(s8, s9), "board_full");
assert.strictEqual(A.detectMilestone(s8, s9extra), "board_full");
assert.strictEqual(A.detectMilestone(s0, s7empty), "tiles_exhausted");
assert.strictEqual(A.detectMilestone(s7empty, s7empty), null);
assert.strictEqual(A.detectMilestone(s8, s9extra) === "tiles_exhausted", false);

assert.strictEqual(A.milestoneHolds("board_full", s9), true);
assert.strictEqual(A.milestoneHolds("board_full", s8), false);
assert.strictEqual(A.milestoneHolds("tiles_exhausted", s7empty), true);
assert.strictEqual(A.milestoneHolds("tiles_exhausted", s9), false);

const note = A.formatBoardNote(s9, "board_full");
assert.ok(note.includes("（孩子在学具上摆完了一步，这不是她打的字）"));
assert.ok(note.includes("学具：snap_grid"));
assert.ok(note.includes("格子：3×3"));
assert.ok(note.includes("已放：9"));
assert.ok(note.includes("空格：0"));
assert.ok(note.includes("托盘剩余：0"));
assert.ok(note.includes("节点：board_full"));

const liveNote = A.formatBoardNote(s8, null);
assert.ok(liveNote.includes("（当前学具盘面，这不是她打的字）"));
assert.ok(!liveNote.includes("节点："));

assert.strictEqual(A.childLabel("board_full", s9), "摆好了：9 个格子都满了");
assert.strictEqual(A.childLabel("tiles_exhausted", s7empty), "方块用完了，格子还空着");

const html = A.renderSnapGridPlaceholder(d);
assert.ok(html.includes("data-snap-grid"));
assert.ok(html.includes("data-spec="));
assert.ok(html.includes("snap-grid-stage"));
assert.ok(html.includes("<svg"));

console.log("activity_state_test.js ok");
```

- [ ] **Step 2: Run the Node test (must fail)**

Run: `node tests/activity_state_test.js`

Expected: FAIL (`Cannot find module .../web/activity/state.js`)

- [ ] **Step 3: Implement `web/activity/state.js`**

Create `web/activity/state.js` with this exact file:

```javascript
"use strict";

(function (root) {
  const A = root.XiaoouActivity || {};

  function clampInt(v, lo, hi, dflt) {
    v = parseInt(v, 10);
    if (isNaN(v)) return dflt;
    return Math.max(lo, Math.min(hi, v));
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[ch]);
  }

  function parseDim(v, dflt) {
    if (v === undefined || v === null || v === "") return dflt;
    const n = parseInt(v, 10);
    if (isNaN(n) || n < 1) return null;
    return Math.min(8, n);
  }

  A.parseSnapGrid = function parseSnapGrid(raw) {
    let s = raw;
    if (typeof raw === "string") {
      try { s = JSON.parse(raw); } catch (e) { return null; }
    }
    if (!s || typeof s !== "object" || s.type !== "snap_grid") return null;
    const cols = parseDim(s.cols, 3);
    const rows = parseDim(s.rows, 3);
    if (cols === null || rows === null) return null;
    let tray;
    if (s.tray === undefined || s.tray === null || s.tray === "") {
      tray = cols * rows;
    } else {
      const n = parseInt(s.tray, 10);
      if (isNaN(n) || n < 0) return null;
      tray = Math.min(64, n);
    }
    const caption = s.caption == null ? "" : String(s.caption);
    return { type: "snap_grid", cols, rows, tray, goal: "fill", caption };
  };

  A.makeSnapshot = function makeSnapshot(spec, filled, trayLeft) {
    const cells = spec.cols * spec.rows;
    const f = clampInt(filled, 0, cells, 0);
    const t = clampInt(trayLeft, 0, 64, 0);
    return {
      type: "snap_grid",
      cols: spec.cols,
      rows: spec.rows,
      filled: f,
      empty: cells - f,
      tray_left: t,
      goal: spec.goal || "fill",
    };
  };

  A.detectMilestone = function detectMilestone(prev, next) {
    if (!prev || !next) return null;
    if (prev.empty > 0 && next.empty === 0) return "board_full";
    if (prev.tray_left > 0 && next.tray_left === 0 && next.empty > 0) return "tiles_exhausted";
    return null;
  };

  A.milestoneHolds = function milestoneHolds(eventName, snapshot) {
    if (!snapshot || !eventName) return false;
    if (eventName === "board_full") return snapshot.empty === 0;
    if (eventName === "tiles_exhausted") return snapshot.tray_left === 0 && snapshot.empty > 0;
    return false;
  };

  A.formatBoardNote = function formatBoardNote(snapshot, eventName) {
    const header = eventName
      ? "（孩子在学具上摆完了一步，这不是她打的字）"
      : "（当前学具盘面，这不是她打的字）";
    const lines = [
      header,
      "学具：snap_grid",
      "格子：" + snapshot.cols + "×" + snapshot.rows,
      "已放：" + snapshot.filled,
      "空格：" + snapshot.empty,
      "托盘剩余：" + snapshot.tray_left,
    ];
    if (eventName) lines.push("节点：" + eventName);
    return lines.join("\n");
  };

  A.childLabel = function childLabel(eventName, snapshot) {
    if (eventName === "board_full") {
      return "摆好了：" + (snapshot.cols * snapshot.rows) + " 个格子都满了";
    }
    if (eventName === "tiles_exhausted") return "方块用完了，格子还空着";
    return "摆了一下";
  };

  A.renderSnapGridPlaceholder = function renderSnapGridPlaceholder(spec) {
    const cell = 28, pad = 8, gap = 4;
    const gw = spec.cols * (cell + gap) - gap;
    const gh = spec.rows * (cell + gap) - gap;
    const w = gw + pad * 2;
    const h = gh + pad * 2;
    let rects = "";
    for (let r = 0; r < spec.rows; r++) {
      for (let c = 0; c < spec.cols; c++) {
        const x = pad + c * (cell + gap);
        const y = pad + r * (cell + gap);
        rects += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="6" fill="#fff" stroke="#c9c4b8"/>`;
      }
    }
    const specJson = encodeURIComponent(JSON.stringify(spec));
    const cap = spec.caption
      ? `<figcaption>${escapeHtml(spec.caption)}</figcaption>`
      : "";
    return (
      `<figure class="diagram snap-grid" data-snap-grid="1" data-spec="${specJson}">` +
      `<div class="snap-grid-stage"></div>` +
      `<svg class="snap-grid-fallback" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">${rects}</svg>` +
      cap +
      `</figure>`
    );
  };

  root.XiaoouActivity = A;
  if (typeof module !== "undefined" && module.exports) module.exports = A;
})(typeof globalThis !== "undefined" ? globalThis : this);
```

Rules encoded here: missing cols/rows default to 3; explicit `0` or NaN fails parse; cols/rows cap at 8; tray missing defaults to `cols*rows`; tray explicit `0` is valid; unknown `goal` becomes `"fill"`; `detectMilestone` is edge-triggered and `board_full` wins over `tiles_exhausted` because empty becomes 0.

- [ ] **Step 4: Re-run Node test (must pass)**

Run: `node tests/activity_state_test.js`

Expected: `activity_state_test.js ok`

- [ ] **Step 5: Hook Node tests into Python unittest**

Add this method to `FrontendRegressionTests` in `tests/test_frontend_regressions.py` (keep existing tests). Add `import subprocess` at the top.

```python
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
```

- [ ] **Step 6: Run Python tests**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: new tests PASS. Pre-existing tests still PASS.

- [ ] **Step 7: Commit**

```bash
git add web/activity/state.js tests/activity_state_test.js tests/test_frontend_regressions.py
git commit -m "feat: add snap-grid activity rule module"
```

---

### Task 2: Prompt + cache-bust regressions

**Files:**
- Modify: `server/tutor.py` (`DRAWING_GUIDE` around lines 264–304)
- Modify: `web/index.html`
- Modify: `tests/test_frontend_regressions.py`

- [ ] **Step 1: Add failing regression assertions**

Append to `FrontendRegressionTests`:

```python
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
```

- [ ] **Step 2: Run the new tests (must fail)**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: FAIL (Konva/`snap_grid` strings missing)

- [ ] **Step 3: Wire scripts in `web/index.html`**

Replace the stylesheet query and the bottom scripts. Cache-bust **all** of: `styles.css`, `state.js`, `snap-grid.js`, `app.js` to `20260814-snap-grid`.

`<head>` link:

```html
  <link rel="stylesheet" href="/styles.css?v=20260814-snap-grid" />
```

Bottom of `<body>` (keep KaTeX, then this exact order):

```html
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/konva@9.3.22/konva.min.js" crossorigin="anonymous"></script>
  <script src="/activity/state.js?v=20260814-snap-grid"></script>
  <script src="/activity/snap-grid.js?v=20260814-snap-grid"></script>
  <script src="/app.js?v=20260814-snap-grid"></script>
```

`snap-grid.js` does not exist yet. Create a stub so the 404 does not matter in tests that only read HTML, and so the browser does not explode later:

Create `web/activity/snap-grid.js`:

```javascript
"use strict";
(function (root) {
  const A = root.XiaoouActivity || {};
  A.mountSnapGrid = A.mountSnapGrid || function () {
    return { freeze() {}, destroy() {}, getSnapshot() { return null; }, getOccupancy() { return { occupied: [], trayLeft: 0 }; } };
  };
  root.XiaoouActivity = A;
})(typeof globalThis !== "undefined" ? globalThis : this);
```

- [ ] **Step 4: Update `DRAWING_GUIDE` in `server/tutor.py`**

Keep the existing six static types. After the `bars` bullet, insert:

```
- 可动手吸附格子（请孩子自己摆时必须用这个，不要用点阵 SVG 代替）：{"type":"snap_grid","cols":3,"rows":3,"tray":9,"caption":"把方块放进格子里试试"}
  cols/rows 为格子行列（1–8），tray 为托盘里的方块数（可多于或少于格子）。孩子能拖方块；你看不到拖的过程，只会在她明显摆完时收到一条「孩子在学具上摆完了一步」的消息，内含已放/空格/托盘剩余/节点（board_full 或 tiles_exhausted）。
```

Replace the 积木平方数 table first rows so hands-on turns use `snap_grid`:

```
| 第一问「这 9 块能不能摆成正方形？」 | snap_grid cols:3 rows:3 tray:9 |
| 她摆满后，问「再包一圈会怎样」 | 新的 snap_grid 4×4 tray:7（只给新的一圈）或静态 square_compare from:3 to:4 |
| 只需要看、不要拖时 | 仍用 square_layers / square_steps / square_compare |
```

Keep the other static rows for look-only turns. Add a new subsection before the final 规则：

```
## 学具回传（你会当普通 user 消息收到）
若消息以「（孩子在学具上摆完了一步，这不是她打的字）」开头，那是前端根据盘面发的，不是孩子打的字。
- 根据已放/空格/托盘剩余问下一句。
- 不要祝贺「成功」「真棒」。
- 不要把 board_full 说成「这就是正方形」或直接报「一共 9 块」。
- 一次仍只问一个问题，仍必须带一张对应当前这一步的 xiaoou-draw 图。
```

Also add to the 规则 list: `需要孩子动手摆、数、试铺满时，用 snap_grid；只看对比/数轴/线段图时用原来的静态类型。禁止输出 SVG/Konva 代码。caption 仍然不得泄露答案。`

- [ ] **Step 5: Re-run the two tests (must pass)**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/index.html web/activity/snap-grid.js server/tutor.py tests/test_frontend_regressions.py
git commit -m "feat: teach snap_grid in prompts and load Konva on H5"
```

---

### Task 3: Markdown emits a snap_grid placeholder

**Files:**
- Modify: `web/app.js` (`DIAGRAM_TYPES`, `renderDiagram`)
- Modify: `web/styles.css`
- Modify: `tests/test_frontend_regressions.py`

- [ ] **Step 1: Failing test that `app.js` knows `snap_grid`**

```python
    def test_app_js_routes_snap_grid(self):
        app = read("web/app.js")
        self.assertIn('"snap_grid"', app)
        self.assertIn("renderSnapGridPlaceholder", app)
        css = read("web/styles.css")
        self.assertIn(".snap-grid-stage", css)
        self.assertIn("touch-action: none", css)
```

- [ ] **Step 2: Run it (must fail)**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: FAIL

- [ ] **Step 3: Route `snap_grid` in `web/app.js`**

Change:

```javascript
const DIAGRAM_TYPES = new Set(["dots", "square_layers", "square_steps", "square_compare", "numberline", "bars"]);
```

to also include `"snap_grid"`.

In `renderDiagram`, after `JSON.parse`, before the old `if (s.type === "dots")` chain:

```javascript
  if (s.type === "snap_grid") {
    const parsed = (window.XiaoouActivity && XiaoouActivity.parseSnapGrid)
      ? XiaoouActivity.parseSnapGrid(s)
      : null;
    if (!parsed) return "";
    return XiaoouActivity.renderSnapGridPlaceholder(parsed);
  }
```

Leave every existing SVG branch unchanged.

- [ ] **Step 4: CSS**

Append to `web/styles.css`:

```css
.msg .bubble .diagram.snap-grid {
  padding: 10px 8px 8px;
}
.snap-grid-stage {
  width: 100%;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}
.snap-grid:not(.is-live) .snap-grid-stage:empty { display: none; }
.snap-grid.is-live .snap-grid-fallback { display: none; }
.snap-grid.is-frozen .snap-grid-stage { pointer-events: none; }
.msg .bubble .activity-status {
  margin: 0;
  font-size: 13px;
  color: var(--ink-soft);
}
```

- [ ] **Step 5: Re-run tests**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/app.js web/styles.css tests/test_frontend_regressions.py
git commit -m "feat: render snap_grid placeholders in chat markdown"
```

---

### Task 4: Konva widget

**Files:**
- Replace: `web/activity/snap-grid.js` (overwrite the stub)

- [ ] **Step 1: Implement `web/activity/snap-grid.js`**

Overwrite with:

```javascript
"use strict";

(function (root) {
  const A = root.XiaoouActivity || {};
  const BLUE = "#4f6bed";
  const CELL_MIN = 44;
  const SNAP_RATIO = 0.55;

  function occupancySnapshot(spec, cells, trayCount) {
    let filled = 0;
    for (let r = 0; r < spec.rows; r++) {
      for (let c = 0; c < spec.cols; c++) {
        if (cells[r][c]) filled += 1;
      }
    }
    return A.makeSnapshot(spec, filled, trayCount);
  }

  A.mountSnapGrid = function mountSnapGrid(host, spec, options) {
    options = options || {};
    spec = spec || (host && host.getAttribute("data-spec")
      ? A.parseSnapGrid(decodeURIComponent(host.getAttribute("data-spec")))
      : null);
    const emptyHandle = {
      freeze() { if (host) host.classList.add("is-frozen"); },
      destroy() {},
      getSnapshot() { return spec ? A.makeSnapshot(spec, 0, spec.tray) : null; },
      getOccupancy() { return { occupied: [], trayLeft: spec ? spec.tray : 0 }; },
    };
    if (!spec || !host) return emptyHandle;
    if (typeof Konva === "undefined") {
      host.classList.add("is-frozen");
      return emptyHandle;
    }

    const interactive = !!options.interactive;
    const stageHost = host.querySelector(".snap-grid-stage") || host;
    const fallback = host.querySelector(".snap-grid-fallback");
    const width = Math.max(220, stageHost.clientWidth || host.clientWidth || 280);
    const gap = 6;
    const pad = 10;
    const cell = Math.max(
      CELL_MIN,
      Math.min(56, Math.floor((width - pad * 2 - gap * (spec.cols - 1)) / spec.cols))
    );
    const gridH = spec.rows * cell + (spec.rows - 1) * gap;
    const trayTop = pad + gridH + 18;
    const perRow = Math.max(1, Math.floor((width - pad * 2 + gap) / (cell + gap)));
    const trayRows = Math.max(1, Math.ceil(Math.max(spec.tray, 1) / perRow));
    const height = trayTop + trayRows * (cell + gap) + pad;

    stageHost.innerHTML = "";
    const stage = new Konva.Stage({ container: stageHost, width: width, height: height });
    const layer = new Konva.Layer();
    stage.add(layer);

    const cells = [];
    const cellRects = [];
    for (let r = 0; r < spec.rows; r++) {
      cells[r] = [];
      cellRects[r] = [];
      for (let c = 0; c < spec.cols; c++) {
        cells[r][c] = null;
        const x = pad + c * (cell + gap);
        const y = pad + r * (cell + gap);
        const rect = new Konva.Rect({
          x: x, y: y, width: cell, height: cell, cornerRadius: 10,
          fill: "#fff", stroke: "#c9c4b8", strokeWidth: 1.5,
        });
        layer.add(rect);
        cellRects[r][c] = { x: x, y: y };
      }
    }

    function trayPosition(index) {
      const c = index % perRow;
      const r = Math.floor(index / perRow);
      return { x: pad + c * (cell + gap), y: trayTop + r * (cell + gap) };
    }

    const tiles = [];
    let trayCount = 0;

    function reindexTray() {
      const trayTiles = tiles.filter((t) => t.place.kind === "tray");
      trayTiles.forEach((t, i) => {
        t.place.index = i;
        t.group.position(trayPosition(i));
      });
      trayCount = trayTiles.length;
    }

    function nearestCell(x, y) {
      let best = null, bestD = Infinity;
      const cx = x + cell / 2, cy = y + cell / 2;
      for (let r = 0; r < spec.rows; r++) {
        for (let c = 0; c < spec.cols; c++) {
          const slot = cellRects[r][c];
          const sx = slot.x + cell / 2, sy = slot.y + cell / 2;
          const d = Math.hypot(cx - sx, cy - sy);
          if (d < bestD) { bestD = d; best = { r: r, c: c, d: d }; }
        }
      }
      if (best && best.d <= cell * SNAP_RATIO && !cells[best.r][best.c]) return best;
      return null;
    }

    let lastSnap = null;

    function readOccupancy() {
      const occupied = [];
      for (let r = 0; r < spec.rows; r++) {
        for (let c = 0; c < spec.cols; c++) {
          if (cells[r][c]) occupied.push({ r: r, c: c });
        }
      }
      return { occupied: occupied, trayLeft: trayCount };
    }

    function settle(tile) {
      const pos = tile.group.position();
      if (tile.place.kind === "cell") cells[tile.place.r][tile.place.c] = null;
      const hit = nearestCell(pos.x, pos.y);
      if (hit) {
        tile.place = { kind: "cell", r: hit.r, c: hit.c };
        cells[hit.r][hit.c] = tile;
        tile.group.position({ x: cellRects[hit.r][hit.c].x, y: cellRects[hit.r][hit.c].y });
      } else {
        tile.place = { kind: "tray", index: 0 };
      }
      reindexTray();
      layer.draw();
      const next = occupancySnapshot(spec, cells, trayCount);
      const eventName = A.detectMilestone(lastSnap, next);
      lastSnap = next;
      if (typeof options.onSettled === "function") options.onSettled(next, eventName);
    }

    const startOccupied = Array.isArray(options.occupied) ? options.occupied.slice() : [];
    let used = 0;
    for (let i = 0; i < spec.tray; i++) {
      const group = new Konva.Group({ x: 0, y: 0, draggable: interactive });
      group.add(new Konva.Rect({
        width: cell, height: cell, cornerRadius: 10, fill: BLUE,
        shadowColor: "rgba(0,0,0,0.18)", shadowBlur: 6, shadowOffsetY: 2,
      }));
      const tile = { group: group, place: { kind: "tray", index: i } };
      const slot = startOccupied[used];
      if (slot && slot.r >= 0 && slot.r < spec.rows && slot.c >= 0 && slot.c < spec.cols && !cells[slot.r][slot.c]) {
        tile.place = { kind: "cell", r: slot.r, c: slot.c };
        cells[slot.r][slot.c] = tile;
        group.position({ x: cellRects[slot.r][slot.c].x, y: cellRects[slot.r][slot.c].y });
        used += 1;
      }
      if (interactive) {
        group.on("dragstart", function () { group.moveToTop(); });
        group.on("dragend", function () { settle(tile); });
      }
      layer.add(group);
      tiles.push(tile);
    }
    reindexTray();
    lastSnap = occupancySnapshot(spec, cells, trayCount);
    layer.draw();

    host.classList.toggle("is-live", interactive);
    host.classList.toggle("is-frozen", !interactive);
    if (fallback) {
      if (interactive || tiles.length) fallback.setAttribute("hidden", "hidden");
    }

    function freeze() {
      tiles.forEach((t) => t.group.draggable(false));
      host.classList.add("is-frozen");
      host.classList.remove("is-live");
    }
    function destroy() {
      freeze();
      stage.destroy();
    }
    function getSnapshot() {
      return occupancySnapshot(spec, cells, trayCount);
    }
    function getOccupancy() {
      return readOccupancy();
    }

    return { freeze: freeze, destroy: destroy, getSnapshot: getSnapshot, getOccupancy: getOccupancy };
  };

  root.XiaoouActivity = A;
  if (typeof module !== "undefined" && module.exports) module.exports = A;
})(typeof globalThis !== "undefined" ? globalThis : this);
```

Important: `lastSnap` is assigned **after** restoring `occupied`, and `onSettled` is **not** called on mount.

- [ ] **Step 2: Grep that `state.js` still has no Konva**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add web/activity/snap-grid.js
git commit -m "feat: add Konva snap-grid widget"
```

---

### Task 5: Hydrate, freeze, restore occupancy

**Files:**
- Modify: `web/app.js` (`state`, `saveSession`/`loadSession`, `renderContentInto`, `renderHistory`, `streamAssistant`)
- Modify: `tests/test_frontend_regressions.py`

Streaming currently does `tutorBubble.innerHTML = renderMarkdown(acc)` on every token. **Do not mount Konva during the stream** — the next token would destroy the canvas. Hydrate only after the stream ends.

- [ ] **Step 1: Failing test**

```python
    def test_app_js_hydrates_and_freezes_snap_grid(self):
        app = read("web/app.js")
        self.assertIn("function hydrateSnapGrids(", app)
        self.assertIn("function freezeLiveActivities(", app)
        self.assertIn("onSnapGridSettled", app)
        self.assertIn("MILESTONE_DEBOUNCE_MS = 400", app)
        self.assertIn("function sendActivityMilestone(", app)
        self.assertIn("activity-status", app)
```

- [ ] **Step 2: Run test (fail), then add the following to `web/app.js`**

Add to `state`:

```javascript
  liveActivities: [],   // handles from mountSnapGrid that are still draggable
  mountedActivities: [], // all handles in DOM order, for occupancy save
  boards: [],           // persisted occupancy, same order as tutor snap-grids
  milestoneTimer: null,
  pendingMilestone: null, // { event, snapshot }
  queuedMilestone: null,
```

In `saveSession`, include boards. Replace the `data` object with:

```javascript
function saveSession() {
  const data = {
    topicKey: state.topicKey,
    level: state.level,
    childName: state.childName,
    mode: state.mode,
    thinking: state.thinking,
    showReasoning: state.showReasoning,
    messages: sanitizeForStore(state.messages),
    boards: collectBoards(),
  };
  try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) {}
}

function collectBoards() {
  return state.mountedActivities.map((h) => h.getOccupancy ? h.getOccupancy() : { occupied: [], trayLeft: 0 });
}
```

In `loadSession` usage inside `loadConfig`, after `state.messages = ...`:

```javascript
  state.boards = (saved && Array.isArray(saved.boards)) ? saved.boards : [];
```

Add helpers **after** `renderDiagram` (not inside markdown):

```javascript
const MILESTONE_DEBOUNCE_MS = 400;

function freezeLiveActivities() {
  state.liveActivities.forEach((h) => { try { h.freeze(); } catch (e) {} });
  state.liveActivities = [];
}

function destroyMountedActivities() {
  freezeLiveActivities();
  state.mountedActivities.forEach((h) => { try { h.destroy(); } catch (e) {} });
  state.mountedActivities = [];
}

function hydrateSnapGrids(bubble, interactive) {
  if (!bubble || !window.XiaoouActivity || !XiaoouActivity.mountSnapGrid) return;
  const hosts = bubble.querySelectorAll("figure.diagram[data-snap-grid]");
  hosts.forEach((host, i) => {
    const spec = XiaoouActivity.parseSnapGrid(decodeURIComponent(host.getAttribute("data-spec") || ""));
    const isLive = !!(interactive && i === hosts.length - 1);
    const occ = state.boards[state.mountedActivities.length] || {};
    const handle = XiaoouActivity.mountSnapGrid(host, spec, {
      interactive: isLive,
      occupied: occ.occupied || [],
      onSettled: onSnapGridSettled,
    });
    state.mountedActivities.push(handle);
    if (isLive) state.liveActivities.push(handle);
    else handle.freeze();
  });
}

function onSnapGridSettled(snapshot, eventName) {
  state.boards = collectBoards();
  saveSession();
  if (!eventName) {
    if (state.pendingMilestone && !XiaoouActivity.milestoneHolds(state.pendingMilestone.event, snapshot)) {
      state.pendingMilestone = null;
      if (state.milestoneTimer) { clearTimeout(state.milestoneTimer); state.milestoneTimer = null; }
    }
    return;
  }
  state.pendingMilestone = { event: eventName, snapshot: snapshot };
  if (state.milestoneTimer) clearTimeout(state.milestoneTimer);
  state.milestoneTimer = setTimeout(flushPendingMilestone, MILESTONE_DEBOUNCE_MS);
}

function flushPendingMilestone() {
  state.milestoneTimer = null;
  const pending = state.pendingMilestone;
  state.pendingMilestone = null;
  if (!pending) return;
  const live = state.liveActivities[state.liveActivities.length - 1];
  const now = live && live.getSnapshot ? live.getSnapshot() : pending.snapshot;
  if (!XiaoouActivity.milestoneHolds(pending.event, now)) return;
  sendActivityMilestone(pending.event, now);
}

function sendActivityMilestone(eventName, snapshot) {
  if (state.streaming) {
    state.queuedMilestone = { event: eventName, snapshot: snapshot };
    return;
  }
  if (!snapshot) return;
  const modelText = XiaoouActivity.formatBoardNote(snapshot, eventName);
  const label = XiaoouActivity.childLabel(eventName, snapshot);
  state.messages.push({ role: "user", content: modelText });
  const bubble = addMessageEl("child");
  bubble.innerHTML = `<p class="activity-status">${escapeHtml(label)}</p>`;
  saveSession();
  streamAssistant(false).catch((err) => console.warn("milestone send failed", err));
}
```

Change `renderHistory`:

```javascript
function renderHistory() {
  destroyMountedActivities();
  $("#messages").innerHTML = "";
  if (state.messages.length === 0) { renderWelcome(); return; }
  for (const m of state.messages) {
    const bubble = addMessageEl(m.role === "user" ? "child" : "tutor");
    renderContentInto(bubble, m.content);
    if (m.role === "assistant") hydrateSnapGrids(bubble, false);
  }
}
```

At the **start** of `streamAssistant` (after `setStreaming(true)`):

```javascript
  freezeLiveActivities();
```

At the **end** of `streamAssistant`, after writing `state.messages.push({ role: "assistant", content: acc })` and `saveSession()`, still inside `if (acc.trim())`:

```javascript
    hydrateSnapGrids(tutorBubble, true);
    saveSession();
```

Then, if a queued milestone exists, Task 6 will flush it. For now add:

```javascript
  if (state.queuedMilestone) {
    const q = state.queuedMilestone;
    state.queuedMilestone = null;
    sendActivityMilestone(q.event, q.snapshot);
  }
```

Do **not** call `hydrateSnapGrids` during token `innerHTML` updates.

At the end of `init` in `web/app.js`, expose a debug hook for the manual check:

```javascript
  window.XiaoouDebug = { addMessageEl, renderMarkdown, hydrateSnapGrids };
```

- [ ] **Step 3: Run `python3 -m unittest tests.test_frontend_regressions -v`**

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/app.js tests/test_frontend_regressions.py
git commit -m "feat: hydrate snap-grid and send debounced milestones"
```

---

### Task 6: Attach board snapshot when the child speaks

**Files:**
- Modify: `web/app.js` (`sendMessage`)
- Modify: `tests/test_frontend_regressions.py`

- [ ] **Step 1: Failing test**

```python
    def test_app_js_appends_board_note_on_typed_send(self):
        app = read("web/app.js")
        self.assertIn("当前学具盘面", app)
        self.assertIn("contentForModel", app)
```

- [ ] **Step 2: In `sendMessage`, after computing `typed` / `content` and before `state.messages.push`**

Replace the push + bubble block with:

```javascript
  let contentForModel = content;
  if (!image && typeof content === "string") {
    const live = state.liveActivities[state.liveActivities.length - 1];
    if (live && live.getSnapshot && window.XiaoouActivity && XiaoouActivity.formatBoardNote) {
      const note = XiaoouActivity.formatBoardNote(live.getSnapshot(), null);
      contentForModel = typed + "\n\n" + note;
    }
  }
  state.messages.push({ role: "user", content: image ? content : contentForModel });
  const childBubble = addMessageEl("child");
  renderContentInto(childBubble, content);
```

The child bubble shows only what she typed or photographed. The model receives the extra board note. If she sent a photo, skip the note.

- [ ] **Step 3: Run tests**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: PASS, including Node rule tests.

- [ ] **Step 4: Commit**

```bash
git add web/app.js tests/test_frontend_regressions.py
git commit -m "feat: attach snap-grid snapshot when the child replies"
```

---

### Task 7: README + spec status + manual check

**Files:**
- Modify: `README.md` (the 图形输出 bullet ~line 83)
- Modify: `docs/superpowers/specs/2026-08-14-snap-grid-activity-design.md` status line

- [ ] **Step 1: README**

Replace the SVG-only bullet with:

```
- **图形输出（数形结合）**：点阵、数轴、线段图仍是静态 SVG。需要动手摆时，H5 会给出可拖的吸附格子（`snap_grid`）；铺满或块用完后才把盘面发给小欧。微信小程序这一期仍是静态图。
```

- [ ] **Step 2: Spec status**

Change the spec status line to `状态：已实现`.

- [ ] **Step 3: Full test run**

Run: `python3 -m unittest tests.test_frontend_regressions -v`

Expected: all PASS.

- [ ] **Step 4: Manual check** (do not skip)

Manual script (console, after page load):

```javascript
const b = XiaoouDebug.addMessageEl("tutor");
b.innerHTML = XiaoouDebug.renderMarkdown("摆一摆\n\n```xiaoou-draw\n{\"type\":\"snap_grid\",\"cols\":3,\"rows\":3,\"tray\":9,\"caption\":\"试试\"}\n```\n能铺满吗？");
XiaoouDebug.hydrateSnapGrids(b, true);
```

Then:

- Drag a tile: it snaps or returns; the page does not scroll.
- Fill 9 cells: wait ~0.4s → a grey status chip → 小欧 replies. Grid stays draggable.
- Fill 9 and immediately pull one off within 0.4s → no chip.
- Fill, then remove, then fill again → second chip.
- Type "我摆好了" with 7 tiles placed → model history contains `已放：7`, the bubble shows only the typed words.
- Reload: old grids frozen, occupancy restored, not draggable.
- A static `bars` / `dots` message still renders SVG.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/superpowers/specs/2026-08-14-snap-grid-activity-design.md web/app.js
git commit -m "docs: note playable snap-grid on H5"
```

---

## Self-review vs spec

| Spec | Task |
|---|---|
| Konva, no React, no miniprogram change | 2, 4, file map |
| `snap_grid` JSON fields / clamp / reject 0 | 1 |
| Static types remain | 2, 3 |
| Placeholder during stream, Konva after stream | 5 |
| Last `snap_grid` in a bubble is live; older frozen | 5 |
| Restore session frozen + last occupancy | 5 (`boards`) |
| No milestone on mount | 4 (`lastSnap` after restore) |
| C: `board_full` / `tiles_exhausted`, edge trigger | 1, 6 |
| 400ms debounce cancel if she undoes | 5 `onSnapGridSettled` |
| Queue one milestone if streaming | 5 + 6 |
| Child chip vs model template | 1 + 6 |
| Speech appends snapshot, not every pointerup | 6 |
| DRAWING_GUIDE + no celebrate | 2 |
| Konva missing → placeholder | 4 early return |
| `state.js` has no Konva | 1 test |
| No auto "this is a square" | widget has no success UI |

Out of scope left out: React, JSXGraph, Polypad, `dots_play`, WeChat, discovery album.
