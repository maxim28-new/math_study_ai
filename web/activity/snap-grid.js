"use strict";

(function (root) {
  const A = root.XiaoouActivity || {};
  const BLUE = "#3f5bd6";
  const CELL_MIN = 44;
  const SNAP_RATIO = 0.55;

  function occupancySnapshot(spec, cells, trayCount) {
    let filled = 0;
    for (let r = 0; r < spec.rows; r++) {
      for (let c = 0; c < spec.cols; c++) {
        if (cells[r][c]) filled += 1;
      }
    }
    return A.makeSnapshot(spec, filled, trayCount);
  }

  function clonePlace(p) {
    if (!p) return { kind: "tray", index: 0 };
    if (p.kind === "cell") return { kind: "cell", r: p.r, c: p.c };
    return { kind: "tray", index: p.index || 0 };
  }

  function placesEqual(a, b) {
    if (!a || !b || a.kind !== b.kind) return false;
    if (a.kind === "cell") return a.r === b.r && a.c === b.c;
    return true;
  }

  A.mountSnapGrid = function mountSnapGrid(host, spec, options) {
    options = options || {};
    spec = spec || (host && host.getAttribute("data-spec")
      ? A.parseSnapGrid(decodeURIComponent(host.getAttribute("data-spec")))
      : null);
    const emptyHandle = {
      freeze() { if (host) host.classList.add("is-frozen"); },
      destroy() {},
      getSnapshot() { return spec ? A.makeSnapshot(spec, 0, spec.tray) : null; },
      getOccupancy() { return { occupied: [], trayLeft: spec ? spec.tray : 0 }; },
      undo() { return false; },
      canUndo() { return false; },
    };
    if (!spec || !host) return emptyHandle;
    if (typeof Konva === "undefined") {
      host.classList.add("is-frozen");
      return emptyHandle;
    }

    const interactive = !!options.interactive;
    const stageHost = host.querySelector(".snap-grid-stage") || host;
    const fallback = host.querySelector(".snap-grid-fallback");
    const width = Math.max(220, stageHost.clientWidth || host.clientWidth || 280);
    const gap = 6;
    const pad = 10;
    const cell = Math.max(
      CELL_MIN,
      Math.min(72, Math.floor((width - pad * 2 - gap * (spec.cols - 1)) / spec.cols))
    );
    const gridH = spec.rows * cell + (spec.rows - 1) * gap;
    const trayTop = pad + gridH + 18;
    const perRow = Math.max(1, Math.floor((width - pad * 2 + gap) / (cell + gap)));
    const trayRows = Math.max(1, Math.ceil(Math.max(spec.tray, 1) / perRow));
    const height = trayTop + trayRows * (cell + gap) + pad;

    stageHost.innerHTML = "";
    const stage = new Konva.Stage({ container: stageHost, width: width, height: height });
    const layer = new Konva.Layer();
    stage.add(layer);

    const cells = [];
    const cellRects = [];
    for (let r = 0; r < spec.rows; r++) {
      cells[r] = [];
      cellRects[r] = [];
      for (let c = 0; c < spec.cols; c++) {
        cells[r][c] = null;
        const x = pad + c * (cell + gap);
        const y = pad + r * (cell + gap);
        const rect = new Konva.Rect({
          x: x, y: y, width: cell, height: cell, cornerRadius: 10,
          fill: "#fff", stroke: "#c9c4b8", strokeWidth: 1.5,
        });
        layer.add(rect);
        cellRects[r][c] = { x: x, y: y };
      }
    }

    function trayPosition(index) {
      const c = index % perRow;
      const r = Math.floor(index / perRow);
      return { x: pad + c * (cell + gap), y: trayTop + r * (cell + gap) };
    }

    const tiles = [];
    const history = [];
    let trayCount = 0;

    function reindexTray() {
      const trayTiles = tiles.filter((t) => t.place.kind === "tray");
      trayTiles.forEach((t, i) => {
        t.place.index = i;
        t.group.position(trayPosition(i));
      });
      trayCount = trayTiles.length;
    }

    function nearestCell(x, y) {
      let best = null, bestD = Infinity;
      const cx = x + cell / 2, cy = y + cell / 2;
      for (let r = 0; r < spec.rows; r++) {
        for (let c = 0; c < spec.cols; c++) {
          const slot = cellRects[r][c];
          const sx = slot.x + cell / 2, sy = slot.y + cell / 2;
          const d = Math.hypot(cx - sx, cy - sy);
          if (d < bestD) { bestD = d; best = { r: r, c: c, d: d }; }
        }
      }
      if (best && best.d <= cell * SNAP_RATIO && !cells[best.r][best.c]) return best;
      return null;
    }

    let lastSnap = null;

    function readOccupancy() {
      const occupied = [];
      for (let r = 0; r < spec.rows; r++) {
        for (let c = 0; c < spec.cols; c++) {
          if (cells[r][c]) occupied.push({ r: r, c: c });
        }
      }
      return { occupied: occupied, trayLeft: trayCount };
    }

    function emitSettled() {
      const next = occupancySnapshot(spec, cells, trayCount);
      const eventName = A.detectMilestone(lastSnap, next);
      lastSnap = next;
      if (typeof options.onSettled === "function") options.onSettled(next, eventName);
    }

    function applyPlace(tile, place) {
      if (tile.place.kind === "cell") cells[tile.place.r][tile.place.c] = null;
      if (place && place.kind === "cell" && !cells[place.r][place.c]) {
        tile.place = { kind: "cell", r: place.r, c: place.c };
        cells[place.r][place.c] = tile;
        tile.group.position({ x: cellRects[place.r][place.c].x, y: cellRects[place.r][place.c].y });
      } else {
        tile.place = { kind: "tray", index: 0 };
      }
      reindexTray();
    }

    function settle(tile) {
      const from = clonePlace(tile.place);
      const pos = tile.group.position();
      if (tile.place.kind === "cell") cells[tile.place.r][tile.place.c] = null;
      const hit = nearestCell(pos.x, pos.y);
      if (hit) {
        tile.place = { kind: "cell", r: hit.r, c: hit.c };
        cells[hit.r][hit.c] = tile;
        tile.group.position({ x: cellRects[hit.r][hit.c].x, y: cellRects[hit.r][hit.c].y });
      } else {
        tile.place = { kind: "tray", index: 0 };
      }
      reindexTray();
      if (!placesEqual(from, clonePlace(tile.place))) history.push({ tile: tile, from: from });
      layer.draw();
      emitSettled();
    }

    const startOccupied = Array.isArray(options.occupied) ? options.occupied.slice() : [];
    let used = 0;
    for (let i = 0; i < spec.tray; i++) {
      const group = new Konva.Group({ x: 0, y: 0, draggable: interactive });
      group.add(new Konva.Rect({
        width: cell, height: cell, cornerRadius: 10, fill: BLUE,
        shadowColor: "rgba(0,0,0,0.18)", shadowBlur: 6, shadowOffsetY: 2,
      }));
      const tile = { group: group, place: { kind: "tray", index: i } };
      const slot = startOccupied[used];
      if (slot && slot.r >= 0 && slot.r < spec.rows && slot.c >= 0 && slot.c < spec.cols && !cells[slot.r][slot.c]) {
        tile.place = { kind: "cell", r: slot.r, c: slot.c };
        cells[slot.r][slot.c] = tile;
        group.position({ x: cellRects[slot.r][slot.c].x, y: cellRects[slot.r][slot.c].y });
        used += 1;
      }
      if (interactive) {
        group.on("dragstart", function () { group.moveToTop(); });
        group.on("dragend", function () { settle(tile); });
      }
      layer.add(group);
      tiles.push(tile);
    }
    reindexTray();
    lastSnap = occupancySnapshot(spec, cells, trayCount);
    layer.draw();

    host.classList.toggle("is-live", interactive);
    host.classList.toggle("is-frozen", !interactive);
    if (fallback) {
      if (interactive || tiles.length) fallback.setAttribute("hidden", "hidden");
    }

    function freeze() {
      tiles.forEach((t) => t.group.draggable(false));
      host.classList.add("is-frozen");
      host.classList.remove("is-live");
    }
    function destroy() {
      freeze();
      stage.destroy();
    }
    function getSnapshot() {
      return occupancySnapshot(spec, cells, trayCount);
    }
    function getOccupancy() {
      return readOccupancy();
    }
    function undo() {
      const step = history.pop();
      if (!step) return false;
      applyPlace(step.tile, step.from);
      layer.draw();
      emitSettled();
      return true;
    }
    function canUndo() {
      return history.length > 0;
    }

    return {
      freeze: freeze,
      destroy: destroy,
      getSnapshot: getSnapshot,
      getOccupancy: getOccupancy,
      undo: undo,
      canUndo: canUndo,
    };
  };

  root.XiaoouActivity = A;
  if (typeof module !== "undefined" && module.exports) module.exports = A;
})(typeof globalThis !== "undefined" ? globalThis : this);
