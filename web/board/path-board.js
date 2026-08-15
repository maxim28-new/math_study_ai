"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};

  function button(label, className) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = className;
    el.textContent = label;
    return el;
  }

  B.mountPathBoard = function mountPathBoard(host, spec, options) {
    options = options || {};
    const pathState = B.createPathState(spec);
    if (!pathState || typeof Konva === "undefined") return null;
    host.innerHTML = "";

    const board = document.createElement("div");
    board.className = "semantic-board path-board";
    board.setAttribute("aria-label", `从第 ${spec.start} 级到第 ${spec.target} 级，可以跳 ${spec.moves.join(" 或 ")} 级`);

    const canvas = document.createElement("div");
    canvas.className = "path-board-canvas";
    board.appendChild(canvas);

    const status = document.createElement("p");
    status.className = "path-board-status";
    status.setAttribute("aria-live", "polite");
    board.appendChild(status);

    const found = document.createElement("div");
    found.className = "path-board-found";
    board.appendChild(found);

    const controls = document.createElement("div");
    controls.className = "path-board-controls";
    const moveButtons = spec.moves.map((step) => {
      const el = button(`跳 ${step} 级`, "path-move-btn");
      el.addEventListener("click", () => applyMove(step));
      controls.appendChild(el);
      return { step, el };
    });
    const reset = button("重新走", "path-reset-btn");
    reset.addEventListener("click", () => {
      pathState.resetRoute();
      render();
      emit("path_reset");
    });
    controls.appendChild(reset);
    board.appendChild(controls);
    host.appendChild(board);

    let stage = null;
    let observer = null;
    let frozen = false;

    function drawCanvas(snapshot) {
      if (stage) stage.destroy();
      canvas.innerHTML = "";
      const width = Math.max(240, Math.min(380, canvas.clientWidth || host.clientWidth || 300));
      const height = Math.max(180, canvas.clientHeight || 220);
      stage = new Konva.Stage({ container: canvas, width, height });
      const layer = new Konva.Layer();
      stage.add(layer);

      const span = spec.target - spec.start;
      const padX = 28;
      const padTop = 28;
      const padBottom = 38;
      const stepW = Math.max(24, Math.min(46, (width - padX * 2) / Math.max(span + 1, 4)));
      const stepH = Math.max(18, Math.min(30, (height - padTop - padBottom) / Math.max(span + 1, 5)));
      const xStep = span ? (width - padX * 2 - stepW) / span : 0;
      const yStep = span ? (height - padTop - padBottom - stepH) / span : 0;
      const points = [];

      for (let i = 0; i <= span; i += 1) {
        const value = spec.start + i;
        const x = padX + i * xStep;
        const y = height - padBottom - stepH - i * yStep;
        points.push({ x: x + stepW / 2, y: y + stepH / 2, value });
        layer.add(new Konva.Rect({
          x, y, width: stepW, height: stepH,
          cornerRadius: Math.min(9, stepH / 3),
          fill: value === snapshot.current ? "#fff1c9" : "#eef1ff",
          stroke: value === snapshot.current ? "#e09a2c" : "#9dacfa",
          strokeWidth: value === snapshot.current ? 2.5 : 1.5,
        }));
        layer.add(new Konva.Text({
          x, y: y + stepH + 4, width: stepW,
          text: String(value), align: "center",
          fontSize: 12, fontStyle: "bold", fill: "#61594f",
        }));
      }

      const currentIndex = snapshot.current - spec.start;
      const currentPoint = points[currentIndex];
      spec.moves.forEach((move) => {
        const endIndex = currentIndex + move;
        if (endIndex >= points.length) return;
        const end = points[endIndex];
        const lift = 22 + move * 5;
        layer.add(new Konva.Arrow({
          points: [
            currentPoint.x, currentPoint.y - stepH / 2 - 3,
            (currentPoint.x + end.x) / 2, Math.min(currentPoint.y, end.y) - lift,
            end.x, end.y - stepH / 2 - 3,
          ],
          tension: 0.45,
          pointerLength: 6,
          pointerWidth: 6,
          stroke: "#6b7ef0",
          fill: "#6b7ef0",
          strokeWidth: 2,
          opacity: 0.72,
        }));
      });
      layer.add(new Konva.Text({
        x: currentPoint.x - 18,
        y: currentPoint.y - stepH / 2 - 30,
        width: 36,
        text: "🐸",
        align: "center",
        fontSize: 25,
      }));
      layer.draw();
    }

    function updateStatus(snapshot) {
      if (snapshot.current === spec.target) {
        status.textContent = "到终点了！可以重新走，看看还有没有别的走法。";
      } else if (snapshot.current_route.length) {
        status.textContent = `刚才跳了 ${snapshot.current_route.join("、")} 级，现在在第 ${snapshot.current} 级。`;
      } else {
        status.textContent = `从第 ${spec.start} 级出发，选一次跳几级。`;
      }
      found.innerHTML = "";
      snapshot.found_paths.forEach((route) => {
        const chip = document.createElement("span");
        chip.className = "path-found-chip";
        chip.textContent = route.join("+");
        found.appendChild(chip);
      });
      moveButtons.forEach(({ step, el }) => {
        el.disabled = frozen || snapshot.current + step > spec.target;
      });
      reset.disabled = frozen || snapshot.current === spec.start;
    }

    function render() {
      const snapshot = pathState.snapshot();
      drawCanvas(snapshot);
      updateStatus(snapshot);
    }

    function emit(eventName) {
      if (typeof options.onChange === "function") options.onChange(pathState.snapshot(), eventName);
    }

    function applyMove(step) {
      if (frozen) return false;
      const result = pathState.move(step);
      if (!result.changed) return false;
      render();
      emit(result.reached ? "path_found" : "path_moved");
      return true;
    }

    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => render());
      observer.observe(canvas);
    }
    render();

    return {
      freeze() {
        frozen = true;
        board.classList.add("is-frozen");
        updateStatus(pathState.snapshot());
      },
      destroy() {
        if (observer) observer.disconnect();
        if (stage) stage.destroy();
        board.remove();
      },
      getSnapshot() { return pathState.snapshot(); },
      apply(action) {
        if (!action || action.type !== "move") return false;
        return applyMove(action.step);
      },
    };
  };

  root.XiaoouSemanticBoard = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
