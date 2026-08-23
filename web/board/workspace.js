"use strict";

(function (root) {
  const MAX_TILES = 64;
  const MAX_SIDE = 8;

  function clip(value, limit) {
    return String(value == null ? "" : value).trim().slice(0, limit || 200);
  }

  function asInt(value) {
    if (typeof value === "boolean" || value === null || value === "") return null;
    const n = Number(value);
    return Number.isInteger(n) ? n : null;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function isOddSquareLayers(layers) {
    return Array.isArray(layers) && layers.length >= 2
      && layers.every((n, i) => n === 2 * i + 1);
  }

  function emptyVisibility() {
    return { hidden: [], emphasis: [], marked: [] };
  }

  function emptyChildModel() {
    return {
      accepted_claims: [],
      current_conjecture: "",
      last_misconception: "",
      focus_question: "",
    };
  }

  function newId(prefix) {
    const rand = Math.random().toString(16).slice(2, 10);
    return (prefix || "ws") + "_" + Date.now().toString(16) + rand;
  }

  function tilesOf(ws, placedOnly) {
    const hidden = new Set(((ws.visibility || {}).hidden || []));
    return (ws.objects || []).filter((obj) => {
      if (!obj || obj.type !== "tile" || hidden.has(obj.id)) return false;
      const attrs = obj.attrs || {};
      if (placedOnly && (asInt(attrs.gx) == null || asInt(attrs.gy) == null)) return false;
      return true;
    });
  }

  function tilePositions(tileObjs) {
    const positions = [];
    const seen = {};
    for (let i = 0; i < tileObjs.length; i += 1) {
      const attrs = tileObjs[i].attrs || {};
      const gx = asInt(attrs.gx);
      const gy = asInt(attrs.gy);
      if (gx == null || gy == null) return null;
      const key = gx + "," + gy;
      if (seen[key]) return null;
      seen[key] = true;
      positions.push([gx, gy]);
    }
    return positions;
  }

  function squareSide(tileObjs) {
    const positions = tilePositions(tileObjs);
    if (!positions) return null;
    const n = positions.length;
    if (n <= 0) return null;
    const side = Math.round(Math.sqrt(n));
    if (side * side !== n || side > MAX_SIDE) return null;
    const xs = positions.map((p) => p[0]);
    const ys = positions.map((p) => p[1]);
    const minX = Math.min.apply(null, xs);
    const maxX = Math.max.apply(null, xs);
    const minY = Math.min.apply(null, ys);
    const maxY = Math.max.apply(null, ys);
    if (maxX - minX !== side - 1 || maxY - minY !== side - 1) return null;
    const expected = {};
    for (let x = 0; x < side; x += 1) {
      for (let y = 0; y < side; y += 1) expected[(minX + x) + "," + (minY + y)] = true;
    }
    if (positions.some((p) => !expected[p[0] + "," + p[1]])) return null;
    return side;
  }

  function formsSquare(ws) {
    const pending = pendingTileIds(ws);
    const placed = tilesOf(ws, true);
    if (pending.length) {
      return {
        ok: false,
        type: "forms_square",
        tile_count: placed.length,
        side: 0,
        shape: "pending",
        pending: pending.length,
      };
    }
    const side = squareSide(placed);
    return {
      ok: side != null,
      type: "forms_square",
      tile_count: placed.length,
      side: side || 0,
      shape: side ? "square" : "other",
    };
  }

  function refreshSquare(ws) {
    const check = formsSquare(ws);
    const ids = tilesOf(ws, true).map((obj) => obj.id);
    ws.relations = (ws.relations || []).filter((rel) => !rel || rel.type !== "forms_square");
    if (check.ok) {
      ws.relations.push({
        id: "rel_forms_square",
        type: "forms_square",
        object_ids: ids,
        attrs: { side: check.side },
      });
    }
    return check;
  }

  function visibleSnapshot(ws) {
    const hidden = new Set(((ws.visibility || {}).hidden || []));
    const objects = (ws.objects || []).filter((obj) => obj && !hidden.has(obj.id));
    const check = formsSquare({ objects: objects, visibility: { hidden: [] } });
    return {
      id: ws.id,
      version: ws.version,
      representation: (ws.view || {}).representation || "tiles",
      objects: objects,
      visibility: ws.visibility || emptyVisibility(),
      view: ws.view || {},
      tile_count: objects.filter((obj) => obj.type === "tile").length,
      shape: check.shape,
      side: check.side,
      item: clip((ws.problem || {}).item, 8) || "块",
      marked: ((ws.visibility || {}).marked || []).filter((id) => !hidden.has(id)),
      emphasis: ((ws.visibility || {}).emphasis || []).filter((id) => !hidden.has(id)),
    };
    const occupancy = occupancyOf(ws);
    if (occupancy) {
      snapshot.occupancy = occupancy;
      snapshot.row_counts = occupancy.counts;
      snapshot.tray_left = occupancy.tray_left;
    }
    return snapshot;
  }

  function emptyOccupancy(rows, tray) {
    const n = Math.max(1, Math.min(8, parseInt(rows, 10) || 1));
    const left = Math.max(0, Math.min(64, parseInt(tray, 10) || 0));
    return { counts: Array(n).fill(0), tray_left: left, occupied: [] };
  }

  function occupancyOf(ws) {
    const raw = ws && ws.view && ws.view.occupancy;
    if (!raw || typeof raw !== "object") return null;
    const counts = (raw.counts || []).map((n) => Math.max(0, Math.min(8, parseInt(n, 10) || 0)));
    const occupied = [];
    (raw.occupied || []).forEach((item) => {
      if (!item || typeof item !== "object") return;
      const r = parseInt(item.r, 10);
      const c = parseInt(item.c, 10);
      if (isNaN(r) || isNaN(c)) return;
      occupied.push({ r: r, c: c });
    });
    let trayLeft = parseInt(raw.tray_left, 10);
    if (isNaN(trayLeft)) trayLeft = 0;
    return { counts: counts, tray_left: Math.max(0, trayLeft), occupied: occupied };
  }

  function occupiedFromCounts(rows, cols, counts) {
    const occupied = [];
    (counts || []).slice(0, rows).forEach((n, r) => {
      const take = Math.max(0, Math.min(cols, parseInt(n, 10) || 0));
      for (let c = 0; c < take; c += 1) occupied.push({ r: r, c: c });
    });
    return occupied;
  }

  function seedShell(wsId, topic, card, representation) {
    const board = (card && card.board) || {};
    const model = board.model || {};
    const views = Array.isArray(card && card.allowed_views)
      ? card.allowed_views.map((name) => clip(name, 32)).filter(Boolean)
      : [];
    if (representation && views.indexOf(representation) < 0) views.unshift(representation);
    return {
      id: wsId,
      version: 1,
      problem: {
        topic: topic || "",
        goal: clip(card && card.insight, 200),
        hook: clip(card && card.hook, 200),
        givens: [],
        board_kind: clip(board.kind, 32),
        item: clip(model.item, 8) || "块",
        first_question: clip(card && card.first_question, 200),
        allowed_layers: [],
        insight_key: clip(card && card.insight_key, 48),
        allowed_views: views,
      },
      objects: [],
      relations: [],
      claims: [],
      conjectures: [],
      visibility: emptyVisibility(),
      view: { representation: representation, camera: "fit" },
      child_model: emptyChildModel(),
    };
  }

  function seedFromCard(card, topic, workspaceId) {
    card = card || {};
    const board = card.board || {};
    const kind = clip(board.kind, 32);
    const model = board.model || {};
    const wsId = clip(workspaceId, 80) || newId("ws");
    if (kind === "layer_sum") {
      const layers = Array.isArray(model.layers) ? model.layers.map(asInt).filter((n) => n && n >= 1 && n <= 20) : [];
      const ws = seedShell(wsId, topic, card, "tiles");
      ws.problem.allowed_layers = layers;
      ws.problem.item = clip(model.item, 8) || "块";
      if (isOddSquareLayers(layers)) {
        ws.objects = [{ id: "tile_1", type: "tile", attrs: { gx: 0, gy: 0, layer: 1, pending: false } }];
        ws.visibility.marked = ["tile_1"];
        refreshSquare(ws);
        return ws;
      }
      const first = layers[0] || 1;
      const objects = [];
      for (let i = 0; i < first; i += 1) {
        objects.push({ id: "tile_" + (i + 1), type: "tile", attrs: { gx: i, gy: 0, layer: 1, pending: false } });
      }
      ws.objects = objects;
      ws.view.representation = "layer_pile";
      return ws;
    }
    if (kind === "geometry_compass") {
      const ws = seedShell(wsId, topic, card, "geometry_compass");
      const roles = ["compass", "center", "radius", "intersection", "segment", "equilateral"];
      const types = ["group", "point", "segment", "point", "segment", "group"];
      ws.objects = roles.map((role, i) => ({ id: role, type: types[i], attrs: { role: role } }));
      return ws;
    }
    if (kind === "color_sequence") {
      const ws = seedShell(wsId, topic, card, "color_sequence");
      ws.objects = [{ id: "pattern", type: "group", attrs: { role: "pattern" } }];
      ws.problem.sequence_unit = Array.isArray(model.unit) ? model.unit.map(String) : [];
      ws.problem.sequence_count = asInt(model.count);
      return ws;
    }
    if (kind === "path_count") {
      const ws = seedShell(wsId, topic, card, "path_count");
      ws.objects = [{ id: "path_board", type: "group", attrs: { role: "path" } }];
      ws.problem.path_model = {
        start: asInt(model.start),
        target: asInt(model.target),
        moves: Array.isArray(model.moves) ? model.moves.map(asInt).filter((n) => n) : [],
      };
      return ws;
    }
    if (kind === "snap_grid") {
      const ws = seedShell(wsId, topic, card, "snap_grid");
      const rows = asInt(model.rows) || 2;
      const cols = asInt(model.cols) || 8;
      const tray = asInt(model.tray) == null ? rows * cols : asInt(model.tray);
      ws.problem.grid_rows = rows;
      ws.problem.grid_cols = cols;
      ws.problem.grid_tray = tray;
      ws.problem.item = "蓝块";
      ws.view.occupancy = emptyOccupancy(rows, tray);
      ws.objects = [{ id: "grid", type: "group", attrs: { role: "snap_grid" } }];
      return ws;
    }
    const ws = seedShell(wsId, topic, card, kind || "static");
    ws.objects = [{ id: "figure", type: "group", attrs: { role: "figure" } }];
    return ws;
  }

  function matchesCard(ws, card) {
    if (!ws || !card) return false;
    const problem = ws.problem || {};
    const board = card.board || {};
    return clip(problem.hook, 200) === clip(card.hook, 200)
      && clip(problem.board_kind, 32) === clip(board.kind, 32);
  }

  function nextObjectId(ws, prefix) {
    const existing = {};
    (ws.objects || []).forEach((obj) => { if (obj && obj.id) existing[obj.id] = true; });
    let n = 1;
    while (existing[prefix + "_" + n]) n += 1;
    return prefix + "_" + n;
  }

  function pendingTileIds(ws) {
    return tilesOf(ws, false).filter((obj) => {
      const attrs = obj.attrs || {};
      return attrs.pending || asInt(attrs.gx) == null;
    }).map((obj) => obj.id);
  }

  function fail(error, extra) {
    return Object.assign({ ok: false, error: error }, extra || {});
  }

  function ok(ws, extra) {
    const snap = visibleSnapshot(ws);
    return Object.assign({
      ok: true,
      workspace: ws,
      workspace_version: ws.version,
      visible_snapshot: {
        tile_count: snap.tile_count,
        shape: snap.shape,
        side: snap.side,
        marked: snap.marked,
        representation: snap.representation,
      },
    }, extra || {});
  }

  function addTiles(ws, count) {
    count = asInt(count);
    if (count == null || count < 1 || count > 16) return fail("count_range");
    const current = tilesOf(ws, false);
    if (current.length + count > MAX_TILES) return fail("too_many_tiles");
    const placed = tilesOf(ws, true);
    const layer = (squareSide(placed) || 0) + 1;
    const created = [];
    for (let i = 0; i < count; i += 1) {
      const oid = nextObjectId(ws, "tile");
      ws.objects.push({ id: oid, type: "tile", attrs: { gx: null, gy: null, layer: layer, pending: true } });
      created.push(oid);
    }
    ws.visibility = ws.visibility || emptyVisibility();
    ws.visibility.marked = created;
    ws.version = (asInt(ws.version) || 0) + 1;
    return ok(ws, { created: created });
  }

  function place(ws, oid, gx, gy, layer) {
    const obj = (ws.objects || []).find((item) => item && item.id === oid);
    if (!obj) return;
    obj.attrs = obj.attrs || {};
    obj.attrs.gx = gx;
    obj.attrs.gy = gy;
    obj.attrs.layer = layer;
    obj.attrs.pending = false;
  }

  function arrangeOuterRing(ws, objectIds) {
    const ids = (objectIds && objectIds.length) ? objectIds.slice() : pendingTileIds(ws);
    if (!ids.length) return fail("no_tiles_to_arrange");
    const placed = tilesOf(ws, true).filter((obj) => ids.indexOf(obj.id) < 0);
    const side = squareSide(placed);
    if (side == null) return fail("outer_ring_needs_current_square");
    const needed = 2 * side + 1;
    if (ids.length !== needed) return fail("outer_ring_count", { needed: needed, got: ids.length });
    const allowed = ((ws.problem || {}).allowed_layers) || [];
    if (allowed.length && allowed.indexOf(needed) < 0) {
      return fail("layer_not_in_problem", { needed: needed, allowed: allowed });
    }
    const positions = [];
    for (let y = 0; y < side; y += 1) positions.push([side, y]);
    for (let x = 0; x < side + 1; x += 1) positions.push([x, side]);
    ids.forEach((oid, i) => place(ws, oid, positions[i][0], positions[i][1], side + 1));
    ws.visibility = ws.visibility || emptyVisibility();
    ws.visibility.marked = ids;
    refreshSquare(ws);
    ws.version = (asInt(ws.version) || 0) + 1;
    return ok(ws, { arranged: ids, layout: "outer_ring" });
  }

  function addNextOddRing(workspace) {
    const ws = clone(workspace);
    const placed = tilesOf(ws, true);
    const side = squareSide(placed);
    if (side == null) return fail("outer_ring_needs_current_square");
    const added = addTiles(ws, 2 * side + 1);
    if (!added.ok) return added;
    return arrangeOuterRing(ws);
  }

  function resetToSeed(workspace, card, topic) {
    const seeded = seedFromCard(card, topic, workspace && workspace.id);
    seeded.version = (asInt(workspace && workspace.version) || 1) + 1;
    return { ok: true, workspace: seeded };
  }

  function fromDict(raw) {
    if (!raw || typeof raw !== "object" || !raw.id || !Array.isArray(raw.objects)) return null;
    const version = asInt(raw.version);
    if (version == null || version < 1) return null;
    return clone(raw);
  }

  function formatNote(ws) {
    const snap = visibleSnapshot(ws || {});
    if (snap.representation === "tiles" || snap.representation === "layer_pile") {
      const lines = [
        "（当前数学工作区，这不是孩子打的字）",
        "可见积木：" + snap.tile_count + " " + snap.item,
        "形状：" + (snap.shape === "square" ? ("每边 " + snap.side + " 的正方形") : "还不是正方形"),
      ];
      return lines.join("\n");
    }
    if (snap.occupancy) {
      const counts = (snap.occupancy.counts || []).join("、");
      return [
        "（当前数学工作区，这不是孩子打的字）",
        "蓝格子各行已放：" + (counts || "0"),
        "托盘还剩：" + snap.occupancy.tray_left + " 块蓝块",
      ].join("\n");
    }
    return "";
  }

  function writeOccupancy(ws, occupancy) {
    if (!ws || !occupancy) return ws;
    ws.view = ws.view || {};
    ws.view.occupancy = occupancy;
    ws.version = (asInt(ws.version) || 0) + 1;
    return ws;
  }

  root.XiaoouMathWorkspace = {
    seedFromCard: seedFromCard,
    matchesCard: matchesCard,
    visibleSnapshot: visibleSnapshot,
    addNextOddRing: addNextOddRing,
    resetToSeed: resetToSeed,
    fromDict: fromDict,
    formatNote: formatNote,
    formsSquare: formsSquare,
    clone: clone,
    isOddSquareLayers: isOddSquareLayers,
    occupancyOf: occupancyOf,
    emptyOccupancy: emptyOccupancy,
    occupiedFromCounts: occupiedFromCounts,
    writeOccupancy: writeOccupancy,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
