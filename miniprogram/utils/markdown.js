const MATH_RE = /\$\$([\s\S]+?)\$\$|\$([^\$\n]+?)\$|\\\(([\s\S]+?)\\\)|\\\[([\s\S]+?)\\\]/g;

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function latexSimple(s) {
  s = String(s);
  s = s.replace(/\\frac\{([^{}]*)\}\{([^{}]*)\}/g, "$1/$2");
  s = s.replace(/\\(?:text|mathrm)\{([^{}]*)\}/g, "$1");
  const map = {
    "\\times": "×", "\\div": "÷", "\\cdot": "·", "\\pm": "±",
    "\\leq": "≤", "\\le": "≤", "\\geq": "≥", "\\ge": "≥",
    "\\neq": "≠", "\\approx": "≈", "\\pi": "π",
  };
  Object.keys(map).forEach((k) => { s = s.split(k).join(map[k]); });
  s = s.replace(/\^\{([^{}]+)\}/g, (_, e) => e);
  s = s.replace(/\\[a-zA-Z]+(\{[^{}]*\})?/g, "");
  return s.trim();
}

function mathToText(s) {
  MATH_RE.lastIndex = 0;
  return String(s).replace(MATH_RE, (_, a, b, c, d) => latexSimple(a || b || c || d));
}

function inlineFmt(s) {
  return esc(mathToText(s))
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/** 轻量 Markdown → rich-text 可用的 HTML */
function markdownToHtml(text) {
  const lines = String(text || "").split("\n");
  let html = "";
  let list = null;
  let para = [];

  const closeList = () => {
    if (list) { html += `</${list}>`; list = null; }
  };
  const flushPara = () => {
    if (para.length) {
      html += `<p>${para.map(inlineFmt).join("<br/>")}</p>`;
      para = [];
    }
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
      closeList();
      para.push(line);
    }
  }
  flushPara(); closeList();
  return html || "<p></p>";
}

/** 把消息拆成 rich-text 段 + diagram 段 */
function parseContent(text) {
  const segments = [];
  const re = /```\s*xiaoou-draw\s*\n([\s\S]*?)```/g;
  let last = 0;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      segments.push({ type: "rich", html: markdownToHtml(text.slice(last, m.index)) });
    }
    try {
      segments.push({ type: "diagram", spec: JSON.parse(m[1].trim()) });
    } catch (e) { /* skip bad json */ }
    last = m.lastIndex;
  }
  if (last < text.length) {
    segments.push({ type: "rich", html: markdownToHtml(text.slice(last)) });
  }
  if (!segments.length) {
    segments.push({ type: "rich", html: markdownToHtml(text || "") });
  }
  return segments;
}

module.exports = { parseContent, markdownToHtml };
