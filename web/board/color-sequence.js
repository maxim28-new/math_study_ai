"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};
  const COLOR_HEX = {
    red: "#e23b3b",
    blue: "#3b6be2",
    yellow: "#f0c02e",
    green: "#2fa86a",
    orange: "#ef8a1f",
    purple: "#8a4fd6",
  };
  const COLOR_LABELS = {
    red: "红",
    blue: "蓝",
    yellow: "黄",
    green: "绿",
    orange: "橙",
    purple: "紫",
  };
  const ITEM_MEASURES = { 花: "朵", 珠: "颗", 块: "块" };

  function expand(unit, count) {
    const out = [];
    for (let i = 0; i < count; i += 1) out.push(unit[i % unit.length]);
    return out;
  }

  function flowerSvg(hex) {
    return (
      '<svg viewBox="0 0 40 40" aria-hidden="true">'
      + `<g fill="${hex}">`
      + '<circle cx="20" cy="10" r="7"></circle>'
      + '<circle cx="29" cy="16" r="7"></circle>'
      + '<circle cx="26" cy="26" r="7"></circle>'
      + '<circle cx="14" cy="26" r="7"></circle>'
      + '<circle cx="11" cy="16" r="7"></circle>'
      + "</g>"
      + '<circle cx="20" cy="20" r="5" fill="#fff6c8"></circle>'
      + "</svg>"
    );
  }

  B.upgradeLegacyPatternBoard = function upgradeLegacyPatternBoard(raw) {
    if (!raw || raw.kind !== "static_diagram" || !raw.model || !raw.model.diagram) return raw;
    const diagram = raw.model.diagram;
    const prompt = raw.task && raw.task.prompt ? String(raw.task.prompt) : "";
    const blob = String(diagram.caption || "") + " " + prompt;
    if (diagram.type !== "dots" || Number(diagram.rows) !== 1) return raw;
    if (blob.indexOf("红") < 0 || blob.indexOf("蓝") < 0) return raw;
    let count = Number(diagram.cols) || 6;
    if (count < 3 || count > 10) count = 6;
    return {
      schema: 3,
      kind: "color_sequence",
      model: { item: "花", unit: ["red", "red", "blue"], count },
      task: { action: "predict", ask: "color_at_end", prompt },
      view: { reveal: "hide_last" },
    };
  };

  B.mountColorSequence = function mountColorSequence(host, spec) {
    host.innerHTML = "";
    const model = spec.model;
    const colors = expand(model.unit, model.count);
    const hideLast = spec.view.reveal === "hide_last";
    const measure = ITEM_MEASURES[model.item] || "个";
    const shape = model.item === "花" ? "flower" : (model.item === "珠" ? "bead" : "tile");

    const board = document.createElement("div");
    board.className = "semantic-board color-seq-board";
    const row = document.createElement("div");
    row.className = "color-seq-row";

    const visible = [];
    colors.forEach((color, index) => {
      const hidden = hideLast && index === colors.length - 1;
      const cell = document.createElement("span");
      cell.className = "color-seq-cell";
      const item = document.createElement("span");
      const label = hidden
        ? `第${index + 1}${measure}还没揭开`
        : `第${index + 1}${measure}${COLOR_LABELS[color] || color}`;
      item.setAttribute("aria-label", label);
      if (hidden) {
        item.className = "color-seq-item is-hidden";
        item.textContent = "?";
      } else {
        item.className = "color-seq-item is-" + shape + " is-" + color;
        item.style.setProperty("--seq-color", COLOR_HEX[color] || color);
        if (shape === "flower") item.innerHTML = flowerSvg(COLOR_HEX[color] || color);
        visible.push(COLOR_LABELS[color] || color);
      }
      const num = document.createElement("span");
      num.className = "color-seq-index";
      num.textContent = String(index + 1);
      cell.appendChild(item);
      cell.appendChild(num);
      row.appendChild(cell);
    });

    const status = document.createElement("p");
    status.className = "color-seq-status";
    status.textContent = hideLast
      ? "空着的那一" + measure + "会是什么颜色？"
      : "看看它们是按什么规律排队的。";

    board.appendChild(row);
    board.appendChild(status);
    board.setAttribute("role", "img");
    board.setAttribute("aria-label", visible.join("、") + (hideLast ? "，最后一" + measure + "还没揭开" : ""));
    host.appendChild(board);

    const snapshot = {
      kind: "color_sequence",
      item: model.item,
      visible: visible.slice(),
      hidden: hideLast,
    };
    return {
      freeze() { board.classList.add("is-frozen"); },
      destroy() { board.remove(); },
      getSnapshot() { return Object.assign({}, snapshot, { visible: snapshot.visible.slice() }); },
      apply() { return false; },
    };
  };

  root.XiaoouSemanticBoard = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
