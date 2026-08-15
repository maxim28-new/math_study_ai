"use strict";

const $ = (sel) => document.querySelector(sel);

const state = {
  config: null,
  topics: [],
  topicKey: null,
  level: null,
  childName: "",
  mode: "explore", // explore=小欧出题 / bring=孩子带题
  thinking: false, // API 深度思考（更慢）
  showReasoning: false, // 是否在界面展示思考过程（独立于 thinking）
  messages: [], // 发给模型的历史：{role:'user'|'assistant', content}（content 可能是字符串或多模态数组）
  pendingImage: null, // 待发送的题目照片（dataURL）
  streaming: false,
  liveActivities: [],
  mountedActivities: [],
  boards: [],
  milestoneTimer: null,
  pendingMilestone: null,
  queuedMilestone: null,
  stageSpec: null,
  talkOpen: false,
  toastTimer: null,
};

const STORE_KEY = "xiaoou.session.v1";

// ---------------- 本地存储 ----------------
// 图片是很大的 base64，存进 localStorage 会撑爆配额，所以持久化时把图片换成占位文字。
function sanitizeForStore(messages) {
  return messages.map((m) => {
    if (!Array.isArray(m.content)) return m;
    const textPart = m.content.find((p) => p.type === "text");
    const text = textPart ? textPart.text : "";
    return { role: m.role, content: (text ? text + "\n" : "") + "[一张题目照片]" };
  });
}
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
function loadSession() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || "null"); } catch (e) { return null; }
}

// ---------------- 安全的轻量 Markdown 渲染（含 KaTeX 公式） ----------------
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
const MATH_RE = /\$\$([\s\S]+?)\$\$|\$([^\$\n]+?)\$|\\\(([\s\S]+?)\\\)|\\\[([\s\S]+?)\\\]/g;
function renderLatex(latex, displayMode) {
  const src = String(latex).trim();
  if (!src) return "";
  if (typeof katex === "undefined") return `<code>${escapeHtml(src)}</code>`;
  try {
    return katex.renderToString(src, { displayMode, throwOnError: false, strict: "ignore" });
  } catch (e) {
    return `<code>${escapeHtml(src)}</code>`;
  }
}
function formatPlainText(s) {
  return escapeHtml(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}
function softenBareLatex(s) {
  if (window.XiaoouActivity && XiaoouActivity.softenBareLatex) {
    return XiaoouActivity.softenBareLatex(s);
  }
  return String(s || "").replace(/\\times/g, "×").replace(/\\div/g, "÷");
}
function renderTextWithMath(s) {
  s = softenBareLatex(s);
  MATH_RE.lastIndex = 0;
  let out = "", last = 0, m;
  while ((m = MATH_RE.exec(s)) !== null) {
    if (m.index > last) out += formatPlainText(s.slice(last, m.index));
    if (m[1] !== undefined) out += renderLatex(m[1], true);
    else if (m[2] !== undefined) out += renderLatex(m[2], false);
    else if (m[3] !== undefined) out += renderLatex(m[3], false);
    else if (m[4] !== undefined) out += renderLatex(m[4], true);
    last = MATH_RE.lastIndex;
  }
  if (last < s.length) out += formatPlainText(s.slice(last));
  return out;
}
function inlineFmt(s) {
  return renderTextWithMath(String(s));
}

const DIAGRAM_TYPES = new Set(["dots", "square_layers", "square_steps", "square_compare", "numberline", "bars", "snap_grid"]);

/** 识别 xiaoou-draw JSON（模型有时用 ```json 或裸 JSON，也要能画图） */
function tryParseDiagramSpec(text) {
  const t = String(text).trim();
  if (!t.startsWith("{")) return null;
  const spec = (window.XiaoouActivity && XiaoouActivity.parseDiagramJson)
    ? XiaoouActivity.parseDiagramJson(t)
    : null;
  if (spec && typeof spec.type === "string" && DIAGRAM_TYPES.has(spec.type)) return spec;
  return null;
}

function renderDiagramBlock(code) {
  const spec = tryParseDiagramSpec(code);
  const svg = renderDiagram(spec ? JSON.stringify(spec) : code.trim());
  return svg || "";
}

function renderMarkdown(text) {
  const lines = text.split("\n");
  let html = "";
  let list = null; // 'ul' | 'ol'
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  let para = [];
  const flushPara = () => {
    if (!para.length) return;
    let textLines = [];
    const emitText = () => {
      if (textLines.length) {
        html += `<p>${textLines.map(inlineFmt).join("<br>")}</p>`;
        textLines = [];
      }
    };
    for (const line of para) {
      const spec = tryParseDiagramSpec(line);
      if (spec) {
        emitText();
        const svg = renderDiagram(JSON.stringify(spec));
        if (svg) html += svg;
      } else {
        textLines.push(line);
      }
    }
    emitText();
    para = [];
  };
  let fence = null; // {lang, buf:[]}
  for (const raw of lines) {
    const line = raw.trimEnd();
    const fenceMatch = line.match(/^```\s*([\w-]*)\s*$/);
    if (fence) {
      if (fenceMatch) {
        // 结束围栏块
        const code = fence.buf.join("\n");
        const svg = renderDiagramBlock(code);
        if (svg) html += svg;
        else if (code.trim()) html += `<pre class="code">${escapeHtml(code)}</pre>`;
        fence = null;
      } else {
        fence.buf.push(raw);
      }
      continue;
    }
    if (fenceMatch) {
      flushPara(); closeList();
      fence = { lang: fenceMatch[1], buf: [] };
      continue;
    }
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    const ul = line.match(/^\s*[-*•]\s+(.*)$/);
    if (ol) {
      flushPara();
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inlineFmt(ol[1])}</li>`;
    } else if (ul) {
      flushPara();
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inlineFmt(ul[1])}</li>`;
    } else if (line === "") {
      flushPara(); closeList();
    } else {
      closeList(); para.push(line);
    }
  }
  // 流式过程中围栏可能还没闭合：把已收到的 xiaoou-draw 尝试渲染，其它按代码显示
  if (fence) {
    const code = fence.buf.join("\n");
    const svg = renderDiagramBlock(code);
    if (svg) html += svg;
    else if (code.trim()) html += `<pre class="code">${escapeHtml(code)}</pre>`;
  }
  flushPara(); closeList();
  return html || "<p></p>";
}

// ---------------- 图形渲染（小欧插入的 xiaoou-draw 图，用 SVG 安全生成） ----------------
function renderDiagram(jsonText) {
  let s = (window.XiaoouActivity && XiaoouActivity.parseDiagramJson)
    ? XiaoouActivity.parseDiagramJson(jsonText)
    : null;
  if (!s) {
    try { s = JSON.parse(jsonText); } catch (e) { return ""; }
  }
  if (s.type === "snap_grid") {
    const parsed = (window.XiaoouActivity && XiaoouActivity.parseSnapGrid)
      ? XiaoouActivity.parseSnapGrid(s)
      : null;
    if (!parsed) return "";
    return XiaoouActivity.renderSnapGridPlaceholder(parsed);
  }
  let inner = "";
  if (s.type === "dots") inner = diagramDots(s);
  else if (s.type === "square_layers") inner = diagramSquareLayers(s);
  else if (s.type === "square_steps") inner = diagramSquareSteps(s);
  else if (s.type === "square_compare") inner = diagramSquareCompare(s);
  else if (s.type === "numberline") inner = diagramNumberline(s);
  else if (s.type === "bars") inner = diagramBars(s);
  if (!inner) return "";
  const cap = s.caption ? `<figcaption>${inlineFmt(String(s.caption))}</figcaption>` : "";
  return `<figure class="diagram">${inner}${cap}</figure>`;
}

const MILESTONE_DEBOUNCE_MS = 400;

function freezeLiveActivities() {
  state.liveActivities.forEach((h) => { try { h.freeze(); } catch (e) {} });
  state.liveActivities = [];
  if (state.milestoneTimer) { clearTimeout(state.milestoneTimer); state.milestoneTimer = null; }
  state.pendingMilestone = null;
}

function destroyMountedActivities() {
  freezeLiveActivities();
  state.mountedActivities.forEach((h) => { try { h.destroy(); } catch (e) {} });
  state.mountedActivities = [];
}

function clearActivitySession() {
  if (state.milestoneTimer) { clearTimeout(state.milestoneTimer); state.milestoneTimer = null; }
  state.pendingMilestone = null;
  state.queuedMilestone = null;
  state.boards = [];
  state.stageSpec = null;
  destroyMountedActivities();
}

function setCaption(text) {
  const el = $("#tutorCaption");
  if (!el) return;
  el.innerHTML = text ? inlineFmt(text) : "";
}

function showStartPlay() {
  const wrap = $("#startPlayWrap");
  const play = $(".play-stage");
  if (wrap) wrap.classList.remove("hidden");
  if (play) play.classList.remove("is-playing");
  const tools = $("#stageTools");
  if (tools) tools.classList.add("hidden");
}

function hideStartPlay() {
  const wrap = $("#startPlayWrap");
  const play = $(".play-stage");
  if (wrap) wrap.classList.add("hidden");
  if (play) play.classList.add("is-playing");
}

function resetExploreEmpty() {
  destroyMountedActivities();
  state.stageSpec = null;
  const host = $("#stageHost");
  if (host) host.innerHTML = "";
  setCaption("点开始玩，把方块拖进格子");
  showStartPlay();
}

function updateTrayUi() {
  const live = state.liveActivities[state.liveActivities.length - 1];
  const snap = live && live.getSnapshot ? live.getSnapshot() : null;
  const count = $("#trayCount");
  if (count && window.XiaoouActivity && XiaoouActivity.trayCountLabel) {
    count.textContent = XiaoouActivity.trayCountLabel(snap ? snap.tray_left : 0);
  }
  const undoBtn = $("#undoTileBtn");
  if (undoBtn) undoBtn.disabled = !(live && live.canUndo && live.canUndo());
}

function showStageToast(text) {
  const el = $("#stageToast");
  if (!el) return;
  el.textContent = text;
  el.classList.remove("hidden");
  if (state.toastTimer) clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => {
    el.classList.add("hidden");
    state.toastTimer = null;
  }, 900);
}

function isStageExpanded() {
  const play = $(".play-stage");
  return !!(play && play.classList.contains("is-expanded"));
}

function syncExpandButton() {
  const btn = $("#expandStageBtn");
  if (!btn) return;
  const on = isStageExpanded();
  btn.textContent = on ? "收起" : "展开";
  btn.setAttribute("aria-pressed", on ? "true" : "false");
}

function toggleStageExpand() {
  const play = $(".play-stage");
  if (!play) return;
  play.classList.toggle("is-expanded");
  syncExpandButton();
  if (state.stageSpec) {
    const live = state.liveActivities[state.liveActivities.length - 1];
    const occ = (live && live.getOccupancy) ? live.getOccupancy().occupied : [];
    remountStage(state.stageSpec, occ);
  }
}

function remountStage(spec, occupied) {
  if (!spec || !window.XiaoouActivity) return;
  freezeLiveActivities();
  state.mountedActivities.forEach((h) => { try { h.destroy(); } catch (e) {} });
  state.mountedActivities = [];
  state.stageSpec = spec;
  state.boards = [{ occupied: occupied || [], trayLeft: 0 }];
  hideStartPlay();
  const host = $("#stageHost");
  if (!host) return;
  host.innerHTML = XiaoouActivity.renderSnapGridPlaceholder(spec);
  const tools = $("#stageTools");
  if (tools) tools.classList.remove("hidden");
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      hydrateSnapGrids(host, true);
      updateTrayUi();
    });
  });
}

function lastSnapGridSpec(text) {
  if (!window.XiaoouActivity || !XiaoouActivity.parseSnapGrid) return null;
  let spec = null;
  const re = /```(?:xiaoou-draw|json)?\s*([\s\S]*?)```/g;
  let m;
  while ((m = re.exec(String(text || ""))) !== null) {
    const parsed = XiaoouActivity.parseSnapGrid(m[1]);
    if (parsed) spec = parsed;
  }
  String(text || "").split("\n").forEach((line) => {
    const parsed = XiaoouActivity.parseSnapGrid(line.trim());
    if (parsed) spec = parsed;
  });
  return spec;
}

function lastStaticDiagramHtml(text) {
  const html = renderMarkdown(String(text || ""));
  const div = document.createElement("div");
  div.innerHTML = html;
  const figs = div.querySelectorAll("figure.diagram");
  if (!figs.length) return "";
  return figs[figs.length - 1].outerHTML;
}

function syncStageFromTutor(text) {
  const spec = lastSnapGridSpec(text);
  if (spec) {
    if (window.XiaoouActivity && XiaoouActivity.sameSnapGrid(state.stageSpec, spec)) return;
    remountStage(spec, []);
    return;
  }
  const html = lastStaticDiagramHtml(text);
  if (!html) return;
  freezeLiveActivities();
  state.mountedActivities.forEach((h) => { try { h.destroy(); } catch (e) {} });
  state.mountedActivities = [];
  state.stageSpec = null;
  hideStartPlay();
  const host = $("#stageHost");
  if (host) host.innerHTML = html;
  const tools = $("#stageTools");
  if (tools) tools.classList.add("hidden");
}

function restoreStageFromHistory() {
  const lastAsst = [...state.messages].reverse().find((m) => m.role === "assistant" && typeof m.content === "string");
  if (lastAsst && window.XiaoouActivity && XiaoouActivity.tutorCaption) {
    const cap = XiaoouActivity.tutorCaption(lastAsst.content);
    if (cap) setCaption(cap);
  }
  if (!lastAsst) return;
  const spec = lastSnapGridSpec(lastAsst.content);
  if (spec) {
    const occ = (state.boards.length && state.boards[state.boards.length - 1].occupied) || [];
    remountStage(spec, occ);
    return;
  }
  syncStageFromTutor(lastAsst.content);
}

async function startPlay() {
  if (state.streaming) return;
  if (state.config && !state.config.configured) return;
  hideStartPlay();
  const spec = window.XiaoouActivity
    ? XiaoouActivity.parseSnapGrid(XiaoouActivity.DEFAULT_SNAP_GRID)
    : null;
  if (spec) remountStage(spec, []);
  setCaption("先随便摆摆，小欧马上出题。");
  applyModeUI();
  await streamAssistant(true);
}

function placeMessages() {
  const messages = $("#messages");
  const historyMount = $("#historyMount");
  const app = $(".app");
  const composer = $(".composer");
  if (!messages) return;
  if (state.mode === "explore" && historyMount) historyMount.appendChild(messages);
  else if (app && composer) app.insertBefore(messages, composer);
}

function setTalkOpen(on) {
  state.talkOpen = !!on;
  const app = $(".app");
  if (app) app.classList.toggle("talk-open", state.talkOpen);
  const talkBtn = $("#talkBtn");
  if (talkBtn) talkBtn.textContent = state.talkOpen ? "收起" : "想跟小欧说";
  if (!state.talkOpen) stopVoiceTalk({ discard: true });
  else refreshVoiceAvailability();
}

function openHistorySheet() {
  placeMessages();
  const sheet = $("#historySheet");
  if (sheet) sheet.classList.add("open");
  scrollToBottom();
}
function closeHistorySheet() {
  const sheet = $("#historySheet");
  if (sheet) sheet.classList.remove("open");
}
function openHelpSheet() {
  const sheet = $("#helpSheet");
  if (sheet) sheet.classList.add("open");
}
function closeHelpSheet() {
  const sheet = $("#helpSheet");
  if (sheet) sheet.classList.remove("open");
}

function hydrateSnapGrids(bubble, interactive) {
  if (!bubble || !window.XiaoouActivity || !XiaoouActivity.mountSnapGrid) return;
  if (!interactive && state.mode === "explore") return;
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
  updateTrayUi();
  if (eventName === "board_full") showStageToast("摆好了");
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

const DIAG_BLUE = "#3f5bd6", DIAG_GOLD = "#e09a2c";
function clampInt(v, lo, hi, dflt) {
  v = parseInt(v, 10);
  if (isNaN(v)) return dflt;
  return Math.max(lo, Math.min(hi, v));
}
function tileRect(cx, cy, size, fill, opacity) {
  const x = cx - size / 2, y = cy - size / 2;
  const rx = Math.max(3, Math.round(size * 0.22));
  const op = opacity == null ? "" : ` opacity="${opacity}"`;
  return `<rect x="${x}" y="${y}" width="${size}" height="${size}" rx="${rx}" fill="${fill}"${op}/>`;
}
function diagramDots(s) {
  const rows = clampInt(s.rows, 1, 10, 1), cols = clampInt(s.cols, 1, 10, 1);
  const cell = 30, size = 20, pad = 14;
  const w = cols * cell + pad * 2, h = rows * cell + pad * 2;
  let dots = `<rect x="0" y="0" width="${w}" height="${h}" rx="16" fill="#fffdf8"/>`;
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      const cx = pad + j * cell + cell / 2, cy = pad + i * cell + cell / 2;
      const isNew = s.newLastRowCol && (i === rows - 1 || j === cols - 1);
      dots += tileRect(cx, cy, size, isNew ? DIAG_GOLD : DIAG_BLUE);
    }
  }
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">${dots}</svg>`;
}
function layerHighlight(raw, n) {
  if (raw === 0 || raw === "0" || raw === "none" || raw === false) return null;
  if (raw === undefined || raw === null) return n;
  return clampInt(raw, 1, n, n);
}
function drawSquareDots(n, ox, oy, cell, r, highlightLayer) {
  const size = Math.max(10, Math.round((r || 7) * 2.1));
  let dots = "";
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const layer = n - Math.min(i, j, n - 1 - i, n - 1 - j);
      const cx = ox + j * cell + cell / 2, cy = oy + i * cell + cell / 2;
      const isHL = highlightLayer !== null && layer === highlightLayer;
      dots += tileRect(cx, cy, size, isHL ? DIAG_GOLD : DIAG_BLUE, isHL ? 1 : 0.45 + layer * 0.08);
    }
  }
  return dots;
}
function diagramSquareLayers(s) {
  const n = clampInt(s.size, 1, 8, 3);
  const highlight = layerHighlight(s.highlight ?? s.highlightLayer, n);
  const cell = 22, r = 7, pad = 12;
  const w = n * cell + pad * 2, h = n * cell + pad * 2;
  const dots = drawSquareDots(n, pad, pad, cell, r, highlight);
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">${dots}</svg>`;
}
function diagramSquareCompare(s) {
  const from = clampInt(s.from, 1, 8, 3);
  let to = clampInt(s.to, 1, 8, from + 1);
  if (to <= from) to = from + 1;
  const cell = 18, r = 6, gap = 22, pad = 10, labelH = 18;
  const fromW = from * cell, toW = to * cell;
  let parts = drawSquareDots(from, pad, pad, cell, r, null);
  parts += `<text x="${pad + fromW / 2}" y="${pad + from * cell + labelH}" font-size="11" text-anchor="middle" fill="#666">${from}×${from}</text>`;
  const x2 = pad + fromW + gap;
  parts += drawSquareDots(to, x2, pad, cell, r, to);
  parts += `<text x="${x2 + toW / 2}" y="${pad + to * cell + labelH}" font-size="11" text-anchor="middle" fill="#666">${to}×${to}</text>`;
  parts += `<text x="${pad + fromW + gap / 2}" y="${pad + Math.max(from, to) * cell / 2 + 4}" font-size="16" text-anchor="middle" fill="#999">→</text>`;
  const w = x2 + toW + pad, h = pad + Math.max(from, to) * cell + labelH + 6;
  return `<svg viewBox="0 0 ${w} ${h}" width="${Math.min(w, 520)}" height="${h}" role="img">${parts}</svg>`;
}
function diagramSquareSteps(s) {
  const max = clampInt(s.max ?? s.count, 1, 6, 3);
  const highlight = clampInt(s.highlight, 1, max, max);
  const cell = 16, r = 6, gap = 14, pad = 10, labelH = 18;
  let x = pad, parts = "";
  for (let size = 1; size <= max; size++) {
    const sqW = size * cell, sqH = size * cell;
    for (let i = 0; i < size; i++) {
      for (let j = 0; j < size; j++) {
        const layer = size - Math.min(i, j, size - 1 - i, size - 1 - j);
        const cx = x + j * cell + cell / 2, cy = pad + i * cell + cell / 2;
        const isHL = size === highlight && layer === size;
        parts += tileRect(cx, cy, Math.max(10, Math.round(r * 2.1)), isHL ? DIAG_GOLD : DIAG_BLUE, isHL ? 1 : 0.55 + layer * 0.07);
      }
    }
    parts += `<text x="${x + sqW / 2}" y="${pad + sqH + labelH}" font-size="11" text-anchor="middle" fill="#666">${size}×${size}</text>`;
    x += sqW + gap;
  }
  const w = x - gap + pad, h = pad + max * cell + labelH + 6;
  return `<svg viewBox="0 0 ${w} ${h}" width="${Math.min(w, 520)}" height="${h}" role="img">${parts}</svg>`;
}
function diagramNumberline(s) {
  let from = clampInt(s.from, -50, 200, 0), to = clampInt(s.to, -50, 200, 10);
  if (to <= from) to = from + 1;
  if (to - from > 30) to = from + 30;
  const n = to - from, step = 34, pad = 24;
  const w = n * step + pad * 2, h = 56, y = 26;
  const marks = Array.isArray(s.marks) ? s.marks : [];
  let el = `<line x1="${pad}" y1="${y}" x2="${pad + n * step}" y2="${y}" stroke="#9aa" stroke-width="2"/>`;
  for (let k = 0; k <= n; k++) {
    const x = pad + k * step, val = from + k;
    const on = marks.includes(val);
    el += `<line x1="${x}" y1="${y - 5}" x2="${x}" y2="${y + 5}" stroke="#9aa" stroke-width="2"/>`;
    if (on) el += `<circle cx="${x}" cy="${y}" r="6" fill="${DIAG_GOLD}"/>`;
    el += `<text x="${x}" y="${y + 22}" font-size="12" text-anchor="middle" fill="#555">${val}</text>`;
  }
  return `<svg viewBox="0 0 ${w} ${h}" width="${Math.min(w, 520)}" height="${h}" role="img">${el}</svg>`;
}
function diagramBars(s) {
  const items = (Array.isArray(s.items) ? s.items : []).slice(0, 8);
  if (!items.length) return "";
  const vals = items.map((it) => Math.max(0, Number(it.value) || 0));
  const max = Math.max(...vals, 1);
  const tile = 18, gap = 5, labelH = 22, rowGap = 16, pad = 8;
  const useTiles = max <= 12;
  let el = "";
  let y = pad;
  let w = 280;
  if (useTiles) {
    items.forEach((it, i) => {
      const v = vals[i];
      const label = escapeHtml(String(it.label ?? ""));
      el += `<text x="${pad}" y="${y + 13}" font-size="13" fill="#5c5348">${label}</text>`;
      y += labelH;
      for (let k = 0; k < v; k++) {
        const x = pad + k * (tile + gap);
        el += `<rect x="${x}" y="${y}" width="${tile}" height="${tile}" rx="6" fill="${DIAG_BLUE}"/>`;
      }
      el += `<text x="${pad + v * (tile + gap)}" y="${y + 14}" font-size="12" fill="#8a8074">${v}</text>`;
      w = Math.max(w, pad + v * (tile + gap) + 28);
      y += tile + rowGap;
    });
  } else {
    const labelW = 72, barMax = 220;
    items.forEach((it, i) => {
      const v = vals[i];
      const bw = Math.round((v / max) * barMax);
      el += `<text x="0" y="${y + 16}" font-size="13" fill="#5c5348">${escapeHtml(String(it.label ?? ""))}</text>`;
      el += `<rect x="${labelW}" y="${y + 4}" width="${bw}" height="18" rx="9" fill="${DIAG_BLUE}"/>`;
      el += `<text x="${labelW + bw + 6}" y="${y + 17}" font-size="12" fill="#8a8074">${v}</text>`;
      y += 32;
    });
    w = labelW + barMax + 40;
  }
  const h = y + pad - (useTiles ? rowGap : 0);
  return `<svg viewBox="0 0 ${w} ${h}" width="${Math.min(w, 360)}" height="${h}" role="img">${el}</svg>`;
}

// ---------------- 消息渲染 ----------------
function avatarText(role) { return role === "child" ? "我" : "欧"; }

function addMessageEl(role) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = avatarText(role);
  const body = document.createElement("div");
  body.className = "msg-body";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  body.appendChild(bubble);
  wrap.appendChild(avatar);
  wrap.appendChild(body);
  $("#messages").appendChild(wrap);
  scrollToBottom();
  return bubble;
}

function scrollToBottom() {
  const m = $("#messages");
  m.scrollTop = m.scrollHeight;
}

function removeReasoningBlocks() {
  document.querySelectorAll(".reasoning").forEach((el) => el.remove());
}

function setReasoningVisibility(show) {
  const messages = $("#messages");
  if (messages) messages.classList.toggle("hide-reasoning", !show);
  if (!show) removeReasoningBlocks();
}

function getReasoningEl(tutorBubble) {
  if (!state.showReasoning) return null;
  const body = tutorBubble.closest(".msg-body");
  if (!body) return null;
  let el = body.querySelector(".reasoning");
  if (!el) {
    el = document.createElement("div");
    el.className = "reasoning";
    el.setAttribute("aria-label", "小欧的思考过程");
    body.insertBefore(el, tutorBubble);
  }
  return el;
}

// content 可能是纯文字，也可能是含图片的数组。这里统一渲染进气泡。
function renderMilestoneStatus(content) {
  const eventM = content.match(/节点：(\w+)/);
  const gridM = content.match(/格子：(\d+)\s*×\s*(\d+)/);
  const filledM = content.match(/已放：(\d+)/);
  const emptyM = content.match(/空格：(\d+)/);
  const trayM = content.match(/托盘剩余：(\d+)/);
  const eventName = eventM ? eventM[1] : "";
  const snapshot = {
    cols: gridM ? parseInt(gridM[1], 10) : 0,
    rows: gridM ? parseInt(gridM[2], 10) : 0,
    filled: filledM ? parseInt(filledM[1], 10) : 0,
    empty: emptyM ? parseInt(emptyM[1], 10) : 0,
    tray_left: trayM ? parseInt(trayM[1], 10) : 0,
  };
  const label = (window.XiaoouActivity && XiaoouActivity.childLabel)
    ? XiaoouActivity.childLabel(eventName, snapshot)
    : "摆了一下";
  return `<p class="activity-status">${escapeHtml(label)}</p>`;
}

function renderContentInto(bubble, content) {
  if (typeof content === "string") {
    if (content.includes("（孩子在学具上摆完了一步，这不是她打的字）")) {
      bubble.innerHTML = renderMilestoneStatus(content);
      return;
    }
    const liveMarker = "（当前学具盘面，这不是她打的字）";
    const cut = content.indexOf(liveMarker);
    if (cut >= 0) {
      const spoken = content.slice(0, cut).trim();
      bubble.innerHTML = renderMarkdown(spoken || "…");
      return;
    }
    bubble.innerHTML = renderMarkdown(content);
    return;
  }
  bubble.innerHTML = "";
  for (const part of content) {
    if (part.type === "image_url" && part.image_url && part.image_url.url) {
      const img = document.createElement("img");
      img.className = "msg-img";
      img.src = part.image_url.url;
      img.addEventListener("click", () => window.open(img.src, "_blank"));
      bubble.appendChild(img);
    } else if (part.type === "text" && part.text) {
      const div = document.createElement("div");
      div.innerHTML = renderMarkdown(part.text);
      bubble.appendChild(div);
    }
  }
}

function renderWelcome() {
  const topic = state.topics.find((t) => t.key === state.topicKey);
  const name = state.childName ? `${state.childName}，` : "";
  const bubble = addMessageEl("tutor");
  const starter = topic ? topic.starter : "";
  const body = `${name}你好呀，我是小欧。我不会直接告诉你答案，但我会陪你一步一步想出来。\n\n我们现在是「带题来问」模式。${starter}`;
  bubble.innerHTML = renderMarkdown(body);
}

function renderHistory() {
  destroyMountedActivities();
  state.stageSpec = null;
  $("#messages").innerHTML = "";
  if (state.messages.length === 0) {
    if (state.mode === "explore") {
      resetExploreEmpty();
    } else {
      renderWelcome();
    }
    applyModeUI();
    return;
  }
  hideStartPlay();
  for (const m of state.messages) {
    const bubble = addMessageEl(m.role === "user" ? "child" : "tutor");
    renderContentInto(bubble, m.content);
    if (m.role === "assistant") hydrateSnapGrids(bubble, false);
  }
  if (state.mode === "explore") restoreStageFromHistory();
  applyModeUI();
}

// ---------------- 配置加载 ----------------
async function loadConfig() {
  const res = await fetch("/api/config");
  if (res.status === 401) {
    window.location.replace("/gate.html");
    return;
  }
  const cfg = await res.json();
  state.config = cfg;
  state.topics = cfg.topics;

  const saved = loadSession();
  state.topicKey = (saved && saved.topicKey) || cfg.default_topic;
  state.level = (saved && saved.level) || cfg.default_level;
  state.childName = (saved && saved.childName) || "";
  state.mode = (saved && saved.mode) || cfg.default_mode || "explore";
  state.thinking = (saved && typeof saved.thinking === "boolean") ? saved.thinking : !!cfg.thinking_enabled;
  state.showReasoning = (saved && typeof saved.showReasoning === "boolean")
    ? saved.showReasoning
    : !!cfg.show_reasoning;
  state.messages = (saved && saved.messages) || [];
  state.boards = (saved && Array.isArray(saved.boards)) ? saved.boards : [];

  // 主题下拉
  const topicSel = $("#topicSelect");
  topicSel.innerHTML = "";
  cfg.topics.forEach((t) => {
    const o = document.createElement("option");
    o.value = t.key; o.textContent = t.name;
    topicSel.appendChild(o);
  });
  topicSel.value = state.topicKey;
  fillTopicList();

  // 难度下拉
  const levelSel = $("#levelSelect");
  const levelNames = { lower: "一二年级 · 启蒙（约 6-8 岁）", middle: "三四年级 · 进阶（约 8-10 岁）", upper: "五六年级 · 挑战（约 11 岁+）" };
  levelSel.innerHTML = "";
  cfg.levels.forEach((l) => {
    const o = document.createElement("option");
    o.value = l.key; o.textContent = levelNames[l.key] || l.key;
    o.title = l.desc;
    levelSel.appendChild(o);
  });
  levelSel.value = state.level;

  $("#thinkingSelect").value = state.thinking ? "on" : "off";
  $("#showReasoningSelect").value = state.showReasoning ? "on" : "off";
  syncReasoningUi();
  setReasoningVisibility(state.showReasoning);

  $("#childName").value = state.childName;

  // 快捷按钮
  const qa = $("#quickActions");
  qa.innerHTML = "";
  const help = $("#helpActions");
  if (help) help.innerHTML = "";
  cfg.quick_actions.forEach((a) => {
    const make = (into) => {
      if (!into) return;
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = a.label;
      b.dataset.message = a.message;
      b.addEventListener("click", () => {
        closeHelpSheet();
        sendMessage(a.message);
      });
      into.appendChild(b);
    };
    make(qa);
    make(help);
  });

  const modeSel = $("#modeSelect");
  if (modeSel) modeSel.value = state.mode;

  // 拍照按钮：未连接模型时禁用并提示
  const attach = $("#attachBtn");
  if (cfg.vision_enabled) {
    attach.disabled = false;
    attach.title = "拍照或上传作业本上的题目";
  } else {
    attach.disabled = true;
    attach.title = "连接大模型后即可拍照上传题目";
  }

  // 模型标签 / 未配置提示
  if (cfg.configured) {
    let tag = "已连接模型：" + cfg.model;
    tag += cfg.pipeline === "unified" ? " · 多模态一体" : " · OCR+文字";
    if (cfg.thinking_enabled) {
      tag += cfg.show_reasoning ? " · Thinking 开（显示思考）" : " · Thinking 开（隐藏思考）";
    }
    $("#modelTag").textContent = tag;
    $("#banner").classList.add("hidden");
  } else {
    $("#modelTag").textContent = "尚未连接大模型";
    const banner = $("#banner");
    banner.classList.remove("hidden");
    banner.innerHTML =
      "还没有连接大模型。请把项目里的 <code>.env.example</code> 复制成 <code>.env</code>，填入你的 API 密钥后重新启动。你仍然可以先浏览界面。";
  }

  updateAxioms();
  updatePhotoHint(cfg);
  applyModeUI();
  renderHistory();
  refreshVoiceAvailability();
}

// 思考模式关闭时，展示思考的选项不可用。
function syncReasoningUi() {
  const on = state.thinking;
  const field = $("#showReasoningField");
  const sel = $("#showReasoningSelect");
  if (field) field.classList.toggle("disabled", !on);
  if (sel) {
    sel.disabled = !on;
    if (!on) {
      state.showReasoning = false;
      sel.value = "off";
    }
  }
  setReasoningVisibility(state.showReasoning);
}

// 根据当前模式调整界面：探索模式突出"出个新题"、隐藏相机；带题模式相反。
function applyModeUI() {
  const explore = state.mode === "explore";
  const app = $(".app");
  if (app) {
    app.classList.toggle("layout-explore", explore);
    app.classList.toggle("layout-bring", !explore);
  }
  placeMessages();
  if (!explore) setTalkOpen(true);
  else if (!state.talkOpen) setTalkOpen(false);

  const exploreBtn = $("#exploreBtn");
  if (exploreBtn) exploreBtn.classList.add("hidden");
  if (state.config && !state.config.configured) {
    if (exploreBtn) exploreBtn.disabled = true;
    const startBtn = $("#startPlayBtn");
    if (startBtn) startBtn.disabled = true;
  }

  const attach = $("#attachBtn");
  if (attach) attach.classList.toggle("hidden", explore);

  const input = $("#input");
  if (input) input.placeholder = explore ? "说给你听，或打字…" : "拍题或打字告诉小欧…";

  const line = $("#topicLine");
  if (line) {
    const topic = state.topics.find((t) => t.key === state.topicKey);
    const tname = topic ? topic.name : "选主题";
    line.textContent = tname;
  }
  const chip = $("#topicChip");
  if (chip) chip.setAttribute("aria-expanded", "false");

  const modeSel = $("#modeSelect");
  if (modeSel) modeSel.value = state.mode;

  const started = explore && ($(".play-stage") && $(".play-stage").classList.contains("is-playing") || state.messages.length > 0);
  const helpBtn = $("#helpBtn");
  const talkBtn = $("#talkBtn");
  const historyBtn = $("#historyBtn");
  if (helpBtn) helpBtn.classList.toggle("hidden", !explore || !started);
  if (talkBtn) talkBtn.classList.toggle("hidden", !explore || !started);
  if (historyBtn) historyBtn.disabled = !explore;
}

function updatePhotoHint(cfg) {
  const hint = document.querySelector(".img-hint");
  if (!hint) return;
  hint.textContent = cfg.pipeline === "unified"
    ? "多模态模式：小欧会直接看图，再反问你，不会直接给答案。"
    : "这张题目会先被读成文字，小欧再陪你想——不会直接给答案。";
}

function updateAxioms() {
  const topic = state.topics.find((t) => t.key === state.topicKey);
  const ul = $("#axiomList");
  ul.innerHTML = "";
  if (!topic) return;
  topic.axioms.forEach((a) => {
    const li = document.createElement("li");
    li.textContent = a;
    ul.appendChild(li);
  });
  applyModeUI();
}

// ---------------- 发送 / 流式接收 ----------------
async function sendMessage(text) {
  if (state.streaming) return;
  const typed = (text || $("#input").value).trim();
  const image = state.pendingImage;
  if (!typed && !image) return;

  // 组装本条消息：有图片时用多模态数组，否则用纯文字。
  let content;
  if (image) {
    const caption = typed || "这是我作业本上的题目，你先帮我看看。";
    content = [
      { type: "text", text: caption },
      { type: "image_url", image_url: { url: image } },
    ];
  } else {
    content = typed;
  }

  // 显示孩子的消息
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
  $("#input").value = "";
  clearPendingImage();
  autoGrow($("#input"));
  saveSession();

  await streamAssistant(false);
}

// 探索模式：点"出个新题"，让小欧出题（不显示孩子气泡）。
async function startExplore() {
  if (state.streaming) return;
  await streamAssistant(true);
}

// 共用的流式接收逻辑。kickoff=true 时请求小欧出题。
async function streamAssistant(kickoff) {
  setStreaming(true);
  const tutorBubble = addMessageEl("tutor");
  tutorBubble.classList.add("cursor-blink");
  let acc = "";
  let reasoningAcc = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: state.messages,
        topic: state.topicKey,
        level: state.level,
        child_name: state.childName,
        mode: state.mode,
        kickoff: !!kickoff,
        thinking: state.thinking,
        show_reasoning: state.showReasoning,
      }),
    });
    if (res.status === 401) {
      window.location.replace("/gate.html");
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop();
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const payload = JSON.parse(line.slice(5).trim());
        if (payload.delta) {
          acc += payload.delta;
          tutorBubble.innerHTML = renderMarkdown(acc);
          if (state.mode === "explore" && window.XiaoouActivity && XiaoouActivity.tutorCaption) {
            const cap = XiaoouActivity.tutorCaption(acc);
            if (cap) setCaption(cap);
          }
          scrollToBottom();
        } else if (payload.reasoning_delta) {
          if (!state.showReasoning) continue;
          reasoningAcc += payload.reasoning_delta;
          const rel = getReasoningEl(tutorBubble);
          if (rel) {
            rel.textContent = reasoningAcc;
            scrollToBottom();
          }
        } else if (payload.transcript) {
          showTranscript(payload.transcript, tutorBubble);
          // 把刚发出的图片消息换成文字，后续更省流量、也能存下来
          const lastUser = state.messages[state.messages.length - 1];
          if (lastUser && Array.isArray(lastUser.content)) {
            lastUser.content = "（这是从我作业照片里读出来的题目）\n" + payload.transcript;
          }
          saveSession();
        } else if (payload.error) {
          acc += (acc ? "\n\n" : "") + payload.error;
          tutorBubble.innerHTML = renderMarkdown(acc);
        }
      }
    }
  } catch (err) {
    acc += (acc ? "\n\n" : "") + "抱歉，连接出了点问题，请稍后再试。";
    tutorBubble.innerHTML = renderMarkdown(acc);
  }

  tutorBubble.classList.remove("cursor-blink");
  if (acc.trim()) {
    state.messages.push({ role: "assistant", content: acc });
    saveSession();
    if (state.mode === "explore") {
      const cap = window.XiaoouActivity && XiaoouActivity.tutorCaption
        ? XiaoouActivity.tutorCaption(acc)
        : "";
      if (cap) setCaption(cap);
      syncStageFromTutor(acc);
    } else {
      const hasGrid = tutorBubble.querySelector("figure.diagram[data-snap-grid]");
      if (hasGrid) freezeLiveActivities();
      hydrateSnapGrids(tutorBubble, true);
    }
    saveSession();
  }
  setStreaming(false);
  if (state.queuedMilestone) {
    const q = state.queuedMilestone;
    state.queuedMilestone = null;
    sendActivityMilestone(q.event, q.snapshot);
  }
}

function setStreaming(on) {
  state.streaming = on;
  $("#sendBtn").disabled = on;
  const attach = $("#attachBtn");
  if (attach && state.config && state.config.vision_enabled) attach.disabled = on;
  const exploreBtn = $("#exploreBtn");
  if (exploreBtn && state.config && state.config.configured) exploreBtn.disabled = on;
  const startBtn = $("#startPlayBtn");
  if (startBtn && state.config && state.config.configured) startBtn.disabled = on;
  const newQ = $("#newQuestionBtn");
  if (newQ) newQ.disabled = on;
  document.querySelectorAll(".quick-actions button, #helpActions button").forEach((b) => (b.disabled = on));
}

// 切换探究模式。切换会清空当前对话（因为教学设定不同）。
function switchMode(mode) {
  if (mode === state.mode || state.streaming) return;
  if (state.messages.length && !confirm("切换模式会清空当前对话，确定吗？")) {
    const modeSel = $("#modeSelect");
    if (modeSel) modeSel.value = state.mode;
    return;
  }
  state.mode = mode;
  state.messages = [];
  state.talkOpen = false;
  clearPendingImage();
  clearActivitySession();
  saveSession();
  applyModeUI();
  renderHistory();
}

// ---------------- 拍照 / 上传题目 ----------------
// 把照片缩小到合适尺寸（长边最多 1280px），既省流量又够清晰。
function resizeImage(file, maxDim = 1280, quality = 0.82) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("图片解析失败"));
      img.onload = () => {
        let { width, height } = img;
        const scale = Math.min(1, maxDim / Math.max(width, height));
        width = Math.round(width * scale);
        height = Math.round(height * scale);
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL("image/jpeg", quality));
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

async function onFileChosen(e) {
  const file = e.target.files && e.target.files[0];
  e.target.value = ""; // 允许再次选同一张
  if (!file) return;
  try {
    state.pendingImage = await resizeImage(file);
    $("#imgPreviewThumb").src = state.pendingImage;
    $("#imgPreview").classList.remove("hidden");
    $("#input").focus();
  } catch (err) {
    alert("这张图片没能读进来，换一张试试看？");
  }
}

function clearPendingImage() {
  state.pendingImage = null;
  $("#imgPreviewThumb").removeAttribute("src");
  $("#imgPreview").classList.add("hidden");
}

function setPendingImage(dataUrl) {
  state.pendingImage = dataUrl;
  $("#imgPreviewThumb").src = dataUrl;
  $("#imgPreview").classList.remove("hidden");
}

// ---------------- 语音输入（点一下说话 → 服务端听写） ----------------
const voiceSession = {
  rec: null,
  stream: null,
  chunks: [],
  listening: false,
  busy: false,
  discard: false,
  timer: null,
  startedAt: 0,
};

function voiceHttpsHost() {
  const host = location.hostname;
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return host + ".sslip.io";
  return host || "8.211.182.149.sslip.io";
}

function voiceBlockReason() {
  if (!window.isSecureContext) {
    return "手机录音需要安全连接。请用 https://" + voiceHttpsHost() + " 打开，并允许麦克风。";
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || typeof MediaRecorder === "undefined") {
    return "这个浏览器还不能录音，换 Safari 或 Chrome 试试。";
  }
  if (state.config && state.config.voice_enabled === false) {
    return "小欧这边还没接上耳朵。";
  }
  return "";
}

function setVoiceUi(mode, message) {
  const btn = $("#voiceTalkBtn");
  const hint = $("#voiceHint");
  const label = btn ? btn.querySelector(".voice-label") : null;
  const micBtn = $("#micBtn");
  if (btn) {
    btn.classList.toggle("is-listening", mode === "listening");
    btn.classList.toggle("is-busy", mode === "busy");
    btn.classList.toggle("is-blocked", mode === "blocked");
    btn.setAttribute("aria-pressed", mode === "listening" ? "true" : "false");
  }
  if (micBtn) {
    micBtn.classList.toggle("recording", mode === "listening");
    micBtn.disabled = mode === "blocked" || mode === "busy";
  }
  const copy = {
    idle: ["点一下，跟小欧说", "说完再点一下，小欧帮你写成字"],
    listening: ["正在听…", message || "说完再点一下"],
    busy: ["小欧在听写…", "马上写成字"],
    blocked: ["现在还不能发语音", message || ""],
    error: ["再试一次", message || "刚才没听清"],
  };
  const pair = copy[mode] || copy.idle;
  if (label) label.textContent = pair[0];
  if (hint) hint.textContent = pair[1];
}

function refreshVoiceAvailability() {
  if (voiceSession.listening || voiceSession.busy) return;
  const reason = voiceBlockReason();
  if (reason) setVoiceUi("blocked", reason);
  else setVoiceUi("idle");
}

function pickRecorderMime() {
  const types = ["audio/mp4", "audio/aac", "audio/webm;codecs=opus", "audio/webm"];
  if (!window.MediaRecorder || !MediaRecorder.isTypeSupported) return types[0];
  for (const type of types) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || "");
      const idx = text.indexOf(",");
      resolve(idx >= 0 ? text.slice(idx + 1) : text);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function formatVoiceClock(ms) {
  const sec = Math.max(0, Math.floor(ms / 1000));
  return "0:" + String(sec).padStart(2, "0");
}

function clearVoiceTimer() {
  if (voiceSession.timer) {
    clearInterval(voiceSession.timer);
    voiceSession.timer = null;
  }
}

function stopVoiceTracks() {
  if (voiceSession.stream) {
    voiceSession.stream.getTracks().forEach((track) => track.stop());
    voiceSession.stream = null;
  }
}

function stopVoiceTalk(opts) {
  const discard = !!(opts && opts.discard);
  voiceSession.discard = discard;
  clearVoiceTimer();
  if (voiceSession.rec && voiceSession.listening) {
    try { voiceSession.rec.stop(); } catch (e) { stopVoiceTracks(); }
    return;
  }
  stopVoiceTracks();
  voiceSession.listening = false;
  if (!voiceSession.busy) refreshVoiceAvailability();
}

async function transcribeVoiceBlob(blob) {
  voiceSession.busy = true;
  setVoiceUi("busy");
  try {
    if (!blob || blob.size < 400) {
      setVoiceUi("error", "再说长一点点，小欧才听得清。");
      return;
    }
    const audio = await blobToBase64(blob);
    const res = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio, mime: blob.type || "audio/webm" }),
    });
    if (res.status === 401) {
      window.location.replace("/gate.html");
      return;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.text) {
      setVoiceUi("error", data.error || "刚才没听清，再说一次吧。");
      return;
    }
    const input = $("#input");
    const prefix = input && input.value.trim() ? input.value.trim() + " " : "";
    if (input) {
      input.value = prefix + data.text.trim();
      autoGrow(input);
      input.focus();
    }
    setVoiceUi("idle");
    const hint = $("#voiceHint");
    if (hint) hint.textContent = "听好了，可以改几个字再发给小欧";
  } catch (e) {
    setVoiceUi("error", "刚才没听清，再说一次吧。");
  } finally {
    voiceSession.busy = false;
  }
}

async function startVoiceTalk() {
  const reason = voiceBlockReason();
  if (reason) {
    setVoiceUi("blocked", reason);
    return;
  }
  const mime = pickRecorderMime();
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
  voiceSession.rec = rec;
  voiceSession.stream = stream;
  voiceSession.chunks = [];
  voiceSession.discard = false;
  voiceSession.listening = true;
  voiceSession.startedAt = Date.now();
  rec.ondataavailable = (e) => {
    if (e.data && e.data.size) voiceSession.chunks.push(e.data);
  };
  rec.onstop = async () => {
    voiceSession.listening = false;
    stopVoiceTracks();
    clearVoiceTimer();
    const chunks = voiceSession.chunks;
    voiceSession.chunks = [];
    voiceSession.rec = null;
    if (voiceSession.discard) {
      voiceSession.discard = false;
      refreshVoiceAvailability();
      return;
    }
    const blob = new Blob(chunks, { type: rec.mimeType || mime || "audio/webm" });
    await transcribeVoiceBlob(blob);
  };
  rec.start(250);
  setVoiceUi("listening", "0:00 · 说完再点一下");
  voiceSession.timer = setInterval(() => {
    const elapsed = Date.now() - voiceSession.startedAt;
    setVoiceUi("listening", formatVoiceClock(elapsed) + " · 说完再点一下");
    if (elapsed >= 45000) stopVoiceTalk();
  }, 250);
}

async function toggleVoiceTalk() {
  if (voiceSession.busy) return;
  if (voiceSession.listening) {
    stopVoiceTalk();
    return;
  }
  try {
    await startVoiceTalk();
  } catch (e) {
    stopVoiceTracks();
    voiceSession.listening = false;
    const denied = e && (e.name === "NotAllowedError" || e.name === "PermissionDeniedError");
    setVoiceUi("error", denied ? "请允许麦克风，才能跟小欧说话。" : "这个浏览器还不能录音。");
  }
}

function initVoice() {
  refreshVoiceAvailability();
  const talkBtn = $("#voiceTalkBtn");
  if (talkBtn) talkBtn.addEventListener("click", toggleVoiceTalk);
  const micBtn = $("#micBtn");
  if (micBtn) micBtn.addEventListener("click", toggleVoiceTalk);
}

// ---------------- 画板输入 ----------------
function initDraw() {
  const modal = $("#drawModal"), canvas = $("#drawCanvas");
  const ctx = canvas.getContext("2d");
  let strokes = [], cur = null, drawing = false;

  function sizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    redraw();
  }
  function redraw() {
    const rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, rect.width, rect.height);
    ctx.strokeStyle = "#2b2a33";
    ctx.lineWidth = 3;
    ctx.lineJoin = ctx.lineCap = "round";
    for (const st of strokes) {
      if (st.length < 1) continue;
      ctx.beginPath();
      ctx.moveTo(st[0].x, st[0].y);
      for (const p of st.slice(1)) ctx.lineTo(p.x, p.y);
      if (st.length === 1) ctx.lineTo(st[0].x + 0.1, st[0].y + 0.1);
      ctx.stroke();
    }
  }
  function pos(e) {
    const rect = canvas.getBoundingClientRect();
    const t = e.touches ? e.touches[0] : e;
    return { x: t.clientX - rect.left, y: t.clientY - rect.top };
  }
  const start = (e) => { e.preventDefault(); drawing = true; cur = [pos(e)]; strokes.push(cur); redraw(); };
  const move = (e) => { if (!drawing) return; e.preventDefault(); cur.push(pos(e)); redraw(); };
  const end = () => { drawing = false; cur = null; };
  canvas.addEventListener("pointerdown", start);
  canvas.addEventListener("pointermove", move);
  window.addEventListener("pointerup", end);

  function open() {
    closeAttachSheet();
    modal.classList.remove("hidden");
    strokes = [];
    requestAnimationFrame(sizeCanvas);
  }
  function close() { modal.classList.add("hidden"); }

  $("#drawBtn").addEventListener("click", open);
  $("#drawCancel").addEventListener("click", close);
  $("#drawClear").addEventListener("click", () => { strokes = []; redraw(); });
  $("#drawUndo").addEventListener("click", () => { strokes.pop(); redraw(); });
  $("#drawSend").addEventListener("click", () => {
    if (!strokes.length) { close(); return; }
    const dataUrl = canvas.toDataURL("image/png");
    setPendingImage(dataUrl);
    close();
    $("#input").focus();
  });
}

// 展示"小欧从照片里读到的题目"，方便家长核对、纠错
function showTranscript(text, tutorBubble) {
  const wrap = tutorBubble.closest(".msg");
  const note = document.createElement("div");
  note.className = "transcript-note";
  note.innerHTML =
    "<strong>小欧读到的题目</strong>（如果哪里读错了，直接打字告诉我）：<br>" +
    escapeHtml(text).replace(/\n/g, "<br>");
  wrap.parentNode.insertBefore(note, wrap);
  scrollToBottom();
}

// ---------------- 输入框行为 ----------------
function autoGrow(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function syncKeyboardInset() {
  const vv = window.visualViewport;
  if (!vv) return;
  const inset = Math.max(0, window.innerHeight - vv.height - vv.offsetTop);
  document.documentElement.style.setProperty("--kb", inset + "px");
}

function openDrawer() {
  const drawer = $("#drawer");
  if (drawer) drawer.classList.add("open");
}
function closeDrawer() {
  const drawer = $("#drawer");
  if (drawer) drawer.classList.remove("open");
}
function openTopicSheet() {
  fillTopicList();
  const sheet = $("#topicSheet");
  const chip = $("#topicChip");
  if (sheet) sheet.classList.add("open");
  if (chip) chip.setAttribute("aria-expanded", "true");
}
function closeTopicSheet() {
  const sheet = $("#topicSheet");
  const chip = $("#topicChip");
  if (sheet) sheet.classList.remove("open");
  if (chip) chip.setAttribute("aria-expanded", "false");
}
function fillTopicList() {
  const list = $("#topicList");
  if (!list) return;
  list.innerHTML = "";
  state.topics.forEach((t) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "topic-option" + (t.key === state.topicKey ? " active" : "");
    b.textContent = t.name;
    b.addEventListener("click", () => chooseTopic(t.key));
    list.appendChild(b);
  });
}
function chooseTopic(key) {
  closeTopicSheet();
  if (key === state.topicKey) return;
  if (state.streaming) return;
  if (state.messages.length && !confirm("换主题会开始新的探究，确定吗？")) return;
  state.topicKey = key;
  const sel = $("#topicSelect");
  if (sel) sel.value = key;
  state.messages = [];
  clearPendingImage();
  if (typeof clearActivitySession === "function") clearActivitySession();
  updateAxioms();
  saveSession();
  renderHistory();
}
function openAttachSheet() {
  const sheet = $("#attachSheet");
  if (sheet) sheet.classList.add("open");
}
function closeAttachSheet() {
  const sheet = $("#attachSheet");
  if (sheet) sheet.classList.remove("open");
}

function bindEvents() {
  const input = $("#input");
  input.addEventListener("input", () => autoGrow(input));
  input.addEventListener("keydown", (e) => {
    const touch = window.matchMedia("(pointer: coarse)").matches;
    if (e.key === "Enter" && !e.shiftKey && !touch) {
      e.preventDefault();
      sendMessage();
    }
  });
  $("#sendBtn").addEventListener("click", () => sendMessage());

  $("#attachBtn").addEventListener("click", () => {
    closeAttachSheet();
    $("#fileInput").click();
  });
  $("#fileInput").addEventListener("change", onFileChosen);
  $("#imgRemoveBtn").addEventListener("click", clearPendingImage);

  document.querySelectorAll("#modeSwitch .mode-btn").forEach((b) => {
    b.addEventListener("click", () => switchMode(b.dataset.mode));
  });
  $("#exploreBtn").addEventListener("click", () => startExplore());
  const startPlayBtn = $("#startPlayBtn");
  if (startPlayBtn) startPlayBtn.addEventListener("click", () => startPlay());
  const talkBtn = $("#talkBtn");
  if (talkBtn) talkBtn.addEventListener("click", () => setTalkOpen(!state.talkOpen));
  const helpBtn = $("#helpBtn");
  if (helpBtn) helpBtn.addEventListener("click", openHelpSheet);
  const helpCancel = $("#helpCancel");
  if (helpCancel) helpCancel.addEventListener("click", closeHelpSheet);
  const helpSheet = $("#helpSheet");
  if (helpSheet) {
    helpSheet.addEventListener("click", (e) => {
      if (e.target === helpSheet) closeHelpSheet();
    });
  }
  const newQuestionBtn = $("#newQuestionBtn");
  if (newQuestionBtn) {
    newQuestionBtn.addEventListener("click", () => {
      closeHelpSheet();
      startExplore();
    });
  }
  const historyBtn = $("#historyBtn");
  if (historyBtn) historyBtn.addEventListener("click", openHistorySheet);
  const historyClose = $("#historyClose");
  if (historyClose) historyClose.addEventListener("click", closeHistorySheet);
  const historySheet = $("#historySheet");
  if (historySheet) {
    historySheet.addEventListener("click", (e) => {
      if (e.target === historySheet) closeHistorySheet();
    });
  }
  const undoTileBtn = $("#undoTileBtn");
  if (undoTileBtn) {
    undoTileBtn.addEventListener("click", () => {
      const live = state.liveActivities[state.liveActivities.length - 1];
      if (live && live.undo) live.undo();
    });
  }
  const expandStageBtn = $("#expandStageBtn");
  if (expandStageBtn) expandStageBtn.addEventListener("click", toggleStageExpand);
  syncExpandButton();
  const homeworkBtn = $("#homeworkBtn");
  if (homeworkBtn) {
    homeworkBtn.addEventListener("click", () => {
      closeAttachSheet();
      switchMode("bring");
    });
  }
  const modeSelect = $("#modeSelect");
  if (modeSelect) {
    modeSelect.addEventListener("change", (e) => switchMode(e.target.value));
  }

  const plus = $("#plusBtn");
  if (plus) plus.addEventListener("click", openAttachSheet);
  const attachCancel = $("#attachCancel");
  if (attachCancel) attachCancel.addEventListener("click", closeAttachSheet);
  const attachSheet = $("#attachSheet");
  if (attachSheet) {
    attachSheet.addEventListener("click", (e) => {
      if (e.target === attachSheet) closeAttachSheet();
    });
  }

  const gear = $("#gearBtn");
  if (gear) gear.addEventListener("click", openDrawer);
  const drawerClose = $("#drawerClose");
  if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
  const drawer = $("#drawer");
  if (drawer) {
    drawer.addEventListener("click", (e) => {
      if (e.target === drawer) closeDrawer();
    });
  }

  const topicChip = $("#topicChip");
  if (topicChip) topicChip.addEventListener("click", openTopicSheet);
  const topicCancel = $("#topicCancel");
  if (topicCancel) topicCancel.addEventListener("click", closeTopicSheet);
  const topicSheet = $("#topicSheet");
  if (topicSheet) {
    topicSheet.addEventListener("click", (e) => {
      if (e.target === topicSheet) closeTopicSheet();
    });
  }

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", syncKeyboardInset);
    window.visualViewport.addEventListener("scroll", syncKeyboardInset);
    syncKeyboardInset();
  }

  $("#topicSelect").addEventListener("change", (e) => {
    state.topicKey = e.target.value;
    updateAxioms();
    saveSession();
  });
  $("#levelSelect").addEventListener("change", (e) => {
    state.level = e.target.value;
    saveSession();
  });
  $("#thinkingSelect").addEventListener("change", (e) => {
    state.thinking = e.target.value === "on";
    syncReasoningUi();
    saveSession();
  });
  $("#showReasoningSelect").addEventListener("change", (e) => {
    state.showReasoning = e.target.value === "on";
    setReasoningVisibility(state.showReasoning);
    saveSession();
  });
  $("#childName").addEventListener("input", (e) => {
    state.childName = e.target.value.trim();
    saveSession();
  });

  $("#resetBtn").addEventListener("click", () => {
    if (state.messages.length && !confirm("开启新的探究会清空当前对话，确定吗？")) return;
    state.messages = [];
    clearPendingImage();
    clearActivitySession();
    saveSession();
    renderHistory();
  });
}

// ---------------- 启动 ----------------
(async function init() {
  bindEvents();
  initVoice();
  initDraw();
  await loadConfig();
  window.XiaoouDebug = { addMessageEl, renderMarkdown, hydrateSnapGrids };
})();
