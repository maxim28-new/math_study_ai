const BLUE = "#4f6bed";
const GOLD = "#e8a13a";

function clampInt(v, lo, hi, d) {
  v = parseInt(v, 10);
  if (isNaN(v)) return d;
  return Math.max(lo, Math.min(hi, v));
}

function layerHL(raw, n) {
  if (raw === 0 || raw === "0" || raw === "none" || raw === false) return null;
  if (raw == null) return n;
  return clampInt(raw, 1, n, n);
}

function measure(spec) {
  const t = spec.type;
  if (t === "dots") {
    const cols = clampInt(spec.cols, 1, 10, 3);
    const rows = clampInt(spec.rows, 1, 10, 3);
    return { w: cols * 26 + 16, h: rows * 26 + 16 };
  }
  if (t === "square_layers") {
    const n = clampInt(spec.size, 1, 8, 3);
    return { w: n * 22 + 24, h: n * 22 + 24 };
  }
  if (t === "square_steps") {
    const max = clampInt(spec.max ?? spec.count, 1, 6, 3);
    let tw = 20;
    for (let s = 1; s <= max; s++) tw += s * 16 + 14;
    return { w: Math.min(tw, 520), h: max * 16 + 44 };
  }
  if (t === "square_compare") {
    const from = clampInt(spec.from, 1, 8, 3);
    let to = clampInt(spec.to, 1, 8, from + 1);
    if (to <= from) to = from + 1;
    return { w: from * 18 + to * 18 + 54, h: Math.max(from, to) * 18 + 44 };
  }
  if (t === "numberline") {
    let from = clampInt(spec.from, -50, 200, 0);
    let to = clampInt(spec.to, -50, 200, 10);
    if (to <= from) to = from + 1;
    if (to - from > 30) to = from + 30;
    return { w: (to - from) * 34 + 48, h: 56 };
  }
  if (t === "bars") {
    const n = (Array.isArray(spec.items) ? spec.items : []).slice(0, 8).length || 1;
    return { w: 360, h: n * 30 + 16 };
  }
  return { w: 200, h: 100 };
}

function drawDots(ctx, spec, pad) {
  const rows = clampInt(spec.rows, 1, 10, 1);
  const cols = clampInt(spec.cols, 1, 10, 1);
  const cell = 26, r = 9;
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      const cx = pad + j * cell + cell / 2;
      const cy = pad + i * cell + cell / 2;
      const nw = spec.newLastRowCol && (i === rows - 1 || j === cols - 1);
      ctx.fillStyle = nw ? GOLD : BLUE;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawSquareDots(ctx, n, ox, oy, cell, r, hl) {
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const layer = n - Math.min(i, j, n - 1 - i, n - 1 - j);
      const cx = ox + j * cell + cell / 2;
      const cy = oy + i * cell + cell / 2;
      const isHL = hl != null && layer === hl;
      ctx.globalAlpha = isHL ? 1 : 0.45 + layer * 0.08;
      ctx.fillStyle = isHL ? GOLD : BLUE;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
}

function drawToCanvas(ctx, spec, cssW, cssH) {
  ctx.clearRect(0, 0, cssW, cssH);
  ctx.fillStyle = "#f8f7f3";
  ctx.fillRect(0, 0, cssW, cssH);
  const t = spec.type;

  if (t === "dots") {
    drawDots(ctx, spec, 8);
    return;
  }
  if (t === "square_layers") {
    const n = clampInt(spec.size, 1, 8, 3);
    drawSquareDots(ctx, n, 12, 12, 22, 7, layerHL(spec.highlight ?? spec.highlightLayer, n));
    return;
  }
  if (t === "square_steps") {
    const max = clampInt(spec.max ?? spec.count, 1, 6, 3);
    const hl = clampInt(spec.highlight, 1, max, max);
    const cell = 16, r = 6, gap = 14;
    let x = 10;
    for (let size = 1; size <= max; size++) {
      for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
          const layer = size - Math.min(i, j, size - 1 - i, size - 1 - j);
          const cx = x + j * cell + cell / 2;
          const cy = 10 + i * cell + cell / 2;
          const isHL = size === hl && layer === size;
          ctx.globalAlpha = isHL ? 1 : 0.55 + layer * 0.07;
          ctx.fillStyle = isHL ? GOLD : BLUE;
          ctx.beginPath();
          ctx.arc(cx, cy, r, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#666";
      ctx.font = "11px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${size}×${size}`, x + (size * cell) / 2, 10 + size * cell + 16);
      x += size * cell + gap;
    }
    return;
  }
  if (t === "square_compare") {
    const from = clampInt(spec.from, 1, 8, 3);
    let to = clampInt(spec.to, 1, 8, from + 1);
    if (to <= from) to = from + 1;
    const cell = 18, r = 6, gap = 22;
    drawSquareDots(ctx, from, 10, 10, cell, r, null);
    ctx.fillStyle = "#666";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${from}×${from}`, 10 + (from * cell) / 2, 10 + from * cell + 16);
    const x2 = 10 + from * cell + gap;
    drawSquareDots(ctx, to, x2, 10, cell, r, to);
    ctx.fillText(`${to}×${to}`, x2 + (to * cell) / 2, 10 + to * cell + 16);
    ctx.fillStyle = "#999";
    ctx.font = "16px sans-serif";
    ctx.fillText("→", 10 + from * cell + gap / 2, 10 + Math.max(from, to) * cell / 2);
    return;
  }
  if (t === "numberline") {
    let from = clampInt(spec.from, -50, 200, 0);
    let to = clampInt(spec.to, -50, 200, 10);
    if (to <= from) to = from + 1;
    if (to - from > 30) to = from + 30;
    const n = to - from, step = 34, pad = 24, y = 26;
    const marks = Array.isArray(spec.marks) ? spec.marks : [];
    ctx.strokeStyle = "#9aa";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(pad + n * step, y);
    ctx.stroke();
    ctx.fillStyle = "#555";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    for (let k = 0; k <= n; k++) {
      const x = pad + k * step;
      const val = from + k;
      ctx.beginPath();
      ctx.moveTo(x, y - 5);
      ctx.lineTo(x, y + 5);
      ctx.stroke();
      if (marks.includes(val)) {
        ctx.fillStyle = GOLD;
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = "#555";
      ctx.fillText(String(val), x, y + 22);
    }
    return;
  }
  if (t === "bars") {
    const items = (Array.isArray(spec.items) ? spec.items : []).slice(0, 8);
    if (!items.length) return;
    const max = Math.max(...items.map((it) => Math.max(0, Number(it.value) || 0)), 1);
    const rowH = 30, labelW = 70, barMax = 200, pad = 8;
    ctx.font = "13px sans-serif";
    items.forEach((it, i) => {
      const v = Math.max(0, Number(it.value) || 0);
      const bw = Math.round((v / max) * barMax);
      const y = pad + i * rowH;
      ctx.fillStyle = "#333";
      ctx.textAlign = "left";
      ctx.fillText(String(it.label || ""), 0, y + 19);
      ctx.fillStyle = BLUE;
      ctx.fillRect(labelW, y + 6, bw, 16);
      ctx.fillStyle = "#555";
      ctx.fillText(String(v), labelW + bw + 6, y + 19);
    });
  }
}

module.exports = { measure, drawToCanvas };
