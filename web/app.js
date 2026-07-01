"use strict";

const $ = (sel) => document.querySelector(sel);

const state = {
  config: null,
  topics: [],
  topicKey: null,
  level: null,
  childName: "",
  messages: [], // 发给模型的历史：{role:'user'|'assistant', content}
  streaming: false,
};

const STORE_KEY = "xiaoou.session.v1";

// ---------------- 本地存储 ----------------
function saveSession() {
  const data = {
    topicKey: state.topicKey,
    level: state.level,
    childName: state.childName,
    messages: state.messages,
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
    bubble.innerHTML = renderMarkdown(m.content);
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

  // 模型标签 / 未配置提示
  if (cfg.configured) {
    $("#modelTag").textContent = "已连接模型：" + cfg.model;
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
  const content = (text || $("#input").value).trim();
  if (!content || state.streaming) return;
  if (!state.config.configured) {
    // 未配置也允许把消息显示出来，但提示需要配置
    $("#input").value = "";
  }

  // 显示孩子的消息
  state.messages.push({ role: "user", content });
  const childBubble = addMessageEl("child");
  childBubble.innerHTML = renderMarkdown(content);
  $("#input").value = "";
  autoGrow($("#input"));
  saveSession();

  setStreaming(true);
  const tutorBubble = addMessageEl("tutor");
  tutorBubble.classList.add("cursor-blink");
  let acc = "";

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
  document.querySelectorAll(".quick-actions button").forEach((b) => (b.disabled = on));
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
    saveSession();
    renderHistory();
  });
}

// ---------------- 启动 ----------------
(async function init() {
  bindEvents();
  await loadConfig();
})();
