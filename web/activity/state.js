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

  A.tutorCaption = function tutorCaption(markdown) {
    let s = String(markdown || "");
    s = s.replace(/```[\s\S]*?```/g, " ");
    s = s.replace(/```[\s\S]*$/g, " ");
    s = s.split("\n").filter((line) => {
      const t = line.trim();
      return !(t.charAt(0) === "{" && t.indexOf('"type"') >= 0);
    }).join("\n");
    s = s.replace(/[*_`#]/g, "");
    s = s.replace(/\s+/g, " ").trim();
    if (!s) return "";
    const sentences = s.match(/[^。！？]+[。！？]?/g);
    if (sentences && sentences.length) {
      let out = sentences[0].trim();
      if (sentences[1] && (out + sentences[1]).length <= 90) {
        out = (out + sentences[1]).trim();
      }
      if (out.length > 90) out = out.slice(0, 90).replace(/[,，、]\s*\S*$/, "") + "…";
      return out;
    }
    if (s.length <= 90) return s;
    return s.slice(0, 90).replace(/[,，、]\s*\S*$/, "") + "…";
  };

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
