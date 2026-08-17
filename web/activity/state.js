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

  A.DEFAULT_SNAP_GRID = {
    type: "snap_grid",
    cols: 3,
    rows: 3,
    tray: 9,
    goal: "fill",
    caption: "把方块放进格子里试试",
  };

  A.sameSnapGrid = function sameSnapGrid(a, b) {
    return !!(a && b
      && a.cols === b.cols
      && a.rows === b.rows
      && a.tray === b.tray);
  };

  A.trayCountLabel = function trayCountLabel(n) {
    const left = clampInt(n, 0, 64, 0);
    return left <= 0 ? "方块用完了" : "还剩 " + left + " 块";
  };

  // 托盘不要按棋盘列数折行：2×8 棋盘、12 块会排成 8+4，看起来像已经摆好了。
  A.trayWrapCols = function trayWrapCols(spec) {
    const cols = Math.max(1, spec && spec.cols || 1);
    const tray = Math.max(1, spec && spec.tray || 1);
    return Math.min(cols, Math.ceil(tray / 2) || cols);
  };

  A.softenBareLatex = function softenBareLatex(s) {
    let t = String(s || "");
    const symbols = [
      // JSON.parse 会把 \times / \neq 收成制表符、换行，先修再换正规 LaTeX。
      ["\times", "×"], ["\\times", "×"],
      ["\\div", "÷"], ["\\cdot", "·"],
      ["\\leq", "≤"], ["\\le", "≤"], ["\\geq", "≥"], ["\\ge", "≥"],
      ["\neq", "≠"], ["\\neq", "≠"],
      ["\\approx", "≈"], ["\\pm", "±"],
    ];
    symbols.forEach((pair) => { t = t.split(pair[0]).join(pair[1]); });
    return t;
  };

  A.repairDiagramJson = function repairDiagramJson(text) {
    return String(text || "").replace(/(^|[^\\])\\(times|frac|neq)(?![A-Za-z])/g, "$1\\\\$2");
  };

  A.parseDiagramJson = function parseDiagramJson(text) {
    if (text && typeof text === "object") return text;
    try {
      return JSON.parse(A.repairDiagramJson(text));
    } catch (e) {
      return null;
    }
  };

  function takeDiagramCaption(raw) {
    const spec = A.parseDiagramJson(String(raw || "").trim());
    if (!spec || typeof spec !== "object") return "";
    return spec.caption == null ? "" : String(spec.caption);
  }

  A.tutorCaption = function tutorCaption(markdown) {
    let s = String(markdown || "");
    const extras = [];
    s = s.replace(/```[\s\S]*?```/g, (block) => {
      const body = block.replace(/^```[a-zA-Z0-9_-]*\s*/, "").replace(/```$/, "");
      const cap = takeDiagramCaption(body);
      if (cap) extras.push(cap);
      return " ";
    });
    s = s.replace(/```[\s\S]*$/g, " ");
    s = s.split("\n").filter((line) => {
      const t = line.trim();
      if (t.charAt(0) === "{" && t.indexOf('"type"') >= 0) {
        const cap = takeDiagramCaption(t);
        if (cap) extras.push(cap);
        return false;
      }
      return true;
    }).join("\n");
    extras.forEach((cap) => {
      const soft = A.softenBareLatex(cap);
      if (soft && s.indexOf(soft) < 0 && s.indexOf(cap) < 0) s += " " + cap;
    });
    s = s.replace(/\*\*/g, "").replace(/[*_`#]/g, "");
    s = A.softenBareLatex(s);
    s = s.replace(/\$\$/g, "").replace(/\$/g, "");
    s = s.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "$1/$2");
    s = s.replace(/\s+/g, " ").trim();
    return s;
  };

  A.parseSnapGrid = function parseSnapGrid(raw) {
    let s = raw;
    if (typeof raw === "string") {
      s = A.parseDiagramJson(raw);
      if (!s) return null;
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

  A.makeSnapshot = function makeSnapshot(spec, filled, trayLeft, rowsFilled) {
    const cells = spec.cols * spec.rows;
    const f = clampInt(filled, 0, cells, 0);
    const t = clampInt(trayLeft, 0, 64, 0);
    const snap = {
      type: "snap_grid",
      cols: spec.cols,
      rows: spec.rows,
      filled: f,
      empty: cells - f,
      tray_left: t,
      goal: spec.goal || "fill",
    };
    if (Array.isArray(rowsFilled) && rowsFilled.length === spec.rows) {
      snap.rows_filled = rowsFilled.slice();
    }
    return snap;
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
    if (Array.isArray(snapshot.rows_filled) && snapshot.rows_filled.length) {
      lines.push(
        "各行已放：" + snapshot.rows_filled.map((n, i) => "第" + (i + 1) + "行" + n + "块").join("，")
      );
    }
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
      ? `<figcaption>${escapeHtml(A.softenBareLatex(spec.caption))}</figcaption>`
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
