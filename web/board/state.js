"use strict";

(function (root) {
  const B = root.XiaoouSemanticBoard || {};
  const SCHEMA_VERSION = 3;
  const STATIC_TYPES = new Set([
    "dots", "stairs", "square_layers", "square_steps",
    "square_compare", "numberline", "bars",
  ]);

  function asInt(value) {
    if (typeof value === "boolean" || value === null || value === "") return null;
    const n = Number(value);
    return Number.isInteger(n) ? n : null;
  }

  function text(value, limit, dflt) {
    const out = String(value || "").trim() || (dflt || "");
    return out.slice(0, limit);
  }

  function normalizeTask(raw, action, ask) {
    if (!raw || typeof raw !== "object" || raw.action !== action || raw.ask !== ask) return null;
    return { action, ask, prompt: text(raw.prompt, 200) };
  }

  function isOddSquareLayers(layers) {
    return Array.isArray(layers) && layers.length >= 2
      && layers.every((n, i) => n === 2 * i + 1);
  }

  function normalizeLayerSum(model, task, view) {
    if (!Array.isArray(model.layers) || model.layers.length < 1 || model.layers.length > 10) return null;
    const layers = model.layers.map(asInt);
    if (layers.some((n) => n === null || n < 1 || n > 20)) return null;
    const normalizedTask = normalizeTask(task, "count", "total");
    const rawReveal = view && view.reveal;
    let reveal = rawReveal === "stepwise" || rawReveal === "items_without_total" ? rawReveal : null;
    if (!normalizedTask || !reveal) return null;
    if (isOddSquareLayers(layers)) reveal = "stepwise";
    return {
      schema: SCHEMA_VERSION,
      kind: "layer_sum",
      model: { layers, item: text(model.item, 4, "块") },
      task: normalizedTask,
      view: { reveal },
    };
  }

  function normalizePathCount(model, task, view) {
    const start = asInt(model.start);
    const target = asInt(model.target);
    if (start === null || target === null || start < 0 || target <= start || target - start > 24) return null;
    if (!Array.isArray(model.moves) || model.moves.length < 1 || model.moves.length > 4) return null;
    const span = target - start;
    const moves = [];
    model.moves.forEach((value) => {
      const n = asInt(value);
      if (n !== null && n > 0 && n <= span && !moves.includes(n)) moves.push(n);
    });
    const normalizedTask = normalizeTask(task, "enumerate", "number_of_paths");
    if (!moves.length || moves.length !== model.moves.length || !normalizedTask || !view || view.reveal !== "rules_only") return null;
    return {
      schema: SCHEMA_VERSION,
      kind: "path_count",
      model: { start, target, moves: moves.sort((a, b) => a - b) },
      task: normalizedTask,
      view: { reveal: "rules_only" },
    };
  }

  function normalizeSnapGrid(model, task, view) {
    const rows = asInt(model.rows);
    const cols = asInt(model.cols);
    const tray = asInt(model.tray);
    const normalizedTask = normalizeTask(task, "arrange", "observe");
    if (rows === null || cols === null || tray === null
      || rows < 1 || rows > 8 || cols < 1 || cols > 8 || tray < 0 || tray > 64
      || !normalizedTask || !view || view.reveal !== "empty_grid_and_tiles") return null;
    return {
      schema: SCHEMA_VERSION,
      kind: "snap_grid",
      model: { rows, cols, tray },
      task: normalizedTask,
      view: { reveal: "empty_grid_and_tiles" },
    };
  }

  function normalizeStaticDiagram(raw) {
    if (!raw || typeof raw !== "object" || !STATIC_TYPES.has(raw.type)) return null;
    const caption = text(raw.caption, 80);
    if (raw.type === "dots") {
      const rows = asInt(raw.rows), cols = asInt(raw.cols);
      if (rows === null || cols === null || rows < 1 || rows > 8 || cols < 1 || cols > 8) return null;
      return { type: raw.type, rows, cols, newLastRowCol: !!raw.newLastRowCol, caption };
    }
    if (raw.type === "stairs") {
      const rows = asInt(raw.rows);
      return rows !== null && rows >= 1 && rows <= 8 ? { type: raw.type, rows, caption } : null;
    }
    if (raw.type === "square_layers" || raw.type === "square_steps") {
      const key = raw.type === "square_steps" ? "max" : "size";
      const size = asInt(raw[key]);
      if (size === null || size < 1 || size > 8) return null;
      const out = { type: raw.type, [key]: size, caption };
      const highlightRaw = raw.highlight == null ? (raw.type === "square_steps" ? size : "none") : raw.highlight;
      if (highlightRaw === "none" && raw.type === "square_layers") out.highlight = "none";
      else {
        const highlight = asInt(highlightRaw);
        if (highlight === null || highlight < 1 || highlight > size) return null;
        out.highlight = highlight;
      }
      return out;
    }
    if (raw.type === "square_compare") {
      const from = asInt(raw.from), to = asInt(raw.to);
      return from !== null && to !== null && from >= 1 && from < to && to <= 8
        ? { type: raw.type, from, to, caption } : null;
    }
    if (raw.type === "numberline") {
      const from = asInt(raw.from), to = asInt(raw.to);
      const rawMarks = raw.marks || [];
      if (from === null || to === null || from >= to || to - from > 30 || !Array.isArray(rawMarks) || rawMarks.length > 12) return null;
      const marks = [];
      for (const value of rawMarks) {
        const mark = asInt(value);
        if (mark === null || mark < from || mark > to) return null;
        if (!marks.includes(mark)) marks.push(mark);
      }
      return { type: raw.type, from, to, marks, caption };
    }
    if (raw.type === "bars") {
      if (!Array.isArray(raw.items) || raw.items.length < 1 || raw.items.length > 6) return null;
      const items = [];
      for (const row of raw.items) {
        const value = row && asInt(row.value);
        const label = row && text(row.label, 12);
        if (!row || value === null || value < 1 || value > 100 || !label) return null;
        items.push({ label, value });
      }
      return { type: raw.type, items, caption };
    }
    return null;
  }

  function normalizeV2(raw) {
    if (raw.kind === "layer_sum") {
      return normalizeLayerSum(
        { layers: raw.layers, item: raw.item },
        { action: "count", ask: raw.ask, prompt: "" },
        { reveal: raw.reveal || "items_without_total" }
      );
    }
    if (raw.kind === "path_count") {
      return normalizePathCount(
        { start: raw.start, target: raw.target, moves: raw.moves },
        { action: "enumerate", ask: raw.ask, prompt: "" },
        { reveal: raw.reveal || "rules_only" }
      );
    }
    return null;
  }

  B.normalize = function normalize(raw) {
    if (!raw || typeof raw !== "object") return null;
    if (asInt(raw.schema) === 2) return normalizeV2(raw);
    if (asInt(raw.schema) !== SCHEMA_VERSION || !raw.model || !raw.task || !raw.view) return null;
    if (raw.kind === "layer_sum") return normalizeLayerSum(raw.model, raw.task, raw.view);
    if (raw.kind === "path_count") return normalizePathCount(raw.model, raw.task, raw.view);
    if (raw.kind === "snap_grid") return normalizeSnapGrid(raw.model, raw.task, raw.view);
    if (raw.kind === "static_diagram") {
      const diagram = normalizeStaticDiagram(raw.model.diagram);
      const task = normalizeTask(raw.task, "observe", "notice");
      if (!diagram || !task || raw.view.reveal !== "model_only") return null;
      return { schema: SCHEMA_VERSION, kind: raw.kind, model: { diagram }, task, view: { reveal: "model_only" } };
    }
    if (raw.kind === "color_sequence") {
      const COLORS = ["red", "blue", "yellow", "green", "orange", "purple"];
      const unit = raw.model.unit;
      const count = asInt(raw.model.count);
      const item = text(raw.model.item, 4, "花");
      const task = normalizeTask(raw.task, "predict", "color_at_end");
      if (!Array.isArray(unit) || unit.length < 2 || unit.length > 4
        || count === null || count < 3 || count > 16 || count < unit.length
        || unit.some((color) => COLORS.indexOf(String(color)) < 0)
        || !item || !task
        || (raw.view.reveal !== "hide_last" && raw.view.reveal !== "all")) return null;
      return {
        schema: SCHEMA_VERSION,
        kind: raw.kind,
        model: { item, unit: unit.map(String), count },
        task,
        view: { reveal: raw.view.reveal },
      };
    }
    if (raw.kind === "geometry_compass") {
      const labels = raw.model.labels;
      const task = normalizeTask(raw.task, "construct", "compare_three_sides");
      if (raw.model.construction !== "equilateral_triangle"
        || !Array.isArray(labels) || labels.length !== 3
        || labels.some((label) => !text(label, 2))
        || new Set(labels.map(String)).size !== 3
        || !task || raw.view.reveal !== "stepwise") return null;
      return {
        schema: SCHEMA_VERSION,
        kind: raw.kind,
        model: { construction: "equilateral_triangle", labels: labels.map((label) => text(label, 2)) },
        task,
        view: { reveal: "stepwise" },
      };
    }
    return null;
  };

  B.createPathState = function createPathState(spec) {
    const board = B.normalize(spec);
    if (!board || board.kind !== "path_count") return null;
    const model = board.model;
    let current = model.start;
    let route = [];
    const found = [];

    function snapshot() {
      return {
        kind: "path_count",
        start: model.start,
        target: model.target,
        moves: model.moves.slice(),
        current,
        current_route: route.slice(),
        found_paths: found.map((path) => path.slice()),
      };
    }

    function move(step) {
      step = asInt(step);
      if (!model.moves.includes(step) || current + step > model.target) {
        return { changed: false, reached: false, snapshot: snapshot() };
      }
      current += step;
      route.push(step);
      let isNew = false;
      if (current === model.target) {
        const key = route.join(",");
        if (!found.some((path) => path.join(",") === key)) {
          found.push(route.slice());
          isNew = true;
        }
      }
      return { changed: true, reached: current === model.target, isNew, snapshot: snapshot() };
    }

    function resetRoute() {
      current = model.start;
      route = [];
      return snapshot();
    }

    return { move, resetRoute, snapshot };
  };

  B.formatSnapshot = function formatSnapshot(snapshot) {
    if (!snapshot || typeof snapshot !== "object") return "";
    if (snapshot.kind === "layer_sum") {
      const visible = snapshot.visible_layers || snapshot.layers || [];
      const side = snapshot.side || 0;
      const lines = [
        "（当前语义画板盘面，这不是孩子打的字）",
        "数学模型：layer_sum",
        "全部层：" + (snapshot.layers || []).join("、"),
        "孩子现在看见的层：" + (visible.join("、") || "还没有"),
      ];
      if (side) {
        lines.push("画板上是每边 " + side + " 块的正方形。新加上的一圈是 " + (snapshot.added || 0) + " 块。");
      } else {
        lines.push("画板没有显示合计答案。");
      }
      if (snapshot.remaining) lines.push("还没加上的层：" + snapshot.remaining.join("、") + "。先不要提这些层。");
      if (!snapshot.completed) lines.push("请让孩子点画板上的「加上下一层」，不要凭空让她在脑子里重排。");
      return lines.join("\n");
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
    if (snapshot.kind === "color_sequence") {
      return [
        "（当前语义画板盘面，这不是孩子打的字）",
        "数学模型：color_sequence",
        "可见颜色：" + ((snapshot.visible || []).join("、") || "还没有"),
        snapshot.hidden ? "最后一朵还没揭开，不要把答案颜色说出来。" : "整排颜色都已经看见了。",
      ].join("\n");
    }
    if (snapshot.kind === "geometry_compass") {
      return [
        "（当前语义画板盘面，这不是孩子打的字）",
        "数学模型：geometry_compass",
        "构造进度：" + snapshot.step + "/3",
        snapshot.completed ? "孩子已经画出两个圆和交点，正在比较三条边。" : "构造还没有完成。",
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
    if (spec.kind === "geometry_compass" && typeof B.mountGeometryCompass === "function") {
      return B.mountGeometryCompass(host, spec, options || {});
    }
    if (spec.kind === "color_sequence" && typeof B.mountColorSequence === "function") {
      return B.mountColorSequence(host, spec, options || {});
    }
    return null;
  };

  B.isBoardLike = function isBoardLike(raw) {
    return !!(raw && typeof raw === "object"
      && (Object.prototype.hasOwnProperty.call(raw, "schema")
        || Object.prototype.hasOwnProperty.call(raw, "kind")
        || Object.prototype.hasOwnProperty.call(raw, "type")));
  };

  root.XiaoouSemanticBoard = B;
  if (typeof module !== "undefined" && module.exports) module.exports = B;
})(typeof globalThis !== "undefined" ? globalThis : this);
