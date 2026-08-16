"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};

  B.mountLayerPile = function mountLayerPile(host, spec) {
    host.innerHTML = "";
    const model = spec.model;

    const board = document.createElement("div");
    board.className = "semantic-board layer-pile-board";
    board.setAttribute("role", "img");
    board.setAttribute(
      "aria-label",
      model.layers.map((count, index) => `第${index + 1}层${count}${model.item}`).join("，")
    );

    const pile = document.createElement("div");
    pile.className = "layer-pile";
    model.layers.forEach((count, rowIndex) => {
      const row = document.createElement("div");
      row.className = "layer-pile-row";
      row.style.setProperty("--items", String(count));
      row.setAttribute("aria-label", `第 ${rowIndex + 1} 层，${count} ${model.item}`);
      for (let index = 0; index < count; index += 1) {
        const item = document.createElement("span");
        item.className = "layer-pile-item";
        item.setAttribute("aria-hidden", "true");
        row.appendChild(item);
      }
      pile.appendChild(row);
    });
    board.appendChild(pile);
    host.appendChild(board);

    const snapshot = {
      kind: "layer_sum",
      layers: model.layers.slice(),
      item: model.item,
      answer_revealed: false,
    };
    return {
      freeze() { board.classList.add("is-frozen"); },
      destroy() { board.remove(); },
      getSnapshot() { return Object.assign({}, snapshot, { layers: snapshot.layers.slice() }); },
      apply() { return false; },
    };
  };

  root.XiaoouSemanticBoard = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
