"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};

  function isOddSquareLayers(layers) {
    if (root.XiaoouMathWorkspace && XiaoouMathWorkspace.isOddSquareLayers) {
      return XiaoouMathWorkspace.isOddSquareLayers(layers);
    }
    return Array.isArray(layers) && layers.length >= 2
      && layers.every((n, i) => n === 2 * i + 1);
  }

  B.mountLayerPile = function mountLayerPile(host, spec, options) {
    options = options || {};
    const model = spec.model;
    const item = model.item || "块";
    const oddSquare = isOddSquareLayers(model.layers);
    const stepwise = spec.view.reveal === "stepwise" || oddSquare;
    const W = root.XiaoouMathWorkspace;
    let workspace = (oddSquare && W && options.workspace && W.fromDict(options.workspace))
      ? options.workspace
      : (oddSquare && W && options.card ? W.seedFromCard(options.card, options.topic) : null);
    let step = 0;
    const maxStep = stepwise ? model.layers.length - 1 : 0;
    let frozen = false;
    let lit = "";

    host.innerHTML = "";
    const board = document.createElement("div");
    board.className = "semantic-board layer-pile-board";
    board.setAttribute("role", "img");

    const canvas = document.createElement("div");
    canvas.className = "layer-pile-canvas";
    board.appendChild(canvas);

    const status = document.createElement("p");
    status.className = "layer-pile-status";
    status.setAttribute("aria-live", "polite");
    board.appendChild(status);

    const controls = document.createElement("div");
    controls.className = "layer-pile-controls";
    const next = document.createElement("button");
    next.type = "button";
    next.className = "layer-next-btn";
    next.textContent = "加上下一层";
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "layer-reset-btn";
    reset.textContent = "重新看";
    if (stepwise) {
      controls.appendChild(next);
      controls.appendChild(reset);
      board.appendChild(controls);
    }
    host.appendChild(board);

    function workspaceSide() {
      if (!workspace || !W) return 0;
      return W.formsSquare(workspace).side || 0;
    }

    function visibleCount() {
      if (workspace && oddSquare) return Math.max(1, workspaceSide());
      return stepwise ? step + 1 : model.layers.length;
    }

    function snapshot() {
      const shown = model.layers.slice(0, visibleCount());
      const remaining = model.layers.slice(visibleCount());
      const side = oddSquare ? visibleCount() : 0;
      const added = oddSquare && side > 1 ? model.layers[side - 1] : 0;
      return {
        kind: "layer_sum",
        layers: model.layers.slice(),
        item,
        visible_layers: shown,
        remaining,
        side,
        added,
        completed: !stepwise || visibleCount() >= model.layers.length,
        step: Math.max(0, visibleCount() - 1),
        workspace: workspace || null,
      };
    }

    function renderPile(shown) {
      const pile = document.createElement("div");
      pile.className = "layer-pile";
      model.layers.slice(0, shown).forEach((count, rowIndex) => {
        const row = document.createElement("div");
        row.className = "layer-pile-row";
        row.style.setProperty("--items", String(count));
        row.setAttribute("aria-label", `第 ${rowIndex + 1} 层，${count} ${item}`);
        for (let index = 0; index < count; index += 1) {
          const cell = document.createElement("span");
          cell.className = "layer-pile-item";
          cell.setAttribute("aria-hidden", "true");
          row.appendChild(cell);
        }
        pile.appendChild(row);
      });
      return pile;
    }

    function renderSquare(side, highlightNew) {
      const grid = document.createElement("div");
      grid.className = "layer-square";
      grid.style.setProperty("--side", String(side));
      for (let row = 0; row < side; row += 1) {
        for (let col = 0; col < side; col += 1) {
          const cell = document.createElement("span");
          cell.className = "layer-square-cell";
          if (highlightNew && side > 1 && (row === side - 1 || col === side - 1)) {
            cell.classList.add("is-new");
          }
          cell.setAttribute("aria-hidden", "true");
          grid.appendChild(cell);
        }
      }
      return grid;
    }

    function renderWorkspaceTiles() {
      const snap = W.visibleSnapshot(workspace);
      const hidden = new Set((snap.visibility.hidden || []));
      const marked = new Set(snap.marked || []);
      const emphasis = new Set(snap.emphasis || []);
      const tiles = (snap.objects || []).filter((obj) => obj.type === "tile" && !hidden.has(obj.id));
      const placed = tiles.filter((obj) => obj.attrs && obj.attrs.gx != null && obj.attrs.gy != null);
      let maxX = 0;
      let maxY = 0;
      placed.forEach((obj) => {
        maxX = Math.max(maxX, obj.attrs.gx);
        maxY = Math.max(maxY, obj.attrs.gy);
      });
      const cols = placed.length ? maxX + 1 : 1;
      const rows = placed.length ? maxY + 1 : 1;
      const byPos = {};
      placed.forEach((obj) => { byPos[obj.attrs.gx + "," + obj.attrs.gy] = obj; });
      const grid = document.createElement("div");
      grid.className = "layer-square";
      grid.style.setProperty("--side", String(Math.max(cols, rows)));
      for (let gy = 0; gy < rows; gy += 1) {
        for (let gx = 0; gx < cols; gx += 1) {
          const obj = byPos[gx + "," + gy];
          const cell = document.createElement("span");
          cell.className = "layer-square-cell";
          if (obj && marked.has(obj.id) && snap.side > 1) cell.classList.add("is-new");
          if (obj && emphasis.has(obj.id)) cell.classList.add("is-emphasis");
          if (!obj) cell.classList.add("is-empty");
          cell.setAttribute("aria-hidden", "true");
          grid.appendChild(cell);
        }
      }
      return { grid, snap };
    }

    function render() {
      canvas.innerHTML = "";
      if (workspace && oddSquare && W) {
        const drawn = renderWorkspaceTiles();
        canvas.appendChild(drawn.grid);
        const snap = drawn.snap;
        if (snap.side <= 1) status.textContent = `先看最中间这一块${item}。`;
        else status.textContent = `外面新加的是金色，现在是每边 ${snap.side} 块的正方形。`;
        board.setAttribute("aria-label", `每边 ${snap.side || 1} 块的正方形`);
        const maxSide = model.layers.length;
        next.textContent = snap.side >= maxSide ? "已经围好" : "加上下一层";
        next.disabled = frozen || snap.side >= maxSide;
        reset.disabled = frozen || snap.side <= 1;
        status.hidden = false;
        board.classList.toggle("is-term-lit", lit === "square");
        return;
      }
      const shown = visibleCount();
      if (oddSquare) {
        canvas.appendChild(renderSquare(shown, step > 0));
        if (step === 0) status.textContent = `先看最中间这一块${item}。`;
        else {
          status.textContent = `外面加上 ${model.layers[step]} 块，现在是每边 ${shown} 块的正方形。`;
        }
        board.setAttribute("aria-label", `每边 ${shown} 块的正方形`);
      } else {
        canvas.appendChild(renderPile(shown));
        status.textContent = stepwise
          ? `已经看到前 ${shown} 层。`
          : model.layers.map((count, index) => `第${index + 1}层${count}${item}`).join("，");
        board.setAttribute(
          "aria-label",
          model.layers.slice(0, shown).map((count, index) => `第${index + 1}层${count}${item}`).join("，")
        );
      }
      board.classList.toggle("is-term-lit", lit === "square");
      if (!stepwise) {
        status.hidden = true;
        return;
      }
      status.hidden = false;
      next.textContent = step >= maxStep ? "已经围好" : "加上下一层";
      next.disabled = frozen || step >= maxStep;
      reset.disabled = frozen || step === 0;
    }

    function emit(eventName) {
      if (typeof options.onChange === "function") options.onChange(snapshot(), eventName);
    }

    if (stepwise) {
      next.addEventListener("click", () => {
        if (frozen) return;
        if (workspace && W) {
          const result = W.addNextOddRing(workspace);
          if (!result.ok) return;
          workspace = result.workspace;
          render();
          emit(snapshot().completed ? "layer_completed" : "layer_advanced");
          return;
        }
        if (step >= maxStep) return;
        step += 1;
        render();
        emit(step >= maxStep ? "layer_completed" : "layer_advanced");
      });
      reset.addEventListener("click", () => {
        if (frozen) return;
        if (workspace && W) {
          const result = W.resetToSeed(workspace, options.card, options.topic);
          if (!result.ok) return;
          workspace = result.workspace;
          render();
          emit("layer_reset");
          return;
        }
        step = 0;
        render();
        emit("layer_reset");
      });
    }

    render();
    return {
      freeze() {
        frozen = true;
        board.classList.add("is-frozen");
        render();
      },
      destroy() { board.remove(); },
      getSnapshot: snapshot,
      highlight(key) {
        lit = String(key || "");
        render();
      },
      apply(action) {
        if (!stepwise || !action || action.type !== "next" || frozen) return false;
        if (workspace && W) {
          const result = W.addNextOddRing(workspace);
          if (!result.ok) return false;
          workspace = result.workspace;
          render();
          emit(snapshot().completed ? "layer_completed" : "layer_advanced");
          return true;
        }
        if (step >= maxStep) return false;
        step += 1;
        render();
        emit(step >= maxStep ? "layer_completed" : "layer_advanced");
        return true;
      },
      applyWorkspace(nextWs) {
        if (!W || !nextWs) return false;
        const parsed = W.fromDict(nextWs);
        if (!parsed) return false;
        workspace = parsed;
        render();
        emit("workspace_applied");
        return true;
      },
    };
  };

  root.XiaoouSemanticBoard = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
