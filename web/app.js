"use strict";

const $ = (sel) => document.querySelector(sel);

const state = {
  config: null,
  topics: [],
  topicKey: null,
  level: null,
  childName: "",
  mode: "explore", // explore=小欧出题 / bring=孩子带题
  thinking: false, // 思考模式（开启时同时展示思考过程）
  messages: [], // 发给模型的历史：{role:'user'|'assistant', content}（content 可能是字符串或多模态数组）
  pendingImage: null, // 待发送的题目照片（dataURL）
  streaming: false,
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
    messages: sanitizeForStore(state.messages),
  };
  try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) {}
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
function renderTextWithMath(s) {
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
function renderMarkdown(text) {
  const lines = text.split("\n");
  let html = "";
  let list = null; // 'ul' | 'ol'
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  let para = [];
  const flushPara = () => {
    if (para.length) { html += `<p>${para.map(inlineFmt).join("<br>")}</p>`; para = []; }
  };
  let fence = null; // {lang, buf:[]}
  for (const raw of lines) {
    const line = raw.trimEnd();
    const fenceMatch = line.match(/^```\s*([\w-]*)\s*$/);
    if (fence) {
      if (fenceMatch) {
        // 结束围栏块
        const code = fence.buf.join("\n");
        if (fence.lang === "xiaoou-draw") {
          html += renderDiagram(code);
        } else if (code.trim()) {
          html += `<pre class="code">${escapeHtml(code)}</pre>`;
        }
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
    if (fence.lang === "xiaoou-draw") {
      const svg = renderDiagram(code);
      if (svg) html += svg;
    } else if (code.trim()) {
      html += `<pre class="code">${escapeHtml(code)}</pre>`;
    }
  }
  flushPara(); closeList();
  return html || "<p></p>";
}

// ---------------- 图形渲染（小欧插入的 xiaoou-draw 图，用 SVG 安全生成） ----------------
function renderDiagram(jsonText) {
  let s;
  try { s = JSON.parse(jsonText); } catch (e) { return ""; }
  let inner = "";
  if (s.type === "dots") inner = diagramDots(s);
  else if (s.type === "square_layers") inner = diagramSquareLayers(s);
  else if (s.type === "square_steps") inner = diagramSquareSteps(s);
  else if (s.type === "numberline") inner = diagramNumberline(s);
  else if (s.type === "bars") inner = diagramBars(s);
  if (!inner) return "";
  const cap = s.caption ? `<figcaption>${escapeHtml(String(s.caption))}</figcaption>` : "";
  return `<figure class="diagram">${inner}${cap}</figure>`;
}
const DIAG_BLUE = "#4f6bed", DIAG_GOLD = "#e8a13a";
function clampInt(v, lo, hi, dflt) {
  v = parseInt(v, 10);
  if (isNaN(v)) return dflt;
  return Math.max(lo, Math.min(hi, v));
}
function diagramDots(s) {
  const rows = clampInt(s.rows, 1, 10, 1), cols = clampInt(s.cols, 1, 10, 1);
  const cell = 26, r = 9, pad = 8;
  const w = cols * cell + pad * 2, h = rows * cell + pad * 2;
  let dots = "";
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      const cx = pad + j * cell + cell / 2, cy = pad + i * cell + cell / 2;
      const isNew = s.newLastRowCol && (i === rows - 1 || j === cols - 1);
      dots += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${isNew ? DIAG_GOLD : DIAG_BLUE}" />`;
    }
  }
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">${dots}</svg>`;
}
function diagramSquareLayers(s) {
  const n = clampInt(s.size, 1, 8, 3);
  const highlight = clampInt(s.highlight ?? s.highlightLayer, 1, n, n);
  const cell = 22, r = 7, pad = 12;
  const w = n * cell + pad * 2, h = n * cell + pad * 2;
  let dots = "";
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const layer = n - Math.min(i, j, n - 1 - i, n - 1 - j);
      const cx = pad + j * cell + cell / 2, cy = pad + i * cell + cell / 2;
      const isNew = layer === highlight;
      dots += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${isNew ? DIAG_GOLD : DIAG_BLUE}" opacity="${isNew ? 1 : 0.45 + layer * 0.08}"/>`;
    }
  }
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img">${dots}</svg>`;
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
        parts += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${isHL ? DIAG_GOLD : DIAG_BLUE}" opacity="${isHL ? 1 : 0.55 + layer * 0.07}"/>`;
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
  const max = Math.max(...items.map((it) => Math.max(0, Number(it.value) || 0)), 1);
  const rowH = 30, labelW = 70, barMax = 240, pad = 8;
  const w = labelW + barMax + 46, h = items.length * rowH + pad * 2;
  let el = "";
  items.forEach((it, i) => {
    const v = Math.max(0, Number(it.value) || 0);
    const bw = Math.round((v / max) * barMax);
    const y = pad + i * rowH;
    el += `<text x="0" y="${y + 19}" font-size="13" fill="#333">${escapeHtml(String(it.label ?? ""))}</text>`;
    el += `<rect x="${labelW}" y="${y + 6}" width="${bw}" height="16" rx="4" fill="${DIAG_BLUE}"/>`;
    el += `<text x="${labelW + bw + 6}" y="${y + 19}" font-size="12" fill="#555">${v}</text>`;
  });
  return `<svg viewBox="0 0 ${w} ${h}" width="${Math.min(w, 420)}" height="${h}" role="img">${el}</svg>`;
}

// ---------------- 消息渲染 ----------------
function avatarText(role) { return role === "child" ? "我" : "欧"; }

function addMessageEl(role) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = avatarText(role);
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  wrap.appendChild(avatar);
  wrap.appendChild(bubble);
  $("#messages").appendChild(wrap);
  scrollToBottom();
  return bubble;
}

function scrollToBottom() {
  const m = $("#messages");
  m.scrollTop = m.scrollHeight;
}

function getReasoningEl(tutorBubble) {
  if (!state.thinking) return null;
  const msg = tutorBubble.closest(".msg");
  let el = msg.querySelector(".reasoning");
  if (!el) {
    el = document.createElement("div");
    el.className = "reasoning";
    el.setAttribute("aria-label", "小欧的思考过程");
    msg.insertBefore(el, tutorBubble);
  }
  return el;
}

// content 可能是纯文字，也可能是含图片的数组。这里统一渲染进气泡。
function renderContentInto(bubble, content) {
  if (typeof content === "string") {
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
  let body;
  if (state.mode === "explore") {
    const tname = topic ? topic.name : "这个主题";
    body = `${name}你好呀，我是小欧。我不会直接告诉你答案，但我会陪你一步一步想出来。\n\n我们现在是「一起探索」模式。选好左边的主题（现在是**${tname}**），点一下 **✨ 出个新题**，我就从那几条公理出发，给你出一个好玩、值得琢磨的问题。`;
  } else {
    const starter = topic ? topic.starter : "";
    body = `${name}你好呀，我是小欧。我不会直接告诉你答案，但我会陪你一步一步想出来。\n\n我们现在是「带题来问」模式。${starter}`;
  }
  bubble.innerHTML = renderMarkdown(body);
}

function renderHistory() {
  $("#messages").innerHTML = "";
  if (state.messages.length === 0) { renderWelcome(); return; }
  for (const m of state.messages) {
    const bubble = addMessageEl(m.role === "user" ? "child" : "tutor");
    renderContentInto(bubble, m.content);
  }
}

// ---------------- 配置加载 ----------------
async function loadConfig() {
  const res = await fetch("/api/config");
  const cfg = await res.json();
  state.config = cfg;
  state.topics = cfg.topics;

  const saved = loadSession();
  state.topicKey = (saved && saved.topicKey) || cfg.default_topic;
  state.level = (saved && saved.level) || cfg.default_level;
  state.childName = (saved && saved.childName) || "";
  state.mode = (saved && saved.mode) || cfg.default_mode || "explore";
  state.thinking = (saved && typeof saved.thinking === "boolean") ? saved.thinking : !!cfg.thinking_enabled;
  state.messages = (saved && saved.messages) || [];

  // 主题下拉
  const topicSel = $("#topicSelect");
  topicSel.innerHTML = "";
  cfg.topics.forEach((t) => {
    const o = document.createElement("option");
    o.value = t.key; o.textContent = t.name;
    topicSel.appendChild(o);
  });
  topicSel.value = state.topicKey;

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

  $("#childName").value = state.childName;

  // 快捷按钮
  const qa = $("#quickActions");
  qa.innerHTML = "";
  cfg.quick_actions.forEach((a) => {
    const b = document.createElement("button");
    b.textContent = a.label;
    b.dataset.message = a.message;
    b.addEventListener("click", () => sendMessage(a.message));
    qa.appendChild(b);
  });

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
}

// 根据当前模式调整界面：探索模式突出"出个新题"、隐藏相机；带题模式相反。
function applyModeUI() {
  const explore = state.mode === "explore";
  document.querySelectorAll("#modeSwitch .mode-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.mode === state.mode);
  });
  const exploreBtn = $("#exploreBtn");
  exploreBtn.classList.toggle("hidden", !explore);
  if (state.config && !state.config.configured) exploreBtn.disabled = true;

  const attach = $("#attachBtn");
  if (attach) attach.style.display = explore ? "none" : "";

  const input = $("#input");
  input.placeholder = explore
    ? "把你的想法告诉小欧……（回车发送，Shift+回车换行）"
    : "把题目告诉小欧，或点相机拍下作业本……（回车发送，Shift+回车换行）";

  const tip = document.querySelector(".composer .tip");
  if (tip) {
    tip.textContent = explore
      ? "点「✨ 出个新题」让小欧出题；它会陪你一步步想，不会直接给答案。"
      : "把题目拍照或打出来发给小欧；它会陪你一步步想，不会直接给答案。";
  }
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
  state.messages.push({ role: "user", content });
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
        show_reasoning: state.thinking,
      }),
    });

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
          scrollToBottom();
        } else if (payload.reasoning_delta) {
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
  }
  setStreaming(false);
}

function setStreaming(on) {
  state.streaming = on;
  $("#sendBtn").disabled = on;
  const attach = $("#attachBtn");
  if (attach && state.config && state.config.vision_enabled) attach.disabled = on;
  const exploreBtn = $("#exploreBtn");
  if (exploreBtn && state.config && state.config.configured) exploreBtn.disabled = on;
  document.querySelectorAll(".quick-actions button").forEach((b) => (b.disabled = on));
}

// 切换探究模式。切换会清空当前对话（因为教学设定不同）。
function switchMode(mode) {
  if (mode === state.mode || state.streaming) return;
  if (state.messages.length && !confirm("切换模式会清空当前对话，确定吗？")) return;
  state.mode = mode;
  state.messages = [];
  clearPendingImage();
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

// ---------------- 语音输入（浏览器 Web Speech API） ----------------
let recognition = null, recognizing = false;
function initVoice() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const micBtn = $("#micBtn");
  if (!SR) {
    micBtn.disabled = true;
    micBtn.title = "这个浏览器不支持语音输入（试试 Chrome/Edge/Safari）";
    return;
  }
  recognition = new SR();
  recognition.lang = "zh-CN";
  recognition.interimResults = true;
  recognition.continuous = false;
  let baseText = "";
  recognition.onstart = () => { recognizing = true; micBtn.classList.add("recording"); };
  recognition.onend = () => { recognizing = false; micBtn.classList.remove("recording"); };
  recognition.onerror = () => { recognizing = false; micBtn.classList.remove("recording"); };
  recognition.onresult = (e) => {
    let txt = "";
    for (let i = 0; i < e.results.length; i++) txt += e.results[i][0].transcript;
    const input = $("#input");
    input.value = (baseText ? baseText + " " : "") + txt;
    autoGrow(input);
  };
  micBtn.addEventListener("click", () => {
    if (recognizing) { recognition.stop(); return; }
    baseText = $("#input").value.trim();
    try { recognition.start(); } catch (e) {}
  });
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
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

function bindEvents() {
  const input = $("#input");
  input.addEventListener("input", () => autoGrow(input));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  $("#sendBtn").addEventListener("click", () => sendMessage());

  $("#attachBtn").addEventListener("click", () => $("#fileInput").click());
  $("#fileInput").addEventListener("change", onFileChosen);
  $("#imgRemoveBtn").addEventListener("click", clearPendingImage);

  document.querySelectorAll("#modeSwitch .mode-btn").forEach((b) => {
    b.addEventListener("click", () => switchMode(b.dataset.mode));
  });
  $("#exploreBtn").addEventListener("click", () => startExplore());

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
})();
