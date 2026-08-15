"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};
  const SCHEMA_VERSION = 2;

  function asInt(value) {
    if (typeof value === "boolean" || value === null || value === "") return null;
    const n = Number(value);
    return Number.isInteger(n) ? n : null;
  }

  function normalizeLayerSum(raw) {
    if (!Array.isArray(raw.layers) || raw.layers.length < 1 || raw.layers.length > 10) return null;
    const layers = raw.layers.map(asInt);
    if (layers.some((n) => n === null || n < 1 || n > 20)) return null;
    if (raw.ask !== "total" || (raw.reveal || "items_without_total") !== "items_without_total") return null;
    return {
      schema: SCHEMA_VERSION,
      kind: "layer_sum",
      layers,
      item: String(raw.item || "块").trim().slice(0, 4) || "块",
      ask: "total",
      purpose: "count_layers",
      reveal: "items_without_total",
    };
  }

  function normalizePathCount(raw) {
    const start = asInt(raw.start);
    const target = asInt(raw.target);
    if (start === null || target === null || start < 0 || target <= start || target - start > 12) return null;
    if (!Array.isArray(raw.moves) || raw.moves.length < 1 || raw.moves.length > 4) return null;
    const span = target - start;
    const moves = [];
    raw.moves.forEach((value) => {
      const n = asInt(value);
      if (n !== null && n > 0 && n <= span && !moves.includes(n)) moves.push(n);
    });
    if (!moves.length || moves.length !== raw.moves.length) return null;
    if (raw.ask !== "number_of_paths" || (raw.reveal || "rules_only") !== "rules_only") return null;
    return {
      schema: SCHEMA_VERSION,
      kind: "path_count",
      start,
      target,
      moves: moves.sort((a, b) => a - b),
      ask: "number_of_paths",
      purpose: "explore_choices",
      reveal: "rules_only",
    };
  }

  B.normalize = function normalize(raw) {
    if (!raw || typeof raw !== "object" || asInt(raw.schema) !== SCHEMA_VERSION) return null;
    if (raw.kind === "layer_sum") return normalizeLayerSum(raw);
    if (raw.kind === "path_count") return normalizePathCount(raw);
    return null;
  };

  B.createPathState = function createPathState(spec) {
    const board = B.normalize(spec);
    if (!board || board.kind !== "path_count") return null;
    let current = board.start;
    let route = [];
    const found = [];

    function snapshot() {
      return {
        kind: "path_count",
        start: board.start,
        target: board.target,
        moves: board.moves.slice(),
        current,
        current_route: route.slice(),
        found_paths: found.map((path) => path.slice()),
      };
    }

    function move(step) {
      step = asInt(step);
      if (!board.moves.includes(step) || current + step > board.target) {
        return { changed: false, reached: false, snapshot: snapshot() };
      }
      current += step;
      route.push(step);
      let isNew = false;
      if (current === board.target) {
        const key = route.join(",");
        if (!found.some((path) => path.join(",") === key)) {
          found.push(route.slice());
          isNew = true;
        }
      }
      return { changed: true, reached: current === board.target, isNew, snapshot: snapshot() };
    }

    function resetRoute() {
      current = board.start;
      route = [];
      return snapshot();
    }

    return { move, resetRoute, snapshot };
  };

  B.formatSnapshot = function formatSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return "";
    if (snapshot.kind === "layer_sum") {
      return [
        "（当前语义画板盘面，这不是孩子打的字）",
        "数学模型：layer_sum",
        "各层物体数：" + (snapshot.layers || []).join("、"),
        "画板没有显示合计答案。",
      ].join("\n");
    }
    if (snapshot.kind === "path_count") {
      const routes = (snapshot.found_paths || []).map((path) => path.join("+"));
      return [
        "（当前语义画板盘面，这不是孩子打的字）",
        "数学模型：path_count",
        "当前位置：" + snapshot.current + "，目标：" + snapshot.target,
        "当前走法：" + ((snapshot.current_route || []).join("+") || "还没开始"),
        "孩子已经找到的走法：" + (routes.join("；") || "还没有"),
      ].join("\n");
    }
    return "";
  };

  B.mount = function mount(host, raw, options) {
    const spec = B.normalize(raw);
    if (!host || !spec) return null;
    if (spec.kind === "layer_sum" && typeof B.mountLayerPile === "function") {
      return B.mountLayerPile(host, spec, options || {});
    }
    if (spec.kind === "path_count" && typeof B.mountPathBoard === "function") {
      return B.mountPathBoard(host, spec, options || {});
    }
    return null;
  };

  root.XiaoouSemanticBoard = B;
  if (typeof module !== "undefined" && module.exports) module.exports = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
