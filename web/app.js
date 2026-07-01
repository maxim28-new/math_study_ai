"use strict";

const $ = (sel) => document.querySelector(sel);

const state = {
  config: null,
  topics: [],
  topicKey: null,
  level: null,
  childName: "",
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
    messages: sanitizeForStore(state.messages),
  };
  try { localStorage.setItem(STORE_KEY, JSON.stringify(data)); } catch (e) {}
}
function loadSession() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || "null"); } catch (e) { return null; }
}

// ---------------- 安全的轻量 Markdown 渲染 ----------------
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
function inlineFmt(s) {
  return escapeHtml(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
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
  for (const raw of lines) {
    const line = raw.trimEnd();
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
  flushPara(); closeList();
  return html || "<p></p>";
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
  if (!state.config || !state.config.show_reasoning) return null;
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
  const starter = topic ? topic.starter : "";
  const bubble = addMessageEl("tutor");
  bubble.innerHTML = renderMarkdown(
    `${name}你好呀，我是小欧。我不会直接告诉你答案，但我会陪你一步一步想出来。\n\n${starter}`
  );
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
  renderHistory();
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
  document.querySelectorAll(".quick-actions button").forEach((b) => (b.disabled = on));
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

  $("#topicSelect").addEventListener("change", (e) => {
    state.topicKey = e.target.value;
    updateAxioms();
    saveSession();
  });
  $("#levelSelect").addEventListener("change", (e) => {
    state.level = e.target.value;
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
  await loadConfig();
})();
