"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};
  const SVG_NS = "http://www.w3.org/2000/svg";

  function svgEl(name, attrs) {
    const el = document.createElementNS(SVG_NS, name);
    Object.keys(attrs || {}).forEach((key) => el.setAttribute(key, String(attrs[key])));
    return el;
  }

  function button(label, className) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = className;
    el.textContent = label;
    return el;
  }

  B.mountGeometryCompass = function mountGeometryCompass(host, spec, options) {
    options = options || {};
    const labels = spec.model.labels;
    let step = 0;
    let frozen = false;
    let lit = "";
    host.innerHTML = "";

    const board = document.createElement("div");
    board.className = "semantic-board geometry-compass-board";
    board.setAttribute("aria-label", "用同一个圆规宽度，从一条线段构造正三角形");

    const canvas = document.createElement("div");
    canvas.className = "geometry-compass-canvas";
    board.appendChild(canvas);

    const status = document.createElement("p");
    status.className = "geometry-compass-status";
    status.setAttribute("aria-live", "polite");
    board.appendChild(status);

    const controls = document.createElement("div");
    controls.className = "geometry-compass-controls";
    const next = button(`夹住 ${labels[0]}${labels[1]}`, "geometry-next-btn");
    const reset = button("重新画", "geometry-reset-btn");
    reset.disabled = true;
    controls.appendChild(next);
    controls.appendChild(reset);
    board.appendChild(controls);
    host.appendChild(board);

    function snapshot() {
      return {
        kind: "geometry_compass",
        construction: "equilateral_triangle",
        step,
        completed: step === 3,
        equal_segments: step === 3
          ? [`${labels[0]}${labels[1]}`, `${labels[0]}${labels[2]}`, `${labels[1]}${labels[2]}`]
          : [],
      };
    }

    function line(x1, y1, x2, y2, className) {
      return svgEl("line", { x1, y1, x2, y2, class: className });
    }

    function label(x, y, value) {
      const el = svgEl("text", { x, y, class: "geometry-point-label", "text-anchor": "middle" });
      el.textContent = value;
      return el;
    }

    function render() {
      canvas.innerHTML = "";
      const svg = svgEl("svg", {
        viewBox: "-70 -20 500 360",
        preserveAspectRatio: "xMidYMid meet",
        role: "img",
        "aria-label": `${labels[0]}${labels[1]} 为圆规宽度，两圆相交于 ${labels[2]}`,
      });
      const ax = 110, bx = 250, baseY = 170, radius = 140;
      const px = (ax + bx) / 2;
      const half = (bx - ax) / 2;
      const py = baseY - Math.sqrt(radius * radius - half * half);

      if (lit === "line") {
        svg.appendChild(line(-60, baseY, 420, baseY, "geometry-line"));
      }
      svg.appendChild(line(ax, baseY, bx, baseY, "geometry-base geometry-segment"));
      svg.appendChild(svgEl("circle", { cx: ax, cy: baseY, r: 4, class: "geometry-point geometry-center" }));
      svg.appendChild(svgEl("circle", { cx: bx, cy: baseY, r: 4, class: "geometry-point geometry-center" }));
      svg.appendChild(label(ax, baseY + 24, labels[0]));
      svg.appendChild(label(bx, baseY + 24, labels[1]));

      if (step >= 1) {
        svg.appendChild(line(ax, baseY - 18, bx, baseY - 18, "geometry-compass-width geometry-compass"));
        svg.appendChild(line(ax, baseY - 25, ax, baseY - 11, "geometry-width-tick"));
        svg.appendChild(line(bx, baseY - 25, bx, baseY - 11, "geometry-width-tick"));
      }
      if (step >= 2) {
        svg.appendChild(svgEl("circle", { cx: ax, cy: baseY, r: radius, class: "geometry-circle geometry-circle-a" }));
        if (lit === "radius") {
          const rx = ax + radius * Math.cos(-0.72);
          const ry = baseY + radius * Math.sin(-0.72);
          svg.appendChild(line(ax, baseY, rx, ry, "geometry-radius"));
        }
      }
      if (step >= 3) {
        svg.appendChild(svgEl("circle", { cx: bx, cy: baseY, r: radius, class: "geometry-circle geometry-circle-b" }));
        svg.appendChild(line(ax, baseY, px, py, "geometry-side"));
        svg.appendChild(line(bx, baseY, px, py, "geometry-side"));
        svg.appendChild(svgEl("circle", { cx: px, cy: py, r: 4, class: "geometry-point geometry-point-p geometry-intersection" }));
        svg.appendChild(label(px, py - 12, labels[2]));
      }
      applyHighlight(svg);
      canvas.appendChild(svg);

      const messages = [
        `先看线段 ${labels[0]}${labels[1]}。`,
        `圆规已经夹成线段 ${labels[0]}${labels[1]} 那么宽。`,
        `以 ${labels[0]} 为圆心画好了第一个圆。`,
        `两个圆相交了。看看交点到两个圆心的距离。`,
      ];
      const labelsByStep = [
        `夹住 ${labels[0]}${labels[1]}`,
        `以 ${labels[0]} 画圆`,
        `以 ${labels[1]} 画圆`,
        "已经画好",
      ];
      status.textContent = messages[step];
      next.textContent = labelsByStep[step];
      next.disabled = frozen || step === 3;
      reset.disabled = frozen || step === 0;
    }

    function applyHighlight(svg) {
      if (!svg || !lit) return;
      const map = {
        compass: ".geometry-compass",
        center: ".geometry-center",
        radius: ".geometry-radius, .geometry-circle",
        intersection: ".geometry-intersection",
        segment: ".geometry-segment",
        line: ".geometry-line",
        equilateral: ".geometry-side, .geometry-segment",
      };
      const sel = map[lit];
      if (!sel) return;
      svg.querySelectorAll(sel).forEach((el) => el.classList.add("is-term-lit"));
    }

    function highlight(key) {
      lit = String(key || "");
      render();
    }

    function emit(eventName) {
      if (typeof options.onChange === "function") options.onChange(snapshot(), eventName);
    }

    next.addEventListener("click", () => {
      if (frozen || step >= 3) return;
      step += 1;
      render();
      emit(step === 3 ? "construction_completed" : "construction_advanced");
    });
    reset.addEventListener("click", () => {
      if (frozen) return;
      step = 0;
      render();
      emit("construction_reset");
    });

    render();
    return {
      freeze() {
        frozen = true;
        board.classList.add("is-frozen");
        render();
      },
      destroy() { board.remove(); },
      getSnapshot: snapshot,
      highlight,
      apply(action) {
        if (!action || action.type !== "next" || frozen || step >= 3) return false;
        step += 1;
        render();
        emit(step === 3 ? "construction_completed" : "construction_advanced");
        return true;
      },
    };
  };

  root.XiaoouSemanticBoard = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
