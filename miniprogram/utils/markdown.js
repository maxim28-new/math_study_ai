const MATH_RE = /\$\$([\s\S]+?)\$\$|\$([^\$\n]+?)\$|\\\(([\s\S]+?)\\\)|\\\[([\s\S]+?)\\\]/g;
const DIAGRAM_TYPES = new Set(["dots", "square_layers", "square_steps", "square_compare", "numberline", "bars"]);

function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function tryParseDiagramSpec(text) {
  const t = String(text).trim();
  if (!t.startsWith("{")) return null;
  try {
    const spec = JSON.parse(t);
    if (spec && typeof spec.type === "string" && DIAGRAM_TYPES.has(spec.type)) return spec;
  } catch (e) { /* ignore */ }
  return null;
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

function parseTextSegment(text) {
  const segments = [];
  const lines = String(text || "").split("\n");
  let buf = [];
  const flush = () => {
    if (buf.length) {
      segments.push({ type: "rich", html: markdownToHtml(buf.join("\n")) });
      buf = [];
    }
  };
  for (const line of lines) {
    const spec = tryParseDiagramSpec(line);
    if (spec) {
      flush();
      segments.push({ type: "diagram", spec });
    } else {
      buf.push(line);
    }
  }
  flush();
  if (!segments.length && text) {
    segments.push({ type: "rich", html: markdownToHtml(text) });
  }
  return segments;
}

/** 把消息拆成 rich-text 段 + diagram 段 */
function parseContent(text) {
  const segments = [];
  const fenceRe = /```\s*([\w-]*)\s*\n([\s\S]*?)```/g;
  let last = 0;
  let m;
  while ((m = fenceRe.exec(text)) !== null) {
    if (m.index > last) {
      segments.push(...parseTextSegment(text.slice(last, m.index)));
    }
    const spec = tryParseDiagramSpec(m[2]);
    if (spec) segments.push({ type: "diagram", spec });
    else if (m[2].trim()) {
      segments.push({ type: "rich", html: `<pre class="code">${esc(m[2])}</pre>` });
    }
    last = m.lastIndex;
  }
  if (last < text.length) {
    segments.push(...parseTextSegment(text.slice(last)));
  }
  if (!segments.length) {
    segments.push({ type: "rich", html: markdownToHtml(text || "") });
  }
  return segments;
}

module.exports = { parseContent, markdownToHtml, tryParseDiagramSpec };
